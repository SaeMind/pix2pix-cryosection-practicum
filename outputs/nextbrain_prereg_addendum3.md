Written 2026-10-30T03:31:29Z (UTC)

# NextBrain pre-registration addendum 3 (protocol v1 confirmed; exploratory arms separated)

This addendum changes no rule. It records what has been seen, confirms protocol v1, and defines how any later change is handled.

## (a) What has been viewed

- Fold 3 H&E training had reached epoch 26 of 100 (last row of `outputs/nextbrain_fold3_he/history.csv`, read 2026-10-30T03:31:13Z UTC), and the validation curve through that epoch was viewed (validation masked L1, training L1, G and D losses).
- No test image, prediction or test metric of any fold has been viewed. No test evaluation has been started for any fold.

## (b) Protocol v1 is unchanged

- 100 epochs per fold (50 constant, 50 linear decay), no early stopping, queue unchanged (folds 1, 2, 4, 5 after fold 3, H&E only, `scripts/run_queue.py`).
- Evaluation checkpoint rule, as stated in the existing pre-registration documents:
  - `outputs/nextbrain_train_prereg.md:33`: "For full runs: best validation masked L1 (L1 on RGB in [0, 1] inside the tissue mask, mean over validation slices) evaluated once per epoch; keep the checkpoint with the lowest value."
  - `outputs/nextbrain_train_prereg.md:34`: "Test data is never used for selection, tuning or early stopping, and is not evaluated in this task."
  - `outputs/nextbrain_eval_addendum3.md:17`: "Selection uses validation only."
  - `outputs/nextbrain_eval_addendum3.md:21`: "after epoch 100, the best-validation checkpoint is evaluated on the test case exactly once (`scripts/eval_nextbrain_test.py` refuses to run if its result file already exists)."
- Checked against source: `scripts/eval_nextbrain_test.py:26` and `scripts/eval_nextbrain_test_fold.py:27` load `ckpt_best.pt`, and both refuse a second run (lines 19 and 20). The queue's automatic evaluation (`scripts/run_queue.py:88`) uses the per-fold script.

## (c) Exploratory arms

Any configuration change (early stopping, learning rate, loss weights, stain augmentation, capacity, discriminator off) is an exploratory arm: new files, a new output directory, labelled exploratory, and it never replaces a protocol v1 result.

## (d) Planned exploratory arm X1

- Fold 3, same split and same checkpoint-selection rule (lowest validation masked L1), L1-only training (discriminator off).
- Starts only after the queue has exited. Requires a new training script file; existing locked scripts are not edited.
- X1 was motivated by the fold 3 validation curve through epoch 26 (validation L1 above its epoch 3 value while D falls and G rises); this is disclosed here.

## (e) Fold 3 test evaluation

Runs once, manually, after `TRAINING_DONE` exists for fold 3.

## (f) Reporting

Protocol v1 results for all five folds are reported whatever they show, next to the lookup and mean-target baselines on the harness grid.
