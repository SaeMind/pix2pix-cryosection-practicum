# NextBrain baselines: test-set sensitivity to the flagged blocks (no model trained)

Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims. Pre-registration: `outputs/nextbrain_analysis_addendum2.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`), `outputs/nextbrain_prereg.md`.

Method: script `scripts/nextbrain_baselines_sensitivity.py`; raw numbers `outputs/nextbrain_baselines_sensitivity.json`. Baselines (mean training-target image; global MRI-to-RGB gray-level LUT) fitted on training records with Case 4 block 28 and Case 5 block 48 removed. Masked L1 on RGB in [0,1] (primary), masked-map SSIM, masked PSNR; mask = MRI nonzero after the pre-registered per-modality resize to 256. Mean and SD across slices; CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345) around the pooled slice mean.

Limitation: the tissue mask is MRI nonzero, so pixels where the MRI is zero inside tissue are not scored. Alignment between MRI and histology is UNVERIFIED.

Primary = test records excluding the 72 flagged records; secondary = all complete triplets. The flagged records are in the test set only in folds 4 (block 28) and 5 (block 48); in folds 1 to 3 the two tables are identical.

## Fold 1: held-out case P57-16 (test 1018 slices, of which 0 flagged; fit on train n=3578)

### Primary: excluding flagged records (n=1018)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2620 (0.0621) | [0.2464, 0.2764] | 0.2372 (0.0904) | [0.2184, 0.2547] | 10.0582 (1.7681) | [9.6366, 10.5274] |
| MRI to H&E | gray_level_LUT | 0.1499 (0.0737) | [0.1390, 0.1622] | 0.4491 (0.1455) | [0.4147, 0.4799] | 13.6103 (2.6129) | [13.1667, 14.0035] |
| MRI to LFB | mean_train_target | 0.3390 (0.0529) | [0.3272, 0.3510] | 0.1875 (0.0706) | [0.1756, 0.1995] | 8.1252 (1.2695) | [7.8417, 8.4309] |
| MRI to LFB | gray_level_LUT | 0.1902 (0.0726) | [0.1826, 0.1988] | 0.4385 (0.1355) | [0.4118, 0.4645] | 12.3281 (2.4182) | [12.0113, 12.6062] |

### Secondary: including flagged records (n=1018)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2620 (0.0621) | [0.2464, 0.2764] | 0.2372 (0.0904) | [0.2184, 0.2547] | 10.0582 (1.7681) | [9.6366, 10.5274] |
| MRI to H&E | gray_level_LUT | 0.1499 (0.0737) | [0.1390, 0.1622] | 0.4491 (0.1455) | [0.4147, 0.4799] | 13.6103 (2.6129) | [13.1667, 14.0035] |
| MRI to LFB | mean_train_target | 0.3390 (0.0529) | [0.3272, 0.3510] | 0.1875 (0.0706) | [0.1756, 0.1995] | 8.1252 (1.2695) | [7.8417, 8.4309] |
| MRI to LFB | gray_level_LUT | 0.1902 (0.0726) | [0.1826, 0.1988] | 0.4385 (0.1355) | [0.4118, 0.4645] | 12.3281 (2.4182) | [12.0113, 12.6062] |

## Fold 2: held-out case P41-16 (test 938 slices, of which 0 flagged; fit on train n=3626)

### Primary: excluding flagged records (n=938)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.3007 (0.0707) | [0.2797, 0.3216] | 0.2836 (0.0863) | [0.2640, 0.3030] | 9.1739 (1.9305) | [8.6131, 9.7672] |
| MRI to H&E | gray_level_LUT | 0.1352 (0.0447) | [0.1283, 0.1425] | 0.5215 (0.1333) | [0.4878, 0.5507] | 15.2264 (2.1981) | [14.9029, 15.5725] |
| MRI to LFB | mean_train_target | 0.3505 (0.0676) | [0.3306, 0.3708] | 0.2309 (0.0661) | [0.2172, 0.2458] | 7.9224 (1.5626) | [7.4811, 8.3911] |
| MRI to LFB | gray_level_LUT | 0.1436 (0.0446) | [0.1380, 0.1490] | 0.5305 (0.1241) | [0.5032, 0.5580] | 14.7662 (2.1352) | [14.5007, 15.0381] |

