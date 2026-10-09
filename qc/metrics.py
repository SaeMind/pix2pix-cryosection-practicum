#!/usr/bin/env python3
import csv
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim, peak_signal_noise_ratio as psnr

DATA, RES, S = Path("datasets/D2_ablation"), Path("results"), 256


def img(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255.0


def met(f, r):
    return np.array([np.abs(f - r).mean(), ssim(r, f, channel_axis=2, data_range=1.0),
                     psnr(r, f, data_range=1.0)])


def per_block(pairs):
    blocks = {}
    for z, m in pairs:
        blocks.setdefault(z // 40, []).append(m)
    return {b: np.mean(v, axis=0) for b, v in sorted(blocks.items())}


mean_img = np.mean([img(p)[:, S:] for p in sorted((DATA / "ct/train").glob("*.png"))], axis=0)
out = {}
for run in ["R1", "R2", "R3", "R4", "R5"]:
    d = RES / run / "test_latest/images"
    fakes = sorted(d.glob("*_fake_B.png"))
    if fakes:
        out[run] = per_block([(int(f.name[:3]), met(img(f), img(d / f"{f.name[:3]}_real_B.png")))
                              for f in fakes])
d0 = RES / "R1/test_latest/images"
out["MEAN_IMG"] = per_block([(int(f.name[:3]), met(mean_img, img(f)))
                             for f in sorted(d0.glob("*_real_B.png"))])


def col(run, i):
    return np.array([v[i] for v in out[run].values()])


rows = [["run", "block", "L1", "SSIM", "PSNR"]]
for run, b in out.items():
    l1 = col(run, 0)
    print(f"{run:9s} L1 {l1.mean():.4f} blocks [{', '.join(f'{x:.4f}' for x in l1)}] "
          f"SSIM {col(run, 1).mean():.3f} PSNR {col(run, 2).mean():.2f}")
    rows += [[run, k, *map(float, v)] for k, v in b.items()]
if all(r in out for r in ("R1", "R2", "R4", "R5")):
    print("noise floor, mean |L1(R1) - L1(R2)|:", round(float(np.abs(col("R1", 0) - col("R2", 0)).mean()), 4))
    for ref in ("R1", "R2", "R5"):
        d = col("R4", 0) - col(ref, 0)
        print(f"R4 vs {ref}: lower L1 in {int((d < 0).sum())}/{len(d)} blocks, mean diff {d.mean():+.4f}")
with open("qc/ablation_metrics.csv", "w", newline="") as fh:
    csv.writer(fh).writerows(rows)
