# NextBrain baselines (no model trained)

Pre-registration: `outputs/nextbrain_prereg.md` (+ `outputs/nextbrain_prereg_addendum1.md`), hashes in `out/r4m_audit/LOCK_HASHES.txt`. Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims.

Files: script `scripts/nextbrain_baselines.py`; raw numbers `outputs/nextbrain_baselines.json`; metadata `outputs/nextbrain_metadata/nextbrain_all_cases.csv`; splits `splits/nextbrain_fold{1..5}.json`; data root `~/Data/NextBrain/Case{1..5}` (path passed as `--root`). Count reconciliation: `outputs/nextbrain_reconciliation.md`.

Metrics: masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR. Mean and SD across slices of the held-out case; CI = block-level bootstrap 95 percent (10,000 resamples of the held-out case's blocks, seed 12345), shown as [low, high] around the pooled slice mean. Baselines fitted on training blocks only (validation blocks excluded).

## Fold 1: held-out case P57-16 (train 3650, val 404, test 1018 slices) - split `splits/nextbrain_fold1.json`

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2639 (0.0620) | [0.2484, 0.2784] | 0.2366 (0.0901) | [0.2178, 0.2540] | 10.0249 (1.7598) | [9.6023, 10.4948] |
| MRI to H&E | gray_level_LUT | 0.1501 (0.0733) | [0.1392, 0.1624] | 0.4500 (0.1455) | [0.4158, 0.4808] | 13.6330 (2.6098) | [13.1892, 14.0272] |
| MRI to LFB | mean_train_target | 0.3419 (0.0526) | [0.3300, 0.3538] | 0.1868 (0.0703) | [0.1750, 0.1987] | 8.0767 (1.2543) | [7.7945, 8.3787] |
| MRI to LFB | gray_level_LUT | 0.1910 (0.0721) | [0.1833, 0.1997] | 0.4385 (0.1353) | [0.4120, 0.4645] | 12.3289 (2.4062) | [12.0095, 12.6070] |

## Fold 2: held-out case P41-16 (train 3698, val 436, test 938 slices) - split `splits/nextbrain_fold2.json`

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.3029 (0.0703) | [0.2820, 0.3237] | 0.2831 (0.0860) | [0.2636, 0.3025] | 9.1358 (1.9117) | [8.5794, 9.7220] |
| MRI to H&E | gray_level_LUT | 0.1367 (0.0444) | [0.1299, 0.1442] | 0.5258 (0.1356) | [0.4913, 0.5556] | 15.1863 (2.1761) | [14.8645, 15.5307] |
| MRI to LFB | mean_train_target | 0.3535 (0.0676) | [0.3337, 0.3738] | 0.2305 (0.0658) | [0.2170, 0.2453] | 7.8767 (1.5476) | [7.4392, 8.3401] |
| MRI to LFB | gray_level_LUT | 0.1451 (0.0444) | [0.1392, 0.1507] | 0.5337 (0.1254) | [0.5061, 0.5618] | 14.7403 (2.1143) | [14.4778, 15.0090] |

## Fold 3: held-out case P58-16 (train 3622, val 405, test 1045 slices) - split `splits/nextbrain_fold3.json`

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2491 (0.0570) | [0.2355, 0.2616] | 0.2945 (0.0866) | [0.2773, 0.3095] | 10.3223 (1.8278) | [9.8876, 10.8182] |
| MRI to H&E | gray_level_LUT | 0.1241 (0.0598) | [0.1170, 0.1326] | 0.5259 (0.1461) | [0.4902, 0.5571] | 14.8311 (2.7414) | [14.3489, 15.2727] |
| MRI to LFB | mean_train_target | 0.3290 (0.0578) | [0.3146, 0.3416] | 0.2200 (0.0770) | [0.2048, 0.2347] | 8.3608 (1.5037) | [8.0182, 8.7714] |
| MRI to LFB | gray_level_LUT | 0.1798 (0.0589) | [0.1701, 0.1902] | 0.5014 (0.1301) | [0.4750, 0.5263] | 12.8811 (2.1740) | [12.4950, 13.2328] |

## Fold 4: held-out case P85-18 (train 3637, val 441, test 994 slices) - split `splits/nextbrain_fold4.json`

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2602 (0.0623) | [0.2428, 0.2767] | 0.2521 (0.0976) | [0.2258, 0.2760] | 10.1718 (2.0900) | [9.6497, 10.7585] |
| MRI to H&E | gray_level_LUT | 0.1698 (0.0928) | [0.1499, 0.2018] | 0.4277 (0.1766) | [0.3728, 0.4749] | 12.7475 (2.7380) | [11.9556, 13.3559] |
| MRI to LFB | mean_train_target | 0.2897 (0.0622) | [0.2723, 0.3059] | 0.1921 (0.0750) | [0.1712, 0.2112] | 9.3082 (2.0155) | [8.8135, 9.8954] |
| MRI to LFB | gray_level_LUT | 0.1869 (0.1107) | [0.1630, 0.2269] | 0.4175 (0.1549) | [0.3681, 0.4599] | 11.8667 (2.6747) | [11.0495, 12.4335] |

## Fold 5: held-out case EX9-19 (train 3611, val 384, test 1077 slices) - split `splits/nextbrain_fold5.json`

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2948 (0.0582) | [0.2781, 0.3125] | 0.3256 (0.1047) | [0.2958, 0.3533] | 9.6145 (1.5310) | [9.1704, 10.0576] |
| MRI to H&E | gray_level_LUT | 0.2082 (0.0639) | [0.1910, 0.2281] | 0.4587 (0.1555) | [0.4136, 0.4986] | 12.3321 (2.1475) | [11.7279, 12.8824] |
| MRI to LFB | mean_train_target | 0.2630 (0.0458) | [0.2512, 0.2743] | 0.2155 (0.0769) | [0.1922, 0.2383] | 10.0555 (1.4142) | [9.6888, 10.4440] |
| MRI to LFB | gray_level_LUT | 0.1696 (0.0714) | [0.1534, 0.1942] | 0.4396 (0.1329) | [0.4014, 0.4713] | 13.2231 (2.4285) | [12.5076, 13.8029] |

Not computed: validation-set baseline scores; visual QC (all records `NOT_REVIEWED`); slice spacing in micrometers per block (UNVERIFIED); alignment accuracy between MRI and histology beyond the size check (UNVERIFIED); any trained model.
