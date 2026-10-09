#!/usr/bin/env python3
"""Primary metric: L1_fov (body pixels inside the PET field-of-view rows).
Secondary: L1_body, L1_full, SSIM, PSNR. Reference: mean training cryosection image (MEAN_IMG).
Blocks come from datasets/D2_ablation/split.json."""
import csv, json
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim, peak_signal_noise_ratio as psnr

DATA, RES, S = Path("datasets/D2_ablation"), Path("results"), 256
META = json.loads((DATA / "split.json").read_text())
BLK = {int(k): v for k, v in META["block"].items()}
R0, R1 = META["pet_rows_256"]
NAMES = ["L1_fov", "L1_body", "L1_full", "SSIM", "PSNR"]


def img(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0


def met(f, r):
    body = (r[..., 0] - r[..., 1]) > 0.18
    fov = body.copy()
    fov[:R0] = False
    fov[R1 + 1:] = False
    d = np.abs(f - r)
    return np.array([d[fov].mean() if fov.any() else np.nan,
                     d[body].mean() if body.any() else np.nan,
                     d.mean(), ssim(r, f, channel_axis=2, data_range=1.0), psnr(r, f, data_range=1.0)])


def per_block(pairs):
    b = {}
    for z, m in pairs:
        b.setdefault(BLK[z], []).append(m)
    return {k: np.nanmean(v, axis=0) for k, v in sorted(b.items())}


mean_img = np.mean([img(p)[:, S:] for p in sorted((DATA / "ct/train").glob("*.png"))], axis=0)
out = {}
for run in ["R1", "R2", "R3", "R4", "R5"]:
    d = RES / run / "test_latest/images"
    fakes = sorted(d.glob("*_fake_B.png"))
    if fakes:
        out[run] = per_block([(int(f.name[:3]), met(img(f), img(d / f"{f.name[:3]}_real_B.png"))) for f in fakes])
ref = next(iter(out), None)
if ref:
    d0 = RES / ref / "test_latest/images"
    out["MEAN_IMG"] = per_block([(int(f.name[:3]), met(mean_img, img(f))) for f in sorted(d0.glob("*_real_B.png"))])


def col(run, i):
    return np.array([v[i] for v in out[run].values()])


table = [["run", "block"] + NAMES]
for run, b in out.items():
    l = col(run, 0)
    print(f"{run:9s} L1_fov {np.nanmean(l):.4f} blocks [{', '.join(f'{x:.4f}' for x in l)}] "
          f"L1_body {np.nanmean(col(run, 1)):.4f} SSIM {np.nanmean(col(run, 3)):.3f} PSNR {np.nanmean(col(run, 4)):.2f}")
    table += [[run, k, *map(float, v)] for k, v in b.items()]
if all(r in out for r in ("R1", "R2", "R4", "R5")):
    nf = float(np.nanmean(np.abs(col("R1", 0) - col("R2", 0))))
    print("noise floor, mean |L1_fov(R1) - L1_fov(R2)|:", round(nf, 4))
    ok = True
    for r in ("R1", "R2", "R5"):
        d = col("R4", 0) - col(r, 0)
        wins = int((d < 0).sum())
        print(f"R4 vs {r}: lower L1_fov in {wins}/{len(d)} blocks, mean diff {np.nanmean(d):+.4f}")
        ok = ok and wins == len(d)
    gain = float(np.nanmean(col("R2", 0) - col("R4", 0)))
    print(f"decision rule: every-block condition {'MET' if ok else 'NOT MET'}; "
          f"mean gain over R2 {gain:+.4f} vs noise floor {nf:.4f} -> {'MET' if gain > nf else 'NOT MET'}")
with open("qc/ablation_metrics.csv", "w", newline="") as fh:
    csv.writer(fh).writerows(table)
