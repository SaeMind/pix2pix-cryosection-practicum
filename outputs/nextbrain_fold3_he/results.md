# NextBrain fold 3 MRI to H&E: Pix2Pix test result (one-time evaluation)

Retrospective multi-dataset evaluation. One held-out case (single animal-equivalent specimen, one seed): within-case description only, no significance claims, no clinical validation. Pre-registration: `outputs/nextbrain_eval_addendum3.md`, `outputs/nextbrain_analysis_addendum2.md`, `outputs/nextbrain_train_prereg.md` (hashes in `out/r4m_audit/LOCK_HASHES.txt`).

Model: best-validation checkpoint, epoch 3 of 100, validation masked L1 0.1370; checkpoint SHA-256 `fa9107b3e1fcb00866cb55232837f74006e49aff86eebf9262d89846aa3f49fa`. Test case P58-16, 1045 slices, evaluated exactly once after training finished. Metrics on the harness grid, mask = MRI nonzero (pixels where the MRI is zero inside tissue are not scored). CI = block-level bootstrap 95 percent (10,000 resamples of blocks, seed 12345). The test case contains 0 of the 72 flagged records (they are in fold 3 training or validation), so primary and secondary are identical for this fold by construction.

### Primary: excluding flagged records

| method | grid | L1 mean (SD) [95% CI] | SSIM mean (SD) [95% CI] | PSNR mean (SD) [95% CI] |
|---|---|---|---|---|
| Pix2Pix (best-validation checkpoint, epoch 3) | harness | 0.1380 (0.0709) [0.1291, 0.1476] | 0.4766 (0.1412) [0.4464, 0.5029] | 13.6394 (2.7389) [13.2179, 14.0351] |
| mean_train_target | harness | 0.2475 (0.0571) [0.2339, 0.2600] | 0.2951 (0.0868) [0.2779, 0.3102] | 10.3548 (1.8344) [9.9193, 10.8505] |
| gray_level_LUT | harness | 0.1237 (0.0606) [0.1163, 0.1323] | 0.5195 (0.1452) [0.4838, 0.5510] | 14.8098 (2.7653) [14.3237, 15.2573] |
| mean_train_target | original (reference only) | 0.2475 (0.0571) [0.2339, 0.2600] | 0.2951 (0.0868) [0.2779, 0.3102] | 10.3548 (1.8344) [9.9193, 10.8505] |
| gray_level_LUT | original (reference only) | 0.1236 (0.0606) [0.1163, 0.1323] | 0.5195 (0.1452) [0.4837, 0.5510] | 14.8098 (2.7657) [14.3242, 15.2574] |

### Secondary: including flagged records

| method | grid | L1 mean (SD) [95% CI] | SSIM mean (SD) [95% CI] | PSNR mean (SD) [95% CI] |
|---|---|---|---|---|
| Pix2Pix (best-validation checkpoint, epoch 3) | harness | 0.1380 (0.0709) [0.1291, 0.1476] | 0.4766 (0.1412) [0.4464, 0.5029] | 13.6394 (2.7389) [13.2179, 14.0351] |
| mean_train_target | harness | 0.2475 (0.0571) [0.2339, 0.2600] | 0.2951 (0.0868) [0.2779, 0.3102] | 10.3548 (1.8344) [9.9193, 10.8505] |
| gray_level_LUT | harness | 0.1237 (0.0606) [0.1163, 0.1323] | 0.5195 (0.1452) [0.4838, 0.5510] | 14.8098 (2.7653) [14.3237, 15.2573] |
| mean_train_target | original (reference only) | 0.2475 (0.0571) [0.2339, 0.2600] | 0.2951 (0.0868) [0.2779, 0.3102] | 10.3548 (1.8344) [9.9193, 10.8505] |
| gray_level_LUT | original (reference only) | 0.1236 (0.0606) [0.1163, 0.1323] | 0.5195 (0.1452) [0.4837, 0.5510] | 14.8098 (2.7657) [14.3242, 15.2574] |

UNVERIFIED: alignment between MRI and histology; generalization beyond this case; sensitivity to seed; whether differences versus the baselines would persist in other folds or for LFB (not run).