### Secondary: including flagged records (n=938)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.3007 (0.0707) | [0.2797, 0.3216] | 0.2836 (0.0863) | [0.2640, 0.3030] | 9.1739 (1.9305) | [8.6131, 9.7672] |
| MRI to H&E | gray_level_LUT | 0.1352 (0.0447) | [0.1283, 0.1425] | 0.5215 (0.1333) | [0.4878, 0.5507] | 15.2264 (2.1981) | [14.9029, 15.5725] |
| MRI to LFB | mean_train_target | 0.3505 (0.0676) | [0.3306, 0.3708] | 0.2309 (0.0661) | [0.2172, 0.2458] | 7.9224 (1.5626) | [7.4811, 8.3911] |
| MRI to LFB | gray_level_LUT | 0.1436 (0.0446) | [0.1380, 0.1490] | 0.5305 (0.1241) | [0.5032, 0.5580] | 14.7662 (2.1352) | [14.5007, 15.0381] |

## Fold 3: held-out case P58-16 (test 1045 slices, of which 0 flagged; fit on train n=3588)

### Primary: excluding flagged records (n=1045)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2475 (0.0571) | [0.2339, 0.2600] | 0.2951 (0.0868) | [0.2779, 0.3102] | 10.3548 (1.8344) | [9.9193, 10.8505] |
| MRI to H&E | gray_level_LUT | 0.1236 (0.0606) | [0.1163, 0.1323] | 0.5195 (0.1452) | [0.4837, 0.5510] | 14.8098 (2.7657) | [14.3242, 15.2574] |
| MRI to LFB | mean_train_target | 0.3270 (0.0579) | [0.3126, 0.3396] | 0.2205 (0.0772) | [0.2052, 0.2351] | 8.3954 (1.5107) | [8.0515, 8.8075] |
| MRI to LFB | gray_level_LUT | 0.1769 (0.0595) | [0.1674, 0.1871] | 0.5031 (0.1308) | [0.4766, 0.5284] | 12.9392 (2.2074) | [12.5505, 13.2900] |

### Secondary: including flagged records (n=1045)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2475 (0.0571) | [0.2339, 0.2600] | 0.2951 (0.0868) | [0.2779, 0.3102] | 10.3548 (1.8344) | [9.9193, 10.8505] |
| MRI to H&E | gray_level_LUT | 0.1236 (0.0606) | [0.1163, 0.1323] | 0.5195 (0.1452) | [0.4837, 0.5510] | 14.8098 (2.7657) | [14.3242, 15.2574] |
| MRI to LFB | mean_train_target | 0.3270 (0.0579) | [0.3126, 0.3396] | 0.2205 (0.0772) | [0.2052, 0.2351] | 8.3954 (1.5107) | [8.0515, 8.8075] |
| MRI to LFB | gray_level_LUT | 0.1769 (0.0595) | [0.1674, 0.1871] | 0.5031 (0.1308) | [0.4766, 0.5284] | 12.9392 (2.2074) | [12.5505, 13.2900] |

## Fold 4: held-out case P85-18 (test 994 slices, of which 38 flagged; fit on train n=3603)

### Primary: excluding flagged records (n=956)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2632 (0.0580) | [0.2482, 0.2777] | 0.2594 (0.0936) | [0.2360, 0.2809] | 10.0138 (1.6730) | [9.5878, 10.4566] |
| MRI to H&E | gray_level_LUT | 0.1561 (0.0629) | [0.1483, 0.1643] | 0.4430 (0.1556) | [0.4018, 0.4804] | 13.0323 (2.3106) | [12.6393, 13.4150] |
| MRI to LFB | mean_train_target | 0.2934 (0.0557) | [0.2793, 0.3073] | 0.1973 (0.0725) | [0.1785, 0.2149] | 9.1280 (1.4874) | [8.7505, 9.5169] |
| MRI to LFB | gray_level_LUT | 0.1694 (0.0658) | [0.1614, 0.1781] | 0.4326 (0.1302) | [0.3986, 0.4653] | 12.1738 (2.1046) | [11.8447, 12.4880] |

