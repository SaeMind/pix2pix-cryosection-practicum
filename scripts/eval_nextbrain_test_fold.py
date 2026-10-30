#!/usr/bin/env python3
"""[Fold-aware copy of scripts/eval_nextbrain_test.py: reads outputs/nextbrain_baselines_harness_grid_fold{fold}.json instead of the fold-3 file; everything else identical.]
usage: python scripts/eval_nextbrain_test_fold.py --config configs/nextbrain_fold3_he.json --root ~/Data/NextBrain [--out_dir outputs/nextbrain_fold3_he]
One-time test evaluation (outputs/nextbrain_eval_addendum3.md): the best-VALIDATION checkpoint (ckpt_best.pt) is scored on every test record of the fold on the harness grid
(MRI resampled onto the H&E grid, longer side to 256, centered zero pad; mask = MRI > 0), generator in eval mode. Primary = excluding flagged records, secondary = including.
Next to both baselines on the harness grid (outputs/nextbrain_baselines_harness_grid.json) and, for reference, the original grid (outputs/nextbrain_baselines_sensitivity.json).
Refuses to run a second time: it writes test_eval_STARTED.txt before reading any test image and results.json at the end."""
import argparse, csv, hashlib, json, sys, time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from skimage.metrics import structural_similarity as ssim
sys.path.insert(0, ".")
from models import networks

ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--root", required=True); ap.add_argument("--out_dir", default="outputs/nextbrain_fold3_he"); a = ap.parse_args()
cfg = json.load(open(a.config)); od = Path(a.out_dir); root = Path(a.root).expanduser()
assert (od / "TRAINING_DONE").exists(), "training has not finished (no TRAINING_DONE marker)"
assert not (od / "results.json").exists() and not (od / "test_eval_STARTED.txt").exists(), "the test evaluation was already started or done; it is allowed exactly once"
(od / "test_eval_STARTED.txt").write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + "\n")
excl = set(cfg["exclude_blocks"]); N = cfg["image_size"]; fold = cfg["fold"]; TARGET = cfg["target"]
S = json.load(open(cfg["splits"])); te = S["test"]; flagged = lambda r: f"{r['subject']}/{r['block']}" in excl
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(cfg["metadata"]))}
dev = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
G = networks.define_G(1, 3, cfg["ngf"], cfg["netG"], cfg["norm"], cfg["use_dropout"]).to(dev)
ck = torch.load(od / "ckpt_best.pt", map_location="cpu", weights_only=False); G.load_state_dict(ck["G"]); G.eval()
ck_sha = hashlib.sha256(open(od / "ckpt_best.pt", "rb").read()).hexdigest()


def load(rid):   # same as load() in scripts/train_nextbrain.py
    m = meta[rid]; cd = root / f"Case{m['case_number']}"
    he = Image.open(cd / m[f"path_{TARGET}"]).convert("RGB"); mri = Image.open(cd / m["path_MRI"]).convert("L").resize(he.size, Image.BILINEAR)
    s = N / max(he.size); nw, nh = round(he.size[0] * s), round(he.size[1] * s); y0, x0 = (N - nh) // 2, (N - nw) // 2
    A = np.zeros((N, N), np.uint8); B = np.zeros((N, N, 3), np.uint8)
    A[y0:y0 + nh, x0:x0 + nw] = np.asarray(mri.resize((nw, nh), Image.BILINEAR)); B[y0:y0 + nh, x0:x0 + nw] = np.asarray(he.resize((nw, nh), Image.BILINEAR))
    return A, B


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


METS = ("L1", "SSIM", "PSNR"); per = {m: [] for m in METS}
with torch.no_grad():
    for r in te:
        A, B = load(r["id"]); m = A > 0
        pr = ((G(torch.from_numpy(A)[None, None].float().div(127.5).sub(1).to(dev))[0] + 1) / 2).clamp(0, 1).permute(1, 2, 0).cpu().numpy().astype(np.float32)
        for mn, x in zip(METS, metrics(pr, B.astype(np.float32) / 255.0, m)): per[mn].append(x)
keep = np.array([not flagged(r) for r in te])


