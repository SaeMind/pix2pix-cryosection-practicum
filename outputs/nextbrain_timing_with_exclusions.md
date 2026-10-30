# NextBrain training harness: fold 3 timing test

Pre-registration: `outputs/nextbrain_train_prereg.md` (SHA-256 and UTC timestamp in `out/r4m_audit/LOCK_HASHES.txt`, written before the harness). Fold 3 = test case Case 3 (P58-16). Retrospective multi-dataset evaluation; no test image was loaded or evaluated, no DigiMouse file or baselines output was read, no data or split was modified.

Files: config `configs/nextbrain_fold3_he.json`; script `scripts/train_nextbrain.py` (run: `python scripts/train_nextbrain.py --config configs/nextbrain_fold3_he.json --root ~/Data/NextBrain --mode timing`); splits `splits/nextbrain_fold3.json`; metadata `outputs/nextbrain_metadata/nextbrain_all_cases.csv`; raw numbers `outputs/nextbrain_timing.json`.

Test isolation: the script asserts, before opening any file and again on every load, that no record id from the split's test list and no record of subject P58-16 is loaded. It passed.

## Setup

- Model: Pix2Pix, U-Net 256 generator ngf 32 (dropout on), PatchGAN ndf 32, vanilla GAN, L1 weight 100, input 1 channel (MRI), output 3 channels (H&E), batch size 1, Adam 2e-4 (0.5, 0.999), seed 1234, float32.
- Data: resize rule from `outputs/nextbrain_shape_audit.md` (MRI resampled to H&E grid, bilinear; longer side to 256; zero-pad to 256x256).
- Records after exclusion: train 3588, validation 367. Excluded blocks: EX9-19/48, P85-18/28 (72 records; both flagged in the shape audit for MRI/H&E size differences over 10 px). Case 4 block 28 was in fold-3 validation, Case 5 block 48 in fold-3 training. This exclusion is a declared, provisional departure from the data-inclusion rule, pending visual QC; it is reversible via `exclude_blocks` in the config.

## Timing (200 iterations, training split, one D step and one G step each)

| item | value |
|---|---|
| device | mps (PyTorch 2.4.0; CUDA not available) |
| seconds per iteration (mean of iterations 11 to 200) | 0.0483 (SD 0.0007) |
| warm-up (first 10 iterations, total) | 1.70 s |
| memory: MPS driver_allocated_memory, sampled after each iteration (no peak API) | 402 MiB (a sampled maximum, not a true peak) |
| process peak RSS (includes preloaded images) | 990 MiB |
| data load + preprocessing per record (JPEG decode, resize, pad) | 3.8 ms (train), 3.4 ms (validation) |
| one validation pass (367 records, eval mode) | 37.1 s |

The 200 training records were preloaded before timing, so seconds per iteration excludes disk and decode time. Preloading the whole fold-3 training split would cost about 14 s once and about 0.88 GiB of uint8 RAM (arithmetic from the measured per-record time, not measured for the full set).

## Estimates for fold 3, one stain (training time plus one validation pass per epoch)

| epochs | estimated time |
|---|---|
| 1 | 211 s (0.06 h) |
| 50 | 10,525 s (2.92 h) |
| 100 | 21,050 s (5.85 h) |

Per epoch: 3588 iterations x 0.0483 s = 173 s training, plus 37 s validation.

## Extrapolation: 5 folds x 2 stains (H&E, LFB) x 100 epochs

Uses each fold's training and validation counts after exclusion (train/val: fold 1 3578/404; fold 2 3626/436; fold 3 3588/367; fold 4 3603/441; fold 5 3573/384) and the fold-3 seconds per iteration and validation time per record, assuming the LFB task has the same speed.

Total estimate: 214,758 s (59.65 h), about 2.5 days of continuous running.

## Sanity check (not a result)

- Validation masked L1 after the 200 iterations (untrained generator, 367 validation slices): 0.1925 (SD across slices 0.0663); last-iteration G loss 10.80, D loss 0.352. No further training was run and no test image was evaluated.

## UNVERIFIED

- Speed of folds other than fold 3 and of the LFB task (assumed equal); thermal throttling or contention over a multi-hour run; convergence behavior, and whether 100 epochs is adequate.
- The validation pass (101 ms per record) is slower than a training iteration (48 ms); it was measured once and probably includes per-slice host synchronization, so it may be reducible. It contributes about 18% of the 100-epoch estimate.
- The memory figure on MPS comes from the driver allocation counter sampled after each iteration; PyTorch offers no peak counter there.

Nothing was committed. New untracked files: `scripts/train_nextbrain.py`, `configs/nextbrain_fold3_he.json`, `scripts/nextbrain_shape_audit.py`, plus ignored `outputs/` files; `README.md` has an uncommitted licensing section.
