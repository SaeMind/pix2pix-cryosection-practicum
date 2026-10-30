#!/usr/bin/env python3
"""usage: python scripts/nextbrain_baselines_sensitivity.py --root <dir with Case1..Case5> [--splits splits] [--meta outputs/nextbrain_metadata/nextbrain_all_cases.csv] [--out outputs] [--exclude P85-18/28 EX9-19/48]
Addendum 2 (outputs/nextbrain_analysis_addendum2.md). Same baselines, preprocessing, mask (MRI > 0), metrics and block-level bootstrap as scripts/nextbrain_baselines.py.
Differences: the flagged blocks are removed from the training (fit) and validation records in every fold; validation records are scored; test records are scored once
and reported excluding the flagged records (primary) and including them (secondary). Reads splits/metadata/data only; writes outputs/nextbrain_baselines_{validation,sensitivity}.{md,json}."""
import argparse, csv, json
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--splits", default="splits")
ap.add_argument("--meta", default="outputs/nextbrain_metadata/nextbrain_all_cases.csv"); ap.add_argument("--out", default="outputs")
ap.add_argument("--exclude", nargs="*", default=["P85-18/28", "EX9-19/48"]); a = ap.parse_args()
root = Path(a.root).expanduser(); excl = set(a.exclude)
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(a.meta))}
flagged = lambda r: f"{r['subject']}/{r['block']}" in excl
BASES = ("mean_train_target", "gray_level_LUT"); TASKS = ("HE", "LFB"); METS = ("L1", "SSIM", "PSNR")


def prep(p, rgb):   # identical to scripts/nextbrain_baselines.py
    im = Image.open(p).convert("RGB" if rgb else "L")
    s = 256 / max(im.size); nw, nh = round(im.size[0] * s), round(im.size[1] * s)
    im = im.resize((nw, nh), Image.BILINEAR)
    out = np.zeros((256, 256, 3) if rgb else (256, 256), np.uint8)
    y0, x0 = (256 - nh) // 2, (256 - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = np.asarray(im)
    return out


cache = {}
def get(rid):
    if rid not in cache:
        r = meta[rid]; cd = root / f"Case{r['case_number']}"
        cache[rid] = (prep(cd / r["path_MRI"], False), prep(cd / r["path_HE"], True), prep(cd / r["path_LFB"], True))
    return cache[rid]


def metrics(pred, tgt, mask):   # identical to scripts/nextbrain_baselines.py
    d = np.abs(pred - tgt)[mask]; l1 = float(d.mean()); mse = float(((pred - tgt)[mask] ** 2).mean())
    _, smap = ssim(tgt, pred, channel_axis=2, data_range=1.0, full=True)
    return l1, float(smap.mean(axis=2)[mask].mean()), float(10 * np.log10(1.0 / max(mse, 1e-12)))


def boot(vals, blocks, B=10000):   # identical to scripts/nextbrain_baselines.py
    ub = sorted(set(blocks)); idx = {b: i for i, b in enumerate(ub)}; bi = np.array([idx[b] for b in blocks])
    sums = np.bincount(bi, weights=vals, minlength=len(ub)); cnt = np.bincount(bi, minlength=len(ub))
    draw = np.random.RandomState(12345).randint(0, len(ub), size=(B, len(ub)))
    m = sums[draw].sum(1) / cnt[draw].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def fit(tr):
    msum = {t: np.zeros((256, 256, 3), np.float64) for t in TASKS}
    lsum = {t: np.zeros((256, 3)) for t in TASKS}; lcnt = np.zeros(256)
    for rid in tr:
        mri, he, lfb = get(rid); m = mri > 0
        for t, tg in (("HE", he), ("LFB", lfb)):
            msum[t] += tg
            for c in range(3):
                lsum[t][:, c] += np.bincount(mri[m], weights=tg[..., c][m].astype(np.float64), minlength=256)
        lcnt += np.bincount(mri[m], minlength=256)
    mean_img = {t: (msum[t] / len(tr) / 255.0).astype(np.float32) for t in TASKS}
    have = np.where(lcnt > 0)[0]; lut = {}
    for t in TASKS:
        L = np.zeros((256, 3), np.float32)
        for c in range(3):
            L[:, c] = np.interp(np.arange(256), have, lsum[t][have, c] / lcnt[have] / 255.0)
        lut[t] = L
    return mean_img, lut