def summ(sel):
    recs = [r for r, k in zip(te, sel) if k]; blocks = [f"{r['subject']}/{r['block']}" for r in recs]
    return {mn: dict(mean=float(np.mean(np.array(v)[sel])), sd=float(np.std(np.array(v)[sel], ddof=1)), ci95_block_bootstrap=boot(np.array(v)[sel], blocks), n_slices=int(sel.sum()), n_blocks=len(set(blocks))) for mn, v in per.items()}


res = dict(fold=fold, target=TARGET, test_case=te[0]["subject"], checkpoint="ckpt_best.pt", checkpoint_sha256=ck_sha, best_epoch=int(ck["epoch"]), best_val_L1=float(ck["val_L1"]),
           n_test=len(te), n_test_flagged=int((~keep).sum()), primary_excl_flagged=summ(keep), secondary_incl_flagged=summ(np.ones(len(te), bool)))
res["per_slice"] = {mn: v for mn, v in per.items()}; res["per_slice_ids"] = [r["id"] for r in te]
json.dump(res, open(od / "results.json", "w"))
hg = json.load(open(f"outputs/nextbrain_baselines_harness_grid_fold{fold}.json")); og = json.load(open("outputs/nextbrain_baselines_sensitivity.json"))[str(fold)]
f = lambda d, m: f"{d[m]['mean']:.4f} ({d[m]['sd']:.4f}) [{d[m]['ci95_block_bootstrap'][0]:.4f}, {d[m]['ci95_block_bootstrap'][1]:.4f}]"
rows = lambda title, mod, hkey, okey: [f"### {title}", "", "| method | grid | L1 mean (SD) [95% CI] | SSIM mean (SD) [95% CI] | PSNR mean (SD) [95% CI] |", "|---|---|---|---|---|",
    f"| Pix2Pix (best-validation checkpoint, epoch {res['best_epoch']}) | harness | {f(mod, 'L1')} | {f(mod, 'SSIM')} | {f(mod, 'PSNR')} |"] + \
    [f"| {b} | harness | {f(hg[hkey][b], 'L1')} | {f(hg[hkey][b], 'SSIM')} | {f(hg[hkey][b], 'PSNR')} |" for b in ("mean_train_target", "gray_level_LUT")] + \
    [f"| {b} | original (reference only) | {f(og[okey]['HE|' + b], 'L1')} | {f(og[okey]['HE|' + b], 'SSIM')} | {f(og[okey]['HE|' + b], 'PSNR')} |" for b in ("mean_train_target", "gray_level_LUT")] + [""]
L = [f"# NextBrain fold {fold} MRI to H&E: Pix2Pix test result (one-time evaluation)", "",
     "Retrospective multi-dataset evaluation. One held-out case (single animal-equivalent specimen, one seed): within-case description only, no significance claims, no clinical validation. "
     "Pre-registration: `outputs/nextbrain_eval_addendum3.md`, `outputs/nextbrain_analysis_addendum2.md`, `outputs/nextbrain_train_prereg.md` (hashes in `out/r4m_audit/LOCK_HASHES.txt`).", "",
     f"Model: best-validation checkpoint, epoch {res['best_epoch']} of 100, validation masked L1 {res['best_val_L1']:.4f}; checkpoint SHA-256 `{ck_sha}`. Test case {res['test_case']}, {res['n_test']} slices, evaluated exactly once after training finished. "
     "Metrics on the harness grid, mask = MRI nonzero (pixels where the MRI is zero inside tissue are not scored). CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). "
     f"The test case contains {res['n_test_flagged']} of the 72 flagged records (they are in fold 3 training or validation), so primary and secondary are identical for this fold by construction.", ""]
L += rows("Primary: excluding flagged records", res["primary_excl_flagged"], "test_primary_excl_flagged", "test_primary_excl_flagged")
L += rows("Secondary: including flagged records", res["secondary_incl_flagged"], "test_secondary_incl_flagged", "test_secondary_incl_flagged")
L += ["UNVERIFIED: alignment between MRI and histology; generalization beyond this case; sensitivity to seed; whether differences versus the baselines would persist in other folds or for LFB (not run).", ""]
(od / "results.md").write_text("\n".join(L)); print("\n".join(L))
