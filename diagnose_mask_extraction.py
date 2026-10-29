"""
diagnose_mask_extraction.py
One-time diagnostic for the m1/m2/m7 "0px captured despite large union"
failure seen in loao_cv_results.json across two consecutive fixes.

Purpose: determine whether get_mask_slice() is extracting a genuinely
non-convex/scattered ROI (in which case the largest-connected-component
fix SHOULD have worked, and its failure to fire is the real bug), or
whether it's extracting the WRONG SLICE ENTIRELY due to the slice-axis
heuristic guessing wrong on phantom_mask's actual shape (in which case
the centroid logic is irrelevant — the input to it is already garbage).

This does NOT modify train_v1.py or re-run training. It only inspects
and reports, per the instruction to confirm the root cause before
touching training logic again.

Usage:
    python diagnose_mask_extraction.py \
        --root "<path-to>/MRI Results-Main" \
        --out-dir ./mask_diagnosis
"""

import argparse
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.ndimage import label as ndimage_label
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TARGET_ANIMALS = ["m1", "m2", "m7"]  # the animals showing the anomaly
DAYS = ["Day1", "Day8"]


def load_var(path: Path, varname: str):
    mat = loadmat(str(path))
    if varname not in mat:
        keys = [k for k in mat.keys() if not k.startswith("__")]
        raise KeyError(f"'{varname}' not found in {path}. Keys: {keys}")
    return mat[varname]


def find_mtr_file(animal_dir: Path, power_ppm: str = "12") -> Path:
    candidates = sorted(animal_dir.glob(f"pwr*_brainMTRmap@{power_ppm}ppm_MTRdata.mat"))
    return candidates[0] if candidates else None


def n_mask_slices(phantom_mask, mtr_shape):
    """EXACT copy of train_v1.py's logic, for parity."""
    if phantom_mask.ndim == 2:
        return 1
    spatial_dims = set(mtr_shape)
    for ax, dim in enumerate(phantom_mask.shape):
        if dim not in spatial_dims:
            return phantom_mask.shape[ax]
    return phantom_mask.shape[0]


