# NextBrain pre-registration (fixed before any NextBrain metric is computed)

Scope: retrospective multi-dataset evaluation. Nothing here is clinical validation. This file is hashed into
`out/r4m_audit/LOCK_HASHES.txt` before the metadata build, the split build and any baseline run. No DigiMouse file,
no existing locked hash and no definition of `L1_maskv2` is touched by this work.

## Disclosure of what was seen before this file was written
- The integrity task (`outputs/nextbrain_integrity.md`) already reported file counts per folder, counts of completely black images
  (pixel maximum equal to 0 at native size: MRI/HE/LFB = 24/9/9, 1/2/1, 0/0/0, 0/18/0, 31/2/0 for cases 1 to 5), and a 20-record size check.
- No NextBrain image-quality metric (L1, SSIM, PSNR), no baseline and no model output had been computed.

## Data
- `~/Data/NextBrain/Case1..5` (UCL NextBrain-Case-N clones; commits recorded in `outputs/nextbrain_integrity.md`). Case IDs: 1 = P57-16, 2 = P41-16, 3 = P58-16, 4 = P85-18, 5 = EX9-19.
- Only `<ID>/histology/NN/` (0.1 mm in-plane) is used. `histology_hr/` is not present and not used.
- `slices_labels_npz` is matched and recorded in the metadata but is never used as an input channel (leakage rule).

## (a) Primary metric
- Mean absolute error (L1) between predicted and target RGB histology, intensities scaled to [0, 1], averaged over the pixels and the 3 channels inside the tissue mask.
- Tissue mask = nonzero MRI after the preprocessing below (MRI pixel value > 0 on the 256x256 padded grid).
- Preprocessing for every image (MRI, H&E, LFB): scale = 256 / max(height, width); new size = round(height*scale) x round(width*scale), PIL bilinear resize; centered zero padding (offset = floor((256 - new) / 2)) to 256x256. MRI (mode L) is used as one channel; H&E and LFB as RGB.
- Each modality is resized independently. Native size mismatches between modalities (seen in the integrity task) are not an exclusion criterion; they are counted and reported in the metadata (`correspondence_status` and image sizes).
- Per-slice value first. Reported per held-out case: mean and SD across slices, and a block-level bootstrap 95 percent CI (below).

## (b) Secondary metrics
- PSNR: from the mean squared error inside the mask, data range 1.0.
- SSIM: `skimage.metrics.structural_similarity`, `channel_axis=2`, `data_range=1.0`, default 7x7 window, computed on the full 256x256 images with the full SSIM map; the reported value is the mean of the map over mask pixels.
- Predictions are zero outside the mask for the baselines; for any later model the evaluation region is the same mask.

## (c) Tasks
- Task 1: MRI to H&E. Task 2: MRI to LFB. Task 1 is analyzed and reported first.

## (d) Pair inclusion
- A record is the set of files sharing one filename stem within `histology/NN/slices_MRI`, `slices_HE`, `slices_LFB`, `slices_labels_npz` (stem `slice_XX`).
- `complete_nonempty_triplet` = MRI, H&E and LFB files all exist, all are readable, and none is completely black (pixel maximum equal to 0 at native size).
- Only complete nonempty triplets enter splits, baselines and any model. Presence of the label file is not required for inclusion.
- The inclusion rule is fixed now and will not be revised after seeing results or after reconciling against the collaborator's counts. Differences from those counts are reported, not corrected by changing the rule.

## (e) Folds and validation
- 5 folds. Fold k holds out all of case k as the test set.
- Validation: from each of the 4 training cases, whole blocks only, never single slices. Number of validation blocks per case = max(1, round(0.10 * number of blocks containing at least one complete nonempty triplet)). Blocks are chosen by `numpy.random.RandomState(1000*k + case_number).permutation` of the sorted block names, taking the first n.
- Training set = remaining blocks of the 4 training cases. The test case contributes nothing to training or validation.
- Split files: `splits/nextbrain_fold{1..5}.json`, records `{"id","subject","z","hash","block"}` with id = `<case_id>/<block>/<slice stem>`, subject = case_id, z = integer slice index within block, hash = SHA-256 of the MRI file bytes.
- Leakage audit (subject mode) must pass for every fold: no subject in more than one of train, validation, test; no (subject, block) in both train and validation; no MRI hash shared between test and train or validation. Any violation stops the run.

## Baselines (no model training)
Both are fitted on training blocks only (validation and test excluded) and evaluated on the held-out case, H&E first, then LFB.
1. Mean training-target image: pixelwise mean over all training target images on the 256x256 padded grid (background zeros included).
2. Global MRI-to-RGB intensity mapping: for each MRI gray level 0 to 255, the mean target RGB over training pixels inside the mask having that level; levels with no training pixels are filled by linear interpolation from neighboring levels (nearest value beyond the ends). Applied pixelwise to the test MRI.

## Aggregation and uncertainty
- Per fold, per baseline: mean and SD of the per-slice metric across held-out slices.
- Block-level bootstrap: 10,000 resamples with `RandomState(12345)`; resample the held-out case's blocks with replacement, pool all slices of the drawn blocks, take the mean of the slice metric; report the 2.5th and 97.5th percentiles. Slices are never resampled individually.
- Each fold has one test subject, so no significance claims and no p-values are made; results are within-case descriptions.

## Not allowed
- Labels as an input channel; training or tuning on test blocks; changing the mask, inclusion rule, folds or metrics after results are seen.
- Wording: "retrospective multi-dataset evaluation"; never "clinically validated".
