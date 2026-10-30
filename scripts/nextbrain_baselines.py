#!/usr/bin/env python3
"""usage: python scripts/nextbrain_baselines.py --root <dir with Case1..Case5> [--splits splits] [--meta outputs/nextbrain_metadata/nextbrain_all_cases.csv] [--out outputs]
Pre-registered baselines (outputs/nextbrain_prereg.md): (i) mean training-target image, (ii) global MRI-to-RGB gray-level LUT fitted on training blocks only.
Tasks: MRI->H&E then MRI->LFB. Metrics: masked L1 (primary), masked-map SSIM, masked PSNR. Block-level bootstrap. No model is trained."""
import argparse, csv, json
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--splits", default="splits")
ap.add_argument("--meta", default="outputs/nextbrain_metadata/nextbrain_all_cases.csv"); ap.add_argument("--out", default="outputs"); a = ap.parse_args()
root = Path(a.root).expanduser()
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(a.meta))}


def prep(p, rgb):
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
        r = meta[rid]; case_dir = root / f"Case{r['case_number']}"
        cache[rid] = (prep(case_dir / r["path_MRI"], False), prep(case_dir / r["path_HE"], True), prep(case_dir / r["path_LFB"], True))
    return cache[rid]


def metrics(pred, tgt, mask):
    d = np.abs(pred - tgt)[mask]; l1 = float(d.mean()); mse = float(((pred - tgt)[mask] ** 2).mean())
    _, smap = ssim(tgt, pred, channel_axis=2, data_range=1.0, full=True)
    return l1, float(smap.mean(axis=2)[mask].mean()), float(10 * np.log10(1.0 / max(mse, 1e-12)))


def boot(vals, blocks, B=10000):
    ub = sorted(set(blocks)); idx = {b: i for i, b in enumerate(ub)}; bi = np.array([idx[b] for b in blocks])
    sums = np.bincount(bi, weights=vals, minlength=len(ub)); cnt = np.bincount(bi, minlength=len(ub))
    draw = np.random.RandomState(12345).randint(0, len(ub), size=(B, len(ub)))
    m = sums[draw].sum(1) / cnt[draw].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


res = {}
for k in range(1, 6):
    sp = json.load(open(f"{a.splits}/nextbrain_fold{k}.json"))
    tr = [r["id"] for r in sp["train"]]
    # fit on training blocks only
    msum = {t: np.zeros((256, 256, 3), np.float64) for t in ("HE", "LFB")}
    lsum = {t: np.zeros((256, 3)) for t in ("HE", "LFB")}; lcnt = np.zeros(256)
    for rid in tr:
        mri, he, lfb = get(rid); m = mri > 0
        for t, tg in (("HE", he), ("LFB", lfb)):
            msum[t] += tg
            for c in range(3):
                lsum[t][:, c] += np.bincount(mri[m], weights=tg[..., c][m].astype(np.float64), minlength=256)
        lcnt += np.bincount(mri[m], minlength=256)
    mean_img = {t: (msum[t] / len(tr) / 255.0).astype(np.float32) for t in msum}
    lut = {}
    have = np.where(lcnt > 0)[0]
    for t in lsum:
        L = np.zeros((256, 3), np.float32)
        for c in range(3):
            L[:, c] = np.interp(np.arange(256), have, lsum[t][have, c] / lcnt[have] / 255.0)
        lut[t] = L
    per = {(t, b): {"L1": [], "SSIM": [], "PSNR": []} for t in ("HE", "LFB") for b in ("mean_train_target", "gray_level_LUT")}
    blocks = []
    for r in sp["test"]:
        mri, he, lfb = get(r["id"]); m = mri > 0; blocks.append(r["block"])
        for t, tg in (("HE", he), ("LFB", lfb)):
            tgt = tg.astype(np.float32) / 255.0
            preds = {"mean_train_target": mean_img[t], "gray_level_LUT": lut[t][mri] * m[..., None]}
            for b, pr in preds.items():
                l1, ss, ps = metrics(pr, tgt, m)
                per[(t, b)]["L1"].append(l1); per[(t, b)]["SSIM"].append(ss); per[(t, b)]["PSNR"].append(ps)
    out = {}
    for (t, b), dd in per.items():
        out[f"{t}|{b}"] = {mn: dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)), ci95_block_bootstrap=boot(np.array(v), blocks), n_slices=len(v), n_blocks=len(set(blocks)))
                           for mn, v in dd.items()}
    res[k] = dict(test_case=sp["test"][0]["subject"], n_train=len(tr), n_val=len(sp["val"]), n_test=len(sp["test"]), results=out)
    print("fold", k, res[k]["test_case"], {kk: round(v["L1"]["mean"], 4) for kk, v in out.items()}, flush=True)
    cache.clear()   # free memory between folds (test+train images are reloaded; ~20 s)

json.dump(res, open(f"{a.out}/nextbrain_baselines.json", "w"), indent=1)
L = ["# NextBrain baselines (no model trained)", "",
     "Pre-registration: `outputs/nextbrain_prereg.md` (+ `outputs/nextbrain_prereg_addendum1.md`), hashes in `out/r4m_audit/LOCK_HASHES.txt`. "
     "Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims.", "",
     "Files: script `scripts/nextbrain_baselines.py`; raw numbers `outputs/nextbrain_baselines.json`; metadata `outputs/nextbrain_metadata/nextbrain_all_cases.csv`; "
     "splits `splits/nextbrain_fold{1..5}.json`; data root `~/Data/NextBrain/Case{1..5}` (path passed as `--root`). Count reconciliation: `outputs/nextbrain_reconciliation.md`.", "",
     "Metrics: masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR. Mean and SD across slices of the held-out case; CI = block-level bootstrap 95 percent "
     "(10,000 resamples of the held-out case's blocks, seed 12345), shown as [low, high] around the pooled slice mean. Baselines fitted on training blocks only (validation blocks excluded).", ""]
for k, r in res.items():
    L += [f"## Fold {k}: held-out case {r['test_case']} (train {r['n_train']}, val {r['n_val']}, test {r['n_test']} slices) - split `splits/nextbrain_fold{k}.json`", "",
          "| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |", "|---|---|---|---|---|---|---|---|"]
    for key in ("HE|mean_train_target", "HE|gray_level_LUT", "LFB|mean_train_target", "LFB|gray_level_LUT"):
        t, b = key.split("|"); d = r["results"][key]
        cell = lambda m: f"{d[m]['mean']:.4f} ({d[m]['sd']:.4f}) | [{d[m]['ci95_block_bootstrap'][0]:.4f}, {d[m]['ci95_block_bootstrap'][1]:.4f}]"
        L.append(f"| {'MRI to H&E' if t == 'HE' else 'MRI to LFB'} | {b} | {cell('L1')} | {cell('SSIM')} | {cell('PSNR')} |")
    L.append("")
L += ["Not computed: validation-set baseline scores; visual QC (all records `NOT_REVIEWED`); slice spacing in micrometers per block (UNVERIFIED); "
      "alignment accuracy between MRI and histology beyond the size check (UNVERIFIED); any trained model.", ""]
open(f"{a.out}/nextbrain_baselines.md", "w").write("\n".join(L))