def get_mask_slice(phantom_mask, slice_idx, mtr_shape):
    """EXACT copy of train_v1.py's logic, for parity."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--power-ppm", type=str, default="12")
    parser.add_argument("--out-dir", type=Path, default=Path("./mask_diagnosis"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MASK EXTRACTION DIAGNOSTIC — m1, m2, m7")
    print("=" * 80)

    for animal in TARGET_ANIMALS:
        print(f"\n{'='*80}\nANIMAL: {animal}\n{'='*80}")

        for day in DAYS:
            animal_dir = args.root / day / animal
            roi_path = animal_dir / "ROImask.mat"
            mtr_path = find_mtr_file(animal_dir, args.power_ppm)

            if not roi_path.exists():
                print(f"  {day}: ROImask.mat NOT FOUND at {roi_path}")
                continue
            if mtr_path is None:
                print(f"  {day}: MTR file NOT FOUND (pattern pwr*_brainMTRmap@{args.power_ppm}ppm_MTRdata.mat)")
                continue

            mask = load_var(roi_path, "phantom_mask")
            mtr = load_var(mtr_path, "MTR")

            print(f"\n  --- {day} ---")
            print(f"  phantom_mask.shape = {mask.shape}, dtype = {mask.dtype}")
            print(f"  MTR.shape          = {mtr.shape}, dtype = {mtr.dtype}")
            print(f"  phantom_mask total nonzero px (ALL slices combined) = {int(mask.astype(bool).sum())}")

            n_slices = n_mask_slices(mask, mtr.shape)
            print(f"  n_mask_slices() heuristic result: {n_slices} slice(s)")

            # Report which axis was picked, explicitly
            if mask.ndim == 3:
                spatial_dims = set(mtr.shape)
                slice_axis = None
                for ax, dim in enumerate(mask.shape):
                    if dim not in spatial_dims:
                        slice_axis = ax
                        break
                if slice_axis is None:
                    print(f"  WARNING: slice-axis heuristic found NO axis outside mtr.shape={mtr.shape} "
                          f"among mask.shape={mask.shape} — defaulted to axis 0. THIS IS A LIKELY BUG SOURCE "
                          f"if mask.shape has more than one dimension matching 64.")
                else:
                    print(f"  Slice axis selected: axis {slice_axis} (size {mask.shape[slice_axis]})")

            for slice_idx in range(n_slices):
                mask_slice = get_mask_slice(mask, slice_idx, mtr.shape)
                mask_bool = mask_slice.astype(bool)
                px_count = int(mask_bool.sum())

                if px_count == 0:
                    print(f"    slice{slice_idx}: shape={mask_slice.shape}, EMPTY (0px) — SKIPPING component analysis")
                    continue

                labeled, n_components = ndimage_label(mask_bool)
                component_sizes = []
                for comp_id in range(1, n_components + 1):
                    component_sizes.append(int((labeled == comp_id).sum()))
                component_sizes.sort(reverse=True)

                ys, xs = np.nonzero(mask_bool)
                bbox = (ys.min(), ys.max(), xs.min(), xs.max())
                bbox_span = (ys.max() - ys.min() + 1, xs.max() - xs.min() + 1)

                print(f"    slice{slice_idx}: shape={mask_slice.shape}, px={px_count}, "
                      f"n_components={n_components}, component_sizes={component_sizes}, "
                      f"bbox_rows=[{bbox[0]}-{bbox[1]}], bbox_cols=[{bbox[2]}-{bbox[3]}], "
                      f"bbox_span={bbox_span}")

                if bbox_span[0] > 16 or bbox_span[1] > 16:
                    print(f"      >>> FLAG: bounding box span {bbox_span} EXCEEDS CROP_SIZE=16 in at "
                          f"least one dimension. Even a perfect centroid cannot fit this ROI in a 16x16 "
                          f"crop without clipping. This alone could explain low px-in-crop counts "
                          f"WITHOUT any centroid bug.")

                # Save visual: full MTR + mask overlay, plus zoomed bbox region
                fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
                axes[0].imshow(mtr, cmap="jet", vmin=-0.05, vmax=0.1)
                axes[0].set_title(f"{animal} {day} MTR (full 64x64)")
                axes[0].axis("off")

                overlay = np.zeros((*mask_bool.shape, 4))
                overlay[mask_bool] = [1, 0, 0, 0.6]
                axes[1].imshow(mtr, cmap="gray", vmin=-0.05, vmax=0.1)
                axes[1].imshow(overlay)
                axes[1].set_title(f"slice{slice_idx} mask overlay\n"
                                   f"{px_count}px, {n_components} component(s)")
                axes[1].axis("off")

                # zoomed view around bbox with margin
                margin = 5
                r0 = max(0, bbox[0] - margin)
                r1 = min(mtr.shape[0], bbox[1] + margin + 1)
                c0 = max(0, bbox[2] - margin)
                c1 = min(mtr.shape[1], bbox[3] + margin + 1)
                axes[2].imshow(mtr[r0:r1, c0:c1], cmap="gray", vmin=-0.05, vmax=0.1)
                axes[2].imshow(overlay[r0:r1, c0:c1])
                axes[2].set_title(f"zoomed to bbox+margin\nrows[{r0}:{r1}] cols[{c0}:{c1}]")
                axes[2].axis("off")

                out_path = args.out_dir / f"{animal}_{day}_slice{slice_idx}_DIAG.png"
                plt.savefig(out_path, dpi=110, bbox_inches="tight")
                plt.close(fig)
                print(f"      saved: {out_path}")

    print(f"\n{'='*80}")
    print(f"Diagnostic complete. PNGs in {args.out_dir}/")
    print("Look for:")
    print("  1. component_sizes with >1 entry -> confirms disconnected/scattered mask")
    print("  2. bbox_span exceeding 16 in either dimension -> ROI too large for CROP_SIZE=16,")
    print("     independent of any centroid logic (this would explain the persistent failure)")
    print("  3. 'WARNING: slice-axis heuristic found NO axis' -> get_mask_slice picked the")
    print("     wrong axis entirely, meaning the extracted 'mask' isn't the real ROI at all")
    print("=" * 80)


if __name__ == "__main__":
    main()
