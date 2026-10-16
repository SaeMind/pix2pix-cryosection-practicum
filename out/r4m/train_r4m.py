#!/usr/bin/env python3
"""usage: python out/r4m/train_r4m.py NAME VARIANT INPUT_NC   (VARIANT: petct | ct | petct_shuf)
Same options as run_queue.sh / checkpoints/R4/train_opt.txt (100 epochs = 50+50, lr 2e-4, lambda_L1 100,
batch 1, unet_256, basic PatchGAN, no_flip, preprocess none). Differences from R4: split, and a fixed seed
(R4 was unseeded). Only the final checkpoint is saved (save_epoch_freq 100, save_latest_freq disabled)."""
import json, random, runpy, sys
import numpy as np, torch
sys.path.insert(0, "."); SEED = 1234
name, variant, nc = sys.argv[1], sys.argv[2], sys.argv[3]
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
args = ["train.py", "--dataroot", f"out/r4m/data/{variant}", "--name", name, "--checkpoints_dir", "out/r4m/checkpoints",
        "--model", "pix2pix", "--direction", "AtoB", "--input_nc", nc, "--output_nc", "3", "--netG", "unet_256",
        "--preprocess", "none", "--batch_size", "1", "--no_flip", "--n_epochs", "50", "--n_epochs_decay", "50",
        "--save_epoch_freq", "100", "--save_latest_freq", "100000000", "--no_html"]
cfg = dict(name=name, variant=variant, seed=SEED, argv=args[1:], epochs=100, lr=2e-4, lambda_L1=100.0, batch_size=1,
           image_size=256, netG="unet_256 (ngf 64)", netD="basic PatchGAN (ndf 64, n_layers 3)", gan_mode="vanilla",
           lr_policy="linear (50 const + 50 decay)", reference_run="R4 (checkpoints/R4/train_opt.txt)",
           differs_from_R4=["split", "seed fixed (R4 unseeded)"])
import os; os.makedirs(f"out/r4m/{name}", exist_ok=True)
json.dump(cfg, open(f"out/r4m/{name}/config.json", "w"), indent=1)
sys.argv = args
runpy.run_path("train.py", run_name="__main__")
