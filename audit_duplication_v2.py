"""
audit_duplication_v2.py
Re-run of audit_duplication.py, now excluding paths that
Ghaemi_et_al__2026_01_dataset_inventory.ipynb (GLOBE_Fall2026, prior work
on this exact dataset) identified as non-canonical:

  1. Archive/sync-copy paths: containing "onedrive_", "copy", or "backup"
     in the relative path (their detect_archive_copy()). Confirmed real
     artifact — e.g. Day8\\M6\\OneDrive_1_11-5-2023 (1)\\m2\\... is a nested
     OneDrive-sync copy of m2's data living inside m6's Day8 folder tree.
  2. Paths containing MORE THAN ONE mouse-id-like token (their
     detect_nested_mouse_ids() + mouse_id_conflict flag) — e.g. a file
     under .../M6/.../m2/... has BOTH m6 and m2 in its path and is
     excluded as ambiguous, regardless of which folder it's nested in.
  3. The "_cest" MTR variant (pwr{N}_brain_cestMTRmap@...) is a GENUINELY
     DIFFERENT product from the standard pwr{N}_brainMTRmap@... file (per
     their extract_cest_variant()/classify_mtr_product()), not a duplicate
     — this script keeps find_mtr_file's existing glob pattern as-is
     (which already excludes "_cest" by not matching "_brain_cestMTRmap")
     but reports if a _cest file is ALSO present, for visibility.

Purpose: determine whether the 7/12 duplicate-session finding from
audit_duplication.py persists once these known-bad paths are excluded, or
whether it fully/partially resolves. Logs findings to
drive-verified-decisions-sept2026.md OPEN ITEM 6 once complete (manual
step, not automated here).

This does NOT modify train_v1.py. It is a standalone re-verification.

Usage:
    python audit_duplication_v2.py \
        --root "<path-to>/MRI Results-Main" \
        --power-ppm 12 \
        --out-dir ./duplication_audit_v2
"""

import argparse
import csv
import hashlib
import re
from pathlib import Path
from itertools import combinations

import numpy as np
from scipy.io import loadmat

LOCKED_ANIMALS = ["m1", "m2", "m3", "m4", "m6", "m7"]
DAYS = ["Day1", "Day8"]

ARCHIVE_TERMS = ["onedrive_", "copy", "backup"]


def is_archive_copy(relative_path: str) -> bool:
    """Ported from GLOBE_Fall2026 notebook's detect_archive_copy()."""
    text = str(relative_path).lower()
    return any(term in text for term in ARCHIVE_TERMS)


def nested_mouse_ids(relative_path: str) -> list:
    """
    Ported from GLOBE_Fall2026 notebook's detect_nested_mouse_ids().

    FIXED vs. the notebook's original: the source notebook was run on
    Windows and iterates Path(relative_path).parts, which splits on
    backslash. On macOS/Linux (this environment), pathlib.Path does NOT
    split on backslash, so a Windows-style path string like
    "Day8\\M6\\OneDrive...\\m2\\B0map1.mat" comes back as a SINGLE part on
    a POSIX system, causing this function to silently return [] instead
    of ['m6','m2'] — verified by a standalone test against the notebook's
    own example path (see chat log, 2026-09-26). Fixed by normalizing
    both backslash and forward-slash separators before splitting, so this
    works regardless of which OS generated the path string or is running
    this script.
    """
    normalized = str(relative_path).replace("\\", "/")
    ids = []
    for part in normalized.split("/"):
        match = re.match(r"^m(\d+)(?:[^0-9]|$)", part, flags=re.IGNORECASE)
        if match:
            mouse_id = f"m{int(match.group(1))}"
            if mouse_id not in ids:
                ids.append(mouse_id)
    return ids


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


