#!/usr/bin/env python3
"""Post-hoc SECONDARY scorer (not the chain's scorer). usage: python out/r4m_audit/score_extra.py [NAME=R4M]  (repo root)
v2 edit (after METRIC_LOCK): adds PSNR_maskv2 (10log10(1/MSE inside mask_v2)) and SSIM_maskv2 (mean of the
SSIM map, channel-averaged, over mask_v2 pixels; 7x7 window, data_range 1). Chain's PSNR/SSIM are unmasked (full image).
Reads out/r4m/<NAME>/pred (written by infer_score.py) and out/r4m/data/test_target; writes only out/r4m_audit/.
Per test block and mean (mean of 3 block means): L1_full (no mask), L1_body (current rule R-G>0.18, repo definition),
L1_maskv2 (masks_ref.py; Otsu over the 118 train+test targets, identical to mask_audit.py; mask depends on targets only),
for the model and for the mean-train-image baseline. Stops if predictions for all 45 test slices are absent."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit")
import masks_ref as M

name = sys.argv[1] if len(sys.argv) > 1 else "R4M"
O = Path("out/r4m"); D = O / "data"; A = Path("out/r4m_audit")
S = json.loads((O / "split.json").read_text()); te = sorted(S["test"])
pd = O / name / "pred"
have = sorted(int(p.stem) for p in pd.glob("*.png")) if pd.exists() else []
if have != te:
    sys.exit(f"STOP: {pd} has {len(have)} of {len(te)} test predictions; run after scoring finishes")
rd = lambda p: np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255
rdu = lambda p: np.asarray(Image.open(p).convert("RGB"))
trp = sorted((D / "petct" / "train").glob("*.png"))
base = np.mean([rd(p)[:, 256:] for p in trp], axis=0)
tgt_u8 = {z: rdu(D / "test_target" / f"{z:03d}.png") for z in te}
dist = {z: M.colour_distance(t, M.border_colour(t)) for z, t in tgt_u8.items()}
dist.update({int(p.stem): M.colour_distance(rdu(p)[:, 256:], M.border_colour(rdu(p)[:, 256:])) for p in trp})
thr = M.distance_otsu(list(dist.values()))
block = lambda z: next(k for k, v in S["blocks"].items() if z in v)


def l1s(f, r, z):
    d = np.abs(f - r)
    cur = (r[..., 0] - r[..., 1]) > 0.18
    v2 = M.largest_filled(dist[z] > thr)
    mse = ((f - r) ** 2)[v2].mean() if v2.any() else np.nan
    smap = ssim(r, f, channel_axis=2, data_range=1.0, full=True)[1].mean(-1)
    return [d.mean(), d[cur].mean() if cur.any() else np.nan, d[v2].mean() if v2.any() else np.nan,
            10 * np.log10(1.0 / mse) if v2.any() else np.nan, smap[v2].mean() if v2.any() else np.nan]


N = ["L1_full", "L1_body", "L1_maskv2", "PSNR_maskv2", "SSIM_maskv2"]
out = {}
for tag, get in (("model", lambda z: rd(pd / f"{z:03d}.png")), ("baseline_mean_train_cryo", lambda z: base)):
    b = {}
    for z in te:
        b.setdefault(block(z), []).append(l1s(get(z), rd(D / "test_target" / f"{z:03d}.png"), z))
    blocks = {k: dict(zip(N, map(float, np.nanmean(v, axis=0)))) for k, v in sorted(b.items())}
    out[tag] = dict(blocks=blocks, mean={n: float(np.mean([blocks[k][n] for k in blocks])) for n in N})
chain = O / name / "metrics.json"
if chain.exists():
    c = json.loads(chain.read_text())["model"]["mean"]["L1_body"]
    out["reproduces_chain_L1_body"] = dict(chain=c, here=out["model"]["mean"]["L1_body"], abs_diff=abs(c - out["model"]["mean"]["L1_body"]))
(A / f"score_extra_{name}.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