def score(recs, mean_img, lut):
    per = {(t, b): {m: [] for m in METS} for t in TASKS for b in BASES}
    for r in recs:
        mri, he, lfb = get(r["id"]); m = mri > 0
        for t, tg in (("HE", he), ("LFB", lfb)):
            tgt = tg.astype(np.float32) / 255.0
            for b, pr in (("mean_train_target", mean_img[t]), ("gray_level_LUT", lut[t][mri] * m[..., None])):
                v = metrics(pr, tgt, m)
                for mn, x in zip(METS, v): per[(t, b)][mn].append(x)
    return per


def summ(per, recs):
    """per: {(task, base): {metric: [values]}} aligned with recs; returns mean, SD, block-bootstrap CI."""
    blocks = [f"{r['subject']}/{r['block']}" for r in recs]; out = {}
    for (t, b), dd in per.items():
        out[f"{t}|{b}"] = {mn: dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)) if len(v) > 1 else None,
                                    ci95_block_bootstrap=boot(np.array(v), blocks) if len(set(blocks)) > 1 else None, n_slices=len(v), n_blocks=len(set(blocks)))
                           for mn, v in dd.items()}
    return out


def subset(per, keep):
    return {k: {m: [x for x, f in zip(v, keep) if f] for m, v in dd.items()} for k, dd in per.items()}


res = {}
for k in range(1, 6):
    sp = json.load(open(f"{a.splits}/nextbrain_fold{k}.json"))
    tr = [r["id"] for r in sp["train"] if not flagged(r)]
    va = [r for r in sp["val"] if not flagged(r)]
    te = sp["test"]    # every complete triplet; never filtered
    assert not ({r["id"] for r in va} | set(tr)) & {r["id"] for r in te}
    mean_img, lut = fit(tr)
    pv = score(va, mean_img, lut); pt = score(te, mean_img, lut)
    prim = [not flagged(r) for r in te]; fl = [flagged(r) for r in te]
    res[k] = dict(test_case=te[0]["subject"], n_train=len(tr), n_val=len(va), n_test_all=len(te), n_test_flagged=int(sum(fl)),
                  validation=summ(pv, va), test_primary_excl_flagged=summ(subset(pt, prim), [r for r, f in zip(te, prim) if f]),
                  test_secondary_incl_flagged=summ(pt, te),
                  test_flagged_only=(summ(subset(pt, fl), [r for r, f in zip(te, fl) if f]) if sum(fl) else None))
    print("fold", k, res[k]["test_case"], "train", len(tr), "val", len(va), "test", len(te), "flagged in test", int(sum(fl)), flush=True)
    for key in ("HE|gray_level_LUT", "LFB|gray_level_LUT"):
        print("   ", key, "val L1 %.4f | test primary L1 %.4f | test incl L1 %.4f" % tuple(res[k][s][key]["L1"]["mean"] for s in ("validation", "test_primary_excl_flagged", "test_secondary_incl_flagged")), flush=True)

json.dump(res, open(f"{a.out}/nextbrain_baselines_sensitivity.json", "w"), indent=1)
try: prev = json.load(open(f"{a.out}/nextbrain_baselines.json"))   # read only, for reference
except Exception: prev = None

TN = {"HE": "MRI to H&E", "LFB": "MRI to LFB"}
def cell(d, m):
    ci = d[m]["ci95_block_bootstrap"]; sd = d[m]["sd"]
    return f"{d[m]['mean']:.4f} ({'n/a' if sd is None else format(sd, '.4f')}) | " + ("[not computed: 1 block]" if ci is None else f"[{ci[0]:.4f}, {ci[1]:.4f}]")
