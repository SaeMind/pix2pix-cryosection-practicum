#!/usr/bin/env python3
"""usage: python out/r4m/infer_score.py NAME VARIANT INPUT_NC   (run from repo root)
infer(): generator sees only data/<VARIANT>/test_input/*.png. score(): the only place test targets are read.
Body mask = repo definition (qc/metrics.py): target (R-G) > 0.18. L1_body is primary; L1_fov (PET-FOV rows) secondary.
Baseline = mean training cryosection image (B halves of data/petct/train). Per-block mean, then mean of 3 block means.
No p-values: 1 animal, 3 test blocks."""
import json, re, shutil, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity as ssim, peak_signal_noise_ratio as psnr
sys.path.insert(0, ".")
from models import networks

OUT = Path("out/r4m"); DATA = OUT / "data"
SPLIT = json.loads((OUT / "split.json").read_text())
NAMES = ["L1_body", "L1_fov", "PSNR", "SSIM"]
PANEL_Z = [65, 70, 105, 110, 145, 150]          # fixed before any result: 2 per block


def block_of(z):
    return next(k for k, v in SPLIT["blocks"].items() if z in v)


def infer(name, variant, nc):
    G = networks.define_G(nc, 3, 64, "unet_256", "batch", True, "normal", 0.02)   # use_dropout as in R4 (no_dropout False)
    G.load_state_dict(torch.load(OUT / "checkpoints" / name / "100_net_G.pth", map_location="cpu"))
    G.eval()
    d = OUT / name / "pred"; d.mkdir(parents=True, exist_ok=True)
    for p in sorted((DATA / variant / "test_input").glob("*.png")):
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255 * 2 - 1
        x = torch.from_numpy(a).permute(2, 0, 1)[None]
        assert x.shape == (1, 3, 256, 256)
        with torch.no_grad():
            y = G(x)[0].permute(1, 2, 0).numpy()
        assert y.shape == (256, 256, 3)
        Image.fromarray(np.clip((y + 1) / 2 * 255 + 0.5, 0, 255).astype(np.uint8)).save(d / p.name)


def metrics(f, r):
    body = (r[..., 0] - r[..., 1]) > 0.18
    fov = body.copy(); fov[:SPLIT["pet_rows_256"][0]] = False; fov[SPLIT["pet_rows_256"][1] + 1:] = False
    d = np.abs(f - r)
    return [d[body].mean() if body.any() else np.nan, d[fov].mean() if fov.any() else np.nan,
            psnr(r, f, data_range=1.0), ssim(r, f, channel_axis=2, data_range=1.0)]


def rd(p):
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255


def agg(rows):
    b = {}
    for z, m in rows:
        b.setdefault(block_of(z), []).append(m)
    blocks = {k: dict(zip(NAMES, map(float, np.nanmean(v, axis=0)))) for k, v in sorted(b.items())}
    mean = {n: float(np.mean([blocks[k][n] for k in blocks])) for n in NAMES}
    return dict(blocks=blocks, mean=mean)


def score(name, variant):
    base = np.mean([rd(p)[:, 256:] for p in sorted((DATA / "petct" / "train").glob("*.png"))], axis=0)
    zs = sorted(int(p.stem) for p in (OUT / name / "pred").glob("*.png"))
    assert zs == sorted(SPLIT["test"])
    tgt = {z: rd(DATA / "test_target" / f"{z:03d}.png") for z in zs}          # targets first touched here
    pred = {z: rd(OUT / name / "pred" / f"{z:03d}.png") for z in zs}
    res = {"model": agg([(z, metrics(pred[z], tgt[z])) for z in zs]),
           "baseline_mean_train_cryo": agg([(z, metrics(base, tgt[z])) for z in zs]),
           "note": "1 animal (within-animal, not generalizable), 3 test blocks, no p-values. L1_body primary (repo body mask)."}
    (OUT / name / "metrics.json").write_text(json.dumps(res, indent=1))
    fig, ax = plt.subplots(6, 4, figsize=(10, 15))
    for i, z in enumerate(PANEL_Z):
        inp = rd(DATA / variant / "test_input" / f"{z:03d}.png")
        err = np.abs(pred[z] - tgt[z]).mean(-1)
        for j, (im, t) in enumerate([(inp, f"input z{z}"), (pred[z], "prediction"), (tgt[z], "target"), (err, "abs error")]):
            h = ax[i, j].imshow(im, vmin=0, vmax=0.5, cmap="magma") if j == 3 else ax[i, j].imshow(im)
            ax[i, j].set_title(t, fontsize=8); ax[i, j].axis("off")
    plt.tight_layout(); plt.savefig(OUT / name / "panels.png", dpi=110); plt.close()
    return res


def curves(name):
    rows = []
    for l in (OUT / "checkpoints" / name / "loss_log.txt").read_text().splitlines():
        m = re.search(r"epoch: (\d+), iters: (\d+).*G_GAN: ([\d.]+), G_L1: ([\d.]+), D_real: ([\d.]+), D_fake: ([\d.]+)", l)
        if m:
            e, it = int(m[1]), int(m[2]); rows.append([e - 1 + it / 73, *map(float, m.groups()[2:])])
    r = np.array(rows)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].plot(r[:, 0], r[:, 2]); ax[0].set_title("G_L1 (train)")
    for k, lab in ((1, "G_GAN"), (3, "D_real"), (4, "D_fake")):
        ax[1].plot(r[:, 0], r[:, k], label=lab)
    ax[1].legend(); ax[1].set_title("GAN losses (train)")
    for a in ax: a.set_xlabel("epoch")
    plt.tight_layout(); plt.savefig(OUT / name / "curves.png", dpi=110); plt.close()
    np.savetxt(OUT / name / "loss_curve.csv", r, delimiter=",", header="epoch,G_GAN,G_L1,D_real,D_fake", comments="")


if __name__ == "__main__":
    name, variant, nc = sys.argv[1], sys.argv[2], int(sys.argv[3])
    infer(name, variant, nc); score(name, variant); curves(name)
    if name == "R4M":
        for f in ("config.json", "metrics.json", "curves.png"):
            shutil.copy(OUT / name / f, OUT / f)
    res = json.loads((OUT / name / "metrics.json").read_text())
    for tag in ("model", "baseline_mean_train_cryo"):
        for k, v in res[tag]["blocks"].items():
            print(f"{name if tag=='model' else 'baseline':9s} block {k}", *(f"{n} {v[n]:.4f}" for n in NAMES))
        print(f"{name if tag=='model' else 'baseline':9s} MEAN   ", *(f"{n} {res[tag]['mean'][n]:.4f}" for n in NAMES))
