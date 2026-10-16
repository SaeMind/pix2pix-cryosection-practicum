#!/usr/bin/env python3
"""Task C checks (targets only). Run from repo root."""
import csv, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit"); sys.path.insert(0, "qc")
import masks_ref as M
import prep_d2_ablation as P
from scipy import ndimage
A = Path("out/r4m_audit"); D = Path("out/r4m/data")
S = json.loads(Path("out/r4m/split.json").read_text())
cryo = P.load_cryo(P.EXT / "cryo_data")
zs = sorted(S["train"] + S["test"])
print("full-res slice shape", cryo[0].shape)
dist_full = {z: M.colour_distance(cryo[z], M.border_colour(cryo[z])) for z in zs}
thr_full = M.distance_otsu(list(dist_full.values()))
rdu = lambda p: np.asarray(Image.open(p).convert("RGB"))
t256 = {z: rdu(D / "test_target" / f"{z:03d}.png") for z in S["test"]}
t256.update({int(p.stem): rdu(p)[:, 256:] for p in (D / "petct" / "train").glob("*.png")})
d256 = {z: M.colour_distance(t, M.border_colour(t)) for z, t in t256.items()}
thr256 = M.distance_otsu(list(d256.values()))
v256 = lambda z: M.largest_filled(d256[z] > thr256)
dice = lambda a, b: 2 * (a & b).sum() / max(a.sum() + b.sum(), 1)
print(f"Otsu thr full-res {thr_full:.2f}, 256px {thr256:.2f}")
res = {}
for z in (60, 100, 140):
    full = M.largest_filled(dist_full[z] > thr_full)
    down = np.asarray(Image.fromarray(full.astype(np.uint8) * 255).resize((256, 256), Image.NEAREST)) > 0
    res[z] = dict(dice=float(dice(down, v256(z))), area_full=float(full.mean()), area_down=float(down.mean()), area_256=float(v256(z).mean()))
    print(z, res[z])
rows = list(csv.DictReader(open(A / "mask_audit.csv")))
big = max(rows, key=lambda r: float(r["area_current"]) / float(r["area_v2"]))
z = int(big["z"]); print("max ratio slice", big)
cont = lambda m: m & ~ndimage.binary_erosion(m, iterations=1)
im = t256[z].copy(); cur = (t256[z][..., 0].astype(float) / 255 - t256[z][..., 1].astype(float) / 255) > 0.18
im[cont(cur)] = (0, 255, 0); im[cont(v256(z))] = (0, 255, 255)
Image.fromarray(np.concatenate([t256[z], im], 1)).resize((1024, 512), Image.NEAREST).save(A / f"overlay_ratio_max_z{z}.png")
print("areas cur/v2", cur.mean(), v256(z).mean(), "ncomp(cur)", ndimage.label(cur)[1])
json.dump(dict(dice_fullres_vs_256=res, thr_full=float(thr_full), thr256=float(thr256), max_ratio_row=big), open(A / "mask_checks.json", "w"), indent=1, default=float)
