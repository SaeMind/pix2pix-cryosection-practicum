"""
train_v1.py
Track 2 Practicum — Phase 2: 2D U-Net regression, Day1 -> Day8 MTR map prediction.

LOCKED SCOPE (per drive-verified-decisions-sept2026.md, PHASE 1 EXECUTION RESULT,
2026-09-25 — supersedes the n=7/Days-1-8-16/7-fold framing in opus-session-phase1-v2.md):

    Animals:     m1, m2, m3, m4, m6, m7   (6 animals — m5 excluded, no Day1/Day8 pair)
    Timepoints:  Day1 (input) -> Day8 (target), same animal, same tumor side
    Sides:       GBM1a-side and M1123-side per animal (ROImask.mat slices)
    CV:          Leave-one-animal-out, 6 folds (NOT 7)
    Architecture: 2D U-Net regression, 32->256 channels, ~500K-1M params
    Loss:        MSE + SSIM (weighted sum)

Target definition (input->output pair) was explicitly decided, not assumed:
    Input:  Day1 MTR map, single channel, cropped to CROP_SIZE x CROP_SIZE (16x16 default)
    Output: Day8 MTR map, single channel, same crop window (same animal, same side)
Rationale logged in chat — matches the practicum's aggressiveness/progression
framing and avoids missing-modality / channel-registration issues present in
the B0/T1 alternative. See chat log if this needs to be revisited.

CROPPING (2026-09-26, revised from initial full-64x64-canvas masking): the
first LOAO-CV run (6 folds, full-canvas masking) produced mean val SSIM of
~0.0012 — effectively no learned structure. Root cause: ROI sizes (12-34px)
on a 4096px (64x64) canvas gave <1% signal density, making the trivial
all-zero-background prediction near-optimal under MSE and leaving SSIM
computed mostly over flat background. Fixed by cropping each sample to a
CROP_SIZE x CROP_SIZE window centered on the ROI, raising signal density to
roughly (ROI px)/(CROP_SIZE^2). See crop_to_roi() for implementation.

Data source note: this script expects .mat files already located under the
Drive-verified path structure:
    <root>/Day1/m{k}/pwr{p}_brainMTRmap@{ppm}ppm_MTRdata.mat  -> var 'MTR', 64x64
    <root>/Day1/m{k}/ROImask.mat                              -> var 'phantom_mask'
    <root>/Day8/m{k}/... (same pattern)

Per the CONSTRAINTS in opus-session-phase1-v2.md:
    - Do NOT use Bruker header metadata for labeling. Folder path is ground truth.
    - Use scipy.io.loadmat for v5 .mat files; h5py for v7.3. Check signature first.
    - Report actual n and actual missingness; do not backfill or interpolate silently.

SIDE-LABELING STATUS (2026-09-26): this script is SIDE-AGNOSTIC by design, not
by default/fallback. Two candidate methods for assigning GBM1a-vs-M1123 identity
to each phantom_mask slice were investigated and BOTH rejected:
  1. MTR-signal-magnitude heuristic (higher signal = M1123) — REJECTED as circular,
     since the model trains on MTR maps; using MTR to assign the label the model
     is evaluated against would guarantee the paper's own finding by construction.
  2. Cross-referencing Ex_vivo-Immunohistopathology/Day{N}-Brain/ CD44/mannose IF
     images — REJECTED: confirmed by direct file listing that these are pooled/
     representative images with NO per-animal identifier in any filename across
     Day1-Brain, Day8-Brain, or Day16-Brain.
See drive-verified-decisions-sept2026.md, OPEN ITEM 5, for full detail. Pending
Dr. Kuddannaya's response, this script trains Day1->Day8 MTR prediction per ROI
slice WITHOUT a class label. Side identity, once resolved, is meant to be applied
as a POST-HOC interpretation layer to trained-model outputs — it is intentionally
not wired into training or into LOAO-CV fold construction here.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("ERROR: PyTorch is required. Install with: pip install torch", file=sys.stderr)
    sys.exit(1)

try:
    from scipy.io import loadmat
except Exception as e:
    print(f"ERROR importing scipy.io.loadmat: {type(e).__name__}: {e}", file=sys.stderr)
    print("This is NOT necessarily a missing-package error — scipy may be installed but "
          "failing to import due to a version conflict (e.g. with numpy). Run this to "
          "isolate it: python -c \"from scipy.io import loadmat; print('OK')\"", file=sys.stderr)
    sys.exit(1)

try:
    from scipy.ndimage import label as ndimage_label, sum as ndimage_sum
except Exception as e:
    print(f"ERROR importing scipy.ndimage: {type(e).__name__}: {e}", file=sys.stderr)
    print("Required for largest-connected-component ROI centroid logic (roi_centroid()).",
          file=sys.stderr)
    sys.exit(1)

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False


# ----------------------------------------------------------------------------
# LOCKED SCOPE CONSTANTS — do not silently expand without a new decision log entry
# ----------------------------------------------------------------------------
LOCKED_ANIMALS = ["m1", "m2", "m3", "m4", "m6", "m7"]  # m5 excluded — see header docstring
LOCKED_DAYS_INPUT = "Day1"
LOCKED_DAYS_TARGET = "Day8"
EXCLUDED_ANIMALS = ["m5"]  # logged explicitly, not silently dropped
MIN_REAL_ROI_PX = 15  # per Phase 1 QC threshold, drive-verified-decisions-sept2026.md

# ROI-sparsity fix (2026-09-26): the largest observed ROI across all usable
# animal/slice combinations was 34px (m1, slice1). On a full 64x64=4096px
# canvas that is <1% signal density, which made MSE/SSIM loss dominated by
# the trivial all-zero-background prediction (see LOAO-CV run 1 result:
# mean val SSIM ~0.0012, effectively no learned structure — logged in chat,
# 2026-09-26). Fix: crop a fixed-size bounding box centered on each ROI's
# centroid instead of masking within the full 64x64 canvas. This increases
# signal density from <1% to roughly (ROI px)/(CROP_SIZE^2), e.g. ~7-13%
# at CROP_SIZE=16 for a 20-34px ROI — still sparse, but no longer degenerate.
CROP_SIZE = 16  # output is CROP_SIZE x CROP_SIZE, fixed across all samples

# Known Day16-orientation-flip animals (excluded from THIS script's scope entirely,
# since this script only touches Day1/Day8 — listed here for traceability only)
KNOWN_DAY16_FLIPS = {"m4": "flipped (mirror)", "m6": "flipped (upside-down)", "m5": "Day8 flipped"}


# ----------------------------------------------------------------------------
# .mat loading (v5 vs v7.3 dispatch, per CONSTRAINTS in opus-session-phase1-v2.md)
# ----------------------------------------------------------------------------
def _is_hdf5(path: Path) -> bool:
    """Check file signature rather than assuming format from extension."""
    with open(path, "rb") as f:
        sig = f.read(8)
    return sig[:4] == b"\x89HDF"


def load_mat_var(path: Path, varname: str) -> np.ndarray:
    """Load a named variable from a .mat file, dispatching v5 vs v7.3 by signature."""
    if not path.exists():
        raise FileNotFoundError(str(path))
    if _is_hdf5(path):
        if not HAS_H5PY:
            raise RuntimeError(f"{path} is HDF5-format (.mat v7.3) but h5py is not installed.")
        with h5py.File(path, "r") as f:
            if varname not in f:
                raise KeyError(f"Variable '{varname}' not found in {path} (v7.3). Keys: {list(f.keys())}")
            arr = np.array(f[varname])
            # h5py stores MATLAB arrays transposed relative to scipy.io.loadmat
            return arr.T if arr.ndim >= 2 else arr
    else:
        mat = loadmat(str(path))
        if varname not in mat:
            keys = [k for k in mat.keys() if not k.startswith("__")]
            raise KeyError(f"Variable '{varname}' not found in {path} (v5). Keys: {keys}")
        return mat[varname]


# ----------------------------------------------------------------------------
# Session discovery + missingness reporting (per CONSTRAINTS: "report actual n
# and actual missingness at each step; do not backfill or interpolate silently")
# ----------------------------------------------------------------------------
@dataclass
class SessionAvailability:
    animal: str
    day1_mtr_found: bool = False
    day8_mtr_found: bool = False
    day1_roimask_found: bool = False
    day8_roimask_found: bool = False
    day1_mtr_path: Path = None
    day8_mtr_path: Path = None
    day1_roimask_path: Path = None
    day8_roimask_path: Path = None
    usable: bool = False
    exclusion_reason: str = ""



ARCHIVE_TERMS = ["onedrive_", "copy", "backup"]  # ported from GLOBE_Fall2026 notebook


def is_archive_copy(relative_path) -> bool:
    """
    Ported from GLOBE_Fall2026 (Ghaemi_et_al__2026_01_dataset_inventory.ipynb)
    detect_archive_copy(). Confirmed real artifact via audit_duplication_v2.py,
    2026-09-26: e.g. Day8/M6/OneDrive_1_11-5-2023 (1)/m2/... is a genuine
    nested OneDrive-sync copy of m2's data inside m6's Day8 folder tree.
    """
    text = str(relative_path).lower()
    return any(term in text for term in ARCHIVE_TERMS)


def nested_mouse_ids(relative_path) -> list:
    """
    Ported from GLOBE_Fall2026 detect_nested_mouse_ids(), WITH a cross-platform
    fix: the original iterates Path(...).parts, which only splits on the
    native OS separator. A Windows-generated path string re-used on macOS/
    Linux (or vice versa) would silently fail to split and return []. Fixed
    by normalizing both backslash and forward-slash before splitting —
    verified against the notebook's own example path, 2026-09-26.
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


