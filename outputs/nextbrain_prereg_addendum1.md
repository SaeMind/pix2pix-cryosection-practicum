# NextBrain pre-registration, addendum 1 (clarification; written before any baseline was run)

The original file `outputs/nextbrain_prereg.md` (hash in `out/r4m_audit/LOCK_HASHES.txt`) is unchanged. Its leakage rule
"no subject in more than one of train, validation, test" contradicts its own validation design (validation = whole blocks held
out from the 4 training cases, so train and validation necessarily share subjects). The first run of `scripts/leakage_audit.py`
stopped on exactly this and no split was altered. Clarified rule, which is what the validation design implies:

- The test subject (held-out case) must not appear in train or validation (subject-level check).
- Train and validation may share subjects but must not share any (subject, block) pair (block-level check).
- Record ids unique and disjoint across sets; no MRI hash shared between test and train or validation (unchanged).

No fold, mask, metric, inclusion rule or seed changed. The splits as built (`splits/nextbrain_fold{1..5}.json`) were not modified.
