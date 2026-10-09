#!/usr/bin/env python3
"""Inspect (default):  python qc/prep_d2_ablation.py
Write:  python qc/prep_d2_ablation.py --write [--zmin N] [--zmax N] [--train 20] [--gap 5] [--test 10]
Orientation ud=0 lr=0 zrev=0 was verified on the CT and PET overlays (Oct 8, 2026);
override only with --ud / --lr / --zrev."""
import argparse, json, re, shutil
from pathlib import Path
import numpy as np
import nibabel as nib
from PIL import Image

EXT = Path("datasets/D2_digimouse/processed/extracted")
OUT = Path("datasets/D2_ablation")
SIZE = 256


def nat(p):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)]


def load_vol(folder):
    hdr = sorted(Path(folder).rglob("*.hdr"))
    if len(hdr) != 1:
        raise SystemExit(f"{folder}: expected 1 .hdr, found {len(hdr)}")
    return np.squeeze(np.asanyarray(nib.load(str(hdr[0])).dataobj)).astype(np.float32)


def load_cryo(folder):
    files = sorted((p for p in Path(folder).rglob("*") if p.suffix.lower() in (".tif", ".tiff")), key=nat)
    if not files:
        raise SystemExit(f"{folder}: no TIFF files")
    print("cryo count:", len(files), "first:", files[0].name, "last:", files[-1].name)
    return np.stack([np.asarray(Image.open(p).convert("RGB")) for p in files])


def ct_slice(vol, z, tr):
    s = vol[:, :, z]
    return s.T if tr else s


def apply(s, ud, lr):
    if ud:
        s = s[::-1]
    if lr:
        s = s[:, ::-1]
    return np.ascontiguousarray(s)


def norm_u8(x, lo, hi):
    return (np.clip((x - lo) / (hi - lo + 1e-8), 0, 1) * 255).astype(np.uint8)


def rs(a):
    return np.asarray(Image.fromarray(a).resize((SIZE, SIZE), Image.BILINEAR))


def tissue_frac(cryo):
    # fraction of red-tinted tissue pixels per slice (thresholds unverified; the printed profile is the check)
    c = cryo[:, ::4, ::4].astype(np.int16)
    return ((c[..., 0] - c[..., 1] > 45) & (c[..., 0] < 235)).mean(axis=(1, 2))


def split_idx(zmin, zmax, train, gap, test):
    per = train + gap + test + gap
    tr, te, blk = [], [], {}
    for z in range(zmin, zmax + 1):
        k, pos = divmod(z - zmin, per)
        if pos < train:
            tr.append(z)
        elif train + gap <= pos < train + gap + test and zmin + k * per + train + gap + test - 1 <= zmax:
            te.append(z)
            blk[z] = k
    return np.array(tr), np.array(te), blk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ud", action="store_true")
    ap.add_argument("--lr", action="store_true")
    ap.add_argument("--zrev", action="store_true")
    ap.add_argument("--zmin", type=int)
    ap.add_argument("--zmax", type=int)
    ap.add_argument("--ext_frac", type=float, default=0.10)
    ap.add_argument("--train", type=int, default=20)
    ap.add_argument("--gap", type=int, default=5)
    ap.add_argument("--test", type=int, default=10)
    a = ap.parse_args()
    ud, lr, zr = int(a.ud), int(a.lr), int(a.zrev)

    ct, pet, cryo = load_vol(EXT / "ct_data"), load_vol(EXT / "pet_data"), load_cryo(EXT / "cryo_data")
    print("CT", ct.shape, "PET", pet.shape, "cryo", cryo.shape)
    Z = ct.shape[2]
    if pet.shape != ct.shape or cryo.shape[0] != Z:
        raise SystemExit("grid or slice-count mismatch: stop and report")
    H, W = cryo.shape[1:3]
    if (H, W) == (ct.shape[1], ct.shape[0]):
        tr, axis = True, 1
    elif (H, W) == ct.shape[:2]:
        tr, axis = False, 0
    else:
        raise SystemExit(f"cryo slice {(H, W)} incompatible with CT slice {ct.shape[:2]}")

    frac = tissue_frac(cryo)
    auto = np.where(frac >= a.ext_frac * frac.max())[0]
    zmin = a.zmin if a.zmin is not None else int(auto.min())
    zmax = a.zmax if a.zmax is not None else int(auto.max())
    print("tissue fraction every 5 slices:", " ".join(f"{z}:{frac[z]:.3f}" for z in range(0, Z, 5)))
    print(f"auto extent {auto.min()}-{auto.max()} (missing inside: {int(auto.max() - auto.min() + 1 - len(auto))}); using {zmin}-{zmax}")

    other = tuple(i for i in range(3) if i != axis)
    rows = np.where(pet.max(axis=other) > 0)[0]
    r0, r1 = int(rows.min()), int(rows.max())
    print(f"PET nonzero rows {r0}-{r1} of {H} ({100 * (r1 - r0 + 1) / H:.1f}% of the long axis)")
    if ud:
        r0, r1 = H - 1 - r1, H - 1 - r0
    rows256 = [int(r0 * SIZE / H), int(r1 * SIZE / H)]

    tr_i, te_i, blk = split_idx(zmin, zmax, a.train, a.gap, a.test)
    for k in sorted(set(blk.values())):
        zs = [z for z in te_i if blk[z] == k]
        print(f"test block {k}: z {min(zs)}-{max(zs)} ({len(zs)} slices)")
    print(f"train {len(tr_i)} test {len(te_i)} discarded {Z - len(tr_i) - len(te_i)} (blocks: {len(set(blk.values()))})")
    if not a.write:
        return

    if OUT.exists():
        shutil.rmtree(OUT)
    stats = {k: np.percentile(v[:, :, tr_i], [1, 99]) for k, v in (("ct", ct), ("pet", pet))}
    n = zmax - zmin + 1

    def sl(vol, key, z):
        return norm_u8(apply(ct_slice(vol, int(z), tr), ud, lr), *stats[key])

    for split, idx in (("train", tr_i), ("test", te_i)):
        for z in idx:
            zp = zmin + (int(z) - zmin + n // 2) % n      # R5: PET from a slice half the extent away
            c, p, ps = rs(sl(ct, "ct", z)), rs(sl(pet, "pet", z)), rs(sl(pet, "pet", zp))
            b = rs(cryo[Z - 1 - z if zr else z])
            zero = np.zeros_like(c)
            A = {"ct": np.stack([c] * 3, -1), "pet": np.stack([p] * 3, -1),
                 "petct": np.stack([p, zero, c], -1), "petct_shuf": np.stack([ps, zero, c], -1)}
            for name, arr in A.items():
                d = OUT / name / split
                d.mkdir(parents=True, exist_ok=True)
                Image.fromarray(np.concatenate([arr, b], 1)).save(d / f"{int(z):03d}.png")
    meta = dict(train=tr_i.tolist(), test=te_i.tolist(), block={int(z): int(k) for z, k in blk.items()},
                zmin=zmin, zmax=zmax, train_gap_test=[a.train, a.gap, a.test], ud=ud, lr=lr, zrev=zr,
                transpose=tr, size=SIZE, pet_rows_256=rows256,
                pct_stats={k: v.tolist() for k, v in stats.items()}, shuffle="roll by half the extent")
    (OUT / "split.json").write_text(json.dumps(meta, indent=1))
    print("written to", OUT)


if __name__ == "__main__":
    main()