def select_canonical_file(candidates: list) -> tuple:
    """
    From a list of candidate file paths, exclude archive-copy paths and
    paths with conflicting nested mouse IDs, then return the shallowest/
    alphabetically-first remaining candidate. Returns (chosen_or_None,
    excluded_list) where excluded_list is [(path, reasons), ...] for
    reporting. Ported+verified in audit_duplication_v2.py, 2026-09-26 —
    see that script's standalone tests for the cases this handles
    (single clean file, only-archive-copy case returns None rather than
    silently falling back).

    NOTE: this filtering explains and fixes m6_Day8/m7_Day8's messy
    candidate pools (confirmed via audit_duplication_v2.py). It does NOT
    explain or fix the separate, still-unresolved cross-animal
    duplication found for m1/m7 Day1, m1/m3/m4 Day8, and m2/m6 Day1 —
    those files sit at clean, non-nested, non-archive paths and remain
    genuinely byte-identical after this filtering. See OPEN ITEM 6,
    drive-verified-decisions-sept2026.md, for full detail. Training
    against those sessions still proceeds (per explicit instruction,
    2026-09-26) but the duplication is NOT fixed by this function for
    those specific sessions — it is a known, labeled limitation.
    """
    excluded = []
    kept = []
    for c in candidates:
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


def find_mtr_file(animal_dir: Path, power_ppm: str = "12") -> Path:
    """
    Locate the MTR map file for a given power level.
    Filename pattern: pwr{1-4}_brainMTRmap@{ppm}ppm_MTRdata.mat
    Default power level is 12ppm (matches the mannose CEST signature used
    throughout the paper's Fig. 3F/5B quantification at 1.2 ppm — but note
    this script operates on the raw MTR map, not the scalar MTRasym metric).

    CHANGED 2026-09-26: now searches RECURSIVELY (rglob, not glob) and
    applies select_canonical_file() to exclude archive-copy/nested-mouse-ID
    candidates before choosing. This is a direct port of the logic verified
    in audit_duplication_v2.py. Confirmed fix for m6_Day8/m7_Day8 (whose
    candidate pools contained OneDrive-nested copies of OTHER animals'
    data); confirmed NOT a fix for the separate m1/m7, m1/m3/m4, m2/m6
    duplication (those candidates are clean at this filter's own criteria
    and remain byte-identical — see OPEN ITEM 6).
    """
    candidates = list(animal_dir.rglob(f"pwr*_brainMTRmap@{power_ppm}ppm_MTRdata.mat"))
    chosen, excluded = select_canonical_file(candidates)
    if excluded:
        print(f"  NOTE [{animal_dir}]: excluded {len(excluded)} MTR candidate(s) as "
              f"archive-copy/nested-mouse-ID conflicts: "
              f"{[(str(p.name), r) for p, r in excluded]}")
    return chosen


