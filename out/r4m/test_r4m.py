"""Run from repo root: pix2pix_env/bin/python out/r4m/test_r4m.py   (checks that need weights/preds skip if absent)"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, ".")
OUT = Path("out/r4m"); D = OUT / "data"
S = json.loads((OUT / "split.json").read_text())
tr, te, bu = set(S["train"]), set(S["test"]), set(S["buffer"])
img = lambda p: np.asarray(Image.open(p).convert("RGB"))


def test_split_disjoint():
    assert (len(tr), len(te), len(bu)) == (73, 45, 30)
    assert not (tr & te) and not (tr & bu) and not (te & bu)
    assert tr | te | bu == set(range(34, 182))
    for k, v in S["blocks"].items():
        assert len(v) == 15 and set(v) <= te
    # blocked: every test block is flanked by 5-slice buffers on both sides
    for k, v in S["blocks"].items():
        assert set(range(min(v) - 5, min(v))) <= bu and set(range(max(v) + 1, max(v) + 6)) <= bu


def test_no_test_target_in_training_loader():
    for variant in ("petct", "ct", "petct_shuf"):
        files = sorted((D / variant / "train").glob("*.png"))
        assert {int(p.stem) for p in files} == tr           # AlignedDataset(phase=train) reads exactly this dir
        assert not (D / variant / "test").exists()          # no A|B pairs for test slices exist anywhere
    tt = {z: img(D / "test_target" / f"{z:03d}.png") for z in te}
    seen = [img(p)[:, 256:] for p in sorted((D / "petct" / "train").glob("*.png"))]
    for z, t in tt.items():
        assert all(not np.array_equal(t, b) for b in seen), z
    for p in (D / "petct" / "test_input").glob("*.png"):     # test inputs are A only
        assert img(p).shape == (256, 256, 3)


def test_shapes():
    for variant in ("petct", "ct", "petct_shuf"):
        assert all(img(p).shape == (256, 512, 3) for p in (D / variant / "train").glob("*.png"))
        assert len(list((D / variant / "test_input").glob("*.png"))) == 45
    a = img(D / "petct" / "test_input" / "060.png")
    assert a[..., 1].max() == 0                                # R4 layout: [PET, 0, CT]
    c = img(D / "ct" / "test_input" / "060.png")
    assert (c[..., 0] == c[..., 1]).all() and (c[..., 1] == c[..., 2]).all()
    assert np.array_equal(a[..., 2], c[..., 0])                # CT channel identical across variants
    import torch
    from models import networks
    G = networks.define_G(3, 3, 64, "unet_256", "batch", True, "normal", 0.02).eval()
    with torch.no_grad():
        assert G(torch.zeros(1, 3, 256, 256)).shape == (1, 3, 256, 256)


def test_preds_scored_only_for_test():
    d = OUT / "R4M" / "pred"
    if d.exists():
        assert {int(p.stem) for p in d.glob("*.png")} == te


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("ok", n)
