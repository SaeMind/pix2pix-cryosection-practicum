# METRIC LOCK, R4-M (written before any R4-M scoring)

1. Time: local Fri Oct 16 01:22:34 CDT 2026; UTC Fri Oct 16 06:22:34 UTC 2026.
   R4-M training epoch at lock time: 53 of 100 completed (from out/r4m/R4M_train.log "End of epoch" lines).
   Checked at lock time: out/r4m/R4M/pred and out/r4m/R4M/metrics.json do not exist.

2. No R4-M predictions have been scored and no model output viewed. The mask audit used target images only.

3. Revision. The mask audit (out/r4m_audit/mask_audit.csv, mask_audit_summary.json) found
   area(current)/area(mask_v2) = 0.094 min, 0.199 median, 0.665 max on the 45 test slices,
   and Dice(current, mask_v2) = 0.165 min, 0.307 median. The primary L1 therefore changes
   from L1_body to L1_maskv2.

4. Metric definitions (all on the 256 px targets; per test block A/B/C = z60-74, 100-114, 140-154, and mean of the 3 block means):
   - PRIMARY: L1_maskv2 = mean |pred - target| over pixels inside mask_v2 of the target
     (mask_v2 as computed in out/r4m_audit/mask_audit.py via masks_ref.py: per-slice median border colour,
     RGB distance, Otsu over all slices, largest component, fill holes).
   - SECONDARY: L1_body (current repo rule, target R-G > 0.18); L1_fov (current-rule body restricted to
     PET field-of-view rows, pet_rows_256 in split.json, as in the chain's scorer); L1_full (no mask);
     PSNR and SSIM.
   - BASELINE: mean training cryosection image (mean of the 73 train targets), scored on the same 45 test
     slices under the same masks.
   - 1 animal, 3 test blocks, no p-values. Within-animal result, not generalizable.

5. Disclosure. The Otsu threshold in mask_v2 was computed over the 118 train and test target images.
   It affects scoring only and not training (no training loss uses a mask; to be confirmed in the final report).

6. SHA-256:
   0624470a09fbad9363b14e690017ea5f29f210ab79107a6b000b628929294b5d  out/r4m/split.json
   48f0909d09c82bbecfd505e892c093c37607fe0d307dd3b719d470bb12ccea12  out/r4m_audit/mask_audit.py
   d40e977e803d1f0a7e8b75ace34f7c87bdf35412a081fe337bd5d4b7ca8b7286  out/r4m_audit/score_extra.py   (pre-edit; see addendum)
   f760af63175321bb8f48efcc88912048b421919fc9a86e0d4af393205bdae09d  out/r4m_audit/masks_ref.py

Note: this lock was written after the user's earlier instruction to keep L1_body as primary; the user's later
instruction supersedes it. A addendum file records the edited score_extra.py hash.
