# NextBrain analysis addendum 2: flagged-block rule, validation baselines, sensitivity analysis

Written 2026-10-29 (local), before `scripts/nextbrain_baselines_sensitivity.py` was written or run. The files `outputs/nextbrain_prereg.md`, `outputs/nextbrain_prereg_addendum1.md`, `outputs/nextbrain_train_prereg.md`, `outputs/nextbrain_train_prereg_addendum1.md`, `splits/nextbrain_fold{1..5}.json`, `outputs/nextbrain_metadata/*` and `outputs/nextbrain_baselines.{json,md}` are unchanged. Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims.

## (a) Flagged-block exclusion from training and validation

After visual QC on 2026-10-29 (`outputs/nextbrain_qc_flagged/`), Case 4 (P85-18) block 28 and Case 5 (EX9-19) block 48 (72 records: 38 + 34) are excluded from TRAINING and VALIDATION in every fold. Reason: the MRI and H&E canvases differ (block 28: MRI 754x1036 vs H&E 333x428; block 48: MRI 289x436 vs H&E 1049x992), and the pre-registered resize rule (MRI resized onto the target grid, then scaled and padded to 256) would stretch block 48's MRI by a factor of 1.60 relative to its H&E (aspect 1.057 / 0.663); block 28: 1.07 (0.778 / 0.728). Whether the content of these blocks is aligned is UNVERIFIED; the QC montages were not used to judge alignment.

This reverses addendum 1 of the training pre-registration (which had withdrawn the exclusion). Mechanism: `exclude_blocks` in the config(s) under `configs/` becomes `["P85-18/28", "EX9-19/48"]`.

Order of events, stated as it happened. The decision was made before any model was trained for evaluation and before any validation or test score of a trained model or of a baseline restricted by this rule exists. It was NOT made before every score of any kind existed:
- The test-set baselines of `outputs/nextbrain_baselines.md` (fitted with the flagged blocks included in training) were computed before this decision; they are unchanged and are the "previous" reference in the sensitivity report.
- Two fold-3 timing runs (200 Pix2Pix iterations, then one validation pass, sanity only; `outputs/nextbrain_timing.json` without exclusion, masked validation L1 0.2004; `outputs/nextbrain_timing_with_exclusions.json` with the exclusion, 0.1925) were run earlier. They are not used for any design choice here, and no test record was loaded.
- The decision rests on image sizes and visual QC, not on any score.

## (b) Test sets and reporting

Test sets keep all complete triplets in every fold. Every test metric is reported two ways: excluding the 72 flagged records (primary) and including them (secondary). The flagged records sit in the test sets of folds 4 (block 28, 38 records) and 5 (block 48, 34 records) only; in folds 1 to 3 they are in training or validation, so primary and secondary test sets are identical there.

Baselines (mean training-target image; global MRI-to-RGB gray-level LUT) are refitted for this analysis on training records with the flagged blocks removed. Preprocessing, masks, metrics and bootstrap are as in `scripts/nextbrain_baselines.py` (each modality resized independently per `outputs/nextbrain_prereg.md`; block-level bootstrap, 10,000 resamples, seed 12345).

## (c) Validation-set baseline scores

Per fold, both baselines are scored on that fold's validation records (flagged blocks removed), for MRI to H&E and MRI to LFB, with the same metrics and block-level bootstrap CIs (bootstrap over validation blocks pooled across the training cases). Output: `outputs/nextbrain_baselines_validation.md`. Sensitivity output: `outputs/nextbrain_baselines_sensitivity.md`. Values are not known when this addendum is written.

## (d) Limitation

The tissue mask is the MRI nonzero mask. Pixels where the MRI is zero inside tissue (the MRI contains black gaps and stair-stepped holes in places) are not scored, and tissue where the histology exists but the MRI is zero is not scored either. Scores therefore describe MRI-covered tissue only. This is a limitation of every metric reported here.

## Not covered (UNVERIFIED)

Alignment accuracy between MRI and histology; slice spacing in micrometers; whether other blocks have within-size-match misalignment; any trained-model result.