### Secondary: including flagged records (n=994)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2588 (0.0621) | [0.2416, 0.2752] | 0.2527 (0.0980) | [0.2263, 0.2768] | 10.1979 (2.0831) | [9.6773, 10.7802] |
| MRI to H&E | gray_level_LUT | 0.1699 (0.0930) | [0.1500, 0.2019] | 0.4256 (0.1759) | [0.3708, 0.4727] | 12.7267 (2.7368) | [11.9362, 13.3348] |
| MRI to LFB | mean_train_target | 0.2883 (0.0618) | [0.2710, 0.3042] | 0.1925 (0.0752) | [0.1715, 0.2117] | 9.3340 (2.0073) | [8.8419, 9.9147] |
| MRI to LFB | gray_level_LUT | 0.1873 (0.1109) | [0.1634, 0.2274] | 0.4154 (0.1542) | [0.3661, 0.4577] | 11.8368 (2.6691) | [11.0208, 12.4018] |

### Flagged records only (n=38, a single block; descriptive, CI not computed)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.1489 (0.0607) | [not computed: 1 block] | 0.0845 (0.0319) | [not computed: 1 block] | 14.8277 (4.6175) | [not computed: 1 block] |
| MRI to H&E | gray_level_LUT | 0.5180 (0.0270) | [not computed: 1 block] | -0.0129 (0.0138) | [not computed: 1 block] | 5.0386 (0.3042) | [not computed: 1 block] |
| MRI to LFB | mean_train_target | 0.1598 (0.0714) | [not computed: 1 block] | 0.0706 (0.0234) | [not computed: 1 block] | 14.5153 (4.7297) | [not computed: 1 block] |
| MRI to LFB | gray_level_LUT | 0.6383 (0.0343) | [not computed: 1 block] | -0.0179 (0.0135) | [not computed: 1 block] | 3.3580 (0.3031) | [not computed: 1 block] |

## Fold 5: held-out case EX9-19 (test 1077 slices, of which 34 flagged; fit on train n=3573)

### Primary: excluding flagged records (n=1043)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2943 (0.0590) | [0.2767, 0.3125] | 0.3338 (0.0957) | [0.3093, 0.3580] | 9.6358 (1.5569) | [9.1734, 10.1028] |
| MRI to H&E | gray_level_LUT | 0.2006 (0.0496) | [0.1882, 0.2136] | 0.4727 (0.1377) | [0.4364, 0.5042] | 12.5354 (1.8754) | [12.0766, 12.9809] |
| MRI to LFB | mean_train_target | 0.2602 (0.0447) | [0.2486, 0.2713] | 0.2207 (0.0721) | [0.2000, 0.2416] | 10.1309 (1.3994) | [9.7589, 10.5245] |
| MRI to LFB | gray_level_LUT | 0.1593 (0.0446) | [0.1514, 0.1674] | 0.4533 (0.1114) | [0.4287, 0.4768] | 13.4854 (1.9916) | [13.0618, 13.9026] |

### Secondary: including flagged records (n=1077)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2941 (0.0584) | [0.2774, 0.3118] | 0.3256 (0.1046) | [0.2958, 0.3533] | 9.6293 (1.5373) | [9.1830, 10.0747] |
| MRI to H&E | gray_level_LUT | 0.2080 (0.0639) | [0.1909, 0.2279] | 0.4589 (0.1556) | [0.4138, 0.4989] | 12.3368 (2.1498) | [11.7321, 12.8876] |
| MRI to LFB | mean_train_target | 0.2621 (0.0458) | [0.2503, 0.2734] | 0.2155 (0.0769) | [0.1922, 0.2382] | 10.0731 (1.4203) | [9.7023, 10.4647] |
| MRI to LFB | gray_level_LUT | 0.1694 (0.0714) | [0.1533, 0.1940] | 0.4397 (0.1330) | [0.4015, 0.4714] | 13.2263 (2.4308) | [12.5101, 13.8065] |

