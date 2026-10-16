#!/usr/bin/env python3
"""Sensitivity scorer. usage: python out/r4m_audit/score_sensitivity.py NAME   (repo root; NAME e.g. R4M, R2M, R5M)
Locked by METRIC_LOCK_ADDENDUM_2.md. Reads out/r4m/<NAME>/pred, out/r4m/data, out/r4m/split.json, out/r4m_audit/mask_valid.json.
Reports L1_maskv2 (mask_v2 from the TARGET; same Otsu over the 118 train+test targets as score_extra.py) for the model and the
mean-train-image baseline, over (a) all 45 test slices and (b) valid slices only: per block A/B/C, mean of block means, and the
number of valid slices per block. Writes out/r4m_audit/score_sensitivity_<NAME>.json. Stops if the 45 predictions are absent."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit")
import masks_ref as M

name = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: score_sensitivity.py NAME")
O = Path("out/r4m"); D = O / "data"; A = Path("out/r4m_audit")
S = json.loads((O / "split.json").read_text()); te = sorted(S["test"])
pd = O / name / "pred"
have = sorted(int(p.stem) for p in pd.glob("*.png")) if pd.exists() else []
if have != te:
    sys.exit(f"STOP: {pd} has {len(have)} of {len(te)} test predictions; run after scoring finishes")
V = json.loads((A / "mask_valid.json").read_text())
valid = {k.split()[0]: set(v) for k, v in V["valid_by_block"].items()}
rd = lambda p: np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255
rdu = lambda p: np.asarray(Image.open(p).convert("RGB"))
trp = sorted((D / "petct" / "train").glob("*.png"))
base = np.mean([rd(p)[:, 256:] for p in trp], axis=0)
tgt_u8 = {z: rdu(D / "test_target" / f"{z:03d}.png") for z in te}
dist = {z: M.colour_distance(t, M.border_colour(t)) for z, t in tgt_u8.items()}
dist.update({int(p.stem): M.colour_distance(rdu(p)[:, 256:], M.border_colour(rdu(p)[:, 256:])) for p in trp})
thr = M.distance_otsu(list(dist.values()))
block = lambda z: next(k for k, v in S["blocks"].items() if z in v)


def l1_maskv2(f, r, z):
    v2 = M.largest_filled(dist[z] > thr)
    return float(np.abs(f - r)[v2].mean()) if v2.any() else float("nan")


def agg(per, keep):
    b = {}
    for z in te:
        if keep(z):
            b.setdefault(block(z), []).append(per[z])
    blocks = {k: float(np.nanmean(v)) for k, v in sorted(b.items())}
    return dict(blocks=blocks, n_slices={k: len(v) for k, v in sorted(b.items())},
                mean_of_block_means=float(np.mean(list(blocks.values()))) if blocks else float("nan"))


out = dict(valid_count_per_block={k: len(v) for k, v in sorted(valid.items())})
for tag, get in (("model", lambda z: rd(pd / f"{z:03d}.png")), ("baseline_mean_train_cryo", lambda z: base)):
    per = {z: l1_maskv2(get(z), rd(D / "test_target" / f"{z:03d}.png"), z) for z in te}
    out[tag] = dict(L1_maskv2_all45=agg(per, lambda z: True),
                    L1_maskv2_valid_only=agg(per, lambda z: z in valid[block(z)]))
(A / f"score_sensitivity_{name}.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
