# NextBrain baselines on the harness grid: fold 5, MRI to H&E (no model trained)

Retrospective multi-dataset evaluation; one test case, so within-case description only, no significance claims. Pre-registration: `outputs/nextbrain_eval_addendum3.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`).

Grid: harness grid = MRI resampled (bilinear) onto the H&E grid, then both scaled so the longer side is 256 (bilinear) and centered zero-padded to 256x256; mask = MRI nonzero on that grid. This is the grid the Pix2Pix model is scored on. Baselines fit on training records minus the flagged blocks (Case 4 block 28, Case 5 block 48). Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mean (SD) across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). Script `scripts/nextbrain_baselines_harness_grid_folds.py`; raw numbers `outputs/nextbrain_baselines_harness_grid_fold5.json`.

Held-out case: EX9-19, test 1077 slices (34 flagged records in the test set; primary and secondary are identical when this is 0). Fit on train n=3573; validation n=384 (flagged blocks removed).

## Harness grid: validation

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2748 (0.0574) | [0.2533, 0.2973] | 0.2661 (0.1200) | [0.2118, 0.3123] | 9.8605 (1.6503) | [9.2418, 10.5177] |
| gray_level_LUT | 0.1443 (0.0589) | [0.1323, 0.1592] | 0.4774 (0.1980) | [0.3836, 0.5597] | 14.2383 (2.6392) | [13.3586, 14.9602] |

## Harness grid: test, primary (excluding flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2942 (0.0588) | [0.2767, 0.3123] | 0.3337 (0.0957) | [0.3092, 0.3580] | 9.6368 (1.5548) | [9.1761, 10.1031] |
| gray_level_LUT | 0.2007 (0.0496) | [0.1883, 0.2137] | 0.4725 (0.1375) | [0.4362, 0.5040] | 12.5306 (1.8746) | [12.0724, 12.9760] |

## Harness grid: test, secondary (including flagged records)

| baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|
| mean_train_target | 0.2930 (0.0585) | [0.2761, 0.3109] | 0.3252 (0.1054) | [0.2950, 0.3532] | 9.6555 (1.5390) | [9.2040, 10.0969] |
| gray_level_LUT | 0.2084 (0.0649) | [0.1910, 0.2286] | 0.4584 (0.1562) | [0.4129, 0.4985] | 12.3287 (2.1593) | [11.7201, 12.8814] |

## Original grid (each modality resized independently; from `outputs/nextbrain_baselines_sensitivity.json`, for comparison of grids; not comparable with model scores)

| set | baseline | original-grid L1 mean | harness-grid L1 mean | difference (harness minus original) |
|---|---|---|---|---|
| validation | mean_train_target | 0.2748 | 0.2748 | +0.0000 |
| validation | gray_level_LUT | 0.1443 | 0.1443 | -0.0000 |
| test primary | mean_train_target | 0.2943 | 0.2942 | -0.0001 |
| test primary | gray_level_LUT | 0.2006 | 0.2007 | +0.0001 |
| test secondary | mean_train_target | 0.2941 | 0.2930 | -0.0011 |
| test secondary | gray_level_LUT | 0.2080 | 0.2084 | +0.0004 |

Limitation: mask = MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED. Test images were read only to score these fixed baselines (fit on training records), before any model output exists.
