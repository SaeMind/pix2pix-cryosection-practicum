"""
verify_m1_m7_duplication.py
One-time diagnostic: m1's Day1 diagnostic images and m7's Day1 diagnostic
images were visually identical (same MTR pattern, same mask bbox positions,
same pixel counts: 18px/34px in both). This checks whether that's a real
data duplication on disk, or a coincidence / a bug in file-path resolution
that pointed both animals at the same underlying files.

Checks, in order:
  1. Resolved file paths for m1/Day1 vs m7/Day1 (ROImask.mat, MTR file) —
     are they literally the same path, or different paths with the same content?
  2. If different paths: byte-for-byte file comparison (md5 hash)
  3. If hashes differ: array-level comparison of the loaded MTR and
     phantom_mask arrays (catches "same data, different file metadata" cases)
  4. Session subfolder names (e.g. 20230528_211354_TumorSphere_1_33) — if
     these differ but content is identical, that's strong evidence of a
     genuine copy in the raw dataset rather than a symlink/path bug.

This does NOT modify train_v1.py or re-run training.

Usage:
    python verify_m1_m7_duplication.py \
        --root "<path-to>/MRI Results-Main" \
        --power-ppm 12
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
from scipy.io import loadmat


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
    """List any raw session subfolders (e.g. 20230528_211354_TumorSphere_1_33)."""
    return sorted([p.name for p in animal_dir.iterdir() if p.is_dir()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--power-ppm", type=str, default="12")
    args = parser.parse_args()

    print("=" * 80)
    print("m1 vs m7 — Day1 DUPLICATION CHECK")
    print("=" * 80)

    m1_dir = args.root / "Day1" / "m1"
    m7_dir = args.root / "Day1" / "m7"

    for label, d in [("m1", m1_dir), ("m7", m7_dir)]:
        print(f"\n{label} Day1 directory: {d}")
        print(f"  Exists: {d.exists()}")
        if not d.exists():
            continue
        print(f"  Session subfolders: {list_session_subfolders(d)}")

    print("\n" + "-" * 80)
    print("STEP 1: Resolved file paths")
    print("-" * 80)

    m1_mtr = find_mtr_file(m1_dir, args.power_ppm)
    m7_mtr = find_mtr_file(m7_dir, args.power_ppm)
    m1_roi = m1_dir / "ROImask.mat"
    m7_roi = m7_dir / "ROImask.mat"

    print(f"m1 MTR file: {m1_mtr}")
    print(f"m7 MTR file: {m7_mtr}")
    print(f"m1 ROImask:  {m1_roi} (exists={m1_roi.exists()})")
    print(f"m7 ROImask:  {m7_roi} (exists={m7_roi.exists()})")

    if m1_mtr == m7_mtr:
        print("\n>>> RESULT: m1 and m7 resolve to the LITERAL SAME MTR FILE PATH.")
        print(">>> This means find_mtr_file() or the glob pattern is broken, OR")
        print(">>> the directories themselves are the same path (symlink/alias).")
    else:
        print(f"\nPaths differ. Proceeding to content comparison.")

    if m1_mtr is None or m7_mtr is None:
        print("Cannot proceed — one or both MTR files not found.")
        return

    print("\n" + "-" * 80)
    print("STEP 2: Byte-for-byte file hash comparison")
    print("-" * 80)

    m1_mtr_hash = md5_of_file(m1_mtr)
    m7_mtr_hash = md5_of_file(m7_mtr)
    print(f"m1 MTR file MD5: {m1_mtr_hash}")
    print(f"m7 MTR file MD5: {m7_mtr_hash}")
    print(f"IDENTICAL FILES: {m1_mtr_hash == m7_mtr_hash}")

    if m1_roi.exists() and m7_roi.exists():
        m1_roi_hash = md5_of_file(m1_roi)
        m7_roi_hash = md5_of_file(m7_roi)
        print(f"\nm1 ROImask.mat MD5: {m1_roi_hash}")
        print(f"m7 ROImask.mat MD5: {m7_roi_hash}")
        print(f"IDENTICAL FILES: {m1_roi_hash == m7_roi_hash}")

    print("\n" + "-" * 80)
    print("STEP 3: Array-level comparison (in case of identical content, different bytes)")
    print("-" * 80)

    m1_mtr_arr = load_var(m1_mtr, "MTR")
    m7_mtr_arr = load_var(m7_mtr, "MTR")
    print(f"m1 MTR array shape: {m1_mtr_arr.shape}")
    print(f"m7 MTR array shape: {m7_mtr_arr.shape}")
    if m1_mtr_arr.shape == m7_mtr_arr.shape:
        arrays_equal = np.array_equal(m1_mtr_arr, m7_mtr_arr)
        print(f"MTR arrays element-wise IDENTICAL: {arrays_equal}")
        if not arrays_equal:
            max_diff = np.max(np.abs(m1_mtr_arr - m7_mtr_arr))
            print(f"  Max absolute difference: {max_diff}")
    else:
        print("Shapes differ — cannot be identical.")

    if m1_roi.exists() and m7_roi.exists():
        m1_roi_arr = load_var(m1_roi, "phantom_mask")
        m7_roi_arr = load_var(m7_roi, "phantom_mask")
        print(f"\nm1 phantom_mask shape: {m1_roi_arr.shape}")
        print(f"m7 phantom_mask shape: {m7_roi_arr.shape}")
        if m1_roi_arr.shape == m7_roi_arr.shape:
            mask_equal = np.array_equal(m1_roi_arr, m7_roi_arr)
            print(f"phantom_mask arrays element-wise IDENTICAL: {mask_equal}")

    print("\n" + "=" * 80)
    print("INTERPRETATION GUIDE")
    print("=" * 80)
    print("- If paths differ but hashes/arrays are identical: genuine file-level")
    print("  duplication in the raw dataset (e.g. m7's Day1 scan may actually be")
    print("  a copy of m1's, mislabeled, or both point to a shared source scan).")
    print("- If paths differ AND content differs: the earlier visual similarity")
    print("  was likely a false read on my part (e.g. superficially similar MTR")
    print("  color patterns at this colormap scale, not truly identical data) —")
    print("  reconsider the root-cause hypothesis.")
    print("- If paths are literally identical: bug in find_mtr_file()/directory")
    print("  resolution, fixable in train_v1.py without any data-integrity concern.")
    print("=" * 80)


if __name__ == "__main__":
    main()
