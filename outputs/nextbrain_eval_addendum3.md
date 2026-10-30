# NextBrain evaluation addendum 3: comparison grid, fold 3 MRI-to-H&E run

Written 2026-10-29 (local), before `scripts/nextbrain_baselines_harness_grid.py` was written or run and before the training run was launched. Unchanged by this addendum: `outputs/nextbrain_prereg.md`, its addenda, `outputs/nextbrain_train_prereg.md` and addendum 1, `outputs/nextbrain_analysis_addendum2.md`, `splits/nextbrain_fold{1..5}.json`, `configs/nextbrain_fold3_he.json`, `outputs/nextbrain_baselines*.{json,md}`. Retrospective multi-dataset evaluation; one test case per fold, so within-case descriptions only, no significance claims.

## Comparison grid

The model and the baselines are compared on the SAME grid, the harness grid: the MRI is resampled (bilinear) onto the H&E grid, then both are scaled so the longer side is 256 (bilinear) and center-padded with zeros to 256x256; the tissue mask is the nonzero MRI on that 256x256 grid. The original-grid baselines (each modality resized independently, `scripts/nextbrain_baselines.py`) differ from this grid whenever MRI and H&E sizes differ by even one pixel, so their values are not directly comparable with model scores.

- The mean-target and gray-level-lookup baselines are recomputed on the harness grid for the comparison (new script `scripts/nextbrain_baselines_harness_grid.py`; fit on fold-3 training records after the addendum 2 exclusion; no existing script is changed).
- Both the original-grid values (`outputs/nextbrain_baselines_sensitivity.md`, `outputs/nextbrain_baselines_validation.md`) and the harness-grid values (`outputs/nextbrain_baselines_harness_grid.md`) are reported, labelled by grid.
- Primary test result excludes the 72 flagged records (Case 4 block 28, Case 5 block 48); secondary includes them. In fold 3 the test case is Case 3 (P58-16), which contains none of the 72 flagged records (they are in fold 3 training or validation), so primary and secondary are identical for fold 3 by construction; both are still reported.
- Addendum 1 of the training pre-registration (`outputs/nextbrain_train_prereg_addendum1.md`) states that `exclude_blocks` is empty; that text is superseded by `outputs/nextbrain_analysis_addendum2.md`: `exclude_blocks` is `["P85-18/28", "EX9-19/48"]`, applied to training and validation only.

## Run protocol (fold 3, MRI to H&E)

- Configuration as in `configs/nextbrain_fold3_he.json` (not changed) and `outputs/nextbrain_train_prereg.md`: 100 epochs (50 constant, 50 linear decay to 0), batch size 1, Adam 2e-4, seed 1234, no augmentation. A `train` mode is added to `scripts/train_nextbrain.py` (the `timing` mode is kept); the file is hashed after that edit and before launch.
- Checkpoints: the latest state is overwritten every epoch (resumable), plus the best-validation checkpoint (lowest validation masked L1, strict improvement). Selection uses validation only.
- The test case (P58-16) is not loaded during training or selection; the harness asserts it. The baseline scoring on the harness grid reads test images but uses them only for scoring (the baselines are fit on training records only), before any model output exists, and affects no training or selection decision.
- Validation and test inference use the generator in eval mode (dropout off, batch-norm running statistics).
- Epoch-10 check: validation masked L1 is printed next to the 0.1925 reference and the validation lookup baselines. The 0.1925 reference is the validation L1 of the generator after 200 iterations in the timing run (`outputs/nextbrain_timing_with_exclusions.json`), not of a truly untrained network. If the minimum validation L1 over epochs 1 to 10 has not dropped below 0.1925, the run stops and is reported (this reading of "by epoch 10" is an interpretation).
- Test evaluation: after epoch 100, the best-validation checkpoint is evaluated on the test case exactly once (`scripts/eval_nextbrain_test.py` refuses to run if its result file already exists). No result of that evaluation can change any choice made here.

## Limitation and UNVERIFIED

Mask = MRI nonzero (pixels where the MRI is zero inside tissue are not scored). Alignment between MRI and histology, convergence within 100 epochs, and the speed estimate (about 5.9 h from the timing run) are UNVERIFIED. A single seed, one held-out case: no significance claim.
