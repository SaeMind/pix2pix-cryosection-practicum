# METRIC LOCK ADDENDUM 2 (valid-slice rule)

1. Time: local Fri Oct 16 06:52:53 CDT 2026, UTC Fri Oct 16 11:52:53 UTC 2026.

2. The chain (out/r4m/run_all.sh) had already finished and scored R4-M, R2-M and R5-M before this lock was written (out/r4m/ALLDONE and per-run score logs exist; only their existence was seen in a top-level directory listing, not their contents). No predictions, metrics.json files or infer/score logs of any run (R4-M, R2-M, R5-M) were opened, listed or read for this addendum. Only target images, the atlas, split.json and prior audit files were read.

3. Rule (fixed now, before anyone in this audit has seen any model output; the chain had already scored the runs before this lock, see item 2; thresholds are judgment, not statistical standards):
   a test slice is VALID iff dice_vs_atlas_body >= 0.85 AND dropped_fraction <= 0.10.
   dice_vs_atlas_body = Dice(mask_v2, atlas body label>0), both at 256 px; dropped_fraction = area of the thresholded mask outside its largest 8-connected component / thresholded area, before fill. Values in out/r4m_audit/mask_validity.csv; valid/invalid lists in out/r4m_audit/mask_valid.json.
   Sanity check passed: median Dice over the 45 test slices = 0.912 vs v0.4 full-resolution 0.910.
   Valid counts per block: A (z60-74) 7, B (z100-114) 15, C (z140-154) 15. Block A is mostly invalid, so block A sensitivity results rest on 7 slices.

4. The lock also applies to R2-M and R5-M (same rule, same file; no change after seeing any result).

5. SHA-256:
   7675d9afcad9c2ead5c61f024fa876ae0b66c8cf2b25d3f42e86b7d8ddd57f80  out/r4m_audit/mask_validity.csv
   27731809d7b0d9cc5e965aa1538e987e9663644ee92c2ee6ba226936da0d29d5  out/r4m_audit/mask_valid.json
   0a57583670faba0e068ad723b5a1a1373c25465928ba6a4ad48707981fceb552  out/r4m_audit/score_extra.py
   0624470a09fbad9363b14e690017ea5f29f210ab79107a6b000b628929294b5d  out/r4m/split.json
