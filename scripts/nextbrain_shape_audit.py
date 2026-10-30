#!/usr/bin/env python3
"""usage: python scripts/nextbrain_shape_audit.py --root <dir with Case1..Case5> [--meta outputs/nextbrain_metadata/nextbrain_all_cases.csv] [--out outputs/nextbrain_shape_audit.json]
Headers only (PIL size; no pixel loading). dH, dW = height/width differences MRI-HE and HE-LFB for complete nonempty triplets."""
import argparse, csv, json
from collections import Counter
from pathlib import Path
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); ap.add_argument("--meta", default="outputs/nextbrain_metadata/nextbrain_all_cases.csv")
ap.add_argument("--out", default="outputs/nextbrain_shape_audit.json"); a = ap.parse_args()
root = Path(a.root).expanduser()
BINS = [("0", lambda m: m == 0), ("1", lambda m: m == 1), ("2", lambda m: m == 2), ("3-5", lambda m: 3 <= m <= 5), ("6-10", lambda m: 6 <= m <= 10), (">10", lambda m: m > 10)]
recs = []
for r in csv.DictReader(open(a.meta)):
    if r["complete_nonempty_triplet"] != "True": continue
    cd = root / f"Case{r['case_number']}"
    s = {m: Image.open(cd / r[f"path_{m}"]).size for m in ("MRI", "HE", "LFB")}   # (W, H), header only
    d = lambda x, y: (s[x][1] - s[y][1], s[x][0] - s[y][0])                         # (dH, dW)
    (h1, w1), (h2, w2) = d("MRI", "HE"), d("HE", "LFB")
    recs.append(dict(case=int(r["case_number"]), case_id=r["case_id"], block=r["block"], slice=r["slice"], mri=s["MRI"], he=s["HE"], lfb=s["LFB"],
                     dH_mri_he=h1, dW_mri_he=w1, dH_he_lfb=h2, dW_he_lfb=w2, m_mri_he=max(abs(h1), abs(w1)), m_he_lfb=max(abs(h2), abs(w2)),
                     path_MRI=r["path_MRI"], path_HE=r["path_HE"], path_LFB=r["path_LFB"]))
json.dump(recs, open(a.out, "w"), indent=0)
for pair, key in (("MRI vs HE", "m_mri_he"), ("HE vs LFB", "m_he_lfb")):
    print("==", pair)
    for n in range(1, 6):
        R = [r for r in recs if r["case"] == n]; dh, dw = ("dH_mri_he", "dW_mri_he") if key == "m_mri_he" else ("dH_he_lfb", "dW_he_lfb")
        z = sum(r[dh] == 0 and r[dw] == 0 for r in R)
        print(f"case {n}: n={len(R)} exact={z} max|dH|={max(abs(r[dh]) for r in R)} max|dW|={max(abs(r[dw]) for r in R)} hist=" +
              str({b: sum(f(r[key]) for r in R) for b, f in BINS}))
