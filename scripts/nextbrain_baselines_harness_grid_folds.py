#!/usr/bin/env python3
"""[Multi-fold copy of scripts/nextbrain_baselines_harness_grid.py; writes outputs/nextbrain_baselines_harness_grid_fold{k}.{json,md}; the fold-3 files are not touched.]
usage: python scripts/nextbrain_baselines_harness_grid_folds.py --root <dir with Case1..Case5> [--fold 3] [--target HE] [--out outputs]
Addendum 3 (outputs/nextbrain_eval_addendum3.md). Same baselines, mask (MRI > 0), metrics and block-level bootstrap as scripts/nextbrain_baselines_sensitivity.py,
but on the HARNESS grid: MRI resampled (bilinear) onto the target (H&E) grid, then the pair scaled so the longer side is 256 (bilinear) and zero-padded, centered, to 256x256
(same operations as load() in scripts/train_nextbrain.py). Baselines fit on training records minus the flagged blocks. Validation minus flagged blocks; test = all complete triplets,
reported excluding (primary) and including (secondary) the flagged records. Writes outputs/nextbrain_baselines_harness_grid.{json,md}. No model is involved."""
import argparse, csv, json
from pathlib import Path
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--folds", type=int, nargs="+", default=[1, 2, 4, 5]); ap.add_argument("--target", default="HE", choices=["HE", "LFB"])
ap.add_argument("--splits", default="splits"); ap.add_argument("--meta", default="outputs/nextbrain_metadata/nextbrain_all_cases.csv"); ap.add_argument("--out", default="outputs")
ap.add_argument("--exclude", nargs="*", default=["P85-18/28", "EX9-19/48"]); a = ap.parse_args()
root = Path(a.root).expanduser(); excl = set(a.exclude); N = 256
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(a.meta))}
flagged = lambda r: f"{r['subject']}/{r['block']}" in excl
METS = ("L1", "SSIM", "PSNR"); BASES = ("mean_train_target", "gray_level_LUT")

cache = {}
def get(rid):   # harness-grid load (copy of train_nextbrain.load, no file outside the requested record is opened)
    if rid not in cache:
        m = meta[rid]; cd = root / f"Case{m['case_number']}"
        he = Image.open(cd / m[f"path_{a.target}"]).convert("RGB"); mri = Image.open(cd / m["path_MRI"]).convert("L").resize(he.size, Image.BILINEAR)
        s = N / max(he.size); nw, nh = round(he.size[0] * s), round(he.size[1] * s); y0, x0 = (N - nh) // 2, (N - nw) // 2
        A = np.zeros((N, N), np.uint8); B = np.zeros((N, N, 3), np.uint8)
        A[y0:y0 + nh, x0:x0 + nw] = np.asarray(mri.resize((nw, nh), Image.BILINEAR)); B[y0:y0 + nh, x0:x0 + nw] = np.asarray(he.resize((nw, nh), Image.BILINEAR))
        cache[rid] = (A, B)
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


