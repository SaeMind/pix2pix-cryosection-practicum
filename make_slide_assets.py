import csv, glob, os, re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

LOG = "train_full.log"
IMG_DIR = "results/facades_pix2pix_full/test_200/images"
OUT = "slide_assets"
N_EPOCHS, ITERS_PER_EPOCH, LR0, DECAY_START = 200, 400, 2e-4, 100
os.makedirs(OUT, exist_ok=True)

# 1. Parse training log (resumed segment overrides the repeated epoch 36)
pat = re.compile(r"epoch: (\d+), iters: (\d+).*G_GAN: ([\d.]+), G_L1: ([\d.]+), D_real: ([\d.]+), D_fake: ([\d.]+)")
tpat = re.compile(r"End of epoch (\d+) / \d+\s+Time Taken: (\d+) sec")
samples, times_all = {}, []
for line in open(LOG):
    m = pat.search(line)
    if m:
        samples[(int(m[1]), int(m[2]))] = tuple(float(m[k]) for k in range(3, 7))
    t = tpat.search(line)
    if t:
        times_all.append((int(t[1]), int(t[2])))
epoch_time = {}
for e, s in times_all:
    epoch_time[e] = s
epochs = sorted({e for e, _ in samples})
assert epochs == list(range(1, N_EPOCHS + 1)), f"Epoch coverage incomplete: n={len(epochs)}"

def epoch_mean(e, k):
    return np.mean([v[k] for (ee, _), v in samples.items() if ee == e])
G_GAN = np.array([epoch_mean(e, 0) for e in epochs])
G_L1 = np.array([epoch_mean(e, 1) for e in epochs])
D_real = np.array([epoch_mean(e, 2) for e in epochs])
D_fake = np.array([epoch_mean(e, 3) for e in epochs])
lr = np.array([LR0 * (1 - max(0, e - DECAY_START) / (N_EPOCHS - DECAY_START + 1)) for e in epochs])

# 2. Loss figure
fig, ax = plt.subplots(1, 3, figsize=(16, 4.2))
ax[0].plot(epochs, G_L1, color="tab:blue"); ax[0].set_title("Generator L1 loss (x100 weight), epoch mean")
ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("G_L1"); ax[0].axvline(DECAY_START, ls="--", c="gray")
ax[1].plot(epochs, D_real, label="D_real"); ax[1].plot(epochs, D_fake, label="D_fake")
ax[1].set_title("Discriminator losses, epoch mean"); ax[1].set_xlabel("Epoch"); ax[1].legend(); ax[1].axvline(DECAY_START, ls="--", c="gray")
ax[2].plot(epochs, lr, color="tab:green"); ax[2].set_title("Learning rate (constant 100, linear decay 100)")
ax[2].set_xlabel("Epoch"); ax[2].set_ylabel("LR")
plt.tight_layout(); plt.savefig(f"{OUT}/loss_curves.png", dpi=200); plt.close()

# 3. Test-set metrics over all images
rows = []
for f in sorted(glob.glob(f"{IMG_DIR}/*_fake_B.png")):
    r = f.replace("_fake_B", "_real_B")
    a = np.asarray(Image.open(f).convert("RGB"), dtype=np.float64) / 255
    b = np.asarray(Image.open(r).convert("RGB"), dtype=np.float64) / 255
    idx = os.path.basename(f).split("_")[0]
    rows.append((idx, np.abs(a - b).mean(), psnr(b, a, data_range=1), ssim(b, a, channel_axis=2, data_range=1)))
