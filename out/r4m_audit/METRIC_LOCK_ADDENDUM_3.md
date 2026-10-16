# METRIC LOCK ADDENDUM 3

1. Time: local Fri Oct 16 07:14:29 CDT 2026, UTC Fri Oct 16 12:14:29 UTC 2026.

2. SHA-256 of score_sensitivity.py:
   46d2cfa69ce2b9fb8a46f102901a931ffa57dffa4f2ad0971e4394a5abef69ee  out/r4m_audit/score_sensitivity.py

3. score_sensitivity.py was written after the Addendum 2 rule, was not run on real predictions before this addendum, and does not change any definition.

4. In THIS session (all turns up to this step), no prediction PNG, metrics.json or infer/score log was opened or read. Only the existence of files in the top-level listing of out/r4m (ALLDONE, R*M dirs, R*M_score.log, metrics.json) was seen. The only scripts run on files under out/r4m were the target-only scripts (mask_validity.py, mask_stats.py) and a smoke test of score_extra.py on target copies. Caveat: the chain itself had already scored the runs before Addendum 2 (see Addendum 2 item 2).
