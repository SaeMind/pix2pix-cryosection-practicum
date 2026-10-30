# NextBrain baselines on the harness grid: fold 1, MRI to H&E (no model trained)

Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).

Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). Script `scripts/nextbrain_baselines_harness_grid_folds.py`; raw numbers `outputs/nextbrain_baselines_harness_grid_fold1.json`.

Held-out case: P57-16, test 1018 slices (0 flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n=3578; validation n=404 (flagged blocks removed).

## Harness grid: validation

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2602 (0.0788) | [0.2231, 0.3001] | 0.3016 (0.0817) | [0.2773, 0.3233] | 10.1981 (2.1269) | [9.1932, 11.2442] |
| gray_level_LUT | 0.1334 (0.0538) | [0.1125, 0.1575] | 0.5353 (0.1353) | [0.4823, 0.5762] | 14.5487 (2.5059) | [13.6619, 15.5144] |

## Harness grid: test, primary (excluding flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2619 (0.0621) | [0.2464, 0.2763] | 0.2370 (0.0902) | [0.2183, 0.2543] | 10.0597 (1.7670) | [9.6378, 10.5287] |
| gray_level_LUT | 0.1501 (0.0736) | [0.1394, 0.1623] | 0.4489 (0.1455) | [0.4146, 0.4798] | 13.5984 (2.6055) | [13.1555, 13.9871] |

## Harness grid: test, secondary (including flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2619 (0.0621) | [0.2464, 0.2763] | 0.2370 (0.0902) | [0.2183, 0.2543] | 10.0597 (1.7670) | [9.6378, 10.5287] |
| gray_level_LUT | 0.1501 (0.0736) | [0.1394, 0.1623] | 0.4489 (0.1455) | [0.4146, 0.4798] | 13.5984 (2.6055) | [13.1555, 13.9871] |

## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)

| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |
|---|---|---|---|---|
| validation | mean_train_target | 0.2604 | 0.2602 | -0.0002 |
| validation | gray_level_LUT | 0.1333 | 0.1334 | +0.0001 |
| test primary | mean_train_target | 0.2620 | 0.2619 | -0.0001 |
| test primary | gray_level_LUT | 0.1499 | 0.1501 | +0.0002 |
| test secondary | mean_train_target | 0.2620 | 0.2619 | -0.0001 |
| test secondary | gray_level_LUT | 0.1499 | 0.1501 | +0.0002 |

Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. Test images were read only to score these fixed baselines (fit on training records), before any model output exists.
