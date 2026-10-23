#!/usr/bin/env python3
"""Inference noise floor of the R4M checkpoint. Run from repo root: python out/r4m_audit/inference_noise_check.py
Definitions fixed before any result (hashed first). Reads ONLY out/r4m/data/petct/test_input, the R4M checkpoint, and stored
predictions out/r4m/{R4M,R2M,R5M}/pred. Reads no target, runs no scorer, writes only out/r4m_audit/scratch_noise/ (refuses if present).
Inference replicates out/r4m/infer_score.py infer() lines 27-39: networks.define_G(3, 3, 64, "unet_256", "batch", True, "normal", 0.02),
load_state_dict(100_net_G.pth, map_location cpu), G.eval() (line 30), RGB/255*2-1 float32 input, torch.no_grad, no seeding anywhere,
output PNG = clip((y+1)/2*255+0.5, 0, 255).astype(uint8).
pass1, pass2: that exact mode. pass_eval: same as pass1 with an explicit G.eval() call (sensitivity only, never scored).
Metric: mean absolute difference of uint8 values over the whole 256x256x3 tile, 0-255 scale."""
import sys, time
from pathlib import Path
import numpy as np
import torch
from PIL import Image

sys.dont_write_bytecode = True
sys.path.insert(0, ".")
from models import networks

O = Path("out/r4m"); SC = Path("out/r4m_audit/scratch_noise")
SLICES = (67, 107, 147)
files = sorted((O / "data/petct/test_input").glob("*.png"))
assert len(files) == 45
for d in ("pass1", "pass2", "pass_eval"):
    if (SC / d).exists():
        sys.exit(f"REFUSING: {SC / d} exists")
for d in ("pass1", "pass2", "pass_eval"):
    (SC / d).mkdir(parents=True)

G = networks.define_G(3, 3, 64, "unet_256", "batch", True, "normal", 0.02)
G.load_state_dict(torch.load(O / "checkpoints/R4M/100_net_G.pth", map_location="cpu"))
G.eval()                                              # infer_score.py:30
print("nn.Dropout modules:", sum(isinstance(m, torch.nn.Dropout) for m in G.modules()),
      "| any Dropout in training mode:", any(m.training for m in G.modules() if isinstance(m, torch.nn.Dropout)),
      "| G.training:", G.training)


def run(tag, explicit_eval):
    t0 = time.time()
    if explicit_eval:
        G.eval()
    for p in files:
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255 * 2 - 1
        x = torch.from_numpy(a).permute(2, 0, 1)[None]
        with torch.no_grad():
            y = G(x)[0].permute(1, 2, 0).numpy()
        Image.fromarray(np.clip((y + 1) / 2 * 255 + 0.5, 0, 255).astype(np.uint8)).save(SC / tag / p.name)
    dt = time.time() - t0
    print(f"{tag}: {dt:.1f} s for 45 slices")
    return dt


rt = {"pass1": run("pass1", False), "pass2": run("pass2", False), "pass_eval": run("pass_eval", True)}
rd = lambda p: np.asarray(Image.open(p).convert("RGB")).astype(int)
mad = lambda a, b: float(np.abs(a - b).mean())
name = lambda z: f"{z:03d}.png"


def table(title, rows):
    print(f"\n{title}")
    for r in rows:
        print("  " + "  ".join(f"{v:>10.4f}" if isinstance(v, float) else f"{v:>10}" for v in r))


# (A) pass1 vs pass2
per = {z: mad(rd(SC / "pass1" / name(z)), rd(SC / "pass2" / name(z))) for z in SLICES}
all45 = np.mean([mad(rd(SC / "pass1" / p.name), rd(SC / "pass2" / p.name)) for p in files])
table("(A) pass1 vs pass2 (0-255 scale)", [["slice"] + [f"z{z}" for z in SLICES] + ["mean(3)", "mean(45)"],
                                           ["MAD"] + [per[z] for z in SLICES] + [float(np.mean(list(per.values()))), float(all45)]])
# (B), (C) against stored R4M predictions
for lab, tag in (("(B) pass1 vs stored R4M/pred", "pass1"), ("(C) pass_eval vs stored R4M/pred (sensitivity only)", "pass_eval")):
    v = {z: mad(rd(SC / tag / name(z)), rd(O / "R4M/pred" / name(z))) for z in SLICES}
    table(lab, [["slice"] + [f"z{z}" for z in SLICES] + ["mean(3)"], ["MAD"] + [v[z] for z in SLICES] + [float(np.mean(list(v.values())))]])
# exact-equality byte checks (extra, information only)
same_12 = all(np.array_equal(rd(SC / "pass1" / p.name), rd(SC / "pass2" / p.name)) for p in files)
same_1s = all(np.array_equal(rd(SC / "pass1" / p.name), rd(O / "R4M/pred" / p.name)) for p in files)
print(f"\nbyte-identical over all 45: pass1==pass2 {same_12}; pass1==stored R4M/pred {same_1s}")
# (D) slide 9 values from stored predictions
pr = lambda n, z: rd(O / n / "pred" / name(z))
d = {}
for lab, a, b, want in (("R4M vs R2M", "R4M", "R2M", 4.75), ("R2M vs R5M", "R2M", "R5M", 5.29), ("R4M vs R5M", "R4M", "R5M", 5.53)):
    d[lab] = (float(np.mean([mad(pr(a, z), pr(b, z)) for z in SLICES])), want)
table("(D) slide 9 recomputed from stored predictions at z67, z107, z147", [["pair", "computed", "slide 9", "match(2dp)"]] +
      [[k, v[0], v[1], str(f"{v[0]:.2f}" == f"{v[1]:.2f}")] for k, v in d.items()])
print("\nruntimes (s):", {k: round(v, 1) for k, v in rt.items()})
