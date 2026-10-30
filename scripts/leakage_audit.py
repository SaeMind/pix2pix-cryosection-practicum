#!/usr/bin/env python3
"""usage: python scripts/leakage_audit.py --split splits/nextbrain_fold1.json --mode subject
NEW script written for the NextBrain task: no earlier leakage_audit.py was found on this machine (UNVERIFIED relation to any prior tool).
Exit code 1 on any violation. Checks (subject mode):
 1 test subject absent from train and val (train/val share subjects by design; see outputs/nextbrain_prereg_addendum1.md)
 2 no (subject, block) shared between validation and train (validation = whole blocks)
 3 record ids unique and disjoint across sets
 4 no MRI hash shared between test and (train or val)
Informational only (not a violation): MRI hashes shared between train and val."""
import argparse, json, sys
ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); ap.add_argument("--mode", default="subject", choices=["subject"]); a = ap.parse_args()
d = json.load(open(a.split)); S = {k: d[k] for k in ("train", "val", "test")}; bad = []
subj = {k: {r["subject"] for r in v} for k, v in S.items()}
# addendum 1: train and val share subjects by design (val = whole blocks of training cases); only the test subject must be disjoint
for x, y in (("train", "test"), ("val", "test")):
    if subj[x] & subj[y]: bad.append(f"subject overlap {x}/{y}: {sorted(subj[x] & subj[y])}")
blk = {k: {(r["subject"], r["block"]) for r in v} for k, v in S.items()}
if blk["train"] & blk["val"]: bad.append(f"validation block present in train: {sorted(blk['train'] & blk['val'])}")
ids = [r["id"] for v in S.values() for r in v]
if len(ids) != len(set(ids)): bad.append("duplicate record ids within or across sets")
h = {k: {r["hash"] for r in v} for k, v in S.items()}
for x in ("train", "val"):
    if h["test"] & h[x]: bad.append(f"MRI hash shared test/{x}: {len(h['test'] & h[x])}")
info = len(h["train"] & h["val"])
print(f"{a.split}: subjects train={sorted(subj['train'])} val={sorted(subj['val'])} test={sorted(subj['test'])}; "
      f"records {len(S['train'])}/{len(S['val'])}/{len(S['test'])}; train/val shared MRI hashes (info): {info}")
if bad:
    print("VIOLATION:", *bad, sep="\n  "); sys.exit(1)
print("  PASS")
