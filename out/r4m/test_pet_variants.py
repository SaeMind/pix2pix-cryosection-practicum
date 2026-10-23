"""Tests for out/r4m/prep_pet_variants.py. Run from repo root after the prep:
  pix2pix_env/bin/python out/r4m/test_pet_variants.py
Test 7 compares against a before-prep snapshot if env PET_SNAPSHOT points to one ({"files": {path: size}, "split_sha": ...});
independently of it, it checks that every pre-existing file is older than every new file."""
import hashlib, json, os, re, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, "out/r4m")
import prep_r4m as R4
P = R4.P

OUT = Path("out/r4m"); D = OUT / "data"
S = json.loads((OUT / "split.json").read_text())
TR, TE = S["train"], S["test"]
n = R4.ZMAX - R4.ZMIN + 1
img = lambda p: np.asarray(Image.open(p).convert("RGB"))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
_cache = {}


def pet_norm():
    if "pet" not in _cache:
        lo, hi = np.asarray(S["pct_stats_train_only"]["pet"], dtype=np.float64)   # float64 scalars, as in prep_r4m.py
        pet = P.load_vol(P.EXT / "pet_data")
        _cache["pet"] = (pet, lambda z: P.rs(P.norm_u8(P.apply(P.ct_slice(pet, z, True), 0, 0), lo, hi)))
    return _cache["pet"]


def A(variant, z):
    p = D / variant / ("train" if z in TR else "test_input") / f"{z:03d}.png"
    a = img(p)
    return a[:, :256] if z in TR else a


def test_1_pet_variant():
    _, f = pet_norm()
    for z in TR + TE:
        a = A("pet", z)
        assert (a[..., 0] == a[..., 1]).all() and (a[..., 1] == a[..., 2]).all(), z
        assert np.array_equal(a[..., 0], f(z)), z
        assert np.array_equal(a[..., 0], A("petct", z)[..., 0]), z       # equals the PET (red) channel of the R4-M input


def test_2_pet_shuf_variant():
    _, f = pet_norm()
    src = Path("out/r4m/prep_pet_variants.py").read_text()
    assert not re.search(r"\b(random|randint|shuffle|permutation|default_rng|seed)\b", src.replace("pet_shuf", "")), "RNG token in prep"
    for z in TR + TE:
        zp = R4.ZMIN + (z - R4.ZMIN + n // 2) % n
        assert zp != z
        a = A("pet_shuf", z)
        assert (a[..., 0] == a[..., 1]).all() and (a[..., 1] == a[..., 2]).all(), z
        assert np.array_equal(a[..., 0], f(zp)), z
        assert np.array_equal(a[..., 0], A("petct_shuf", z)[..., 0]), z  # equals the R5-M shuffled PET channel


def test_3_shapes_dtypes_counts():
    for v in ("pet", "pet_shuf"):
        for k in ("train", "test_input"):
            ref = sorted(p.name for p in (D / "ct" / k).glob("*.png")); new = sorted(p.name for p in (D / v / k).glob("*.png"))
            assert ref == new and len(new) == {"train": 73, "test_input": 45}[k], (v, k)
            for nm in new:
                a, r = Image.open(D / v / k / nm), Image.open(D / "ct" / k / nm)
                assert (a.mode, a.size) == (r.mode, r.size) == ("RGB", (512, 256) if k == "train" else (256, 256))
                assert np.asarray(a).dtype == np.asarray(r).dtype == np.uint8
        assert sorted(int(p.stem) for p in (D / v / "train").glob("*.png")) == sorted(TR)    # no buffer slices
        assert sorted(int(p.stem) for p in (D / v / "test_input").glob("*.png")) == sorted(TE)
        assert not (D / v / "test").exists() and not (D / v / "test_target").exists()


def test_4_targets_identical_to_ct():
    for v in ("pet", "pet_shuf"):
        for z in TR:
            assert np.array_equal(img(D / v / "train" / f"{z:03d}.png")[:, 256:], img(D / "ct" / "train" / f"{z:03d}.png")[:, 256:]), (v, z)
    # test targets are the single shared directory out/r4m/data/test_target (not duplicated); the new variants rely on it unchanged
    assert len(list((D / "test_target").glob("*.png"))) == 45


def test_5_split_sha_unchanged():
    rec = [l.split()[0] for l in Path("out/r4m_audit/LOCK_HASHES.txt").read_text().splitlines() if l.endswith("out/r4m/split.json")]
    assert rec and all(sha(OUT / "split.json") == r for r in rec), (sha(OUT / "split.json"), rec)
    snap = os.environ.get("PET_SNAPSHOT")
    if snap:
        assert json.loads(Path(snap).read_text())["split_sha"] == sha(OUT / "split.json")


def test_6_percentiles_train_only():
    pet, _ = pet_norm()
    ct = P.load_vol(P.EXT / "ct_data")
    for key, vol in (("pet", pet), ("ct", ct)):
        assert np.allclose(S["pct_stats_train_only"][key], np.percentile(vol[:, :, TR], [1, 99]), atol=1e-6, rtol=0), key
    allz = np.percentile(pet[:, :, R4.ZMIN:R4.ZMAX + 1], [1, 99]).tolist()
    print("  info: PET bounds train-only", S["pct_stats_train_only"]["pet"], "| all slices", allz)
    src = Path("out/r4m/prep_pet_variants.py").read_text()
    assert "pct_stats_train_only" in src and "R4.TRAIN]" in src


def test_7_existing_data_untouched():
    old = [p for d in ("ct", "petct", "petct_shuf", "test_target") for p in (D / d).rglob("*") if p.is_file()] + [OUT / "split.json"]
    new = [p for d in ("pet", "pet_shuf") for p in (D / d).rglob("*") if p.is_file()]
    assert len(old) == 400 and len(new) == 236, (len(old), len(new))
    assert max(p.stat().st_mtime for p in old) < min(p.stat().st_mtime for p in new), "an existing file is newer than a new file"
    snap = os.environ.get("PET_SNAPSHOT")
    if snap:
        before = json.loads(Path(snap).read_text())["files"]
        assert before == {str(p): p.stat().st_size for p in old}, "existing file listing or sizes changed"
    else:
        print("  note: PET_SNAPSHOT not set; only the mtime check ran")


if __name__ == "__main__":
    for nm, f in list(globals().items()):
        if nm.startswith("test_"):
            f(); print("ok", nm)
