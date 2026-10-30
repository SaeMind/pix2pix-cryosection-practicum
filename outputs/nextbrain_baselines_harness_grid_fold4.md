# NextBrain baselines on the harness grid: fold 4, MRI to H&E (no model trained)

Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).

Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). Script `scripts/nextbrain_baselines_harness_grid_folds.py`; raw numbers `outputs/nextbrain_baselines_harness_grid_fold4.json`.

Held-out case: P85-18, test 994 slices (38 flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n=3603; validation n=441 (flagged blocks removed).

## Harness grid: validation

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2823 (0.0495) | [0.2629, 0.3039] | 0.3048 (0.0989) | [0.2676, 0.3445] | 9.6904 (1.3264) | [9.1185, 10.2304] |
| gray_level_LUT | 0.1380 (0.0558) | [0.1232, 0.1545] | 0.5460 (0.1380) | [0.4953, 0.5853] | 14.6711 (2.4272) | [13.9660, 15.3852] |

## Harness grid: test, primary (excluding flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2632 (0.0580) | [0.2482, 0.2777] | 0.2594 (0.0936) | [0.2360, 0.2809] | 10.0138 (1.6730) | [9.5878, 10.4566] |
| gray_level_LUT | 0.1560 (0.0629) | [0.1483, 0.1642] | 0.4432 (0.1556) | [0.4020, 0.4806] | 13.0340 (2.3113) | [12.6407, 13.4169] |

## Harness grid: test, secondary (including flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2581 (0.0633) | [0.2399, 0.2751] | 0.2539 (0.0963) | [0.2286, 0.2772] | 10.2449 (2.2296) | [9.6818, 10.9117] |
| gray_level_LUT | 0.1701 (0.0941) | [0.1499, 0.2028] | 0.4258 (0.1758) | [0.3711, 0.4729] | 12.7254 (2.7457) | [11.9300, 13.3363] |

## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)

| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |
|---|---|---|---|---|
| validation | mean_train_target | 0.2823 | 0.2823 | +0.0000 |
| validation | gray_level_LUT | 0.1380 | 0.1380 | +0.0000 |
| test primary | mean_train_target | 0.2632 | 0.2632 | +0.0000 |
| test primary | gray_level_LUT | 0.1561 | 0.1560 | -0.0001 |
| test secondary | mean_train_target | 0.2588 | 0.2581 | -0.0007 |
| test secondary | gray_level_LUT | 0.1699 | 0.1701 | +0.0002 |

Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. Test images were read only to score these fixed baselines (fit on training records), before any model output exists.
