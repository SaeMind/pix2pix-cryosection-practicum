# NextBrain Pix2Pix training pre-registration (fixed before the harness is written or run)

Scope: retrospective multi-dataset evaluation; no clinical claim. This file covers the training harness and the 200-iteration timing test on fold 3
(test case = Case 3, P58-16). Folds, mask, metrics, inclusion rule and splits remain those of `outputs/nextbrain_prereg.md` and
`outputs/nextbrain_prereg_addendum1.md`. No DigiMouse file and no baselines output is read or modified by this work.

## Architecture (Pix2Pix, reduced capacity)
- Repo code: `models/networks.py` (`define_G`, `define_D`, `GANLoss`), pix2pix objective as in `models/pix2pix_model.py`.
- Generator: `unet_256`, ngf 32, batch norm, dropout on (upstream pix2pix default), init normal 0.02.
- Discriminator: PatchGAN `basic` (3 layers), ndf 32, batch norm, conditional on (input, output) concatenated (1 + 3 = 4 channels).
- Losses: GAN on, `vanilla` (BCE with logits as in the repo), L1 weight 100. D loss = 0.5 * (fake + real).
- Input: MRI, 1 channel. Output: RGB, 3 channels. Task for this harness: MRI to H&E first; the same config with the LFB target is the second stain.

## Data and resize rule (from `outputs/nextbrain_shape_audit.md`)
- Per record: resample the MRI to the H&E grid (`size = HE.size`) with bilinear interpolation (LFB already equals the H&E size in all records);
  then scale the pair so the longer side is 256 (bilinear) and center-pad with zeros to 256x256. Intensities mapped to [-1, 1] by x/127.5 - 1.
- Tissue mask = nonzero MRI on the final 256x256 grid.
- Augmentation: none (no flips, no crops, no jitter).
- Records: only those in `splits/nextbrain_fold3.json` (train, val). The test list is never loaded: the code asserts that no record of the test case (P58-16),
  and no id from the split's `test` list, is loaded in training or validation.
- Declared handling of the two blocks flagged in the shape audit (MRI/HE size difference over 10 px, possible misalignment, 72 records): Case 4 block 28 (P85-18/28, 38 records, in fold 3 validation)
  and Case 5 block 48 (EX9-19/48, 34 records, in fold 3 training). The resize rule above would distort them, so the harness excludes these two blocks
  from training and validation by a config list (`exclude_blocks`). This departs from the data-inclusion rule of `outputs/nextbrain_prereg.md` and is made now, before any training loss or validation value exists, with
  the test set untouched. It is provisional pending visual QC and can be reverted by emptying the list. It does not alter the already-built splits or the baselines.

## Optimization
- Seed 1234 for Python `random`, NumPy and PyTorch; training records shuffled each epoch with a `torch.Generator` seeded 1234 + epoch.
- Adam, lr 2e-4, betas (0.5, 0.999), batch size 1, one D step and one G step per iteration (upstream order: G forward, D update, then G update).
- Learning-rate policy for full runs: linear, 50 epochs constant then 50 epochs linear decay to 0 (100 epochs). The timing test uses the constant rate 2e-4 and does not run epochs.
- Precision: float32.

## Selection rule
- For full runs: best validation masked L1 (L1 on RGB in [0, 1] inside the tissue mask, mean over validation slices) evaluated once per epoch; keep the checkpoint with the lowest value.
- Test data is never used for selection, tuning or early stopping, and is not evaluated in this task.

## Timing test (this task only)
- 200 iterations on the fold-3 training split (after exclusions), batch size 1, fixed seed; the first 10 iterations are timed separately as warm-up and excluded from seconds-per-iteration.
- Device preference: CUDA, then MPS, then CPU; the device used is reported. Peak memory: device allocator statistic (MPS current/driver allocated, CUDA max allocated) or process peak RSS for CPU; the statistic used is named in the report.
- Validation masked L1 once after the 200 iterations, on the fold-3 validation records (after exclusions), as a sanity check only; no further training.
- Estimates: seconds per iteration x training records per epoch for 1, 50 and 100 epochs, plus the measured time of one validation pass per epoch; extrapolation to 5 folds x 2 stains
  uses each fold's training-record count from its split file (minus excluded blocks) and the fold-3 seconds per iteration. These are estimates (UNVERIFIED for other folds' speed and for convergence behavior).

## Not allowed
- Loading or scoring test-case records; using labels (`slices_labels*`) as an input; changing the architecture, seed, rule or selection criterion after seeing any validation value.
