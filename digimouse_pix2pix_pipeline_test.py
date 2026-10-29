#!/usr/bin/env python3
"""
Digimouse -> Pix2Pix PIPELINE TEST
==================================
Purpose : Validate the loader / split / training / metrics scaffolding on a
          single-animal dataset BEFORE the real longitudinal brain-tumor MRI
          datasets are locked. Results from this script are NOT scientific
          findings and must not appear in the practicum paper.

Task    : Same-timepoint modality translation (NOT forecasting).
          --pair ct    : CT    -> cryosection
          --pair pet   : PET   -> cryosection
          --pair atlas : Atlas -> cryosection (22-channel one-hot input)

Data    : Digimouse_Cryosection (CC BY-SA 4.0). Four co-registered Analyze 7.5
          volumes, 380 x 992 x 208 voxels, uint8, 0.1 mm isotropic.
          Slice k of a volume is a 992 (rows) x 380 (cols) image.

Split   : CONTIGUOUS slice blocks with a gap (default 5 slices) between
          train / val / test, because adjacent slices are near-duplicates.
          Random splitting would leak and is deliberately not offered.

Baselines (all fitted on the TRAIN block only):
          global_mean  : one constant intensity
          mean_image   : per-pixel mean cryo image of the train block
          linear_fit   : y = a*x + b on intensity (ct / pet)
          label_lut    : mean cryo intensity per atlas label (atlas)

Metrics : L1 (whole crop), L1 (body mask = atlas > 0; PRIMARY: used for model
          selection, verdict and win rates), PSNR, SSIM, all on
          [0, 1] intensity scale, reported as mean +/- SD over test slices.

Outputs : <out>/config.json, split.json, loss_history.csv,
          checkpoints/{best,last}_G.pt, metrics_test.json,
          metrics_test_per_slice.csv, results_summary.md, samples/*.png

Dependencies: torch, numpy, scikit-image, Pillow  (pip install torch numpy scikit-image pillow)

Examples
--------
  # 2-epoch end-to-end check (a few minutes on CPU):
  python digimouse_pix2pix_pipeline_test.py --data-root Digimouse_Cryosection.zip --smoke

  # Standard run (CT -> cryo, brain-centered 256x256 crop, 40 epochs):
  python digimouse_pix2pix_pipeline_test.py --data-root Digimouse_Cryosection.zip --pair ct

  # L1-only ablation (no discriminator):
  python digimouse_pix2pix_pipeline_test.py --data-root Digimouse_Cryosection.zip --pair ct --no-gan --out runs/ct_l1only

  # Atlas -> cryo, full-body view:
  python digimouse_pix2pix_pipeline_test.py --data-root Digimouse_Cryosection.zip --pair atlas --roi body
"""

import argparse
import csv
import json
import random
import struct
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from skimage.metrics import structural_similarity
from skimage.transform import resize
from torch.utils.data import DataLoader, Dataset

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
DIMS_XYZ = (380, 992, 208)           # header order: x, y, z
N_Z, H, W = 208, 992, 380            # numpy order after reshape: (z, y, x)
N_LABELS = 22                        # atlas labels 0..21
BRAIN_LABELS = (4, 5, 6, 7, 8, 10)   # medulla, cerebellum, olfactory bulbs, external cerebrum, striatum, rest of brain
BODY_SIZE = (512, 192)               # (rows, cols) for --roi body; divisible by 64

VOLUME_STEMS = {
    "atlas": "atlas/atlas/atlas_380x992x208",
    "ct": "ct_data/ct_data/ct_380x992x208",
    "pet": "pet_data/pet_data/pet_380x992x208",
    "cryo": "cryo_data/cryo_data/cryostat_380x992x208",
}


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pick_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Data location and loading
# --------------------------------------------------------------------------- #
def resolve_root(data_root: str, extract_dir: Path) -> Path:
    """Accept the .zip, the unzipped folder, or any parent of it. Return the folder
    that contains atlas/, ct_data/, pet_data/, cryo_data/."""
    p = Path(data_root).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"--data-root not found: {p}")
    if p.is_file() and p.suffix.lower() == ".zip":
        marker = extract_dir / ".extracted_ok"
        if not marker.exists():
            log(f"Extracting {p.name} -> {extract_dir} (one-time, ~350 MB)")
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(p) as zf:
                zf.extractall(extract_dir)
            marker.touch()
        p = extract_dir
    hits = list(p.rglob("cryostat_380x992x208.img"))
    if not hits:
        raise FileNotFoundError(f"cryostat_380x992x208.img not found under {p}")
    return hits[0].parents[2]  # .../<root>/cryo_data/cryo_data/<file>


