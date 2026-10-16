#!/usr/bin/env python3
"""Step 1: statistics from mask_validity.csv and mask_valid.json only. Run from repo root."""
import csv, json, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
A = Path("out/r4m_audit")
S = json.loads(Path("out/r4m/split.json").read_text())
rows = [{**r, **{k: float(r[k]) for k in ("area_v2", "dropped_fraction", "dice_vs_atlas_body")}, "z": int(r["z"])}
        for r in csv.DictReader(open(A / "mask_validity.csv"))]
V = json.loads((A / "mask_valid.json").read_text())
blk = {z: k for k, zs in S["blocks"].items() for z in zs}


def stats(rs):
    d = np.array([r["dice_vs_atlas_body"] for r in rs]); lo = d < 0.85
    dr = np.array([r["dropped_fraction"] > 0.10 for r in rs])
    return dict(n=len(rs), dice_median=float(np.median(d)), dice_min=float(d.min()), dice_max=float(d.max()),
                n_dice_below_0p85=int(lo.sum()), n_dropped_above_0p10=int(dr.sum()),
                z_dropped_above_0p10=[r["z"] for r, f in zip(rs, dr) if f],
                n_fail_both=int((lo & dr).sum()), n_only_dice=int((lo & ~dr).sum()), n_only_dropped=int((~lo & dr).sum()),
                area_v2_median=float(np.median([r["area_v2"] for r in rs])))


te = [r for r in rows if r["split"] == "test"]; tr = [r for r in rows if r["split"] == "train"]
out = dict(test=stats(te), train=stats(tr), test_by_block={k: stats([r for r in te if blk[r["z"]] == k]) for k in sorted(S["blocks"])})
inv = []
for r in te:
    f = []
    if r["dice_vs_atlas_body"] < 0.85: f.append("dice")
    if r["dropped_fraction"] > 0.10: f.append("dropped_fraction")
    if f: inv.append(dict(z=r["z"], block=blk[r["z"]], dice_vs_atlas_body=r["dice_vs_atlas_body"], dropped_fraction=r["dropped_fraction"], failing="+".join(f)))
out["invalid_test_slices"] = inv
vj = sorted(z for v in V["invalid"] for z in [v["z"]])
out["check_invalid_matches_mask_valid_json"] = dict(csv_invalid=[i["z"] for i in inv], json_invalid=vj, match=[i["z"] for i in inv] == vj)
out["valid_counts_json"] = {k: len(v) for k, v in V["valid_by_block"].items()}
out["train_slices_in_split"] = len(S["train"]); out["train_slices_in_csv"] = len(tr)
out["train_missing_from_csv"] = sorted(set(S["train"]) - {r["z"] for r in tr})
out["test_missing_from_csv"] = sorted(set(S["test"]) - {r["z"] for r in te})
(A / "mask_stats.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