HDR = ["| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |", "|---|---|---|---|---|---|---|---|"]
def table(d):
    rows = list(HDR)
    for t in TASKS:
        for b in BASES:
            x = d[f"{t}|{b}"]; rows.append(f"| {TN[t]} | {b} | {cell(x, 'L1')} | {cell(x, 'SSIM')} | {cell(x, 'PSNR')} |")
    return rows + [""]

COMMON = ["Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims. Pre-registration: `outputs/nextbrain_analysis_addendum2.md` "
          "(hash in `out/r4m_audit/LOCK_HASHES.txt`), `outputs/nextbrain_prereg.md`.", "",
          "Method: script `scripts/nextbrain_baselines_sensitivity.py`; raw numbers `outputs/nextbrain_baselines_sensitivity.json`. Baselines (mean training-target image; global MRI-to-RGB gray-level LUT) "
          "fitted on training records with Case 4 block 28 and Case 5 block 48 removed. Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mask = MRI nonzero after the "
          "pre-registered per-modality resize to 256. Mean and SD across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345) around the pooled slice mean.", "",
          "Limitation: the tissue mask is MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED.", ""]

V = ["# NextBrain baselines: validation-set scores (no model trained)", ""] + COMMON + \
    ["Records scored: each fold's validation blocks (4 training cases, whole blocks per the split file) minus the flagged blocks. Bootstrap blocks are the validation blocks pooled across cases.", ""]
for k, r in res.items():
    V += [f"## Fold {k} (test case {r['test_case']}): validation n={r['n_val']} slices, fit on train n={r['n_train']} slices", ""] + table(r["validation"])
V += ["Not computed: any trained-model score; test-set scores (see `outputs/nextbrain_baselines_sensitivity.md`).", ""]
open(f"{a.out}/nextbrain_baselines_validation.md", "w").write("\n".join(V))

S = ["# NextBrain baselines: test-set sensitivity to the flagged blocks (no model trained)", ""] + COMMON + \
    ["Primary = test records excluding the 72 flagged records; secondary = all complete triplets. The flagged records are in the test set only in folds 4 (block 28) and 5 (block 48); in folds 1 to 3 the two tables are identical.", ""]
for k, r in res.items():
    S += [f"## Fold {k}: held-out case {r['test_case']} (test {r['n_test_all']} slices, of which {r['n_test_flagged']} flagged; fit on train n={r['n_train']})", "",
          f"### Primary: excluding flagged records (n={r['test_primary_excl_flagged']['HE|gray_level_LUT']['L1']['n_slices']})", ""] + table(r["test_primary_excl_flagged"]) + \
         [f"### Secondary: including flagged records (n={r['test_secondary_incl_flagged']['HE|gray_level_LUT']['L1']['n_slices']})", ""] + table(r["test_secondary_incl_flagged"])
    if r["test_flagged_only"]:
        S += [f"### Flagged records only (n={r['n_test_flagged']}, a single block; descriptive, CI not computed)", ""] + table(r["test_flagged_only"])
if prev:
    S += ["## Reference: earlier baselines (flagged blocks included in training, all test records), L1 mean, from `outputs/nextbrain_baselines.json`", "",
          "| fold | task | baseline | earlier L1 | this analysis, secondary L1 | difference (this minus earlier) |", "|---|---|---|---|---|---|"]
    for k, r in res.items():
        for t in TASKS:
            for b in BASES:
                e = prev[str(k)]["results"][f"{t}|{b}"]["L1"]["mean"]; n = r["test_secondary_incl_flagged"][f"{t}|{b}"]["L1"]["mean"]
                S.append(f"| {k} | {TN[t]} | {b} | {e:.4f} | {n:.4f} | {n - e:+.4f} |")
    S.append("")
S += ["Not computed: any trained-model score; per-block bootstrap for the flagged-only subsets (one block each); alignment accuracy (UNVERIFIED).", ""]
open(f"{a.out}/nextbrain_baselines_sensitivity.md", "w").write("\n".join(S))