def check_header(hdr_path: Path) -> None:
    b = hdr_path.read_bytes()
    if len(b) < 348:
        raise ValueError(f"{hdr_path.name}: header shorter than 348 bytes")
    endian = "<" if struct.unpack("<i", b[:4])[0] == 348 else ">"
    dim = struct.unpack(endian + "8h", b[40:56])
    datatype = struct.unpack(endian + "h", b[70:72])[0]
    if tuple(dim[1:4]) != DIMS_XYZ:
        raise ValueError(f"{hdr_path.name}: dims {dim[1:4]} != expected {DIMS_XYZ}")
    if datatype != 2:  # 2 = unsigned char
        raise ValueError(f"{hdr_path.name}: datatype {datatype} != 2 (uint8)")


def read_volume(root: Path, key: str) -> np.ndarray:
    stem = root / VOLUME_STEMS[key]
    check_header(stem.with_suffix(".hdr"))
    img = stem.with_suffix(".img")
    expected = N_Z * H * W
    if img.stat().st_size != expected:
        raise ValueError(f"{img.name}: {img.stat().st_size} bytes, expected {expected}")
    return np.fromfile(img, dtype=np.uint8).reshape(N_Z, H, W)  # (z, y, x)


def resize_stack(arr: np.ndarray, shape: tuple, order: int) -> np.ndarray:
    out = np.empty((arr.shape[0],) + shape, dtype=np.uint8)
    for i in range(arr.shape[0]):
        r = resize(arr[i].astype(np.float32), shape, order=order,
                   anti_aliasing=(order > 0), preserve_range=True)
        out[i] = np.clip(np.rint(r), 0, 255).astype(np.uint8)
    return out


