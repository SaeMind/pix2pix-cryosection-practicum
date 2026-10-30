#!/usr/bin/env python3
"""usage: python scripts/baseline_per_slice_fold3.py [--root ~/Data/NextBrain]
Post-hoc, unlocked analysis (NOT part of the pre-registered protocol). Computes PER-SLICE L1/SSIM/PSNR on the fold 3 test case for the two baselines
(mean_train_target, gray_level_LUT) with the code copied from scripts/nextbrain_baselines_harness_grid.py (harness grid, mask = MRI > 0, fit on training records
minus the flagged blocks), checks that the aggregate means reproduce outputs/nextbrain_baselines_harness_grid.json (test_primary_excl_flagged) to 4 decimals, and only then
writes outputs/nextbrain_fold3_he/baseline_per_slice.json. Then pairs the stored Pix2Pix per-slice values (outputs/nextbrain_fold3_he/results.json) with the LUT values:
mean difference (Pix2Pix minus LUT), 95% CI from a block bootstrap over the histology blocks (10,000 resamples, seed 0), and the share of slices where Pix2Pix is better.
No checkpoint is loaded; no existing file is modified; an existing output file is never overwritten."""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("--root", default="~/Data/NextBrain"); a = ap.parse_args()
root = Path(a.root).expanduser(); N = 256; FOLD = 3; TARGET = "HE"; excl = {"P85-18/28", "EX9-19/48"}
OUT = Path("outputs/nextbrain_fold3_he/baseline_per_slice.json")
assert not OUT.exists(), f"{OUT} already exists; not overwriting"
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open("outputs/nextbrain_metadata/nextbrain_all_cases.csv"))}
flagged = lambda r: f"{r['subject']}/{r['block']}" in excl
METS = ("L1", "SSIM", "PSNR"); BASES = ("mean_train_target", "gray_level_LUT")

cache = {}
def get(rid):   # copy of get() in nextbrain_baselines_harness_grid.py
    if rid not in cache:
        m = meta[rid]; cd = root / f"Case{m['case_number']}"
        he = Image.open(cd / m[f"path_{TARGET}"]).convert("RGB"); mri = Image.open(cd / m["path_MRI"]).convert("L").resize(he.size, Image.BILINEAR)
        s = N / max(he.size); nw, nh = round(he.size[0] * s), round(he.size[1] * s); y0, x0 = (N - nh) // 2, (N - nw) // 2
        A = np.zeros((N, N), np.uint8); B = np.zeros((N, N, 3), np.uint8)
        A[y0:y0 + nh, x0:x0 + nw] = np.asarray(mri.resize((nw, nh), Image.BILINEAR)); B[y0:y0 + nh, x0:x0 + nw] = np.asarray(he.resize((nw, nh), Image.BILINEAR))
        cache[rid] = (A, B)
    return cache[rid]


def metrics(pred, tgt, mask):   # copy
    d = np.abs(pred - tgt)[mask]; l1 = float(d.mean()); mse = float(((pred - tgt)[mask] ** 2).mean())
    _, smap = ssim(tgt, pred, channel_axis=2, data_range=1.0, full=True)
    return l1, float(smap.mean(axis=2)[mask].mean()), float(10 * np.log10(1.0 / max(mse, 1e-12)))


sp = json.load(open(f"splits/nextbrain_fold{FOLD}.json"))
tr = [r["id"] for r in sp["train"] if not flagged(r)]; te = sp["test"]
msum = np.zeros((N, N, 3), np.float64); lsum = np.zeros((256, 3)); lcnt = np.zeros(256)
for rid in tr:   # fit on training records only
    A, B = get(rid); m = A > 0; msum += B
    for c in range(3): lsum[:, c] += np.bincount(A[m], weights=B[..., c][m].astype(np.float64), minlength=256)
    lcnt += np.bincount(A[m], minlength=256)
    cache.pop(rid)
mean_img = (msum / len(tr) / 255.0).astype(np.float32); have = np.where(lcnt > 0)[0]; lut = np.zeros((256, 3), np.float32)
for c in range(3): lut[:, c] = np.interp(np.arange(256), have, lsum[have, c] / lcnt[have] / 255.0)
print(f"fit on {len(tr)} training records", flush=True)

