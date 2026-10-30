# NextBrain baselines: validation-set scores (no model trained)

Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims. Pre-registration: `outputs/nextbrain_analysis_addendum2.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`), `outputs/nextbrain_prereg.md`.

Method: script `scripts/nextbrain_baselines_sensitivity.py`; raw numbers `outputs/nextbrain_baselines_sensitivity.json`. Baselines (mean training-target image; global MRI-to-RGB gray-level LUT) fitted on training records with Case 4 block 28 and Case 5 block 48 removed. Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mask = MRI nonzero after the pre-registered per-modality resize to 256. Mean and SD across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345) around the pooled slice mean.

Limitation: the tissue mask is MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED.

Records scored: each fold's validation blocks (4 training cases, whole blocks per the split file) minus the flagged blocks. Bootstrap blocks are the validation blocks pooled across cases.

## Fold 1 (test case P57-16): validation n=404 slices, fit on train n=3578 slices

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2604 (0.0792) | [0.2231, 0.3007] | 0.3019 (0.0818) | [0.2775, 0.3235] | 10.1958 (2.1312) | [9.1871, 11.2442] |
| MRI to H&E | gray_level_LUT | 0.1333 (0.0537) | [0.1125, 0.1573] | 0.5353 (0.1352) | [0.4822, 0.5761] | 14.5516 (2.5036) | [13.6694, 15.5169] |
| MRI to LFB | mean_train_target | 0.2920 (0.0573) | [0.2664, 0.3146] | 0.2227 (0.0697) | [0.1990, 0.2479] | 9.1745 (1.5874) | [8.5405, 9.9409] |
| MRI to LFB | gray_level_LUT | 0.1467 (0.0484) | [0.1371, 0.1587] | 0.5021 (0.1390) | [0.4464, 0.5612] | 14.0259 (2.2005) | [13.3786, 14.6640] |

## Fold 2 (test case P41-16): validation n=436 slices, fit on train n=3626 slices

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2983 (0.0723) | [0.2695, 0.3337] | 0.2631 (0.0888) | [0.2341, 0.2905] | 9.1108 (1.7354) | [8.3404, 9.8134] |
| MRI to H&E | gray_level_LUT | 0.1605 (0.0692) | [0.1371, 0.1865] | 0.4795 (0.1287) | [0.4399, 0.5167] | 13.5335 (2.5411) | [12.6763, 14.3419] |
| MRI to LFB | mean_train_target | 0.3272 (0.0503) | [0.3119, 0.3415] | 0.1932 (0.0794) | [0.1629, 0.2215] | 8.2776 (1.2002) | [7.9519, 8.6782] |
| MRI to LFB | gray_level_LUT | 0.1705 (0.0656) | [0.1550, 0.1886] | 0.4427 (0.1163) | [0.4127, 0.4740] | 13.0132 (2.4522) | [12.2809, 13.7236] |

## Fold 3 (test case P58-16): validation n=367 slices, fit on train n=3588 slices

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2690 (0.0542) | [0.2457, 0.2900] | 0.2937 (0.0975) | [0.2561, 0.3290] | 9.9306 (1.5994) | [9.2672, 10.6835] |
| MRI to H&E | gray_level_LUT | 0.1439 (0.0502) | [0.1346, 0.1558] | 0.4904 (0.1454) | [0.4341, 0.5355] | 14.0291 (2.2542) | [13.4660, 14.5444] |
| MRI to LFB | mean_train_target | 0.2949 (0.0560) | [0.2699, 0.3186] | 0.2141 (0.0706) | [0.1895, 0.2399] | 9.1133 (1.5076) | [8.4547, 9.8486] |
| MRI to LFB | gray_level_LUT | 0.1574 (0.0579) | [0.1426, 0.1728] | 0.4886 (0.1368) | [0.4401, 0.5384] | 13.6376 (2.3538) | [12.9881, 14.3514] |

## Fold 4 (test case P85-18): validation n=441 slices, fit on train n=3603 slices

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2823 (0.0495) | [0.2629, 0.3039] | 0.3048 (0.0989) | [0.2676, 0.3445] | 9.6904 (1.3264) | [9.1185, 10.2304] |
| MRI to H&E | gray_level_LUT | 0.1380 (0.0558) | [0.1232, 0.1544] | 0.5460 (0.1380) | [0.4952, 0.5853] | 14.6709 (2.4252) | [13.9674, 15.3836] |
| MRI to LFB | mean_train_target | 0.3205 (0.0770) | [0.2813, 0.3581] | 0.2332 (0.0754) | [0.2059, 0.2629] | 8.7510 (1.8824) | [7.8285, 9.7186] |
| MRI to LFB | gray_level_LUT | 0.1471 (0.0567) | [0.1351, 0.1618] | 0.5581 (0.1317) | [0.5171, 0.5929] | 14.1877 (2.5952) | [13.3983, 14.8922] |

## Fold 5 (test case EX9-19): validation n=384 slices, fit on train n=3573 slices

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2748 (0.0574) | [0.2533, 0.2973] | 0.2661 (0.1200) | [0.2118, 0.3123] | 9.8605 (1.6503) | [9.2418, 10.5177] |
| MRI to H&E | gray_level_LUT | 0.1443 (0.0590) | [0.1323, 0.1592] | 0.4773 (0.1981) | [0.3835, 0.5597] | 14.2384 (2.6393) | [13.3588, 14.9604] |
| MRI to LFB | mean_train_target | 0.3230 (0.0614) | [0.2961, 0.3493] | 0.2080 (0.0945) | [0.1694, 0.2452] | 8.5877 (1.5772) | [7.9318, 9.2974] |
| MRI to LFB | gray_level_LUT | 0.1651 (0.0656) | [0.1507, 0.1826] | 0.4648 (0.1773) | [0.3870, 0.5376] | 13.2320 (2.7501) | [12.2944, 14.0527] |

Not computed: any trained-model score; test-set scores (see `outputs/nextbrain_baselines_sensitivity.md`).
