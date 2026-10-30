#!/usr/bin/env python3
"""Figures for fold 3 (post-hoc, unlocked). Run from the repo root. Writes only to outputs/figures_fold3/. CPU inference, eval mode, no eval script."""
import csv, hashlib, json, shutil, sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from skimage.metrics import structural_similarity as ssim
sys.path.insert(0, ".")
from models import networks
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.set_num_threads(2)
cfg = json.load(open("configs/nextbrain_fold3_he.json")); root = Path("~/Data/NextBrain").expanduser(); N = cfg["image_size"]; TARGET = cfg["target"]
excl = set(cfg["exclude_blocks"]); od = Path("outputs/nextbrain_fold3_he"); OUT = Path("outputs/figures_fold3")
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(cfg["metadata"]))}
flagged = lambda r: f"{r['subject']}/{r['block']}" in excl
R = json.load(open(od / "results.json")); BL = json.load(open(od / "baseline_per_slice.json"))
ids = R["per_slice_ids"]; assert ids == BL["per_slice_ids"]; n = len(ids); assert n == 1045


def load(rid):   # same as load() in eval_nextbrain_test.py
    m = meta[rid]; cd = root / f"Case{m['case_number']}"
    he = Image.open(cd / m[f"path_{TARGET}"]).convert("RGB"); mri = Image.open(cd / m["path_MRI"]).convert("L").resize(he.size, Image.BILINEAR)
    s = N / max(he.size); nw, nh = round(he.size[0] * s), round(he.size[1] * s); y0, x0 = (N - nh) // 2, (N - nw) // 2
    A = np.zeros((N, N), np.uint8); B = np.zeros((N, N, 3), np.uint8)
    A[y0:y0 + nh, x0:x0 + nw] = np.asarray(mri.resize((nw, nh), Image.BILINEAR)); B[y0:y0 + nh, x0:x0 + nw] = np.asarray(he.resize((nw, nh), Image.BILINEAR))
    return A, B


# LUT fit: copy of the fitting code in baseline_per_slice_fold3.py (training records minus flagged blocks)
sp = json.load(open(cfg["splits"])); tr = [r["id"] for r in sp["train"] if not flagged(r)]; te = sp["test"]; assert [r["id"] for r in te] == ids
msum = np.zeros((N, N, 3), np.float64); lsum = np.zeros((256, 3)); lcnt = np.zeros(256)
for rid in tr:
    A, B = load(rid); m = A > 0; msum += B
    for c in range(3): lsum[:, c] += np.bincount(A[m], weights=B[..., c][m].astype(np.float64), minlength=256)
    lcnt += np.bincount(A[m], minlength=256)
have = np.where(lcnt > 0)[0]; lut = np.zeros((256, 3), np.float32)
for c in range(3): lut[:, c] = np.interp(np.arange(256), have, lsum[have, c] / lcnt[have] / 255.0)
print(f"LUT fit on {len(tr)} training records", flush=True)

dev = torch.device("cpu")
G = networks.define_G(1, 3, cfg["ngf"], cfg["netG"], cfg["norm"], cfg["use_dropout"]).to(dev)
ck = torch.load(od / "ckpt_best.pt", map_location="cpu", weights_only=False); G.load_state_dict(ck["G"]); G.eval()

picks = [round(p * (n - 1)) for p in (0.25, 0.5, 0.75)]; assert picks == [261, 522, 783], picks
rows, check, bad = [], [], []
with torch.no_grad():
    for i in picks:
        A, B = load(ids[i]); m = A > 0; tgt = B.astype(np.float32) / 255.0
        pr = ((G(torch.from_numpy(A)[None, None].float().div(127.5).sub(1).to(dev))[0] + 1) / 2).clamp(0, 1).permute(1, 2, 0).cpu().numpy().astype(np.float32)
        lp = lut[A] * m[..., None]
        l1 = float(np.abs(pr - tgt)[m].mean()); l1_lut = float(np.abs(lp - tgt)[m].mean())
        stored, stored_lut = R["per_slice"]["L1"][i], BL["per_slice"]["gray_level_LUT"]["L1"][i]
        ok = round(l1, 4) == round(stored, 4)
        check.append((i, ids[i], stored, l1, stored_lut, l1_lut, ok))
        if not ok: bad.append(ids[i])
        err = np.clip(np.abs(pr - tgt) * 4, 0, 1)
        rows.append([np.stack([A] * 3, -1), pr, lp, tgt, err])
print("L1 check (index | id | stored | recomputed | LUT stored | LUT recomputed | OK):")
for c in check: print(f"  {c[0]} | {c[1]} | {c[2]:.6f} | {c[3]:.6f} | {c[4]:.6f} | {c[5]:.6f} | {'OK' if c[6] else 'MISMATCH'}")
if bad: print("STOP: Pix2Pix L1 mismatch, nothing saved:", bad); sys.exit(1)

OUT.mkdir(parents=True, exist_ok=False); written = []
u8 = lambda x: (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8) if x.dtype != np.uint8 else x

# 1. per-slice curve
blocks = [s.split("/")[1] for s in ids]; p = np.array(R["per_slice"]["L1"]); l = np.array(BL["per_slice"]["gray_level_LUT"]["L1"])
fig, ax = plt.subplots(figsize=(16, 9.4), dpi=100); plt.rcParams.update({"font.size": 20})
start, shade = 0, False
for k in range(1, n + 1):
    if k == n or blocks[k] != blocks[start]:
        if shade: ax.axvspan(start - 0.5, k - 0.5, color="0.88", lw=0)
        shade = not shade; start = k
x = np.arange(n); ax.plot(x, p, color="#c0392b", lw=1.6, label="Pix2Pix (epoch 3 checkpoint)"); ax.plot(x, l, color="#1f4e9c", lw=1.6, label="Gray-level lookup")
ax.set_xlim(-0.5, n - 0.5); ax.set_xlabel("Slice index within test case P58-16 (alternating shading = histology block)", fontsize=20); ax.set_ylabel("Masked L1 (RGB, 0-1)", fontsize=20)
ax.tick_params(labelsize=18); ax.legend(fontsize=20, loc="upper right", frameon=True); fig.tight_layout()
f1 = OUT / "perslice_L1_fold3.png"; fig.savefig(f1, dpi=100); plt.close(fig); written.append(f1)
# 2. training curve
f2 = OUT / "val_curve_fold3.png"; shutil.copyfile(od / "val_curve_epoch100.png", f2); written.append(f2)
# 3. panels and tiles
for r, row in enumerate(rows, 1):
    for c, im in enumerate(row, 1):
        f = OUT / f"tile_r{r}_c{c}.png"; Image.fromarray(u8(im)).save(f); written.append(f)
grid = Image.new("RGB", (5 * N, 3 * N))
for r, row in enumerate(rows):
    for c, im in enumerate(row): grid.paste(Image.fromarray(u8(im)), (c * N, r * N))
f3 = OUT / "panels_fold3.png"; grid.save(f3); written.append(f3)
print("\nfiles written (SHA-256):")
for f in written: print(hashlib.sha256(open(f, "rb").read()).hexdigest(), f)
print("image size perslice:", Image.open(f1).size, "panels:", Image.open(f3).size)