def find_roi_file(animal_dir: Path) -> Path:
    """
    Locate ROImask.mat, with the same archive-copy/nested-mouse-ID
    filtering as find_mtr_file(). The ORIGINAL script only ever checked
    `animal_dir / "ROImask.mat"` directly (no search, no duplicate-safety
    at all) — this is a stricter replacement that also protects against a
    nested/archived ROImask.mat shadowing the real one, consistent with
    how audit_duplication_v2.py verified ROI hashes, not just MTR hashes.
    """
    candidates = list(animal_dir.rglob("ROImask.mat"))
    chosen, excluded = select_canonical_file(candidates)
    if excluded:
        print(f"  NOTE [{animal_dir}]: excluded {len(excluded)} ROImask candidate(s) as "
              f"archive-copy/nested-mouse-ID conflicts: "
              f"{[(str(p.name), r) for p, r in excluded]}")
    return chosen


def discover_sessions(root: Path, power_ppm: str, animals=LOCKED_ANIMALS) -> list[SessionAvailability]:
    """
    Scan the locked animal set for Day1/Day8 MTR + ROImask availability.
    Does NOT scan Day16, m5, or any GBM1a/M{k}-D30 folders — out of scope for
    this script by design (see header docstring).
    """
    results = []
    for animal in animals:
        avail = SessionAvailability(animal=animal)

        day1_dir = root / LOCKED_DAYS_INPUT / animal
        day8_dir = root / LOCKED_DAYS_TARGET / animal

        if day1_dir.exists():
            mtr_path = find_mtr_file(day1_dir, power_ppm)
            if mtr_path:
                avail.day1_mtr_found = True
                avail.day1_mtr_path = mtr_path
            roi_path = find_roi_file(day1_dir)
            if roi_path:
                avail.day1_roimask_found = True
                avail.day1_roimask_path = roi_path

        if day8_dir.exists():
            mtr_path = find_mtr_file(day8_dir, power_ppm)
            if mtr_path:
                avail.day8_mtr_found = True
                avail.day8_mtr_path = mtr_path
            roi_path = find_roi_file(day8_dir)
            if roi_path:
                avail.day8_roimask_found = True
                avail.day8_roimask_path = roi_path

        if avail.day1_mtr_found and avail.day8_mtr_found and avail.day1_roimask_found and avail.day8_roimask_found:
            avail.usable = True
        else:
            missing = []
            if not avail.day1_mtr_found:
                missing.append("Day1 MTR")
            if not avail.day8_mtr_found:
                missing.append("Day8 MTR")
            if not avail.day1_roimask_found:
                missing.append("Day1 ROImask")
            if not avail.day8_roimask_found:
                missing.append("Day8 ROImask")
            avail.exclusion_reason = "missing: " + ", ".join(missing)

        results.append(avail)
    return results


def print_missingness_report(sessions: list[SessionAvailability], power_ppm: str):
    print("=" * 72)
    print(f"SESSION DISCOVERY REPORT (power level: {power_ppm}ppm)")
    print(f"Locked animal set: {LOCKED_ANIMALS} (n={len(LOCKED_ANIMALS)})")
    print(f"Explicitly excluded animal (not scanned): {EXCLUDED_ANIMALS}")
    print("=" * 72)
    n_usable = 0
    for s in sessions:
        status = "USABLE" if s.usable else f"EXCLUDED ({s.exclusion_reason})"
        print(f"  {s.animal}: {status}")
        if s.usable:
            n_usable += 1
    print("-" * 72)
    print(f"Usable animals: {n_usable} / {len(sessions)}")
    if n_usable < len(sessions):
        print("WARNING: fewer than the full locked cohort is usable at this power level.")
        print("This is NOT auto-corrected. Re-run with a different --power-ppm or")
        print("investigate the missing files before training.")
    print("=" * 72)

    print("!" * 72)
    print("KNOWN DATA-QUALITY LIMITATION — READ BEFORE INTERPRETING RESULTS")
    print("!" * 72)
    print("Cross-animal file duplication was confirmed via MD5+array-level audit")
    print("(audit_duplication.py, audit_duplication_v2.py, 2026-09-26). Archive-copy/")
    print("OneDrive-sync artifacts were identified and filtered (fixed m6_Day8, m7_Day8).")
    print("The following remain GENUINE, UNEXPLAINED duplicates at clean file paths —")
    print("NOT fixed by this script's filtering, confirmed still present as of the last audit:")
    print("  - m1 Day1 == m7 Day1 (byte-identical MTR + ROImask)")
    print("  - m1 Day8 == m3 Day8 == m4 Day8 (byte-identical MTR + ROImask, 3-way)")
    print("  - m2 Day1 == m6 Day1 (byte-identical MTR + ROImask)")
    print("Net effect: ZERO animals in this 6-animal cohort have both Day1 AND Day8")
    print("confirmed independent. Training proceeds on explicit instruction (2026-09-26)")
    print("as a PRELIMINARY / PROOF-OF-CONCEPT run pending Dr. Kuddannaya's input on data")
    print("provenance. Results below should NOT be presented as a validated LOAO-CV finding.")
    print("See OPEN ITEM 6, drive-verified-decisions-sept2026.md, for full detail.")
    print("!" * 72)

    if n_usable == 0:
        print("FATAL: zero usable animals. Cannot train. Exiting.")
        sys.exit(1)


