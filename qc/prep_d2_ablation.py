#!/usr/bin/env python3
"""Inspect:  python qc/prep_d2_ablation.py
   Write:    python qc/prep_d2_ablation.py --write [--ud] [--lr] [--zrev]"""
import argparse, json, re
from pathlib import Path
import numpy as np
import nibabel as nib
from PIL import Image

EXT = Path("datasets/D2_digimouse/processed/extracted")
OUT = Path("datasets/D2_ablation")
QC = Path("qc/overlays")
SIZE, TRAIN, GAP, TEST = 256, 20, 5, 10


def nat(p):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)]


def load_vol(folder):
    hdr = sorted(Path(folder).rglob("*.hdr"))
    if len(hdr) != 1:
        raise SystemExit(f"{folder}: expected 1 .hdr, found {len(hdr)}")
    return np.squeeze(np.asanyarray(nib.load(str(hdr[0])).dataobj)).astype(np.float32)


def load_cryo(folder):
    files = sorted((p for p in Path(folder).rglob("*") if p.suffix.lower() in (".tif", ".tiff")), key=nat)
    if not files:
        raise SystemExit(f"{folder}: no TIFF files")
    print("cryo count:", len(files), "first:", files[0].name, "last:", files[-1].name,
          "mode:", Image.open(files[0]).mode)
    return np.stack([np.asarray(Image.open(p).convert("RGB")) for p in files])


def split_idx(n):
    pos = np.arange(n) % (TRAIN + GAP + TEST + GAP)
    return np.where(pos < TRAIN)[0], np.where((pos >= TRAIN + GAP) & (pos < TRAIN + GAP + TEST))[0]


def ct_slice(vol, z, tr):
    s = vol[:, :, z]
    return s.T if tr else s


def apply(s, ud, lr):
    if ud:
        s = s[::-1]
    if lr:
        s = s[:, ::-1]
    return np.ascontiguousarray(s)


def norm_u8(x, lo, hi):
    return (np.clip((x - lo) / (hi - lo + 1e-8), 0, 1) * 255).astype(np.uint8)


def rs(a):
    return np.asarray(Image.fromarray(a).resize((SIZE, SIZE), Image.BILINEAR))


def score(ct, cryo, tr, ud, lr, zr):
    Z, r = ct.shape[2], []
    for z in range(40, 170, 10):
        c = apply(ct_slice(ct, z, tr), ud, lr)[::4, ::4]
        g = cryo[Z - 1 - z if zr else z].mean(-1)[::4, ::4]
        r.append(abs(np.corrcoef(c.ravel(), g.ravel())[0, 1]))
    return float(np.nanmean(r))


def overlay(ct, cryo, tr, ud, lr, zr, z):
    Z = ct.shape[2]
    c = apply(ct_slice(ct, z, tr), ud, lr)
    c8 = norm_u8(c, *np.percentile(c, [1, 99]))
    g = cryo[Z - 1 - z if zr else z]
    red = np.stack([c8, 0 * c8, 0 * c8], -1)
    blend = (0.6 * g + 0.4 * red).astype(np.uint8)
    panel = np.concatenate([g, np.stack([c8] * 3, -1), blend], 1)
    QC.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel).save(QC / f"overlay_z{z:03d}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ud", action="store_true")
    ap.add_argument("--lr", action="store_true")
    ap.add_argument("--zrev", action="store_true")
    a = ap.parse_args()

    ct, pet, cryo = load_vol(EXT / "ct_data"), load_vol(EXT / "pet_data"), load_cryo(EXT / "cryo_data")
    print("CT", ct.shape, "PET", pet.shape, "cryo", cryo.shape)
    Z = ct.shape[2]
    if pet.shape != ct.shape or cryo.shape[0] != Z:
        raise SystemExit("grid or slice-count mismatch: stop and report")
    H, W = cryo.shape[1:3]
    if (H, W) == (ct.shape[1], ct.shape[0]):
        tr = True
    elif (H, W) == ct.shape[:2]:
        tr = False
    else:
        raise SystemExit(f"cryo slice {(H, W)} incompatible with CT slice {ct.shape[:2]}")

    res = sorted(((score(ct, cryo, tr, ud, lr, zr), ud, lr, zr)
                  for ud in (0, 1) for lr in (0, 1) for zr in (0, 1)), reverse=True)
    for s, ud, lr, zr in res:
        print(f"score={s:.3f} ud={ud} lr={lr} zrev={zr}")
    ud, lr, zr = res[0][1:] if not a.write else (int(a.ud), int(a.lr), int(a.zrev))
    for z in (40, 80, 110, 140, 170):
        overlay(ct, cryo, tr, ud, lr, zr, z)
    print(f"overlays in {QC} using ud={ud} lr={lr} zrev={zr} (heuristic; review before --write)")
    if not a.write:
        return

    tr_i, te_i = split_idx(Z)
    stats = {k: np.percentile(v[:, :, tr_i], [1, 99]) for k, v in (("ct", ct), ("pet", pet))}
    perm = np.random.default_rng(0).permutation(Z)

    def sl(vol, key, z):
        return norm_u8(apply(ct_slice(vol, int(z), tr), ud, lr), *stats[key])

    for split, idx in (("train", tr_i), ("test", te_i)):
        for z in idx:
            c, p, ps = rs(sl(ct, "ct", z)), rs(sl(pet, "pet", z)), rs(sl(pet, "pet", perm[z]))
            b = rs(cryo[Z - 1 - z if zr else z])
            zero = np.zeros_like(c)
            A = {"ct": np.stack([c] * 3, -1), "pet": np.stack([p] * 3, -1),
                 "petct": np.stack([p, zero, c], -1), "petct_shuf": np.stack([ps, zero, c], -1)}
            for name, arr in A.items():
                d = OUT / name / split
                d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(np.concatenate([arr, b], 1)).save(d / f"{int(z):03d}.png")
    meta = dict(train=tr_i.tolist(), test=te_i.tolist(), ud=ud, lr=lr, zrev=zr, transpose=tr,
                size=SIZE, pct_stats={k: v.tolist() for k, v in stats.items()}, shuffle_seed=0)
    (OUT / "split.json").write_text(json.dumps(meta, indent=1))
    print("train", len(tr_i), "test", len(te_i), "discarded", Z - len(tr_i) - len(te_i))


if __name__ == "__main__":
    main()
