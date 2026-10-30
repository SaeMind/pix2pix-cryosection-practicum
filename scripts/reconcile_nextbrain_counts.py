#!/usr/bin/env python3
"""usage: python scripts/reconcile_nextbrain_counts.py [--meta outputs/nextbrain_metadata] [--out outputs/nextbrain_reconciliation.md]"""
import argparse, csv
from collections import Counter
ap = argparse.ArgumentParser(); ap.add_argument("--meta", default="outputs/nextbrain_metadata"); ap.add_argument("--out", default="outputs/nextbrain_reconciliation.md")
a = ap.parse_args()
REC = {1: (45, 1051, 1018), 2: (40, 942, 938), 3: (40, 1045, 1045)}
rows = list(csv.DictReader(open(f"{a.meta}/nextbrain_all_cases.csv")))
L = ["| Case | blocks (ours / recorded) | records with MRI file (ours / recorded) | records, union of 4 folders (ours) | complete nonempty triplets (ours / recorded) | status |", "|---|---|---|---|---|---|"]
D = []
for n in range(1, 6):
    r = [x for x in rows if x["case_number"] == str(n)]
    nb = len({x["block"] for x in r}); mri = sum(1 for x in r if x["path_MRI"]); tri = sum(x["complete_nonempty_triplet"] == "True" for x in r)
    rec = REC.get(n); f = lambda o, i: f"{o} / {rec[i]:,}" if rec else f"{o} / unrecorded"
    ok = rec and (nb, mri, tri) == rec
    L.append(f"| {n} | {f(nb, 0)} | {f(mri, 1)} | {len(r)} | {f(tri, 2)} | {'match' if ok else ('MISMATCH' if rec else 'first counts')} |")
    bad = [x for x in r if x["complete_nonempty_triplet"] != "True"]
    why = lambda x: x["correspondence_status"] if x["correspondence_status"] != "complete" else "black:" + "+".join(m for m in ("MRI", "HE", "LFB") if x[f"is_black_{m}"] == "True")
    D += [f"", f"Case {n}: {len(bad)} records not complete-nonempty. Reasons: {dict(Counter(why(x) for x in bad))}",
          "Block/slice: " + "; ".join(f"{x['block']}/{x['slice']} ({why(x)})" for x in bad) if bad else "none"]
open(a.out, "w").write("\n".join(["# NextBrain count reconciliation", "", *L, "", "Recorded counts are the collaborator's, as given in the task. Records not complete-nonempty are listed with block and slice:", *D, ""]))
print("\n".join(L)); print("\n".join(D))