def find_mtr_candidates(animal_dir: Path, power_ppm: str) -> list:
    """
    Find ALL matching MTR files under animal_dir (recursive, unlike
    train_v1.py's original non-recursive glob) — this deliberately
    searches recursively so nested archive-copy files (which live in
    subfolders like OneDrive_1_11-5-2023 (1)/m2/) are found and can be
    reported/excluded explicitly, rather than silently missed by a
    shallow glob.
    """
    pattern = f"pwr*_brainMTRmap@{power_ppm}ppm_MTRdata.mat"
    return sorted(animal_dir.rglob(pattern))


def find_roi_candidates(animal_dir: Path) -> list:
    return sorted(animal_dir.rglob("ROImask.mat"))


def find_canonical_file(candidates: list, animal_dir: Path) -> tuple:
    """
    From a list of candidate file paths, select the canonical one:
    exclude archive-copy paths and paths with nested/conflicting mouse
    IDs, then take the first remaining (shallowest depth, then
    alphabetical). Returns (chosen_path_or_None, excluded_list) where
    excluded_list records why each candidate was dropped.
    """
    excluded = []
    kept = []

    for c in candidates:
        rel = str(c.relative_to(animal_dir))
        full_rel_from_root = str(c)  # for archive/nested-id checks, use full relative-ish path

        reasons = []
        if is_archive_copy(str(c)):
            reasons.append("archive_copy")

        ids_in_path = nested_mouse_ids(str(c))
        if len(ids_in_path) > 1:
            reasons.append(f"nested_mouse_id_conflict{ids_in_path}")

        if reasons:
            excluded.append((c, reasons))
        else:
            kept.append(c)

    kept.sort(key=lambda p: (len(p.parts), str(p)))
    chosen = kept[0] if kept else None
    return chosen, excluded


def list_session_subfolders(animal_dir: Path) -> list:
    if not animal_dir.exists():
        return []
    return sorted([p.name for p in animal_dir.iterdir() if p.is_dir()])