### Flagged records only (n=34, a single block; descriptive, CI not computed)

| task | baseline | L1 mean (SD) | L1 95% CI | SSIM mean (SD) | SSIM 95% CI | PSNR mean (SD) | PSNR 95% CI |
|---|---|---|---|---|---|---|---|
| MRI to H&E | mean_train_target | 0.2891 (0.0331) | [not computed: 1 block] | 0.0754 (0.0379) | [not computed: 1 block] | 9.4283 (0.6882) | [not computed: 1 block] |
| MRI to H&E | gray_level_LUT | 0.4354 (0.0260) | [not computed: 1 block] | 0.0363 (0.0325) | [not computed: 1 block] | 6.2449 (0.4081) | [not computed: 1 block] |
| MRI to LFB | mean_train_target | 0.3208 (0.0431) | [not computed: 1 block] | 0.0542 (0.0286) | [not computed: 1 block] | 8.3020 (0.7719) | [not computed: 1 block] |
| MRI to LFB | gray_level_LUT | 0.4799 (0.0292) | [not computed: 1 block] | 0.0238 (0.0239) | [not computed: 1 block] | 5.2777 (0.4404) | [not computed: 1 block] |

## Reference: earlier baselines (flagged blocks included in training, all test records), L1 mean, from `outputs/nextbrain_baselines.json`

| fold | task | baseline | earlier L1 | this analysis, secondary L1 | difference (this minus earlier) |
|---|---|---|---|---|---|
| 1 | MRI to H&E | mean_train_target | 0.2639 | 0.2620 | -0.0020 |
| 1 | MRI to H&E | gray_level_LUT | 0.1501 | 0.1499 | -0.0002 |
| 1 | MRI to LFB | mean_train_target | 0.3419 | 0.3390 | -0.0028 |
| 1 | MRI to LFB | gray_level_LUT | 0.1910 | 0.1902 | -0.0008 |
| 2 | MRI to H&E | mean_train_target | 0.3029 | 0.3007 | -0.0022 |
| 2 | MRI to H&E | gray_level_LUT | 0.1367 | 0.1352 | -0.0016 |
| 2 | MRI to LFB | mean_train_target | 0.3535 | 0.3505 | -0.0030 |
| 2 | MRI to LFB | gray_level_LUT | 0.1451 | 0.1436 | -0.0014 |
| 3 | MRI to H&E | mean_train_target | 0.2491 | 0.2475 | -0.0016 |
| 3 | MRI to H&E | gray_level_LUT | 0.1241 | 0.1236 | -0.0005 |
| 3 | MRI to LFB | mean_train_target | 0.3290 | 0.3270 | -0.0020 |
| 3 | MRI to LFB | gray_level_LUT | 0.1798 | 0.1769 | -0.0029 |
| 4 | MRI to H&E | mean_train_target | 0.2602 | 0.2588 | -0.0013 |
| 4 | MRI to H&E | gray_level_LUT | 0.1698 | 0.1699 | +0.0001 |
| 4 | MRI to LFB | mean_train_target | 0.2897 | 0.2883 | -0.0015 |
| 4 | MRI to LFB | gray_level_LUT | 0.1869 | 0.1873 | +0.0004 |
| 5 | MRI to H&E | mean_train_target | 0.2948 | 0.2941 | -0.0007 |
| 5 | MRI to H&E | gray_level_LUT | 0.2082 | 0.2080 | -0.0002 |
| 5 | MRI to LFB | mean_train_target | 0.2630 | 0.2621 | -0.0009 |
| 5 | MRI to LFB | gray_level_LUT | 0.1696 | 0.1694 | -0.0001 |

Not computed: any trained-model score; per-block bootstrap for the flagged-only subsets (one block each); alignment accuracy (UNVERIFIED).