def run(fold):
    cache.clear()
    sp = json.load(open(f"{a.splits}/nextbrain_fold{fold}.json"))
    tr = [r["id"] for r in sp["train"] if not flagged(r)]; va = [r for r in sp["val"] if not flagged(r)]; te = sp["test"]
    assert not ({r["id"] for r in va} | set(tr)) & {r["id"] for r in te}
    msum = np.zeros((N, N, 3), np.float64); lsum = np.zeros((256, 3)); lcnt = np.zeros(256)
    for rid in tr:
        A, B = get(rid); m = A > 0; msum += B
        for c in range(3): lsum[:, c] += np.bincount(A[m], weights=B[..., c][m].astype(np.float64), minlength=256)
        lcnt += np.bincount(A[m], minlength=256)
        cache.pop(rid)
    mean_img = (msum / len(tr) / 255.0).astype(np.float32); have = np.where(lcnt > 0)[0]; lut = np.zeros((256, 3), np.float32)
    for c in range(3): lut[:, c] = np.interp(np.arange(256), have, lsum[have, c] / lcnt[have] / 255.0)


    def score(recs):
        per = {b: {m: [] for m in METS} for b in BASES}
        for r in recs:
            A, B = get(r["id"]); m = A > 0; tgt = B.astype(np.float32) / 255.0
            for b, pr in (("mean_train_target", mean_img), ("gray_level_LUT", lut[A] * m[..., None])):
                for mn, x in zip(METS, metrics(pr, tgt, m)): per[b][mn].append(x)
        return per


    def summ(per, recs):
        blocks = [f"{r['subject']}/{r['block']}" for r in recs]
        return {b: {mn: dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)), ci95_block_bootstrap=boot(np.array(v), blocks), n_slices=len(v), n_blocks=len(set(blocks))) for mn, v in dd.items()} for b, dd in per.items()}


    pv, pt = score(va), score(te)
    keep = [not flagged(r) for r in te]
    sub = lambda per, k: {b: {m: [x for x, f in zip(v, k) if f] for m, v in dd.items()} for b, dd in per.items()}
    res = dict(fold=fold, target=a.target, test_case=te[0]["subject"], grid="harness (MRI resampled to target grid, scale longer side to 256, centered zero pad)", n_train=len(tr), n_val=len(va), n_test=len(te), n_test_flagged=int(len(te) - sum(keep)),
               validation=summ(pv, va), test_primary_excl_flagged=summ(sub(pt, keep), [r for r, f in zip(te, keep) if f]), test_secondary_incl_flagged=summ(pt, te))
    json.dump(res, open(f"{a.out}/nextbrain_baselines_harness_grid_fold{fold}.json", "w"), indent=1)

    orig = json.load(open(f"{a.out}/nextbrain_baselines_sensitivity.json"))[str(fold)]
    def cell(d, m): ci = d[m]["ci95_block_bootstrap"]; return f"{d[m]['mean']:.4f} ({d[m]['sd']:.4f}) | [{ci[0]:.4f}, {ci[1]:.4f}]"
    HDR = ["| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |", "|---|---|---|---|---|---|---|"]
    tab = lambda d: HDR + [f"| {b} | {cell(d[b], 'L1')} | {cell(d[b], 'SSIM')} | {cell(d[b], 'PSNR')} |" for b in BASES] + [""]
    tn = "MRI to H&E" if a.target == "HE" else "MRI to LFB"
    L = [f"# NextBrain baselines on the harness grid: fold {fold}, {tn} (no model trained)", "",
         "Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).", "",
         "Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. "
         "This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). "
         "Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). "
         f"Script `scripts/nextbrain_baselines_harness_grid_folds.py`; raw numbers `outputs/nextbrain_baselines_harness_grid_fold{fold}.json`.", "",
         f"Held-out case: {res['test_case']}, test {res['n_test']} slices ({res['n_test_flagged']} flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n={res['n_train']}; validation n={res['n_val']} (flagged blocks removed).", "",
         "## Harness grid: validation", ""] + tab(res["validation"]) + ["## Harness grid: test, primary (excluding flagged records)", ""] + tab(res["test_primary_excl_flagged"]) + \
        ["## Harness grid: test, secondary (including flagged records)", ""] + tab(res["test_secondary_incl_flagged"]) + \
        ["## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)", "",
         "| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |", "|---|---|---|---|---|"]
    for nm, ok, hk in (("validation", "validation", "validation"), ("test primary", "test_primary_excl_flagged", "test_primary_excl_flagged"), ("test secondary", "test_secondary_incl_flagged", "test_secondary_incl_flagged")):
        for b in BASES:
            o = orig[ok][f"{a.target}|{b}"]["L1"]["mean"]; h = res[hk][b]["L1"]["mean"]; L.append(f"| {nm} | {b} | {o:.4f} | {h:.4f} | {h - o:+.4f} |")
    L += ["", "Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. "
          "Test images were read only to score these fixed baselines (fit on training records), before any model output exists.", ""]
    open(f"{a.out}/nextbrain_baselines_harness_grid_fold{fold}.md", "w").write("\n".join(L))
    print("\n".join(L[L.index("## Harness grid: validation"):]))

for fold in a.folds: run(fold)
