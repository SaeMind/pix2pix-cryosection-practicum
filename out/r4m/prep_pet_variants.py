#!/usr/bin/env python3
"""PET-only data prep for R6-M / R7-M / R6b-M (Addendum 4). Run once from repo root: python out/r4m/prep_pet_variants.py
Writes ONLY out/r4m/data/pet and out/r4m/data/pet_shuf (refuses if either exists). Never writes split.json or any existing file.
Import safety: out/r4m/prep_r4m.py has only defs/constants at module level (main() is under __main__ guard, lines 61-62),
so its constants and the qc/prep_d2_ablation.py helpers are imported, not copied. Layout mirrors out/r4m/data/ct:
train/NNN.png = A|B, 512x256 RGB uint8; test_input/NNN.png = A, 256x256 RGB uint8; test targets are the shared data/test_target."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, "out/r4m")
import prep_r4m as R4           # TRAIN, TEST, ZMIN, ZMAX, P (= qc/prep_d2_ablation)
P = R4.P

OUT = Path("out/r4m")
NEW = ("pet", "pet_shuf")


def main():
    split = json.loads((OUT / "split.json").read_text())           # read-only
    assert split["train"] == R4.TRAIN and split["test"] == R4.TEST and (split["zmin"], split["zmax"]) == (R4.ZMIN, R4.ZMAX)
    dirs = {v: OUT / "data" / v for v in NEW}
    for v, d in dirs.items():
        if d.exists():
            sys.exit(f"REFUSING: {d} already exists")
    pet, ct, cryo = P.load_vol(P.EXT / "pet_data"), P.load_vol(P.EXT / "ct_data"), P.load_cryo(P.EXT / "cryo_data")
    assert pet.shape == ct.shape and cryo.shape[0] == ct.shape[2]
    stored = split["pct_stats_train_only"]["pet"]
    fresh = np.percentile(pet[:, :, R4.TRAIN], [1, 99])             # prep_r4m.py:34 (train slices only)
    assert np.allclose(stored, fresh, atol=1e-6, rtol=0), (stored, fresh)
    lo, hi = np.asarray(stored, dtype=np.float64)                    # stored bounds as float64 scalars, as np.percentile gave in prep_r4m.py:34;
    #                                                                  python floats would promote differently in norm_u8 (1-level diffs)
    n = R4.ZMAX - R4.ZMIN + 1                                        # 148
    assert n == 148
    sl = lambda z: P.norm_u8(P.apply(P.ct_slice(pet, z, True), 0, 0), lo, hi)   # prep_r4m.py:36
    for d in dirs.values():
        (d / "train").mkdir(parents=True, exist_ok=False); (d / "test_input").mkdir()
    for z in R4.TRAIN + R4.TEST:
        zp = R4.ZMIN + (z - R4.ZMIN + n // 2) % n                    # prep_r4m.py:42 (no RNG)
        arrs = {"pet": np.stack([P.rs(sl(z))] * 3, -1), "pet_shuf": np.stack([P.rs(sl(zp))] * 3, -1)}
        b = P.rs(cryo[z])                                            # prep_r4m.py:46
        for v, a in arrs.items():
            if z in R4.TRAIN:
                Image.fromarray(np.concatenate([a, b], 1)).save(dirs[v] / "train" / f"{z:03d}.png")
            else:
                Image.fromarray(a).save(dirs[v] / "test_input" / f"{z:03d}.png")
    print("done", {v: {k: len(list((d / k).glob("*.png"))) for k in ("train", "test_input")} for v, d in dirs.items()})


if __name__ == "__main__":
    main()
