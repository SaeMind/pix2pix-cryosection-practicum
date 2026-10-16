#!/usr/bin/env python3
"""R4-M data prep. Run from repo root: python out/r4m/prep_r4m.py
Reuses qc/prep_d2_ablation.py helpers (orientation ud=0 lr=0 zrev=0, transpose, 256px bilinear, percentile 1/99 norm)
but takes percentile stats from the NEW train slices only. Writes only under out/r4m/."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, "qc")
import prep_d2_ablation as P

OUT = Path("out/r4m")
R = lambda a, b: list(range(a, b + 1))
TEST = R(60, 74) + R(100, 114) + R(140, 154)
BUFFER = R(55, 59) + R(75, 79) + R(95, 99) + R(115, 119) + R(135, 139) + R(155, 159)
TRAIN = R(34, 54) + R(80, 94) + R(120, 134) + R(160, 181)
BLOCKS = {"A": R(60, 74), "B": R(100, 114), "C": R(140, 154)}
ZMIN, ZMAX = 34, 181


def build_split():
    assert (len(TEST), len(BUFFER), len(TRAIN)) == (45, 30, 73)
    assert not (set(TEST) & set(TRAIN)) and not (set(TEST) & set(BUFFER)) and not (set(TRAIN) & set(BUFFER))
    assert set(TEST) | set(BUFFER) | set(TRAIN) == set(range(ZMIN, ZMAX + 1))
    return dict(test=TEST, buffer=BUFFER, train=TRAIN, blocks=BLOCKS, zmin=ZMIN, zmax=ZMAX,
                orientation=dict(ud=0, lr=0, zrev=0, transpose=True), size=P.SIZE)


def main():
    split = build_split()
    ct, pet, cryo = P.load_vol(P.EXT / "ct_data"), P.load_vol(P.EXT / "pet_data"), P.load_cryo(P.EXT / "cryo_data")
    Z = ct.shape[2]
    assert pet.shape == ct.shape and cryo.shape[0] == Z and cryo.shape[1:3] == (ct.shape[1], ct.shape[0])
    stats = {k: np.percentile(v[:, :, TRAIN], [1, 99]) for k, v in (("ct", ct), ("pet", pet))}
    n = ZMAX - ZMIN + 1
    sl = lambda vol, key, z: P.norm_u8(P.apply(P.ct_slice(vol, z, True), 0, 0), *stats[key])
    rows = np.where(pet.max(axis=(0, 2)) > 0)[0]          # transposed layout: long axis = axis 1
    H = cryo.shape[1]
    split["pet_rows_256"] = [int(rows.min() * P.SIZE / H), int(rows.max() * P.SIZE / H)]
    split["pct_stats_train_only"] = {k: v.tolist() for k, v in stats.items()}
    for z in TRAIN + TEST:
        zp = ZMIN + (z - ZMIN + n // 2) % n
        c, p, ps = P.rs(sl(ct, "ct", z)), P.rs(sl(pet, "pet", z)), P.rs(sl(pet, "pet", zp))
        zero = np.zeros_like(c)
        A = {"ct": np.stack([c] * 3, -1), "petct": np.stack([p, zero, c], -1), "petct_shuf": np.stack([ps, zero, c], -1)}
        b = P.rs(cryo[z])
        for name, a in A.items():
            if z in TRAIN:      # aligned A|B pairs, train only
                d = OUT / "data" / name / "train"; d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(np.concatenate([a, b], 1)).save(d / f"{z:03d}.png")
            else:               # test: input and target stored separately
                d = OUT / "data" / name / "test_input"; d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(a).save(d / f"{z:03d}.png")
        if z in TEST:
            d = OUT / "data" / "test_target"; d.mkdir(parents=True, exist_ok=True)
            Image.fromarray(b).save(d / f"{z:03d}.png")
    (OUT / "split.json").write_text(json.dumps(split, indent=1))
    print("done", {k: len(list((OUT / "data" / "petct" / k).glob("*.png"))) for k in ("train", "test_input")})


if __name__ == "__main__":
    main()
