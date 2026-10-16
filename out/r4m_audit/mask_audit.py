#!/usr/bin/env python3
"""Read-only mask audit on 256px cryosection targets. Run from repo root.
mask_v2 = masks_ref.py (read-only copy of ../pix2pix-matched-pairs/pairverify/masks.py, repo commit ef4b8de lineage):
per-slice median border colour (5 px ring) -> RGB distance -> Otsu over ALL loaded slices -> largest component -> fill holes.
Difference vs original: runs on the 256x256 resized targets (original ran on full-resolution slices).
mask_bg = same distance>Otsu rule WITHOUT largest-component/fill-holes ("plain not background")."""
import csv, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage
sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit")
import masks_ref as M

D = Path("out/r4m/data"); A = Path("out/r4m_audit")
S = json.loads(Path("out/r4m/split.json").read_text())
rd = lambda p: np.asarray(Image.open(p).convert("RGB"))
tgt = {z: rd(D / "test_target" / f"{z:03d}.png") for z in S["test"]}
tr = sorted(S["train"])
sample = [tr[i] for i in np.linspace(0, len(tr) - 1, 12).round().astype(int)]
for p in sorted((D / "petct" / "train").glob("*.png")):
    z = int(p.stem)
    tgt[z] = rd(p)[:, 256:]
dist = {z: M.colour_distance(t, M.border_colour(t)) for z, t in tgt.items()}
thr = M.distance_otsu(list(dist.values()))                       # over all 118 train+test targets
cur = lambda t: (t[..., 0].astype(np.float32) / 255 - t[..., 1].astype(np.float32) / 255) > 0.18
v2 = lambda z: M.largest_filled(dist[z] > thr)
bg = lambda z: dist[z] > thr
dice = lambda a, b: 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)
rows = []
for z, split in [(z, "test") for z in sorted(S["test"])] + [(z, "train") for z in sample]:
    c, m2, b = cur(tgt[z]), v2(z), bg(z)
    rows.append(dict(z=z, split=split, area_current=c.mean(), area_v2=m2.mean(), area_bg=b.mean(), dice_current_v2=dice(c, m2)))
with open(A / "mask_audit.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
te = [r for r in rows if r["split"] == "test"]; trr = [r for r in rows if r["split"] == "train"]
ratio = lambda rs: np.array([r["area_current"] / r["area_v2"] for r in rs])
flag = [r["z"] for r in te if r["area_current"] < 0.8 * r["area_v2"]]
summ = dict(otsu_distance_threshold=float(thr),
            ratio_test=dict(min=ratio(te).min(), median=float(np.median(ratio(te))), max=ratio(te).max()),
            ratio_train12=dict(min=ratio(trr).min(), median=float(np.median(ratio(trr))), max=ratio(trr).max()),
            dice_test=dict(min=min(r["dice_current_v2"] for r in te), median=float(np.median([r["dice_current_v2"] for r in te]))),
            flagged_count=len(flag), flagged_z=flag, train_sample_z=sample,
            area_v2_zero_slices=[r["z"] for r in rows if r["area_v2"] == 0])
json.dump(summ, open(A / "mask_audit_summary.json", "w"), indent=1, default=float)
cont = lambda m: m & ~ndimage.binary_erosion(m, iterations=1)
fig, ax = plt.subplots(2, 6, figsize=(18, 6.5))
for j, z in enumerate([60, 74, 100, 114, 140, 154]):
    for i, (m, col, lab) in enumerate([(cur(tgt[z]), (0, 255, 0), "current (R-G>0.18)"), (v2(z), (0, 255, 255), "mask_v2")]):
        im = tgt[z].copy(); im[cont(m)] = col
        ax[i, j].imshow(im); ax[i, j].set_title(f"z{z} {lab}", fontsize=8); ax[i, j].axis("off")
plt.tight_layout(); plt.savefig(A / "mask_overlays.png", dpi=100)
for z in [60, 74, 100, 114, 140, 154]:
    im = tgt[z].copy(); im[cont(cur(tgt[z]))] = (0, 255, 0); im[cont(v2(z))] = (0, 255, 255)
    Image.fromarray(im).resize((512, 512), Image.NEAREST).save(A / f"overlay_z{z}.png")
print(json.dumps(summ, indent=1, default=float))
