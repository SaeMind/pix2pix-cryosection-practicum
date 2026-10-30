#!/usr/bin/env python3
"""usage: python scripts/build_nextbrain_splits.py [--meta outputs/nextbrain_metadata/nextbrain_all_cases.csv] [--out splits]
Pre-registered in outputs/nextbrain_prereg.md: fold k holds out case k; validation = whole blocks (max(1, round(0.10*n_blocks)))
per training case, chosen by RandomState(1000*k + case_number).permutation of sorted block names. Complete nonempty triplets only."""
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--meta", default="outputs/nextbrain_metadata/nextbrain_all_cases.csv")
ap.add_argument("--out", default="splits"); ap.add_argument("--prereg", default="outputs/nextbrain_prereg.md"); a = ap.parse_args()
rows = [r for r in csv.DictReader(open(a.meta)) if r["complete_nonempty_triplet"] == "True"]
prereg = hashlib.sha256(open(a.prereg, "rb").read()).hexdigest()
rec = lambda r: {"id": f"{r['case_id']}/{r['block']}/{r['slice']}", "subject": r["case_id"], "z": int(r["slice"].split("_")[1]), "hash": r["sha256_MRI"], "block": r["block"]}
Path(a.out).mkdir(exist_ok=True)
for k in range(1, 6):
    tr, va, te, vb = [], [], [], {}
    for n in range(1, 6):
        cr = [r for r in rows if r["case_number"] == str(n)]
        if n == k:
            te += [rec(r) for r in cr]; continue
        blocks = sorted({r["block"] for r in cr}); nv = max(1, round(0.10 * len(blocks)))
        pick = sorted(np.array(blocks)[np.random.RandomState(1000 * k + n).permutation(len(blocks))[:nv]].tolist())
        vb[cr[0]["case_id"]] = pick
        for r in cr:
            (va if r["block"] in pick else tr).append(rec(r))
    d = {"fold": k, "test_case_number": k, "task_note": "MRI->H&E first, then MRI->LFB", "prereg_sha256": prereg,
         "validation_blocks": vb, "counts": {"train": len(tr), "val": len(va), "test": len(te)}, "train": tr, "val": va, "test": te}
    json.dump(d, open(f"{a.out}/nextbrain_fold{k}.json", "w"), indent=1)
    print(f"fold {k}: train {len(tr)} val {len(va)} test {len(te)} val_blocks {vb}")
