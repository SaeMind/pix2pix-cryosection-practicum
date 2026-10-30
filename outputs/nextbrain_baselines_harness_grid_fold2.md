# NextBrain baselines on the harness grid: fold 2, MRI to H&E (no model trained)

Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).

Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). Script `scripts/nextbrain_baselines_harness_grid_folds.py`; raw numbers `outputs/nextbrain_baselines_harness_grid_fold2.json`.

Held-out case: P41-16, test 938 slices (0 flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n=3626; validation n=436 (flagged blocks removed).

## Harness grid: validation

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2981 (0.0719) | [0.2695, 0.3331] | 0.2628 (0.0887) | [0.2340, 0.2902] | 9.1139 (1.7311) | [8.3469, 9.8135] |
| gray_level_LUT | 0.1606 (0.0692) | [0.1373, 0.1866] | 0.4796 (0.1287) | [0.4401, 0.5168] | 13.5272 (2.5373) | [12.6725, 14.3362] |

## Harness grid: test, primary (excluding flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.3007 (0.0707) | [0.2797, 0.3216] | 0.2836 (0.0863) | [0.2640, 0.3030] | 9.1739 (1.9305) | [8.6131, 9.7672] |
| gray_level_LUT | 0.1352 (0.0446) | [0.1283, 0.1425] | 0.5218 (0.1333) | [0.4880, 0.5509] | 15.2265 (2.1987) | [14.9023, 15.5726] |

## Harness grid: test, secondary (including flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.3007 (0.0707) | [0.2797, 0.3216] | 0.2836 (0.0863) | [0.2640, 0.3030] | 9.1739 (1.9305) | [8.6131, 9.7672] |
| gray_level_LUT | 0.1352 (0.0446) | [0.1283, 0.1425] | 0.5218 (0.1333) | [0.4880, 0.5509] | 15.2265 (2.1987) | [14.9023, 15.5726] |

## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)

| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |
|---|---|---|---|---|
| validation | mean_train_target | 0.2983 | 0.2981 | -0.0002 |
| validation | gray_level_LUT | 0.1605 | 0.1606 | +0.0001 |
| test primary | mean_train_target | 0.3007 | 0.3007 | +0.0000 |
| test primary | gray_level_LUT | 0.1352 | 0.1352 | -0.0000 |
| test secondary | mean_train_target | 0.3007 | 0.3007 | +0.0000 |
| test secondary | gray_level_LUT | 0.1352 | 0.1352 | -0.0000 |

Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. Test images were read only to score these fixed baselines (fit on training records), before any model output exists.