# ----------------------------------------------------------------------------
# Side mapping — OPTIONAL, side-agnostic by default
# ----------------------------------------------------------------------------
def load_side_map(path: Path) -> dict:
    """
    Optional. Expected CSV columns: animal,slice_index,side
    where side in {"GBM1a", "M1123"} and slice_index indexes into the
    phantom_mask's slice dimension for that animal.

    NOT required for training (see module docstring, "SIDE-LABELING STATUS").
    When provided, it is used ONLY to annotate output rows/reports with a side
    label for post-hoc interpretation — it does not gate which samples are
    built and does not enter the model, loss, or LOAO-CV fold construction.
    Any animal/slice not covered by this file is still trained on, tagged
    side="unknown".
    """
    if not path.exists():
        print(f"NOTE: --side-map not found at {path} — proceeding side-agnostic "
              f"(all slices tagged side='unknown'). This is expected until the "
              f"per-animal GBM1a/M1123 mapping is resolved (see OPEN ITEM 5, "
              f"drive-verified-decisions-sept2026.md).")
        return {}
    mapping = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        required_cols = {"animal", "slice_index", "side"}
        if not required_cols.issubset(reader.fieldnames or []):
            raise ValueError(f"--side-map CSV must have columns {required_cols}, found {reader.fieldnames}")
        for row in reader:
            animal = row["animal"].strip()
            side = row["side"].strip()
            if side not in ("GBM1a", "M1123"):
                raise ValueError(f"Invalid side '{side}' for animal {animal}; must be GBM1a or M1123")
            slice_idx = int(row["slice_index"])
            mapping.setdefault(animal, {})[slice_idx] = side
    return mapping


# ----------------------------------------------------------------------------
# Dataset
# ----------------------------------------------------------------------------
@dataclass
class Sample:
    animal: str
    slice_index: int  # traceable back to phantom_mask slice — needed to apply
                       # a side label later once OPEN ITEM 5 is resolved, without
                       # re-running the full pipeline
    side: str          # "GBM1a" / "M1123" if --side-map covers it, else "unknown"
    input_map: np.ndarray  # Day1 MTR, cropped to CROP_SIZE x CROP_SIZE around this slice's ROI
    target_map: np.ndarray  # Day8 MTR, same crop window, CROP_SIZE x CROP_SIZE
    roi_px_count: int


def n_mask_slices(phantom_mask: np.ndarray, mtr_shape: tuple) -> int:
    """Determine how many ROI slices phantom_mask contains (see slice-axis
    heuristic used in inspect_roimask.py — same logic applied here)."""
    if phantom_mask.ndim == 2:
        return 1
    spatial_dims = set(mtr_shape)
    for ax, dim in enumerate(phantom_mask.shape):
        if dim not in spatial_dims:
            return phantom_mask.shape[ax]
    return phantom_mask.shape[0]  # ambiguous fallback, flagged by caller


def get_mask_slice(phantom_mask: np.ndarray, slice_idx: int, mtr_shape: tuple) -> np.ndarray:
    if phantom_mask.ndim == 2:
        return phantom_mask
    spatial_dims = set(mtr_shape)
    slice_axis = None
    for ax, dim in enumerate(phantom_mask.shape):
        if dim not in spatial_dims:
            slice_axis = ax
            break
    if slice_axis is None:
        slice_axis = 0
    return np.take(phantom_mask, slice_idx, axis=slice_axis)


def apply_roi_mask(mtr_map: np.ndarray, mask_slice: np.ndarray) -> tuple:
    """
    Apply one already-extracted ROI slice to the MTR map. Returns
    (masked_map, pixel_count). Pixels outside the ROI are set to 0 (not NaN)
    so the network sees a consistent zero-background.

    RETAINED for px_count/thresholding purposes only. As of 2026-09-26 this
    is NO LONGER what feeds the network — see crop_to_roi() below, which
    replaces the full-64x64-masked-canvas approach with a fixed-size crop.
    """
    mask_bool = mask_slice.astype(bool)
    px_count = int(mask_bool.sum())

    if px_count < MIN_REAL_ROI_PX:
        return None, px_count

    masked = np.where(mask_bool, mtr_map, 0.0).astype(np.float32)
    return masked, px_count


def roi_centroid(mask_slice: np.ndarray) -> tuple:
    """
    Return (row, col) centroid of the LARGEST CONNECTED COMPONENT in a
    boolean mask, rounded to nearest int.

    CHANGED 2026-09-26 from a plain mean-of-all-mask-pixels centroid. That
    approach silently failed on non-convex/multi-blob masks: the arithmetic
    mean of two disconnected fragments can land in the empty gap between
    them (confirmed by reproduction test — a 116px union mask produced a
    centroid landing on 0 mask pixels, causing m1/m2/m7 to lose entire
    animals' worth of samples in the crop-size=16 LOAO-CV run). Since each
    phantom_mask slice is expected to represent ONE tumor side (GBM1a or
    M1123 — see paper Methods), a real ROI should be a single contiguous
    region; any additional disconnected fragment is more likely segmentation
    noise than a second tumor focus, so it is dropped, not preserved.

    Falls back to the plain all-pixel centroid if scipy.ndimage labeling
    finds no components at all (should not happen if px_count > 0, included
    defensively).
    """
    mask_bool = mask_slice.astype(bool)
    labeled, n_components = ndimage_label(mask_bool)

    if n_components == 0:
        # Defensive fallback — should be unreachable if caller already
        # checked px_count > 0, but avoid a crash if it happens anyway.
        ys, xs = np.nonzero(mask_bool)
        return int(round(ys.mean())), int(round(xs.mean()))

    if n_components > 1:
        sizes = ndimage_sum(mask_bool, labeled, index=range(1, n_components + 1))
        largest_label = int(np.argmax(sizes)) + 1
        component_mask = labeled == largest_label
    else:
        component_mask = mask_bool

    ys, xs = np.nonzero(component_mask)
    return int(round(ys.mean())), int(round(xs.mean()))


