# ADDENDUM 4a (clarification to Addendum 4)

Clarification to Addendum 4, written before R6M scoring. No rule changed.

Written 2026-10-23 (local). Precondition checked before writing: out/r4m/R6M, R7M, R6bM and their checkpoint folders do not exist; no R6M output has been opened. Addendum 4 is out/r4m_audit/addendum4_pet_only.md (sha256 7a861b432b9943454b354814f26f66bc7f884a0d7efed978aaf03c0f4739f1ea, commit 8ca6fdf).

1. Evaluation basis. P1, P2 and P4 are decided on L1_maskv2 over all 45 test slices, per block A (z60-74), B (z100-114), C (z140-154), with strict inequalities; a tie counts as not met. The valid-37 value is reported beside each as information only and does not decide.

2. P4 and P5 are descriptive outcome statements, not pass/fail rules.

3. Preview rule. R6M results may be shown before R7M and R6bM exist. In that case P2 and P3 are "not yet evaluable", and no statement is made about whether PET carries information. P1 and P4 may be reported for R6M alone.

4. Preview slices, fixed here before any R6M output was opened: z67 (block A centre), z107 (block B centre), z147 (block C centre). Source: these are the block centres used by out/r4m_audit/make_panels_centres.py for the existing R4M/R2M/R5M panels (out/r4m_audit/panels_centres.png). Note: block A has 8 of 15 slices with an invalid mask (Addendum 2); whether z67 is itself valid is not stated here (UNVERIFIED; look it up in out/r4m_audit/mask_valid.json when building the panel and say so on the figure).

5. Panel definition. Rows = the three slices above. Columns = input (as stored, 256 x 256 A half of data/<variant>/test_input), run prediction, target (data/test_target), absolute error x4. Absolute error x4 = per pixel and per colour channel, |prediction - target| computed on uint8 values as integers, multiplied by 4, clipped to [0, 255] (same expression as make_panels_centres.py line 14: np.clip(np.abs(p.astype(int) - tg.astype(int)) * 4, 0, 255)). The six-slice panels.png written by infer_score.py (z65, 70, 105, 110, 145, 150; mean absolute error, magma, 0-0.5) are a different, earlier display and are not the preview panel.

6. Panels are display only. They do not enter any decision rule.