with open(f"{OUT}/test_metrics_per_image.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["image_id", "L1_0to1", "PSNR_dB", "SSIM"]); w.writerows(rows)
M = np.array([r[1:] for r in rows])

# 4. Example montage: best / median / worst by SSIM
order = sorted(range(len(rows)), key=lambda i: rows[i][3])
picks = [("Best", order[-1]), ("Median", order[len(order) // 2]), ("Worst", order[0])]
fig, axs = plt.subplots(3, 3, figsize=(9, 9.6))
for r_i, (tag, i) in enumerate(picks):
    idx = rows[i][0]
    for c_i, (kind, title) in enumerate([("real_A", "Input label map"), ("fake_B", "Generated"), ("real_B", "Ground truth")]):
        axs[r_i, c_i].imshow(Image.open(f"{IMG_DIR}/{idx}_{kind}.png")); axs[r_i, c_i].axis("off")
        if r_i == 0: axs[r_i, c_i].set_title(title)
    axs[r_i, 0].text(-0.02, 0.5, f"{tag}\nid {idx}\nSSIM {rows[i][3]:.3f}", transform=axs[r_i, 0].transAxes,
                     ha="right", va="center", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/test_examples.png", dpi=200, bbox_inches="tight"); plt.close()

# 5. Summary tables
def blk(a, i): return a[i * 20:(i + 1) * 20].mean()
L = ["# pix2pix (facades, BtoA) - Full 200-Epoch Run Summary\n", "## Configuration\n| Item | Value |\n| --- | --- |",
     "| Architecture | U-Net 256 generator (54.414 M params), PatchGAN discriminator (2.769 M params) |",
     "| Training data | 400 paired images (facades) |",
     f"| Schedule | {DECAY_START} epochs constant LR {LR0:g} + {N_EPOCHS-DECAY_START} epochs linear decay to 0 |",
     "| Loss | Vanilla GAN + 100 x L1, batch size 1, Adam beta1 0.5 |",
     f"| Iterations | {N_EPOCHS * ITERS_PER_EPOCH:,} ({ITERS_PER_EPOCH}/epoch) |"]
tot = sum(s for _, s in times_all); kept = sum(epoch_time.values())
L.append(f"| Training compute (CPU) | {kept/3600:.2f} h counted once per epoch; {tot/3600:.2f} h including {len(times_all)-len(epoch_time)} repeated epoch(s) after the interruption |")
L.append(f"| Time per epoch | mean {np.mean(list(epoch_time.values())):.0f} s (min {min(epoch_time.values())}, max {max(epoch_time.values())}) |\n")
L.append("## Training loss by 20-epoch block (epoch means of logged iterations)\n| Epochs | G_L1 | G_GAN | D_real | D_fake |\n| --- | --- | --- | --- | --- |")
for i in range(10):
    L.append(f"| {i*20+1}-{(i+1)*20} | {blk(G_L1,i):.2f} | {blk(G_GAN,i):.2f} | {blk(D_real,i):.3f} | {blk(D_fake,i):.3f} |")
L.append(f"\nG_L1 change, block 1 to block 10: {blk(G_L1,0):.2f} to {blk(G_L1,9):.2f} ({100*(blk(G_L1,9)/blk(G_L1,0)-1):+.1f}%).\n")
both = np.mean([(a < 0.05) and (b < 0.05) for a, b in zip(D_real, D_fake)])
L.append(f"Discriminator balance: epoch means with both D_real and D_fake < 0.05: {100*both:.1f}% of epochs.\n")
L.append(f"## Held-out test set (n = {len(rows)} images, epoch-200 weights)\n| Metric | Mean | SD | Min | Max |\n| --- | --- | --- | --- | --- |")
for j, n in enumerate(["L1 (0-1 scale)", "PSNR (dB)", "SSIM"]):
    L.append(f"| {n} | {M[:,j].mean():.4f} | {M[:,j].std(ddof=1):.4f} | {M[:,j].min():.4f} | {M[:,j].max():.4f} |")
L.append("\nExample rows in test_examples.png are the best, median, and worst test images by SSIM.\n")
L.append("## Caveats\n- Training losses are logged at 4 iterations per epoch (training set), not a held-out measure.\n- No FID or perceptual metric; PSNR/SSIM reward pixel agreement, not visual realism.\n- Learning rate in the figure follows the scheduler formula (consistent with the logged values at epochs 100-101 and 200).\n- Reference implementation (Isola et al.); not the Track 2 practicum model.")
open(f"{OUT}/slide_summary.md", "w").write("\n".join(L))
print("\n".join(L)); print(f"\nSaved to ./{OUT}/")