def crop_to_roi(mtr_map: np.ndarray, mask_slice: np.ndarray, center: tuple, crop_size: int = CROP_SIZE) -> tuple:
    """
    Crop a fixed crop_size x crop_size window from mtr_map, centered on
    `center` (row, col) — NOT on this slice's own centroid, so that Day1
    and Day8 crops for the same sample use an IDENTICAL window (see
    build_samples: center is computed once from the union of Day1+Day8
    masks per slice_idx, not independently per day). This avoids the
    input/target windows silently differing if the tumor position drifted
    slightly between days, which would otherwise misalign the regression
    target.

    Pixels outside the ROI within the crop are zeroed (same convention as
    apply_roi_mask). Pixels outside the mtr_map's own bounds (crop window
    extends past image edge) are zero-padded.

    Returns (cropped_map, px_count_within_crop). px_count is the ROI pixel
    count actually captured inside this crop window — may be less than the
    slice's total ROI px_count if the ROI is larger than crop_size or if
    edge-padding clipped part of it. Caller re-checks against
    MIN_REAL_ROI_PX using this crop-local count, not the pre-crop count.
    """
    H, W = mtr_map.shape
    r, c = center
    half = crop_size // 2

    r0, r1 = r - half, r - half + crop_size
    c0, c1 = c - half, c - half + crop_size

    canvas_mtr = np.zeros((crop_size, crop_size), dtype=np.float32)
    canvas_mask = np.zeros((crop_size, crop_size), dtype=bool)

    src_r0, src_r1 = max(0, r0), min(H, r1)
    src_c0, src_c1 = max(0, c0), min(W, c1)
    dst_r0, dst_r1 = src_r0 - r0, src_r1 - r0
    dst_c0, dst_c1 = src_c0 - c0, src_c1 - c0

    if src_r1 > src_r0 and src_c1 > src_c0:
        canvas_mtr[dst_r0:dst_r1, dst_c0:dst_c1] = mtr_map[src_r0:src_r1, src_c0:src_c1]
        canvas_mask[dst_r0:dst_r1, dst_c0:dst_c1] = mask_slice.astype(bool)[src_r0:src_r1, src_c0:src_c1]

    px_count = int(canvas_mask.sum())
    cropped = np.where(canvas_mask, canvas_mtr, 0.0).astype(np.float32)
    return cropped, px_count


def build_samples(sessions: list[SessionAvailability], side_map: dict, power_ppm: str) -> tuple[list, dict]:
    """
    Build (input, target) sample pairs for EVERY ROI slice found in each
    animal's phantom_mask on Day1, matched by slice_index to the same slice
    on Day8 — WITHOUT requiring or assuming a GBM1a/M1123 side label (see
    module docstring, "SIDE-LABELING STATUS"). If side_map has an entry for
    a given animal/slice_index, that label is attached for reporting only;
    otherwise side is tagged "unknown". Returns (samples, exclusion_log).

    NOTE: this assumes slice_index is stable between Day1 and Day8 for the
    same animal (i.e., phantom_mask slice 0 on Day1 and slice 0 on Day8
    refer to the same physical tumor side). This is a genuine assumption,
    not verified against the data — flag if cross-day slice-index stability
    turns out to be false (e.g. if QC or manual review shows slice order
    was re-generated per session rather than fixed per animal).

    CROPPING (2026-09-26): both Day1 and Day8 are cropped to a shared
    CROP_SIZE x CROP_SIZE window, centered on the CENTROID OF THE UNION of
    the Day1 and Day8 masks for this slice_idx (not each day's own
    centroid independently). This guarantees input and target windows are
    spatially identical, which matters for the regression task to be
    well-posed — if the two days used different centers, the network could
    be asked to predict apparent tumor "movement" that is actually just a
    difference in crop placement, not a real biological change.
    """
    samples = []
    exclusion_log = {}

    for s in sessions:
        if not s.usable:
            exclusion_log[s.animal] = f"session-level: {s.exclusion_reason}"
            continue

        day1_mtr = load_mat_var(s.day1_mtr_path, "MTR")
        day8_mtr = load_mat_var(s.day8_mtr_path, "MTR")
        day1_mask = load_mat_var(s.day1_roimask_path, "phantom_mask")
        day8_mask = load_mat_var(s.day8_roimask_path, "phantom_mask")

        n_slices_day1 = n_mask_slices(day1_mask, day1_mtr.shape)
        n_slices_day8 = n_mask_slices(day8_mask, day8_mtr.shape)
        n_slices = min(n_slices_day1, n_slices_day8)

        if n_slices_day1 != n_slices_day8:
            print(f"  WARNING [{s.animal}]: slice count mismatch Day1={n_slices_day1} "
                  f"vs Day8={n_slices_day8}. Using min={n_slices}; extra slices dropped.")

        animal_exclusions = []
        for slice_idx in range(n_slices):
            day1_slice = get_mask_slice(day1_mask, slice_idx, day1_mtr.shape)
            day8_slice = get_mask_slice(day8_mask, slice_idx, day8_mtr.shape)

            day1_bool = day1_slice.astype(bool)
            day8_bool = day8_slice.astype(bool)
            union_bool = day1_bool | day8_bool

            union_px = int(union_bool.sum())
            if union_px < MIN_REAL_ROI_PX:
                animal_exclusions.append(
                    f"slice{slice_idx}: union of Day1+Day8 ROI below {MIN_REAL_ROI_PX}px threshold ({union_px}px)")
                continue

            n_components = ndimage_label(union_bool)[1]
            if n_components > 1:
                print(f"  NOTE [{s.animal} slice{slice_idx}]: union mask has {n_components} "
                      f"disconnected components ({union_px}px total) — cropping around the "
                      f"largest component only. Worth a visual QC check (same method as the "
                      f"Phase 1 Day16-flip sweep) to confirm this is segmentation noise and "
                      f"not a real secondary focus.")

            center = roi_centroid(union_bool)

            in_cropped, in_px = crop_to_roi(day1_mtr, day1_slice, center)
            out_cropped, out_px = crop_to_roi(day8_mtr, day8_slice, center)

            if in_px < MIN_REAL_ROI_PX:
                animal_exclusions.append(
                    f"slice{slice_idx}: Day1 ROI below {MIN_REAL_ROI_PX}px threshold within "
                    f"{CROP_SIZE}x{CROP_SIZE} crop ({in_px}px of {union_px}px union — ROI may "
                    f"exceed crop_size or lie mostly outside the shared window)")
                continue
            if out_px < MIN_REAL_ROI_PX:
                animal_exclusions.append(
                    f"slice{slice_idx}: Day8 ROI below {MIN_REAL_ROI_PX}px threshold within "
                    f"{CROP_SIZE}x{CROP_SIZE} crop ({out_px}px of {union_px}px union)")
                continue

            side_label = side_map.get(s.animal, {}).get(slice_idx, "unknown")

            samples.append(Sample(
                animal=s.animal,
                slice_index=slice_idx,
                side=side_label,
                input_map=in_cropped,
                target_map=out_cropped,
                roi_px_count=min(in_px, out_px),
            ))

        if animal_exclusions:
            exclusion_log[s.animal] = "; ".join(animal_exclusions)

    return samples, exclusion_log


