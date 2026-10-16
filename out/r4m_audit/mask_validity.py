#!/usr/bin/env python3
"""Tasks 1-2 (targets only). Run from repo root: python out/r4m_audit/mask_validity.py
mask_v2 identical to mask_audit.py (Otsu over the 118 train+test targets). Atlas body = label>0 (pairverify atlas_checks.py),
atlas slice = vol[:, :, z].T (qc/prep_d2_ablation.py ct_slice, transpose=True, ud=lr=zrev=0), PIL resize to 256x256 NEAREST."""
import csv, json, sys
from pathlib import Path
import numpy as np
import nibabel as nib
from PIL import Image, ImageDraw
from scipy import ndimage
sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit")
import masks_ref as M

D = Path("out/r4m/data"); A = Path("out/r4m_audit")
S = json.loads(Path("out/r4m/split.json").read_text())
te = sorted(S["test"])
rd = lambda p: np.asarray(Image.open(p).convert("RGB"))
tgt = {z: rd(D / "test_target" / f"{z:03d}.png") for z in te}
split = {z: "test" for z in te}
for p in sorted((D / "petct" / "train").glob("*.png")):
    z = int(p.stem); tgt[z] = rd(p)[:, 256:]; split[z] = "train"
assert len(tgt) == 118, len(tgt)
dist = {z: M.colour_distance(t, M.border_colour(t)) for z, t in tgt.items()}
thr = M.distance_otsu(list(dist.values()))

hdr = sorted(Path("datasets/D2_digimouse/processed/extracted/atlas_data").glob("*.hdr"))
assert len(hdr) == 1
atlas = np.squeeze(np.asanyarray(nib.load(str(hdr[0])).dataobj)).astype(np.int16)
print("atlas", atlas.shape, "thr", thr)
atl = lambda z: np.asarray(Image.fromarray(((atlas[:, :, z] > 0).T).astype(np.uint8)).resize((256, 256), Image.NEAREST)) > 0
dice = lambda a, b: 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)

rows, v2s = [], {}
for z in sorted(tgt):
    raw = dist[z] > thr
    lab, n = ndimage.label(raw, structure=np.ones((3, 3)))
    sizes = ndimage.sum(raw, lab, index=np.arange(1, n + 1)) if n else np.array([0.0])
    dropped = float((raw.sum() - sizes.max()) / raw.sum()) if raw.sum() else float("nan")
    v2 = M.largest_filled(raw); v2s[z] = v2
    rows.append(dict(z=z, split=split[z], area_v2=float(v2.mean()), n_components_thresholded=int(n),
                     dropped_fraction=dropped, dice_vs_atlas_body=float(dice(v2, atl(z)))))
with open(A / "mask_validity.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# Task 1 contact sheet
cont = lambda m: m & ~ndimage.binary_erosion(m, iterations=1)
sheet = Image.new("RGB", (9 * 256, 5 * 256))
for i, z in enumerate(te):
    im = tgt[z].copy(); im[cont(v2s[z])] = (0, 255, 255)
    t = Image.fromarray(im); d = ImageDraw.Draw(t)
    d.rectangle((0, 0, 40, 12), fill=(0, 0, 0)); d.text((2, 0), f"z{z}", fill=(255, 255, 255))
    sheet.paste(t, ((i % 9) * 256, (i // 9) * 256))
sheet.save(A / "test_mask_sheet.png")

T = [r for r in rows if r["split"] == "test"]; R = [r for r in rows if r["split"] == "train"]
for tag, rs in (("test", T), ("train", R)):
    d = np.array([r["dice_vs_atlas_body"] for r in rs])
    print(tag, len(rs), "median dice", np.median(d), "min", d.min(), "dropped>0.10:", sum(r["dropped_fraction"] > 0.10 for r in rs))