per = {b: {m: [] for m in METS} for b in BASES}
for r in te:
    A, B = get(r["id"]); m = A > 0; tgt = B.astype(np.float32) / 255.0
    for b, pr in (("mean_train_target", mean_img), ("gray_level_LUT", lut[A] * m[..., None])):
        for mn, x in zip(METS, metrics(pr, tgt, m)): per[b][mn].append(x)
    cache.pop(r["id"])
print(f"scored {len(te)} test slices", flush=True)

# integrity check against the stored aggregates (test_primary_excl_flagged); the test case has 0 flagged records
assert not any(flagged(r) for r in te), "test set contains flagged records; the check below assumes none"
hg = json.load(open("outputs/nextbrain_baselines_harness_grid.json"))["test_primary_excl_flagged"]
quoted = {("gray_level_LUT", "L1"): 0.1237, ("gray_level_LUT", "SSIM"): 0.5195, ("gray_level_LUT", "PSNR"): 14.81,
          ("mean_train_target", "L1"): 0.2475, ("mean_train_target", "SSIM"): 0.2951, ("mean_train_target", "PSNR"): 10.35}
bad = []
print("integrity check (recomputed mean | stored mean | quoted):")
for (b, mn), q in quoted.items():
    new = float(np.mean(per[b][mn])); old = hg[b][mn]["mean"]; nd = 2 if mn == "PSNR" else 4
    ok = abs(new - old) < 5e-5 and round(new, nd) == q
    print(f"  {b:18s} {mn:5s} {new:.6f} | {old:.6f} | {q}  {'OK' if ok else 'MISMATCH'}")
    if not ok: bad.append((b, mn, new, old, q))
if bad:
    print("STOP: integrity check failed; nothing written:", bad); sys.exit(1)

ids = [r["id"] for r in te]
res = dict(fold=FOLD, target=TARGET, test_case=te[0]["subject"], n_test=len(te), grid="harness", provenance="post-hoc, unlocked; code copied from scripts/nextbrain_baselines_harness_grid.py; fit on training records minus flagged blocks",
           per_slice=per, per_slice_ids=ids)
json.dump(res, open(OUT, "w")); print("wrote", OUT, "sha256", hashlib.sha256(open(OUT, "rb").read()).hexdigest())

# paired analysis: Pix2Pix minus LUT, block bootstrap over histology blocks
R = json.load(open("outputs/nextbrain_fold3_he/results.json")); assert R["per_slice_ids"] == ids, "slice order differs between results.json and the baseline run"
blocks = [f"{r['subject']}/{r['block']}" for r in te]; ub = sorted(set(blocks)); bi = np.array([ub.index(b) for b in blocks]); nb = len(ub)
draw = np.random.RandomState(0).randint(0, nb, size=(10000, nb)); cnt = np.bincount(bi, minlength=nb)
print(f"\npaired analysis: {len(ids)} slices, {nb} blocks, 10,000 resamples, seed 0 (Pix2Pix minus gray_level_LUT)")
print("| metric | Pix2Pix mean | LUT mean | mean diff | 95% CI (block bootstrap) | CI excludes 0 | share of slices Pix2Pix better | better = |")
print("|---|---|---|---|---|---|---|---|")
for mn in METS:
    p = np.array(R["per_slice"][mn]); l = np.array(per["gray_level_LUT"][mn]); d = p - l
    sums = np.bincount(bi, weights=d, minlength=nb); boot = sums[draw].sum(1) / cnt[draw].sum(1)
    lo, hi = np.percentile(boot, [2.5, 97.5]); better = (d < 0) if mn == "L1" else (d > 0)
    print(f"| {mn} | {p.mean():.4f} | {l.mean():.4f} | {d.mean():+.4f} | [{lo:+.4f}, {hi:+.4f}] | {'yes' if lo > 0 or hi < 0 else 'no'} | {better.mean():.3f} ({int(better.sum())}/{len(d)}) | {'lower' if mn == 'L1' else 'higher'} |")