class MTRDataset(Dataset):
    def __init__(self, samples: list):
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        x = torch.from_numpy(s.input_map).unsqueeze(0).float()   # (1, CROP_SIZE, CROP_SIZE)
        y = torch.from_numpy(s.target_map).unsqueeze(0).float()  # (1, CROP_SIZE, CROP_SIZE)
        return x, y


# ----------------------------------------------------------------------------
# 2D U-Net (regression) — sized to ~500K-1M params per architecture decision
# (rejecting the oversized pix2pix/3D-UNet configs for this sample size,
# see drive-verified-decisions-sept2026.md "ARCHITECTURE DECISION")
# ----------------------------------------------------------------------------
class ConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class UNet2D(nn.Module):
    """
    2-stage 2D U-Net (16x16 -> 8x8 -> 4x4 bottleneck), sized for CROP_SIZE=16
    input/target crops (see ROI-sparsity fix, 2026-09-26).

    ARCHITECTURE CHANGE FROM ORIGINAL SPEC: opus-session-phase1-v2.md /
    drive-verified-decisions-sept2026.md specified a 4-downsampling-stage
    U-Net (32->256ch) sized for the original full-64x64-canvas input. That
    depth is no longer compatible with CROP_SIZE=16 inputs — 4 stages of
    MaxPool2d(2) would take 16->8->4->2->1, collapsing the bottleneck to a
    1x1 feature map and destroying the spatial context a U-Net's bottleneck
    is meant to preserve. This is reduced to 2 stages (bottleneck at 4x4)
    to keep genuine multi-scale structure at this crop size. Channel widths
    are rebalanced (see below) to keep total params in the original
    ~500K-1M target band despite the shallower depth.

    Input: (B, 1, CROP_SIZE, CROP_SIZE) Day1 MTR map, ROI-cropped
    Output: (B, 1, CROP_SIZE, CROP_SIZE) predicted Day8 MTR map, same window
    """
    def __init__(self, in_ch=1, out_ch=1, base_ch=48):
        super().__init__()
        # 2-stage topology: enc1 -> pool -> enc2 -> pool -> bottleneck -> dec2 -> dec1
        # base_ch=48 (48->96, bottleneck 96) targets ~500K-1M params at this
        # shallower depth — verify against the printed n_params at runtime,
        # same as always; --base-channels remains CLI-overridable.
        c1, c2, cb = base_ch, base_ch * 2, base_ch * 2

        self.enc1 = ConvBlock(in_ch, c1)      # 48, at 16x16
        self.enc2 = ConvBlock(c1, c2)         # 96, at 8x8
        self.pool = nn.MaxPool2d(2)

        self.bottleneck = ConvBlock(c2, cb)   # 96, at 4x4

        self.up2 = nn.ConvTranspose2d(cb, c2, 2, stride=2)
        self.dec2 = ConvBlock(c2 + c2, c2)
        self.up1 = nn.ConvTranspose2d(c2, c1, 2, stride=2)
        self.dec1 = ConvBlock(c1 + c1, c1)

        self.out_conv = nn.Conv2d(c1, out_ch, 1)

    def forward(self, x):
        e1 = self.enc1(x)                      # 16x16
        e2 = self.enc2(self.pool(e1))           # 8x8

        b = self.bottleneck(self.pool(e2))      # 4x4

        d2 = self.up2(b)                        # 8x8
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)                       # 16x16
        d1 = self.dec1(torch.cat([d1, e1], dim=1))

        return self.out_conv(d1)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ----------------------------------------------------------------------------
# SSIM (simple single-channel implementation, no external dep required)
# ----------------------------------------------------------------------------
def gaussian_window(size: int, sigma: float) -> torch.Tensor:
    coords = torch.arange(size, dtype=torch.float32) - size // 2
    g = torch.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = g / g.sum()
    return g.unsqueeze(0) * g.unsqueeze(1)