def find_groups(pairs_equal: dict, session_ids: list) -> list:
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
    parser.add_argument("--out-dir", type=Path, default=Path("./duplication_audit_v2"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 90)
    print("DUPLICATION RE-AUDIT v2 — WITH ARCHIVE-COPY / NESTED-MOUSE-ID EXCLUSION")
    print("(filters ported from GLOBE_Fall2026 Ghaemi_et_al__2026_01_dataset_inventory.ipynb)")
    print("=" * 90)

    sessions = {}
    for animal in LOCKED_ANIMALS:
        for day in DAYS:
            sid = f"{animal}_{day}"
            animal_dir = args.root / day / animal

            mtr_candidates = find_mtr_candidates(animal_dir, args.power_ppm)
            roi_candidates = find_roi_candidates(animal_dir)

            mtr_chosen, mtr_excluded = find_canonical_file(mtr_candidates, animal_dir)
            roi_chosen, roi_excluded = find_canonical_file(roi_candidates, animal_dir)

            entry = {
                "animal": animal, "day": day, "session_id": sid,
                "animal_dir": animal_dir,
                "mtr_candidates_found": len(mtr_candidates),
                "mtr_excluded_count": len(mtr_excluded),
                "mtr_excluded_reasons": mtr_excluded,
                "mtr_path": mtr_chosen,
                "roi_candidates_found": len(roi_candidates),
                "roi_excluded_count": len(roi_excluded),
                "roi_excluded_reasons": roi_excluded,
                "roi_path": roi_chosen,
                "mtr_hash": None, "roi_hash": None,
                "subfolders": list_session_subfolders(animal_dir),
            }

            if mtr_chosen is not None and mtr_chosen.exists():
                entry["mtr_hash"] = md5_of_file(mtr_chosen)
            if roi_chosen is not None and roi_chosen.exists():
                entry["roi_hash"] = md5_of_file(roi_chosen)

            sessions[sid] = entry

    session_ids = list(sessions.keys())

    print("\nPER-SESSION SUMMARY (canonical file selection after filtering)")
    print("-" * 90)
    for sid in session_ids:
        e = sessions[sid]
        print(f"  {sid:12s} MTR candidates={e['mtr_candidates_found']} "
              f"(excluded {e['mtr_excluded_count']}) -> "
              f"{e['mtr_path'].name if e['mtr_path'] else 'NONE FOUND'} | "
              f"ROI candidates={e['roi_candidates_found']} "
              f"(excluded {e['roi_excluded_count']}) -> "
              f"{e['roi_path'].name if e['roi_path'] else 'NONE FOUND'}")
        if e["mtr_excluded_count"] > 0:
            for path, reasons in e["mtr_excluded_reasons"]:
                print(f"      EXCLUDED (MTR): {path.name} -- {reasons} -- full: {path}")
        if e["roi_excluded_count"] > 0:
            for path, reasons in e["roi_excluded_reasons"]:
                print(f"      EXCLUDED (ROI): {path.name} -- {reasons} -- full: {path}")

    # --- Pairwise comparison on the NEWLY CHOSEN canonical files ---
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

    both_pairs_equal = {
        pair: mtr_pairs_equal.get(pair, False) and roi_pairs_equal.get(pair, False)
        for pair in mtr_pairs_equal
    }
    full_dup_groups = find_groups(both_pairs_equal, session_ids)

    print("\n" + "=" * 90)
    print("RESULT — DUPLICATE GROUPS AFTER FILTERING (both MTR and ROI identical)")
    print("=" * 90)
    if full_dup_groups:
        for i, g in enumerate(full_dup_groups, 1):
            print(f"  Group {i}: {sorted(g)}")
            for sid in sorted(g):
                e = sessions[sid]
                print(f"    {sid}: chosen MTR={e['mtr_path']}")
                print(f"    {sid}: chosen ROI={e['roi_path']}")
    else:
        print("  NONE FOUND — duplication fully resolved by archive-copy/nested-id filtering.")

    n_affected = len(set(sid for g in full_dup_groups for sid in g))
    print(f"\n>>> {n_affected} / {len(session_ids)} sessions still involved in a full "
          f"duplicate group AFTER filtering (was 7/12 before filtering).")

    # --- Also report: any session where a candidate was found but ALL were excluded ---
    print("\n" + "=" * 90)
    print("SESSIONS WITH NO CANONICAL FILE AFTER FILTERING (all candidates excluded)")
    print("=" * 90)
    any_orphaned = False
    for sid in session_ids:
        e = sessions[sid]
        if e["mtr_candidates_found"] > 0 and e["mtr_path"] is None:
            print(f"  {sid}: {e['mtr_candidates_found']} MTR candidate(s) found, ALL excluded — "
                  f"this session now has NO usable MTR file")
            any_orphaned = True
        if e["roi_candidates_found"] > 0 and e["roi_path"] is None:
            print(f"  {sid}: {e['roi_candidates_found']} ROI candidate(s) found, ALL excluded — "
                  f"this session now has NO usable ROI file")
            any_orphaned = True
    if not any_orphaned:
        print("  None — every session that had a candidate before filtering still has a canonical one.")

    # --- CSV output ---
    csv_path = args.out_dir / "duplication_v2_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "animal", "day", "mtr_candidates", "mtr_excluded",
                          "mtr_chosen_path", "mtr_hash", "roi_candidates", "roi_excluded",
                          "roi_chosen_path", "roi_hash", "still_in_dup_group"])
        sid_to_group = {}
        for i, g in enumerate(full_dup_groups, 1):
            for sid in g:
                sid_to_group[sid] = i
        for sid in session_ids:
            e = sessions[sid]
            writer.writerow([
                sid, e["animal"], e["day"],
                e["mtr_candidates_found"], e["mtr_excluded_count"],
                str(e["mtr_path"]) if e["mtr_path"] else "", e["mtr_hash"],
                e["roi_candidates_found"], e["roi_excluded_count"],
                str(e["roi_path"]) if e["roi_path"] else "", e["roi_hash"],
                sid_to_group.get(sid, ""),
            ])
    print(f"\nWrote {csv_path}")
    print("=" * 90)


if __name__ == "__main__":
    main()
