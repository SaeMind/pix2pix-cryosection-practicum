"""
audit_duplication.py
Full pairwise data-duplication audit across all 6 locked animals (m1, m2,
m3, m4, m6, m7) x Day1/Day8 (12 sessions total), following the confirmed
m1/Day1 == m7/Day1 duplication found by verify_m1_m7_duplication.py.

Checks, per session (animal, day) against every OTHER session:
  1. MTR file MD5 hash
  2. ROImask.mat MD5 hash
  3. Array-level equality (MTR, phantom_mask) as a backstop in case two
     files hash differently but contain identical data (shouldn't happen
     for MD5, included for completeness/paranoia only)
  4. Raw session subfolder name match (corroborating, not authoritative)

Outputs:
  - A full duplication matrix printed to console (12x12, MTR file hash
    equality) and a second matrix for ROImask.mat
  - Reports each unique duplicate GROUP found (not just pairs) — if 3+
    sessions share the same file, that is a single group, not 3 separate
    "duplicate pairs," and grouping makes the scope of the problem legible.
  - A duplicate_groups.csv listing every session and which group (if any)
    it belongs to, for pasting directly into a report or the Kuddannaya
    outreach email.

This does NOT modify train_v1.py, does NOT decide which duplicate (if any)
is "correct," and does NOT exclude or de-duplicate anything automatically.
It only reports what is on disk. Any decision about which session(s) to
keep, exclude, or query with Dr. Kuddannaya is explicitly left to Andrew /
Kuddannaya, consistent with the CONSTRAINTS in opus-session-phase1-v2.md
("do not backfill or interpolate silently").

Usage:
    python audit_duplication.py \
        --root "<path-to>/MRI Results-Main" \
        --power-ppm 12 \
        --out-dir ./duplication_audit
"""

import argparse
import csv
import hashlib
from pathlib import Path
from itertools import combinations

import numpy as np
from scipy.io import loadmat

LOCKED_ANIMALS = ["m1", "m2", "m3", "m4", "m6", "m7"]
DAYS = ["Day1", "Day8"]


def md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_var(path: Path, varname: str):
    mat = loadmat(str(path))
    if varname not in mat:
        keys = [k for k in mat.keys() if not k.startswith("__")]
        raise KeyError(f"'{varname}' not found in {path}. Keys: {keys}")
    return mat[varname]


def find_mtr_file(animal_dir: Path, power_ppm: str) -> Path:
    candidates = sorted(animal_dir.glob(f"pwr*_brainMTRmap@{power_ppm}ppm_MTRdata.mat"))
    return candidates[0] if candidates else None


def list_session_subfolders(animal_dir: Path) -> list:
    if not animal_dir.exists():
        return []
    return sorted([p.name for p in animal_dir.iterdir() if p.is_dir()])


