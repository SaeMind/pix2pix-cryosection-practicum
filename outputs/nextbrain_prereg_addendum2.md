# NextBrain pre-registration addendum 2 (Phase 1 accounting)

Written 2026-10-30 (UTC) while fold 3 H&E training was still running (epoch 24 of 100 logged). No NextBrain test result existed when this was written.

## (a) Files recorded (not all locked)

SHA-256 and file modification time (UTC) at the moment of recording.

| File | SHA-256 | mtime UTC | Status |
|---|---|---|---|
| .gitignore | 48ac6a2d0ebf656868fc92a7cf220f0395056182a81d98f2be3b5e6eab01af9f | 2026-10-30T02:38:38Z | recorded only, not locked |
| README.md | dbc825eada0642089352a907de63746a549f88ab4014a2613862f1c0be6bb662 | 2026-10-30T00:13:53Z | recorded only, not locked |
| .github/workflows/ci.yml | e7db095fb5b211b7726ed6d8a3ad3ecc349c3b588ac5c61d9c2fcb08cbb1521d | 2026-10-30T02:38:38Z | recorded only, not locked |
| mpbench/synthetic_smoke.py | 5df1bd21de44998430716b46966f67692e1111843ccf791176403374ba722af0 | 2026-10-30T02:38:38Z | locked (appended to LOCK_HASHES.txt) |
| tests/test_synthetic_smoke.py | 3ab71a39ed64889dfc874b659e61c09bf9dd6e3460cbd87c309d5850987b1d4f | 2026-10-30T02:38:38Z | locked (appended to LOCK_HASHES.txt) |

Also noted: mpbench/adapters/nextbrain.py (sha256 cd7dcf34e335a8509725449432dc154e00d83a7d94b1dac290a60d9a0714da87, mtime 2026-10-30T01:16:25Z) is not in the manifest and is not locked here. It is subject to the v2 adapter change in (d).

None of the six files above was in the manifest before this addendum, so no lock violation is possible for them.

## (b) What did not change

All 73 manifest entries were re-hashed sequentially: 0 missing, 0 mismatches. The manifest includes splits/nextbrain_fold1..5.json, configs/nextbrain_fold{1,2,3,4,5}_he.json, scripts/train_nextbrain.py, scripts/train_nextbrain_fold.py, scripts/eval_nextbrain_test.py, scripts/eval_nextbrain_test_fold.py and scripts/run_queue.py. Therefore no split, config or training file changed after it was hashed. This statement covers only files in the manifest.

## (c) Chronology result

Each manifest entry with a UTC time (from the comment line above it) was compared with the file mtime converted to UTC.

- Manifest time later than mtime: 52 entries (of 73; the other 12 are equal to the second or have no UTC time in the manifest, not itemised). This is the normal order (file written, then hashed). The largest gaps are the five split files (hashed 2026-10-30T00:51:48Z, mtime 00:05:15Z) and outputs/nextbrain_baselines.json (hashed 00:51:48Z, mtime 00:10:46Z). All hashes still match, so content was unchanged in that interval.
- mtime later than manifest time: 9 entries, all with mtime within the same whole second as the manifest time (the comparison used the fractional mtime against a whole-second manifest time; sub-second ordering is not measurable). Hashes match. Sub-second order is UNVERIFIED.
- Manifest time earlier than the mtime of outputs/nextbrain_prereg_addendum1.md (2026-10-30T00:05:30Z): only outputs/nextbrain_prereg.md (hashed 00:03:56Z), which is the document that addendum 1 amends and therefore precedes it by design. outputs/nextbrain_prereg_addendum1.md itself equals its own mtime. No later-addendum violation found.
- Entries dated 2026-10-23 (PET-only series) are outside the NextBrain addenda; they were checked on the same two rules and reported above.

## (d) Decisions

1. Aggregate NextBrain metrics and tables stay out of Git until the source authors or mentors clear them.
2. The v2 adapter adds `registration_status` in {registered_by_source, independently_verified, unverified} and `registration_verified_by` (null by default), in one schema.
3. Code tasks d and f start only after all tests pass and the manifest check shows 0 hash mismatches.
