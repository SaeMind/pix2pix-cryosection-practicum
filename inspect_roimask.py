"""
inspect_roimask.py
Builds the side_map.csv that train_v1.py requires, by rendering each
animal's ROImask.mat slices as PNGs (overlaid on the corresponding MTR map)
so you can visually assign each slice to GBM1a (left, per Fig. 5A convention)
or M1123 (right) — the same visual-QC method already used in the Phase 1
Day16-flip sweep (drive-verified-decisions-sept2026.md).

This does NOT guess the mapping. It produces images for YOU to look at and
a side_map.csv template with slice_index pre-filled and side left BLANK for
you to fill in after visual inspection.

Usage:
    python inspect_roimask.py \
        --root "<path-to>/MRI Results-Main" \
        --day Day1 \
        --power-ppm 12 \
        --out-dir ./roi_inspection
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOCKED_ANIMALS = ["m1", "m2", "m3", "m4", "m6", "m7"]


def load_var(path: Path, varname: str):
    mat = loadmat(str(path))
    if varname not in mat:
        keys = [k for k in mat.keys() if not k.startswith("__")]
        raise KeyError(f"'{varname}' not found in {path}. Keys: {keys}")
    return mat[varname]


def find_mtr_file(animal_dir: Path, power_ppm: str) -> Path:
    candidates = sorted(animal_dir.glob(f"pwr*_brainMTRmap@{power_ppm}ppm_MTRdata.mat"))
    return candidates[0] if candidates else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--day", type=str, default="Day1")
    parser.add_argument("--power-ppm", type=str, default="12")
    parser.add_argument("--out-dir", type=Path, default=Path("./roi_inspection"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    template_rows = []

    for animal in LOCKED_ANIMALS:
        animal_dir = args.root / args.day / animal
        roi_path = animal_dir / "ROImask.mat"
        mtr_path = find_mtr_file(animal_dir, args.power_ppm)

        if not roi_path.exists():
            print(f"{animal}: SKIP — ROImask.mat not found at {roi_path}")
            continue
        if mtr_path is None:
            print(f"{animal}: SKIP — no MTR file matching pwr*_brainMTRmap@{args.power_ppm}ppm_MTRdata.mat")
            continue

        mask = load_var(roi_path, "phantom_mask")
        mtr = load_var(mtr_path, "MTR")

        print(f"{animal}: phantom_mask shape={mask.shape}, dtype={mask.dtype}, MTR shape={mtr.shape}")

        # Determine slice axis: whichever dimension is NOT 64x64-shaped is the slice axis.
        if mask.ndim == 2:
            n_slices = 1
            slices = [mask]
        elif mask.ndim == 3:
            # heuristic: the axis matching neither of MTR's two spatial dims is the slice axis
            spatial_dims = set(mtr.shape)
            slice_axis = None
            for ax, dim in enumerate(mask.shape):
                if dim not in spatial_dims:
                    slice_axis = ax
                    break
            if slice_axis is None:
                # ambiguous (e.g. cube-shaped) — default to first axis, FLAG for manual check
                slice_axis = 0
                print(f"  {animal}: WARNING — could not unambiguously identify slice axis "
                      f"from shape {mask.shape} vs MTR shape {mtr.shape}. Defaulting to axis 0. "
                      f"VERIFY the rendered PNGs match expected ROI count.")
            n_slices = mask.shape[slice_axis]
            slices = [np.take(mask, i, axis=slice_axis) for i in range(n_slices)]
        else:
            print(f"{animal}: SKIP — unexpected mask ndim={mask.ndim}")
            continue

        print(f"  {animal}: {n_slices} slice(s) found in phantom_mask")

        for i, mask_slice in enumerate(slices):
            px_count = int(mask_slice.astype(bool).sum())
            fig, axes = plt.subplots(1, 2, figsize=(8, 4))
            axes[0].imshow(mtr, cmap="jet", vmin=-0.05, vmax=0.1)
            axes[0].set_title(f"{animal} {args.day} MTR (full)")
            axes[0].axis("off")

            overlay = np.zeros((*mask_slice.shape, 4))
            overlay[mask_slice.astype(bool)] = [1, 0, 0, 0.5]
            axes[1].imshow(mtr, cmap="gray", vmin=-0.05, vmax=0.1)
            axes[1].imshow(overlay)
            axes[1].set_title(f"slice_index={i} ({px_count}px)")
            axes[1].axis("off")

            out_path = args.out_dir / f"{animal}_{args.day}_slice{i}.png"
            plt.savefig(out_path, dpi=100, bbox_inches="tight")
            plt.close(fig)

            template_rows.append({"animal": animal, "slice_index": i, "side": "", "px_count": px_count, "png": str(out_path)})

    template_path = args.out_dir / "side_map_TEMPLATE.csv"
    with open(template_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["animal", "slice_index", "side", "px_count", "png"])
        writer.writeheader()
        writer.writerows(template_rows)

    print(f"\nWrote {len(template_rows)} candidate rows to {template_path}")
    print(f"PNGs written to {args.out_dir}/")
    print("\nNEXT STEP (manual, required):")
    print("  1. Open each PNG. Compare against Fig. 5A convention: GBM1a=left, M1123=right,")
    print("     within the single bilateral scan image.")
    print("  2. Fill in the 'side' column in side_map_TEMPLATE.csv with GBM1a or M1123 for")
    print("     each row where px_count is not near-zero (near-zero rows are likely not a")
    print("     real tumor ROI and may need EXCLUDING from side_map.csv entirely).")
    print("  3. Drop the px_count and png columns (or leave them — train_v1.py only reads")
    print("     animal, slice_index, side) and save as side_map.csv for train_v1.py.")


if __name__ == "__main__":
    main()
