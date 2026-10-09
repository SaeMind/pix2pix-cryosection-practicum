# Practicum: Pix2Pix development (Stage 0)

## Scope
- Capstone: multi-dataset Pix2Pix forecasting of future brain tumor MRI from prior scans (due Dec 17, 2026).
- D1 (Virtual Mouse Brain, Dryad doi:10.5061/dryad.1vhhmgqv8) and D2 (DigiMouse) are Stage 0 pipeline-development sets, NOT forecasting training sets. They are not longitudinal and not tumor data. D2 is n=1.

## Rules
- Raw archives are read-only after checksum. Never modify files in */raw.
- Log SHA-256 for every download in datasets/manifests/.
- Splits: blocked and interleaved by slice (train 20, gap 5, test 10, gap 5). Never random slice splits. Report that D2 results are within-animal, not generalizable.
- Do NOT use the atlas labels as an input channel (leakage).
- Wording: "retrospective multi-dataset evaluation"; never "clinically validated".
- Mark anything unverified as unverified.

## Released (Andrew, Oct 8, 2026)
- The CT+PET ablation (R1, R2, R2b, R4, R4b, R5; R3 optional; R2b and R4b are replicates) is released to run tonight. Exit condition 1 (Diana's metadata) is waived for D2: its content is SHA-256-identical to the official USC zips.
- Gates still in force, in order: (a) R1 runs first under the blocked split; (b) Andrew reviews the PET/CT-to-cryosection overlays before any run launches.
- Splits: blocked (train 20, gap 5, test 10, gap 5), fixed once, never revised after seeing test results. Percentile normalization uses training slices only.
- No significance claims (n=1 animal). Test = 3 blocks (z54-63, z94-103, z134-143). Train = z29-48, 69-88, 109-128, 149-166 (78 slices). Split fixed Oct 8, 2026. A 2-epoch R1 smoke test was evaluated on these test slices before launch; no design change used its numbers.
- Atlas labels are never an input channel.
- Disk: keep at least 20 GB free. Only the final checkpoint is saved. Do not extract MRI_C57_data.zip or MRI_Shiverer.zip in full.

## Updates (Oct 8, 2026, after overlay review)
- Orientation ud=0 lr=0 zrev=0 verified on CT and PET overlays.
- Splits use only slices inside the measured animal extent, and only complete test blocks. The old last test block (z185-194) was probably fixture-only (inference, verified by the extent profile).
- Primary metric L1_fov (body pixels inside the PET field-of-view rows); secondary L1_body, L1_full, SSIM, PSNR. Reference = mean training cryosection image.
- Decision rule (fixed Oct 8, 2026 before any ablation result; thresholds are judgment, not a statistical standard): PET is credited only if ALL hold on L1_fov: (C1) the R4/R4b average is lower than R1, than the R2/R2b average, and than R5 in all 3 test blocks; (C2) mean gain over the R2 average exceeds 2x the larger replicate noise (mean block |R2-R2b| or |R4-R4b|); (C3) both R4 and R4b have a lower block-mean L1_fov than both R2 and R2b. If replicates are missing the verdict is inconclusive. No p-values.
- Training flags: --no_flip. This fork rejects --display_id and --gpu_ids.
- PET nonzero rows 26-834 of 992 (81.6% of the long axis, measured). Raw PET field-of-view arithmetic gives about 76.8 mm of the 99.2 mm axis; the roughly 4 mm excess is unexplained (unverified).
