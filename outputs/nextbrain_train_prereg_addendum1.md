# NextBrain training pre-registration, addendum 1 (decision by the project owner; written before any further training or validation run)

The original `outputs/nextbrain_train_prereg.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`) is unchanged. It excluded two blocks flagged in
`outputs/nextbrain_shape_audit.md` (Case 4 / P85-18 block 28 and Case 5 / EX9-19 block 48; 72 records; MRI/H&E size differences over 10 px) via `exclude_blocks`.
Decision recorded on 2026-10-29: include them. The exclusion is withdrawn and `exclude_blocks` is empty in `configs/nextbrain_fold3_he.json`, so the
original data-inclusion rule of `outputs/nextbrain_prereg.md` applies unchanged.

- The resize rule is applied unchanged to all records. For these two blocks it stretches the MRI onto the H&E grid anisotropically (aspect ratios 0.663 vs 1.058 for Case 5 block 48; 0.728 vs 0.778 for Case 4 block 28), and whether their content is aligned is UNVERIFIED (no image viewed). They remain visual-QC candidates.
- Architecture, seed, optimizer, selection rule and test isolation are unchanged. Fold 3 validation again contains Case 4 block 28; training again contains Case 5 block 48.
- The earlier timing run with the exclusion is kept as `outputs/nextbrain_timing_with_exclusions.{json,md}`; the timing test is repeated without it.
