# NextBrain training harness: fold 3 timing test (flagged blocks included)

Pre-registration: `outputs/nextbrain_train_prereg.md` plus `outputs/nextbrain_train_prereg_addendum1.md` (both hashed in `out/r4m_audit/LOCK_HASHES.txt` before this run). Fold 3 = test case Case 3 (P58-16). Retrospective multi-dataset evaluation; no test image was loaded or evaluated, no DigiMouse file or baselines output was read, no data or split was modified.

Files: config `configs/nextbrain_fold3_he.json`; script `scripts/train_nextbrain.py` (run: `python scripts/train_nextbrain.py --config configs/nextbrain_fold3_he.json --root ~/Data/NextBrain --mode timing`); splits `splits/nextbrain_fold3.json`; metadata `outputs/nextbrain_metadata/nextbrain_all_cases.csv`; raw numbers `outputs/nextbrain_timing.json`. Earlier run with the two flagged blocks excluded: `outputs/nextbrain_timing_with_exclusions.{json,md}`.

Test isolation: the script asserts, before opening any file and on every load, that no test-list record id and no P58-16 record is loaded. It passed.

## Setup

- Model: Pix2Pix, U-Net 256 generator ngf 32 (dropout on), PatchGAN ndf 32, vanilla GAN, L1 weight 100, input 1 channel (MRI), output 3 channels (H&E), batch size 1, Adam 2e-4 (0.5, 0.999), seed 1234, float32.
- Data: resize rule from `outputs/nextbrain_shape_audit.md` applied to every record.
- Records: train 3622, validation 405; no blocks excluded (owner decision, addendum 1). Case 4 block 28 and Case 5 block 48 (72 records, MRI/H&E size differences over 10 px, alignment UNVERIFIED) are therefore included and are stretched anisotropically by the resize rule.

## Timing (200 iterations, training split, one D step and one G step each)

| item | value |
|---|---|
| device | mps (PyTorch 2.4.0; CUDA not available) |
| seconds per iteration (mean of iterations 11 to 200) | 0.0560 (SD 0.0107); previous run 0.0483 |
| warm-up (first 10 iterations, total) | 1.24 s |
| memory: MPS driver_allocated_memory, sampled after each iteration (no peak API) | 402 MiB (sampled maximum, not a true peak) |
| process peak RSS (includes preloaded images) | 955 MiB |
| data load + preprocessing per record | 3.8 ms (train), 3.4 ms (validation) |
| one validation pass (405 records) | 13.3 s (previous run 37.1 s for 367 records) |

The 200 training records were preloaded before timing, so seconds per iteration excludes disk and decode time.

## Estimates for fold 3, one stain (training time plus one validation pass per epoch)

| epochs | estimated time |
|---|---|
| 1 | 216 s (0.06 h) |
| 50 | 10,809 s (3.00 h) |
| 100 | 21,617 s (6.00 h) |

Per epoch: 3622 iterations x 0.0560 s = 203 s training, plus 13 s validation.

## Extrapolation: 5 folds x 2 stains (H&E, LFB) x 100 epochs

Uses each fold's train/val counts (fold 1 3650/404; fold 2 3698/436; fold 3 3622/405; fold 4 3637/441; fold 5 3611/384) and the fold-3 seconds per iteration and validation time per record, assuming LFB runs at the same speed.

Total estimate: 217,677 s (60.47 h), about 2.5 days of continuous running.

## Sanity check (not a result)

- Validation masked L1 after the 200 iterations (untrained generator, 405 slices): 0.2004 (SD 0.0947); last-iteration G loss 7.73, D loss 0.134. No further training; no test image evaluated.

## UNVERIFIED

- Speed of other folds and of the LFB task (assumed equal); thermal or contention effects over a multi-hour run (seconds per iteration differed between the two runs, 0.048 and 0.056); convergence and adequacy of 100 epochs.
- The earlier run's validation pass (37 s) was much slower than this run's (13 s); the first pass likely included one-time warm-up, so this run's value is the better estimate.
- Memory on MPS is a sampled driver counter; PyTorch has no peak counter there.

Nothing was committed.
