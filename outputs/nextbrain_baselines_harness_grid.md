# NextBrain baselines on the harness grid: fold 3, MRI to H&E (no model trained)

Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).

Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). Script `scripts/nextbrain_baselines_harness_grid.py`; raw numbers `outputs/nextbrain_baselines_harness_grid.json`.

Held-out case: P58-16, test 1045 slices (0 flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n=3588; validation n=367 (flagged blocks removed).

## Harness grid: validation

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2690 (0.0542) | [0.2457, 0.2900] | 0.2937 (0.0975) | [0.2561, 0.3290] | 9.9306 (1.5994) | [9.2672, 10.6835] |
| gray_level_LUT | 0.1439 (0.0502) | [0.1346, 0.1559] | 0.4905 (0.1454) | [0.4342, 0.5356] | 14.0273 (2.2544) | [13.4648, 14.5430] |

## Harness grid: test, primary (excluding flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2475 (0.0571) | [0.2339, 0.2600] | 0.2951 (0.0868) | [0.2779, 0.3102] | 10.3548 (1.8344) | [9.9193, 10.8505] |
| gray_level_LUT | 0.1237 (0.0606) | [0.1163, 0.1323] | 0.5195 (0.1452) | [0.4838, 0.5510] | 14.8098 (2.7653) | [14.3237, 15.2573] |

## Harness grid: test, secondary (including flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2475 (0.0571) | [0.2339, 0.2600] | 0.2951 (0.0868) | [0.2779, 0.3102] | 10.3548 (1.8344) | [9.9193, 10.8505] |
| gray_level_LUT | 0.1237 (0.0606) | [0.1163, 0.1323] | 0.5195 (0.1452) | [0.4838, 0.5510] | 14.8098 (2.7653) | [14.3237, 15.2573] |

## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)

| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |
|---|---|---|---|---|
| validation | mean_train_target | 0.2690 | 0.2690 | +0.0000 |
| validation | gray_level_LUT | 0.1439 | 0.1439 | +0.0000 |
| test primary | mean_train_target | 0.2475 | 0.2475 | +0.0000 |
| test primary | gray_level_LUT | 0.1236 | 0.1237 | +0.0000 |
| test secondary | mean_train_target | 0.2475 | 0.2475 | +0.0000 |
| test secondary | gray_level_LUT | 0.1236 | 0.1237 | +0.0000 |

Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. Test images were read only to score these fixed baselines (fit on training records), before any model output exists.
