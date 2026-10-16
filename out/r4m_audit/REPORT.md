# R4-M audit report (Oct 16, 2026)

1. Task 1: tests pass (4/4) with `pytest -c out/r4m_audit/pytest.ini`. The earlier failure was `ModuleNotFoundError: No module named 'models'` (script run directly, repo root not on sys.path). The failed `sed -i` (BSD: "invalid command code o") never changed anything; the path line in out/r4m/test_r4m.py had already been fixed with Python. Rerun after scoring:
   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=out/r4m_audit/pytest_pkg nice -n 10 pix2pix_env/bin/python -m pytest -c out/r4m_audit/pytest.ini -p no:cacheprovider -q out/r4m/test_r4m.py`
2. Task 2: case (ii), another clone: /Users/gihbeom/Documents/01_Academic/BMI_Coursework/Practicum/pix2pix-matched-pairs (ef4b8de is a v0.4 commit there; not an object in this repo). mask_v2 lives in pairverify/masks.py and pairverify/spatial3.py (mask_v2_stack).
3. Task 3: current rule covers a fraction of the body; see mask_audit_summary.json. score_extra.py written, guard-stopped (0 of 45 predictions).
4. Task 4: MPS 52/60 s per epoch under contention, no NaN; CPU chain 41-52 s per epoch. NOT RECOMMENDED.
