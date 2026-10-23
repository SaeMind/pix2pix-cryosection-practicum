#!/usr/bin/env python3
"""Slide 9 (pixel difference) and slide 10 (edge detail) values, descriptive only. Run from repo root:
  python out/r4m_audit/slide9_10_update.py
Definitions (confirmed by reproducing the existing slides before any new number; the script stops if reproduction fails):
 - pixel difference: mean |a - b| over the whole 256x256x3 tile, uint8 values, 0-255 scale; mean over z67, z107, z147.
 - edge detail: L = 0.299R + 0.587G + 0.114B (uint8 values as float); forward differences gx = diff(L, axis=1)[:-1, :],
   gy = diff(L, axis=0)[:, :-1] (255x255); gradient magnitude hypot(gx, gy); ratio = mean(pred) / mean(target) over the whole tile.
   (np.gradient and Sobel variants did NOT reproduce the slide 10 values; forward differences reproduced all nine to 3 decimals.)
Runs used: those of R4M, R2M, R5M, R6M, R7M, R6bM with 45 PNGs in out/r4m/<RUN>/pred. Reads predictions and test targets only
(three slices for the main tables; all 45 only for the labelled sensitivity). No scorer, no training, writes only the two output files
(refuses if they exist). No interpretation."""
import csv, itertools, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
O = Path("out/r4m"); A = Path("out/r4m_audit")
ORDER = ["R4M", "R2M", "R5M", "R6M", "R7M", "R6bM"]
Z3 = (67, 107, 147)
MD, CSV = A / "slide9_10_values.md", A / "slide9_10_values.csv"
if MD.exists() or CSV.exists():
    sys.exit("REFUSING: output exists")
runs = [r for r in ORDER if len(list((O / r / "pred").glob("*.png"))) == 45]
print("runs used:", runs)
test_z = sorted(int(p.stem) for p in (O / runs[0] / "pred").glob("*.png"))
assert len(test_z) == 45

rd = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(int)
img = lambda who, z: rd((O / "data/test_target" if who == "target" else O / who / "pred") / f"{z:03d}.png")
mad = lambda a, b: float(np.abs(a - b).mean())


def edge(a):
    L = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return float(np.hypot(np.diff(L, axis=1)[:-1, :], np.diff(L, axis=0)[:, :-1]).mean())


who = runs + ["target"]
pairs = [(a, b) for a, b in itertools.combinations(who, 2)]
cache = {}
def get(w, z):
    if (w, z) not in cache:
        cache[(w, z)] = img(w, z)
    return cache[(w, z)]


# ---- slide 9, three slices
d3 = {(a, b): [mad(get(a, z), get(b, z)) for z in Z3] for a, b in pairs}
# ---- slide 10, three slices
e3 = {r: [edge(get(r, z)) / edge(get("target", z)) for z in Z3] for r in runs}

# ---- reproduction of the existing slides (stop if any fails)
rep9 = [(("R4M", "R2M"), 4.75), (("R2M", "R5M"), 5.29), (("R4M", "R5M"), 5.53), (("R4M", "target"), 10.54), (("R5M", "target"), 10.96), (("R2M", "target"), 11.14)]
rep10 = {"R4M": (0.786, 0.793, 0.799), "R5M": (0.798, 0.811, 0.813), "R2M": (0.705, 0.709, 0.719)}
look = lambda a, b: np.mean(d3[(a, b)] if (a, b) in d3 else d3[(b, a)])
ok = True
print("\nReproduction (existing slide vs recomputed)")
for (a, b), want in rep9:
    got = look(a, b); m = f"{got:.2f}" == f"{want:.2f}"; ok &= m
    print(f"  slide 9  {a} vs {b}: slide {want:.2f} recomputed {got:.4f} {'OK' if m else 'MISMATCH'}")
for r, w in rep10.items():
    for z, want, got in zip(Z3, w, e3[r]):
        m = f"{got:.3f}" == f"{want:.3f}"; ok &= m
        print(f"  slide 10 {r} z{z}: slide {want:.3f} recomputed {got:.4f} {'OK' if m else 'MISMATCH'}")
if not ok:
    sys.exit("STOP: reproduction failed; no output written")

# ---- sensitivity: all 45 test slices
d45 = {(a, b): float(np.mean([mad(img(a, z), img(b, z)) for z in test_z])) for a, b in pairs}

# ---- write outputs
f4 = lambda x: f"{x:.2f}"
md = ["# Slide 9 and 10 values (descriptive; mean absolute pixel difference, 0-255 scale; edge detail = gradient ratio pred/target)", "",
      f"Runs used: {', '.join(runs)}. Slices z67, z107, z147 (block centres). Within-animal, one animal; no scoring, no significance claim.", "",
      "## Slide 9: pairwise mean absolute pixel difference, mean over z67, z107, z147", "",
      "| | " + " | ".join(who) + " |", "|" + "---|" * (len(who) + 1)]
for a in who:
    md.append(f"| {a} | " + " | ".join("-" if a == b else f4(look(a, b)) for b in who) + " |")
md += ["", "## Slide 9: per slice", "", "| pair | z67 | z107 | z147 | mean of 3 |", "|---|---|---|---|---|"]
for (a, b), v in d3.items():
    md.append(f"| {a} vs {b} | " + " | ".join(f4(x) for x in v) + f" | {f4(np.mean(v))} |")
md += ["", "## Slide 9 SENSITIVITY: mean over all 45 test slices", "", "| pair | mean over 45 slices |", "|---|---|"]
for (a, b), v in d45.items():
    md.append(f"| {a} vs {b} | {f4(v)} |")
md += ["", "## Slide 10: edge detail (mean luminance gradient magnitude of prediction / of target, whole tile)", "",
       "| run | z67 | z107 | z147 | mean of 3 |", "|---|---|---|---|---|"]
for r in runs:
    md.append(f"| {r} | " + " | ".join(f"{x:.3f}" for x in e3[r]) + f" | {np.mean(e3[r]):.3f} |")
if "R6M" in runs and "R6bM" in runs:
    md += ["", "## R6M vs R6bM (same input, different seed)", "", f"Mean over z67, z107, z147: {f4(look('R6M', 'R6bM'))}; all 45 slices: {f4(d45[('R6M', 'R6bM')])}."]
else:
    md += ["", "R6M vs R6bM: not available (R6bM missing)."]
MD.write_text("\n".join(md) + "\n")
with open(CSV, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["table", "a", "b", "slice", "value"])
    for (a, b), v in d3.items():
        for z, x in zip(Z3, v):
            w.writerow(["pixel_diff", a, b, f"z{z}", f"{x:.4f}"])
        w.writerow(["pixel_diff", a, b, "mean3", f"{np.mean(v):.4f}"])
    for (a, b), v in d45.items():
        w.writerow(["pixel_diff_sensitivity_45", a, b, "mean45", f"{v:.4f}"])
    for r in runs:
        for z, x in zip(Z3, e3[r]):
            w.writerow(["edge_ratio", r, "target", f"z{z}", f"{x:.4f}"])
        w.writerow(["edge_ratio", r, "target", "mean3", f"{np.mean(e3[r]):.4f}"])
print("\n".join(md)); print("\nwrote", MD, CSV)
