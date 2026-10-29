"""Screenshot-ready summary of the full 200-epoch pix2pix run (terminal output).
Run from the pytorch-CycleGAN-and-pix2pix folder:
    python pix2pix_summary.py            # full report
    python pix2pix_summary.py --part 1   # configuration + training only
    python pix2pix_summary.py --part 2   # evaluation only
"""
import argparse, glob, os, re
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

LOG = "train_full.log"
RES = "results/facades_pix2pix_full"
N_EPOCHS, ITERS, LR0, DECAY_START = 200, 400, 2e-4, 100
W = 84
ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, choices=[1, 2]); args = ap.parse_args()

def bar(t=""): print(("=" * W) if not t else f"{t}\n" + "-" * W)
def row(*cells, widths): print(" ".join(str(c).rjust(w) if i else str(c).ljust(w) for i, (c, w) in enumerate(zip(cells, widths))))

# ---------- parse log (resumed segment overrides the repeated epoch 36) ----------
pat = re.compile(r"epoch: (\d+), iters: (\d+).*G_GAN: ([\d.]+), G_L1: ([\d.]+), D_real: ([\d.]+), D_fake: ([\d.]+)")
tpat = re.compile(r"End of epoch (\d+) / \d+\s+Time Taken: (\d+) sec")
samples, times = {}, []
for line in open(LOG):
    m = pat.search(line)
    if m: samples[(int(m[1]), int(m[2]))] = tuple(float(m[k]) for k in range(3, 7))
    t = tpat.search(line)
    if t: times.append((int(t[1]), int(t[2])))
epochs = sorted({e for e, _ in samples})
assert epochs == list(range(1, N_EPOCHS + 1)), f"log covers {len(epochs)} of {N_EPOCHS} epochs"
em = lambda k: np.array([np.mean([v[k] for (e, _), v in samples.items() if e == ep]) for ep in epochs])
G_GAN, G_L1, D_real, D_fake = em(0), em(1), em(2), em(3)
blk = lambda a, i: a[i * 20:(i + 1) * 20].mean()

# timing: epochs slower than 5x the median are treated as machine suspension
secs = np.array([s for _, s in times]); thr = 5 * np.median(secs)
susp = secs[secs > thr]; active = secs[secs <= thr]

def eval_dir(phase):
    d = f"{RES}/{phase}_200/images"; out = []
    for f in sorted(glob.glob(f"{d}/*_fake_B.png")):
        a = np.asarray(Image.open(f).convert("RGB"), dtype=np.float64) / 255
        b = np.asarray(Image.open(f.replace("_fake_B", "_real_B")).convert("RGB"), dtype=np.float64) / 255
        out.append((os.path.basename(f).split("_")[0], np.abs(a - b).mean(), psnr(b, a, data_range=1), ssim(b, a, channel_axis=2, data_range=1)))
    return out

if args.part in (None, 1):
    bar(); print("pix2pix  |  facades label -> photo (BtoA)  |  full 200-epoch run".center(W)); bar()
    print("\nCONFIGURATION"); print("-" * W)
    for k, v in [("Generator", "U-Net 256, 54.414 M parameters"), ("Discriminator", "PatchGAN, 2.769 M parameters"),
                 ("Training data", "400 paired images"),
                 ("Schedule", f"{DECAY_START} epochs LR {LR0:g}, then {N_EPOCHS-DECAY_START} epochs linear decay to 0"),
                 ("Loss", "GAN + 100 x L1  (batch 1, Adam beta1 0.5)"), ("Iterations", f"{N_EPOCHS*ITERS:,}"),
                 ("Active compute", f"{active.sum()/3600:.1f} h CPU  (mean {active.mean():.0f} s/epoch, max {active.max()} s)"),
                 ("Wall-clock", f"{secs.sum()/3600:.1f} h  ({susp.sum()/3600:.1f} h machine suspension, {len(susp)} epoch(s) excluded)"),
                 ("Interruption", f"resumed from epoch 35 checkpoint; {len(secs)-N_EPOCHS} epoch(s) repeated")]:
        print(f"  {k:<15}{v}")
    print("\nTRAINING LOSS  (epoch means of logged iterations, 20-epoch blocks)"); print("-" * W)
    wd = [10, 8, 9, 8, 8, 9]; row("Epochs", "G_L1", "vs. blk 1", "G_GAN", "D_real", "D_fake", widths=wd)
    for i in range(10):
        row(f"{i*20+1}-{(i+1)*20}", f"{blk(G_L1,i):.2f}", f"{100*(blk(G_L1,i)/blk(G_L1,0)-1):+.1f}%" if i else "-",
            f"{blk(G_GAN,i):.2f}", f"{blk(D_real,i):.3f}", f"{blk(D_fake,i):.3f}", widths=wd)
    both = np.mean([(a < .05) and (b < .05) for a, b in zip(D_real, D_fake)])
    print(f"\n  G_L1 {blk(G_L1,0):.2f} -> {blk(G_L1,9):.2f} ({100*(blk(G_L1,9)/blk(G_L1,0)-1):+.1f}%); "
          f"{100*(blk(G_L1,0)-blk(G_L1,4))/(blk(G_L1,0)-blk(G_L1,9)):.0f}% of the drop occurs by epoch {DECAY_START}")
    print(f"  Epochs with both D losses < 0.05: {100*both:.1f}%   LR: {LR0:g} -> ~0 (linear, epochs 101-200)\n")

if args.part in (None, 2):
    te, tr = eval_dir("test"), (eval_dir("train") if os.path.isdir(f"{RES}/train_200/images") else None)
    M = np.array([r[1:] for r in te]); T = np.array([r[1:] for r in tr]) if tr else None
    if args.part == 2: bar(); print("pix2pix  |  evaluation, epoch-200 weights".center(W)); bar()
    print("EVALUATION  (fake_B vs. ground-truth photo)"); print("-" * W)
    wd = [14, 18, 14, 14]; row("Metric", f"Test (n={len(te)})", f"Train (n={len(tr)})" if tr else "Train", "Test vs train", widths=wd)
    for j, (n, f, sign) in enumerate([("L1 (0-1)", "{:.4f}", 1), ("PSNR (dB)", "{:.2f}", 1), ("SSIM", "{:.3f}", 1)]):
        tv = f.format(M[:, j].mean()); trv = f.format(T[:, j].mean()) if tr else "n/a"
        gap = (f"{100*(M[:,j].mean()/T[:,j].mean()-1):+.1f}%" if tr else "n/a")
        row(n, f"{tv} +/-{M[:,j].std(ddof=1):.3f}", trv, gap, widths=wd)
    S = np.array([r[3] for r in te]); o = np.argsort(S)
    print(f"\n  Examples by SSIM  best: id {te[o[-1]][0]} ({S[o[-1]]:.3f})   median: id {te[o[len(o)//2]][0]} "
          f"({S[o[len(o)//2]]:.3f})   worst: id {te[o[0]][0]} ({S[o[0]]:.3f})")
    print("\nNOTES"); print("-" * W)
    for s in [f"Train metrics: first {len(tr) if tr else 0} of 400 training pairs. Test: n={len(te)}.",
              "Training loss is logged on 4 iterations/epoch (training set).",
              "Label maps do not fix color/material, so plausible outputs score low.",
              "No FID/perceptual metric. Reference model, not the Track 2 U-Net."]:
        print(f"  - {s}")
    bar()