def ssim(img1: torch.Tensor, img2: torch.Tensor, window_size: int = 5, data_range: float = 1.0) -> torch.Tensor:
    """Single-channel SSIM, batched. img1/img2: (B, 1, H, W).
    window_size lowered from 7->5 (2026-09-26) to suit CROP_SIZE=16 inputs —
    a 7px window on a 16px image covers ~44% of the dimension per window,
    which is large relative to image size; 5px is a better fit for local
    structure at this scale. Not independently re-verified beyond this
    reasoning — flag if SSIM values still look degenerate after re-running."""
    device = img1.device
    window = gaussian_window(window_size, sigma=1.5).to(device).unsqueeze(0).unsqueeze(0)

    C1 = (0.01 * data_range) ** 2
    C2 = (0.03 * data_range) ** 2

    pad = window_size // 2
    mu1 = F.conv2d(img1, window, padding=pad)
    mu2 = F.conv2d(img2, window, padding=pad)

    mu1_sq, mu2_sq, mu1_mu2 = mu1 ** 2, mu2 ** 2, mu1 * mu2

    sigma1_sq = F.conv2d(img1 * img1, window, padding=pad) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=pad) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=pad) - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return ssim_map.mean()


def combined_loss(pred: torch.Tensor, target: torch.Tensor, ssim_weight: float, data_range: float) -> tuple:
    mse = F.mse_loss(pred, target)
    s = ssim(pred, target, data_range=data_range)
    ssim_loss = 1.0 - s
    total = (1 - ssim_weight) * mse + ssim_weight * ssim_loss
    return total, mse.item(), s.item()