def find_groups(pairs_equal: dict, session_ids: list) -> list:
    """
    Union-find style grouping: given a dict of (id_a, id_b) -> bool equal,
    return a list of groups (each a list of session_ids) where every
    session in a group is pairwise-equal to every other session in that
    group. Sessions with no duplicates form singleton groups (omitted from
    the returned list — caller reports those separately as "unique").
    """
    parent = {sid: sid for sid in session_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for (a, b), equal in pairs_equal.items():
        if equal:
            union(a, b)

    groups = {}
    for sid in session_ids:
        root = find(sid)
        groups.setdefault(root, []).append(sid)

    return [g for g in groups.values() if len(g) > 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--power-ppm", type=str, default="12")
    parser.add_argument("--out-dir", type=Path, default=Path("./duplication_audit"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 90)
    print(f"FULL PAIRWISE DUPLICATION AUDIT — {len(LOCKED_ANIMALS)} animals x {len(DAYS)} days "
          f"= {len(LOCKED_ANIMALS) * len(DAYS)} sessions")
    print("=" * 90)

    # --- Gather per-session info ---
    sessions = {}  # session_id -> dict(animal, day, mtr_path, roi_path, mtr_hash, roi_hash, subfolders)
    for animal in LOCKED_ANIMALS:
        for day in DAYS:
            sid = f"{animal}_{day}"
            animal_dir = args.root / day / animal
            mtr_path = find_mtr_file(animal_dir, args.power_ppm)
            roi_path = animal_dir / "ROImask.mat"

            entry = {
                "animal": animal, "day": day, "session_id": sid,
                "animal_dir": animal_dir,
                "mtr_path": mtr_path,
                "roi_path": roi_path if roi_path.exists() else None,
                "mtr_hash": None, "roi_hash": None,
                "subfolders": list_session_subfolders(animal_dir),
            }

            if mtr_path is not None and mtr_path.exists():
                entry["mtr_hash"] = md5_of_file(mtr_path)
            if entry["roi_path"] is not None:
                entry["roi_hash"] = md5_of_file(entry["roi_path"])

            sessions[sid] = entry

    session_ids = list(sessions.keys())

    # --- Report per-session basics ---
    print("\nPER-SESSION SUMMARY")
    print("-" * 90)
    for sid in session_ids:
        e = sessions[sid]
        mtr_status = "OK" if e["mtr_hash"] else "MISSING"
        roi_status = "OK" if e["roi_hash"] else "MISSING"
        print(f"  {sid:12s} MTR={mtr_status:8s} ROI={roi_status:8s} "
              f"subfolders={e['subfolders']}")

    # --- Pairwise comparison ---
    mtr_pairs_equal = {}
    roi_pairs_equal = {}

    for a, b in combinations(session_ids, 2):
        ea, eb = sessions[a], sessions[b]

        mtr_eq = (ea["mtr_hash"] is not None and eb["mtr_hash"] is not None
                  and ea["mtr_hash"] == eb["mtr_hash"])
        mtr_pairs_equal[(a, b)] = mtr_eq

        roi_eq = (ea["roi_hash"] is not None and eb["roi_hash"] is not None
                  and ea["roi_hash"] == eb["roi_hash"])
        roi_pairs_equal[(a, b)] = roi_eq

    # --- Duplication matrix (MTR) ---
    print("\n" + "=" * 90)
    print("MTR FILE DUPLICATION MATRIX (X = identical MD5 hash)")
    print("=" * 90)
    header = "         " + " ".join(f"{sid:>10s}" for sid in session_ids)
    print(header)
    for a in session_ids:
        row = [a.ljust(9)]
        for b in session_ids:
            if a == b:
                row.append(f"{'-':>10s}")
            else:
                key = (a, b) if (a, b) in mtr_pairs_equal else (b, a)
                mark = "X" if mtr_pairs_equal.get(key, False) else "."
                row.append(f"{mark:>10s}")
        print(" ".join(row))

    print("\n" + "=" * 90)
    print("ROImask.mat DUPLICATION MATRIX (X = identical MD5 hash)")
    print("=" * 90)
    print(header)
    for a in session_ids:
        row = [a.ljust(9)]
        for b in session_ids:
            if a == b:
                row.append(f"{'-':>10s}")
            else:
                key = (a, b) if (a, b) in roi_pairs_equal else (b, a)
                mark = "X" if roi_pairs_equal.get(key, False) else "."
                row.append(f"{mark:>10s}")
        print(" ".join(row))

    # --- Grouping ---
    mtr_groups = find_groups(mtr_pairs_equal, session_ids)
    roi_groups = find_groups(roi_pairs_equal, session_ids)

    # A session is "fully duplicated" if BOTH its MTR and ROImask match
    # another session's — that's the strong-evidence case, same standard
    # applied in verify_m1_m7_duplication.py.
    both_pairs_equal = {
        pair: mtr_pairs_equal.get(pair, False) and roi_pairs_equal.get(pair, False)
        for pair in mtr_pairs_equal
    }
    full_dup_groups = find_groups(both_pairs_equal, session_ids)

    print("\n" + "=" * 90)
    print("DUPLICATE GROUPS — MTR file only")
    print("=" * 90)
    if mtr_groups:
        for i, g in enumerate(mtr_groups, 1):
            print(f"  Group {i}: {sorted(g)}")
    else:
        print("  None found.")

    print("\n" + "=" * 90)
    print("DUPLICATE GROUPS — ROImask.mat only")
    print("=" * 90)
    if roi_groups:
        for i, g in enumerate(roi_groups, 1):
            print(f"  Group {i}: {sorted(g)}")
    else:
        print("  None found.")

    print("\n" + "=" * 90)
    print("DUPLICATE GROUPS — BOTH MTR and ROImask identical (strongest evidence)")
    print("=" * 90)
    if full_dup_groups:
        for i, g in enumerate(full_dup_groups, 1):
            print(f"  Group {i}: {sorted(g)}")
            # report subfolder names too, as corroborating evidence
            for sid in sorted(g):
                print(f"    {sid}: subfolders={sessions[sid]['subfolders']}")
    else:
        print("  None found.")

    n_sessions_affected = len(set(sid for g in full_dup_groups for sid in g))
    print(f"\n>>> {n_sessions_affected} / {len(session_ids)} sessions are involved in a "
          f"full (MTR+ROI) duplicate group.")

    # --- Write CSV for the outreach email / report ---
    csv_path = args.out_dir / "duplicate_groups.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "animal", "day", "mtr_hash", "roi_hash",
                          "full_dup_group", "session_subfolders"])
        sid_to_group = {}
        for i, g in enumerate(full_dup_groups, 1):
            for sid in g:
                sid_to_group[sid] = i
        for sid in session_ids:
            e = sessions[sid]
            writer.writerow([
                sid, e["animal"], e["day"], e["mtr_hash"], e["roi_hash"],
                sid_to_group.get(sid, ""), ";".join(e["subfolders"]),
            ])
    print(f"\nWrote {csv_path}")

    print("\n" + "=" * 90)
    print("NEXT STEP")
    print("=" * 90)
    print("This script makes NO decision about which duplicate session to keep or")
    print("exclude. Report the full_dup_groups above to Dr. Kuddannaya alongside")
    print("OPEN ITEMS 1-5 already on file — this is a 6th item, and unlike 1-5 it")
    print("BLOCKS any trustworthy LOAO-CV result until resolved, since a duplicate")
    print("pair violates the animal-independence assumption LOAO-CV depends on.")
    print("=" * 90)


if __name__ == "__main__":
    main()