def build_arrays(root: Path, pair: str, roi: str, crop: int, min_body_frac: float):
    """Return src (n,h,w) uint8, tgt (n,h,w) uint8, body_mask (n,h,w) bool, z_idx (n,), geometry dict.
    Slices whose ROI contains < min_body_frac body pixels (atlas > 0) are dropped, so the
    train/val/test blocks never consist of empty background."""
    src = read_volume(root, pair)
    tgt = read_volume(root, "cryo")
    atlas = read_volume(root, "atlas")

    if roi == "brain":
        brain = np.isin(atlas, BRAIN_LABELS)
        ys = np.where(brain.any(axis=(0, 2)))[0]
        xs = np.where(brain.any(axis=(0, 1)))[0]
        cy, cx = (ys.min() + ys.max()) // 2, (xs.min() + xs.max()) // 2
        y0 = int(np.clip(cy - crop // 2, 0, H - crop))
        x0 = int(np.clip(cx - crop // 2, 0, W - crop))
        sl = (slice(None), slice(y0, y0 + crop), slice(x0, x0 + crop))
        src, tgt, atlas = src[sl], tgt[sl], atlas[sl]
        geom = {"roi": "brain", "crop": crop, "y0": y0, "x0": x0,
                "brain_y_range": [int(ys.min()), int(ys.max())],
                "brain_x_range": [int(xs.min()), int(xs.max())]}
    elif roi == "body":
        src_order = 0 if pair == "atlas" else 1
        src = resize_stack(src, BODY_SIZE, src_order)
        tgt = resize_stack(tgt, BODY_SIZE, 1)
        atlas = resize_stack(atlas, BODY_SIZE, 0)
        geom = {"roi": "body", "size": list(BODY_SIZE)}
    else:
        raise ValueError(f"unknown roi {roi}")

    body_mask = atlas > 0
    frac = body_mask.mean(axis=(1, 2))
    keep = np.where(frac >= min_body_frac)[0]
    if len(keep) < 40:
        raise ValueError(f"only {len(keep)} slices have >= {min_body_frac:.0%} body coverage in this ROI")
    if len(keep) != keep.max() - keep.min() + 1:
        raise ValueError("body-bearing slices are not contiguous; contiguous splitting would be invalid")
    geom["z_kept"] = [int(keep.min()), int(keep.max())]
    geom["n_dropped_background_slices"] = int(N_Z - len(keep))
    geom["min_body_frac"] = min_body_frac
    return (np.ascontiguousarray(src[keep]), np.ascontiguousarray(tgt[keep]),
            np.ascontiguousarray(body_mask[keep]), keep, geom)


# --------------------------------------------------------------------------- #
# Contiguous split
# --------------------------------------------------------------------------- #
def contiguous_split(n: int, train_frac: float, val_frac: float, gap: int):
    n_tr = int(round(n * train_frac))
    n_va = int(round(n * val_frac))
    tr = np.arange(0, n_tr)
    va = np.arange(n_tr + gap, n_tr + gap + n_va)
    te = np.arange(n_tr + gap + n_va + gap, n)
    if len(te) < 5 or len(va) < 5:
        raise ValueError(f"split too small (val={len(va)}, test={len(te)}); adjust fractions or gap")
    # leakage guards
    assert tr.max() + gap < va.min() and va.max() + gap < te.min()
    assert not (set(tr) & set(va)) and not (set(va) & set(te)) and not (set(tr) & set(te))
    return tr, va, te


# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #
class SliceDataset(Dataset):
    def __init__(self, src, tgt, mask, idx, onehot: bool, augment: bool):
        self.src, self.tgt, self.mask = src, tgt, mask
        self.idx = np.asarray(idx)
        self.onehot, self.augment = onehot, augment

    def __len__(self):
        return len(self.idx)

    def __getitem__(self, i):
        j = int(self.idx[i])
        s = torch.from_numpy(self.src[j])
        t = torch.from_numpy(self.tgt[j]).float().div(127.5).sub(1.0).unsqueeze(0)
        m = torch.from_numpy(self.mask[j]).float().unsqueeze(0)
        if self.onehot:
            s = F.one_hot(s.long(), N_LABELS).permute(2, 0, 1).float()
        else:
            s = s.float().div(127.5).sub(1.0).unsqueeze(0)
        if self.augment:
            if random.random() < 0.5:
                s, t, m = s.flip(-1), t.flip(-1), m.flip(-1)
            if random.random() < 0.5:
                s, t, m = s.flip(-2), t.flip(-2), m.flip(-2)
        return s, t, m


# --------------------------------------------------------------------------- #
# Pix2Pix networks
# --------------------------------------------------------------------------- #
def norm_layer(kind: str, ch: int) -> nn.Module:
    return nn.InstanceNorm2d(ch, affine=True) if kind == "instance" else nn.BatchNorm2d(ch)


class UNetGenerator(nn.Module):
    """U-Net with skip connections. Spatial size must be divisible by 2**n_down."""

    def __init__(self, in_ch, out_ch=1, ngf=32, n_down=6, norm="instance", dropout=0.5):
        super().__init__()
        chs = [min(ngf * 2 ** i, ngf * 8) for i in range(n_down)]
        self.downs = nn.ModuleList()
        prev = in_ch
        for i, c in enumerate(chs):
            layers = [nn.Conv2d(prev, c, 4, 2, 1, bias=not (0 < i < n_down - 1))]
            if 0 < i < n_down - 1:
                layers.append(norm_layer(norm, c))
            layers.append(nn.LeakyReLU(0.2, inplace=True))
            self.downs.append(nn.Sequential(*layers))
            prev = c
        self.ups = nn.ModuleList()
        for i in range(n_down - 1, -1, -1):
            cin = chs[i] if i == n_down - 1 else chs[i] * 2
            cout = out_ch if i == 0 else chs[i - 1]
            if i == 0:
                block = nn.Sequential(nn.ConvTranspose2d(cin, cout, 4, 2, 1), nn.Tanh())
            else:
                layers = [nn.ConvTranspose2d(cin, cout, 4, 2, 1, bias=False), norm_layer(norm, cout)]
                if (n_down - 1 - i) < 3:
                    layers.append(nn.Dropout(dropout))
                layers.append(nn.ReLU(inplace=True))
                block = nn.Sequential(*layers)
            self.ups.append(block)

    def forward(self, x):
        skips = []
        h = x
        for d in self.downs:
            h = d(h)
            skips.append(h)
        h = skips.pop()  # bottleneck
        for k, u in enumerate(self.ups):
            h = u(h) if k == 0 else u(torch.cat([h, skips.pop()], dim=1))
        return h


class PatchDiscriminator(nn.Module):
    """Conditional 70x70-style PatchGAN: input is concat(source, target-or-fake)."""

    def __init__(self, in_ch, ndf=32, n_layers=3, norm="instance"):
        super().__init__()
        layers = [nn.Conv2d(in_ch, ndf, 4, 2, 1), nn.LeakyReLU(0.2, inplace=True)]
        mult = 1
        for n in range(1, n_layers):
            prev, mult = mult, min(2 ** n, 8)
            layers += [nn.Conv2d(ndf * prev, ndf * mult, 4, 2, 1, bias=False),
                       norm_layer(norm, ndf * mult), nn.LeakyReLU(0.2, inplace=True)]
        prev, mult = mult, min(2 ** n_layers, 8)
        layers += [nn.Conv2d(ndf * prev, ndf * mult, 4, 1, 1, bias=False),
                   norm_layer(norm, ndf * mult), nn.LeakyReLU(0.2, inplace=True),
                   nn.Conv2d(ndf * mult, 1, 4, 1, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def init_weights(m: nn.Module) -> None:
    if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
        nn.init.normal_(m.weight, 0.0, 0.02)
        if m.bias is not None:
            nn.init.zeros_(m.bias)
    elif isinstance(m, (nn.BatchNorm2d, nn.InstanceNorm2d)) and m.weight is not None:
        nn.init.normal_(m.weight, 1.0, 0.02)
        nn.init.zeros_(m.bias)


# --------------------------------------------------------------------------- #
# Prediction and metrics
# --------------------------------------------------------------------------- #
@torch.no_grad()
def predict(G, src, tgt, mask, idx, onehot, device, batch) -> np.ndarray:
    G.eval()
    ds = SliceDataset(src, tgt, mask, idx, onehot, augment=False)
    out = []
    for s, _, _ in DataLoader(ds, batch_size=batch, shuffle=False):
        o = G(s.to(device))
        out.append(((o + 1.0) / 2.0).clamp(0, 1).cpu().numpy()[:, 0])
    return np.concatenate(out).astype(np.float32)


def slice_metrics(pred: np.ndarray, tgt01: np.ndarray, mask: np.ndarray) -> list:
    rows = []
    for p, t, m in zip(pred, tgt01, mask):
        err = np.abs(p - t)
        mse = float(np.mean((p - t) ** 2))
        rows.append({
            "l1": float(err.mean()),
            "l1_body": float(err[m].mean()) if m.any() else float("nan"),
            "psnr": float(10.0 * np.log10(1.0 / max(mse, 1e-12))),
            "ssim": float(structural_similarity(t, p, data_range=1.0)),
        })
    return rows


def aggregate(rows: list) -> dict:
    out = {}
    for k in ("l1", "l1_body", "psnr", "ssim"):
        v = np.array([r[k] for r in rows], dtype=np.float64)
        out[k] = {"mean": float(np.nanmean(v)), "sd": float(np.nanstd(v, ddof=1)) if len(v) > 1 else 0.0}
    return out


def fit_baselines(src, tgt, tr, te, pair):
    """Fit on TRAIN slices only; return dict name -> prediction array for TEST slices ([0,1])."""
    t_tr = tgt[tr].astype(np.float32) / 255.0
    n_te, h, w = len(te), tgt.shape[1], tgt.shape[2]
    preds = {
        "global_mean": np.full((n_te, h, w), float(t_tr.mean()), dtype=np.float32),
        "mean_image": np.broadcast_to(t_tr.mean(axis=0), (n_te, h, w)).astype(np.float32),
    }
    if pair == "atlas":
        lut = np.full(N_LABELS, float(t_tr.mean()), dtype=np.float32)
        s_tr = src[tr]
        for lab in range(N_LABELS):
            sel = s_tr == lab
            if sel.any():
                lut[lab] = float(t_tr[sel].mean())
        preds["label_lut"] = lut[src[te]].astype(np.float32)
    else:
        x = (src[tr].astype(np.float64) / 255.0).ravel()
        y = t_tr.astype(np.float64).ravel()
        xm, ym = x.mean(), y.mean()
        var = ((x - xm) ** 2).mean()
        a = ((x - xm) * (y - ym)).mean() / var if var > 0 else 0.0
        b = ym - a * xm
        preds["linear_fit"] = np.clip(a * (src[te].astype(np.float32) / 255.0) + b, 0, 1).astype(np.float32)
    return preds


# --------------------------------------------------------------------------- #
# Visual samples
# --------------------------------------------------------------------------- #
def input_to_u8(src_slice: np.ndarray, pair: str) -> np.ndarray:
    if pair == "atlas":
        return (src_slice.astype(np.float32) * (255.0 / (N_LABELS - 1))).astype(np.uint8)
    return src_slice


def save_sample_grid(path: Path, src_s, pred, tgt01, base_pred, pair):
    u8 = lambda a: np.clip(a * 255.0, 0, 255).astype(np.uint8)
    err = np.clip(np.abs(pred - tgt01) * 4.0, 0, 1)  # error amplified 4x for visibility
    panels = [input_to_u8(src_s, pair), u8(pred), u8(tgt01), u8(base_pred), u8(err)]
    Image.fromarray(np.hstack(panels)).save(path)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args():
    ap = argparse.ArgumentParser(description="Digimouse Pix2Pix pipeline test")
    ap.add_argument("--data-root", required=True, help="Digimouse_Cryosection.zip, or the unzipped folder")
    ap.add_argument("--out", default="digimouse_p2p_run")
    ap.add_argument("--extract-dir", default="_digimouse_extracted")
    ap.add_argument("--pair", choices=["ct", "pet", "atlas"], default="ct")
    ap.add_argument("--roi", choices=["brain", "body"], default="brain")
    ap.add_argument("--crop", type=int, default=256, help="brain ROI crop size (divisible by 2**n_down)")
    ap.add_argument("--min-body-frac", type=float, default=0.05,
                    help="drop slices whose ROI has < this fraction of body pixels (empty background)")
    ap.add_argument("--train-frac", type=float, default=0.67)
    ap.add_argument("--val-frac", type=float, default=0.165)
    ap.add_argument("--gap", type=int, default=5, help="slices discarded between blocks")
    ap.add_argument("--max-train", type=int, default=0, help="truncate train block (0 = all)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lambda-l1", type=float, default=100.0)
    ap.add_argument("--ngf", type=int, default=32, help="generator base width (reduced capacity default)")
    ap.add_argument("--ndf", type=int, default=32)
    ap.add_argument("--n-down", type=int, default=6)
    ap.add_argument("--norm", choices=["instance", "batch"], default="instance")
    ap.add_argument("--no-gan", action="store_true", help="L1-only generator training (ablation)")
    ap.add_argument("--no-augment", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda | mps")
    ap.add_argument("--num-workers", type=int, default=0)
    ap.add_argument("--smoke", action="store_true", help="2 epochs, 16 train slices, batch 4")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.smoke:
        args.epochs, args.max_train, args.batch = 2, 16, 4

    out = Path(args.out)
    (out / "checkpoints").mkdir(parents=True, exist_ok=True)
    (out / "samples").mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)
    device = pick_device(args.device)
    log(f"Device: {device} | torch {torch.__version__}")

    # ---- data ------------------------------------------------------------ #
    root = resolve_root(args.data_root, Path(args.extract_dir))
    log(f"Data root: {root}")
    src, tgt, mask, z_idx, geom = build_arrays(root, args.pair, args.roi, args.crop, args.min_body_frac)
    n, h, w = tgt.shape
    div = 2 ** args.n_down
    if h % div or w % div:
        raise ValueError(f"Image {h}x{w} not divisible by 2**n_down = {div}")
    onehot = args.pair == "atlas"
    in_ch = N_LABELS if onehot else 1
    log(f"Pair {args.pair} -> cryo | ROI {geom} | slices kept {n} | image {h}x{w}")

    tr, va, te = contiguous_split(n, args.train_frac, args.val_frac, args.gap)
    if args.max_train and args.max_train < len(tr):
        tr = tr[:args.max_train]
    log(f"Split (original z index): train {z_idx[tr[0]]}-{z_idx[tr[-1]]} (n={len(tr)}) | "
        f"val {z_idx[va[0]]}-{z_idx[va[-1]]} (n={len(va)}) | test {z_idx[te[0]]}-{z_idx[te[-1]]} (n={len(te)}) | gap {args.gap}")

    cfg = {**vars(args), "geometry": geom, "device": str(device), "n_slices": int(n),
           "image_hw": [int(h), int(w)], "torch": str(torch.__version__)}
    (out / "config.json").write_text(json.dumps(cfg, indent=2))
    (out / "split.json").write_text(json.dumps(
        {"gap": args.gap,
         "train_positions": tr.tolist(), "val_positions": va.tolist(), "test_positions": te.tolist(),
         "train_z": z_idx[tr].tolist(), "val_z": z_idx[va].tolist(), "test_z": z_idx[te].tolist()}, indent=2))

    train_ds = SliceDataset(src, tgt, mask, tr, onehot, augment=not args.no_augment)
    drop_last = args.norm == "batch" and len(train_ds) > args.batch
    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                              num_workers=args.num_workers, drop_last=drop_last)

    # ---- models ---------------------------------------------------------- #
    G = UNetGenerator(in_ch, 1, args.ngf, args.n_down, args.norm).to(device)
    G.apply(init_weights)
    use_gan = not args.no_gan
    if use_gan:
        D = PatchDiscriminator(in_ch + 1, args.ndf, 3, args.norm).to(device)
        D.apply(init_weights)
        opt_D = torch.optim.Adam(D.parameters(), lr=args.lr, betas=(0.5, 0.999))
    opt_G = torch.optim.Adam(G.parameters(), lr=args.lr, betas=(0.5, 0.999))
    bce = nn.BCEWithLogitsLoss()
    n_params = sum(p.numel() for p in G.parameters())
    log(f"Generator params: {n_params / 1e6:.2f} M | GAN loss: {use_gan} | lambda_L1: {args.lambda_l1}")

    tgt01_val = tgt[va].astype(np.float32) / 255.0
    mask_val = mask[va]

    # ---- training -------------------------------------------------------- #
    best_val, best_epoch = float("inf"), -1
    history = []
    t_start = time.time()
    for epoch in range(1, args.epochs + 1):
        G.train()
        if use_gan:
            D.train()
        t0 = time.time()
        acc = {"d": 0.0, "g_gan": 0.0, "g_l1": 0.0, "n": 0}
        for s, t, _ in train_loader:
            s, t = s.to(device), t.to(device)
            fake = G(s)

            loss_d = torch.zeros(())
            loss_gan = torch.zeros(())
            if use_gan:
                opt_D.zero_grad(set_to_none=True)
                pr = D(torch.cat([s, t], 1))
                pf = D(torch.cat([s, fake.detach()], 1))
                loss_d = 0.5 * (bce(pr, torch.ones_like(pr)) + bce(pf, torch.zeros_like(pf)))
                loss_d.backward()
                opt_D.step()

            opt_G.zero_grad(set_to_none=True)
            loss_l1 = F.l1_loss(fake, t)
            if use_gan:
                pf = D(torch.cat([s, fake], 1))
                loss_gan = bce(pf, torch.ones_like(pf))
                loss_g = loss_gan + args.lambda_l1 * loss_l1
            else:
                loss_g = loss_l1
            loss_g.backward()
            opt_G.step()

            b = s.size(0)
            acc["d"] += float(loss_d.detach()) * b
            acc["g_gan"] += float(loss_gan.detach()) * b
            acc["g_l1"] += float(loss_l1.detach()) * b
            acc["n"] += b

        # validation (body-masked L1 on [0,1] scale; model selection criterion)
        pv = predict(G, src, tgt, mask, va, onehot, device, args.batch)
        val_l1 = float(np.abs(pv - tgt01_val)[mask_val].mean())  # body-masked L1 = model-selection criterion
        row = {"epoch": epoch, "loss_D": acc["d"] / acc["n"], "loss_G_gan": acc["g_gan"] / acc["n"],
               "loss_G_l1_scaled": acc["g_l1"] / acc["n"] / 2.0,  # [-1,1] -> [0,1] scale
               "val_l1": val_l1, "seconds": time.time() - t0}
        history.append(row)
        flag = ""
        if val_l1 < best_val:
            best_val, best_epoch = val_l1, epoch
            torch.save({"G": G.state_dict(), "epoch": epoch, "val_l1": val_l1, "config": cfg},
                       out / "checkpoints" / "best_G.pt")
            flag = " *best*"
        log(f"Epoch {epoch:3d}/{args.epochs} | D {row['loss_D']:.3f} | G_gan {row['loss_G_gan']:.3f} | "
            f"train L1 {row['loss_G_l1_scaled']:.4f} | val L1(body) {val_l1:.4f} | {row['seconds']:.1f}s{flag}")

    torch.save({"G": G.state_dict(), "epoch": args.epochs, "config": cfg}, out / "checkpoints" / "last_G.pt")
    with open(out / "loss_history.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        wr.writeheader()
        wr.writerows(history)
    log(f"Training done in {(time.time() - t_start) / 60:.1f} min | best val L1(body) {best_val:.4f} @ epoch {best_epoch}")

    # ---- test evaluation (best-val checkpoint) ---------------------------- #
    ckpt = torch.load(out / "checkpoints" / "best_G.pt", map_location=device, weights_only=False)
    G.load_state_dict(ckpt["G"])
    tgt01_te = tgt[te].astype(np.float32) / 255.0
    pred_te = predict(G, src, tgt, mask, te, onehot, device, args.batch)

    models = {"pix2pix": pred_te}
    models.update(fit_baselines(src, tgt, tr, te, args.pair))
    per_slice = {name: slice_metrics(p, tgt01_te, mask[te]) for name, p in models.items()}
    summary = {name: aggregate(rows) for name, rows in per_slice.items()}

    base_names = [k for k in models if k != "pix2pix"]
    best_base = min(base_names, key=lambda k: summary[k]["l1_body"]["mean"])
    wins = {k: float(np.mean([a["l1_body"] < b["l1_body"] for a, b in zip(per_slice["pix2pix"], per_slice[k])]))
            for k in base_names}
    verdict = (f"Pix2Pix beats the best baseline ({best_base}) on body-masked L1"
               if summary["pix2pix"]["l1_body"]["mean"] < summary[best_base]["l1_body"]["mean"]
               else f"Pix2Pix does NOT beat the best baseline ({best_base}) on body-masked L1")

    result = {"summary": summary, "best_baseline": best_base, "l1_win_rate_vs_baseline": wins,
              "verdict": verdict, "n_test_slices": int(len(te)), "best_epoch": best_epoch,
              "caveat": "Pipeline test on n=1 animal. Adjacent slices are correlated; SDs are across slices, not animals."}
    (out / "metrics_test.json").write_text(json.dumps(result, indent=2))

    with open(out / "metrics_test_per_slice.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["model", "test_slice_z", "l1", "l1_body", "psnr", "ssim"])
        for name, rows in per_slice.items():
            for pos, r in zip(z_idx[te], rows):
                wr.writerow([name, int(pos), r["l1"], r["l1_body"], r["psnr"], r["ssim"]])

    # markdown summary (Notion-pasteable)
    fmt = lambda d: f"{d['mean']:.4f} ± {d['sd']:.4f}"
    fmtp = lambda d: f"{d['mean']:.2f} ± {d['sd']:.2f}"
    lines = [f"# Digimouse Pix2Pix pipeline test: {args.pair} -> cryo ({args.roi} ROI)",
             "",
             f"- Test slices: {len(te)} | train: {len(tr)} | val: {len(va)} | gap: {args.gap}",
             f"- Epochs: {args.epochs} | best val epoch: {best_epoch} | GAN: {use_gan} | seed: {args.seed}",
             f"- Verdict: {verdict}",
             "",
             "| Model | L1 | L1 (body) | PSNR (dB) | SSIM |",
             "|---|---|---|---|---|"]
    for name in ["pix2pix"] + base_names:
        s = summary[name]
        lines.append(f"| {name} | {fmt(s['l1'])} | {fmt(s['l1_body'])} | {fmtp(s['psnr'])} | {fmt(s['ssim'])} |")
    lines += ["", "| Baseline | Pix2Pix per-slice body-L1 win rate |", "|---|---|"]
    lines += [f"| {k} | {wins[k] * 100:.0f}% |" for k in base_names]
    lines += ["", "Caveat: n = 1 animal; neighboring slices are correlated; results validate the pipeline only."]
    (out / "results_summary.md").write_text("\n".join(lines))

    # sample images: 3 evenly spaced test slices, best baseline as 4th panel
    for k in np.linspace(0, len(te) - 1, 3).astype(int):
        save_sample_grid(out / "samples" / f"test_slice_z{int(z_idx[te[k]]):03d}.png",
                         src[te[k]], pred_te[k], tgt01_te[k], models[best_base][k], args.pair)

    print("\n" + "\n".join(lines))
    log(f"All outputs in: {out.resolve()}")
    log("Sample panel order (left to right): input | Pix2Pix | target | best baseline | |error| x4")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # surface a clean message for VS Code terminal use
        print(f"\nERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