# ----------------------------------------------------------------------------
# LOAO-CV training loop — 6 FOLDS (per locked scope, not 7)
# ----------------------------------------------------------------------------
def train_one_fold(train_samples, val_samples, args, fold_animal, device):
    train_ds = MTRDataset(train_samples)
    val_ds = MTRDataset(val_samples)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    model = UNet2D(in_ch=1, out_ch=1, base_ch=args.base_channels).to(device)
    n_params = count_params(model)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_val_loss = float("inf")
    history = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_losses = []
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            pred = model(x)
            loss, mse_val, ssim_val = combined_loss(pred, y, args.ssim_weight, args.data_range)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses, val_mses, val_ssims = [], [], []
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x)
                loss, mse_val, ssim_val = combined_loss(pred, y, args.ssim_weight, args.data_range)
                val_losses.append(loss.item())
                val_mses.append(mse_val)
                val_ssims.append(ssim_val)

        train_loss_mean = float(np.mean(train_losses)) if train_losses else float("nan")
        val_loss_mean = float(np.mean(val_losses)) if val_losses else float("nan")
        val_mse_mean = float(np.mean(val_mses)) if val_mses else float("nan")
        val_ssim_mean = float(np.mean(val_ssims)) if val_ssims else float("nan")

        history.append({
            "epoch": epoch,
            "train_loss": train_loss_mean,
            "val_loss": val_loss_mean,
            "val_mse": val_mse_mean,
            "val_ssim": val_ssim_mean,
        })

        if val_loss_mean < best_val_loss:
            best_val_loss = val_loss_mean

        if epoch % max(1, args.epochs // 10) == 0 or epoch == 1 or epoch == args.epochs:
            print(f"    [fold={fold_animal}] epoch {epoch:3d}/{args.epochs} "
                  f"train_loss={train_loss_mean:.5f} val_loss={val_loss_mean:.5f} "
                  f"val_mse={val_mse_mean:.5f} val_ssim={val_ssim_mean:.4f}")

    return {
        "fold_animal": fold_animal,
        "n_train": len(train_samples),
        "n_val": len(val_samples),
        "n_params": n_params,
        "best_val_loss": best_val_loss,
        "final_val_mse": history[-1]["val_mse"] if history else None,
        "final_val_ssim": history[-1]["val_ssim"] if history else None,
        "history": history,
    }


def run_loao_cv(samples: list, args, device):
    """
    Leave-one-animal-out. LOCKED SCOPE = 6 animals => 6 folds.
    Explicit assertion below guards against silent scope drift.
    """
    animals_present = sorted(set(s.animal for s in samples))
    n_folds = len(animals_present)

    if n_folds != len(LOCKED_ANIMALS):
        print(f"WARNING: expected {len(LOCKED_ANIMALS)} animals for LOAO-CV per locked scope, "
              f"found {n_folds} with usable samples: {animals_present}")
        print("Proceeding with the animals actually present rather than failing, but this")
        print("is a scope deviation and should be logged, not silently accepted as final.")

    print(f"\nRunning LOAO-CV: {n_folds} folds over animals {animals_present}\n")

    fold_results = []
    for held_out in animals_present:
        train_samples = [s for s in samples if s.animal != held_out]
        val_samples = [s for s in samples if s.animal == held_out]
        print(f"  Fold: hold out {held_out} (train n={len(train_samples)}, val n={len(val_samples)})")
        result = train_one_fold(train_samples, val_samples, args, held_out, device)
        fold_results.append(result)

    return fold_results


def summarize_cv(fold_results: list) -> dict:
    val_mses = [r["final_val_mse"] for r in fold_results if r["final_val_mse"] is not None]
    val_ssims = [r["final_val_ssim"] for r in fold_results if r["final_val_ssim"] is not None]

    summary = {
        "n_folds": len(fold_results),
        "mean_val_mse": float(np.mean(val_mses)) if val_mses else None,
        "sd_val_mse": float(np.std(val_mses)) if val_mses else None,
        "mean_val_ssim": float(np.mean(val_ssims)) if val_ssims else None,
        "sd_val_ssim": float(np.std(val_ssims)) if val_ssims else None,
        "per_fold": [
            {"animal": r["fold_animal"], "n_train": r["n_train"], "n_val": r["n_val"],
             "final_val_mse": r["final_val_mse"], "final_val_ssim": r["final_val_ssim"]}
            for r in fold_results
        ],
    }
    return summary


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Track 2 Phase 2 — 2D U-Net regression, Day1->Day8 MTR, "
                     "LOCKED SCOPE: 6 animals (m1,m2,m3,m4,m6,m7), LOAO-6."
    )
    parser.add_argument("--root", type=Path, required=True,
                         help="Path to 'MRI Results-Main' directory containing Day1/, Day8/, etc.")
    parser.add_argument("--side-map", type=Path, default=Path("side_map.csv"),
                         help="OPTIONAL CSV with columns animal,slice_index,side. If absent, "
                              "training proceeds side-agnostic (all slices tagged 'unknown') — "
                              "this is the current expected mode pending OPEN ITEM 5 resolution. "
                              "When provided, side labels are for reporting only and do NOT "
                              "affect training, loss, or LOAO-CV fold construction.")
    parser.add_argument("--power-ppm", type=str, default="12",
                         help="Which power-level MTR map to use (default: 12, matching the paper's "
                              "1.2ppm mannose CEST signature). Must match filename pattern @{ppm}ppm.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--base-channels", type=int, default=48,
                         help="U-Net base channel count for the 2-stage architecture "
                              "(48->96, bottleneck 96), sized for CROP_SIZE x CROP_SIZE "
                              "inputs. Targets ~500K-1M total params. Changed from the "
                              "original 4-stage/base_ch=16 default on 2026-09-26 when the "
                              "network was shallowed to match cropped (not full-canvas) "
                              "inputs — see UNet2D docstring.")
    parser.add_argument("--ssim-weight", type=float, default=0.3,
                         help="Weight of SSIM term in combined loss; (1-w)*MSE + w*(1-SSIM).")
    parser.add_argument("--data-range", type=float, default=0.25,
                         help="Approximate MTR value range for SSIM normalization "
                              "(paper reports MTR in ~[-0.11, +0.13]; default covers that span).")
    parser.add_argument("--out-dir", type=Path, default=Path("./track2_output"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda", "mps"])

    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    if args.device == "auto":
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
    else:
        device = torch.device(args.device)
    print(f"Using device: {device}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: discover sessions, report missingness (no silent backfill) ---
    sessions = discover_sessions(args.root, args.power_ppm)
    print_missingness_report(sessions, args.power_ppm)

    # --- Step 2: load required side mapping (not inferred) ---
    side_map = load_side_map(args.side_map)

    # --- Step 3: build (input, target) samples, applying ROI masks ---
    samples, exclusion_log = build_samples(sessions, side_map, args.power_ppm)

    print("\n" + "=" * 72)
    print("SAMPLE-LEVEL BUILD REPORT (side-agnostic mode)")
    print("=" * 72)
    print(f"Total usable (animal, slice) samples: {len(samples)}")
    animals_in_samples = sorted(set(s.animal for s in samples))
    print(f"Animals contributing >=1 sample: {animals_in_samples} (n={len(animals_in_samples)})")
    n_unknown_side = sum(1 for s in samples if s.side == "unknown")
    print(f"Samples with side='unknown' (no --side-map coverage): {n_unknown_side} / {len(samples)}")
    print("Per-animal sample detail:")
    for animal in animals_in_samples:
        animal_samples = [s for s in samples if s.animal == animal]
        detail = ", ".join(f"slice{s.slice_index}(side={s.side}, {s.roi_px_count}px)" for s in animal_samples)
        print(f"  {animal}: {len(animal_samples)} sample(s) — {detail}")
    if exclusion_log:
        print("Exclusions:")
        for animal, reason in exclusion_log.items():
            print(f"  {animal}: {reason}")
    print("=" * 72)

    if len(samples) == 0:
        print("FATAL: no usable samples after masking. Cannot train. Exiting.")
        sys.exit(1)

    # --- Step 4: model size sanity check against ~500K-1M param target ---
    probe_model = UNet2D(in_ch=1, out_ch=1, base_ch=args.base_channels)
    n_params = count_params(probe_model)
    print(f"\nModel parameter count: {n_params:,}")
    if not (400_000 <= n_params <= 1_400_000):
        print(f"WARNING: parameter count {n_params:,} is outside the ~500K-1M target range "
              f"specified in the architecture decision. Consider adjusting --base-channels.")
    print("NOTE: this count was computed live by torch, not hand-verified against the "
          "architecture spec's exact target — treat the ~500K-1M figure as a band, not "
          "a hard gate, and confirm against this printed number before treating the run as valid.")
    del probe_model

    # --- Step 5: LOAO-CV, 6 folds per locked scope ---
    fold_results = run_loao_cv(samples, args, device)
    cv_summary = summarize_cv(fold_results)

    print("\n" + "=" * 72)
    print("LOAO-CV SUMMARY")
    print("=" * 72)
    print(f"Folds: {cv_summary['n_folds']}")
    print(f"Mean val MSE: {cv_summary['mean_val_mse']:.5f} (SD {cv_summary['sd_val_mse']:.5f})")
    print(f"Mean val SSIM: {cv_summary['mean_val_ssim']:.4f} (SD {cv_summary['sd_val_ssim']:.4f})")
    for pf in cv_summary["per_fold"]:
        print(f"  {pf['animal']}: n_train={pf['n_train']} n_val={pf['n_val']} "
              f"val_mse={pf['final_val_mse']:.5f} val_ssim={pf['final_val_ssim']:.4f}")
    print("=" * 72)

    # --- Step 6: persist results ---
    out_json = args.out_dir / "loao_cv_results.json"
    with open(out_json, "w") as f:
        json.dump({
            "locked_scope": {
                "animals": LOCKED_ANIMALS,
                "excluded_animals": EXCLUDED_ANIMALS,
                "input_day": LOCKED_DAYS_INPUT,
                "target_day": LOCKED_DAYS_TARGET,
                "n_folds_expected": len(LOCKED_ANIMALS),
            },
            "args": vars(args) | {"root": str(args.root), "side_map": str(args.side_map), "out_dir": str(args.out_dir)},
            "n_params": n_params,
            "cv_summary": cv_summary,
            "exclusion_log": exclusion_log,
            "fold_results": fold_results,
        }, f, indent=2, default=str)
    print(f"\nResults written to: {out_json}")


if __name__ == "__main__":
    main()
