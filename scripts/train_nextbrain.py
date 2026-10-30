#!/usr/bin/env python3
"""Config-driven NextBrain Pix2Pix harness (pre-registered in outputs/nextbrain_train_prereg.md).
usage: python scripts/train_nextbrain.py --config configs/nextbrain_fold3_he.json --root <dir with Case1..Case5> --mode timing
Mode 'timing' (200 iterations + one validation pass) and mode 'train' (full run, see outputs/nextbrain_eval_addendum3.md; add --epochs 100 [--out_dir outputs/nextbrain_fold3_he]).
Test-case records are never loaded by this script; the one-time test evaluation is scripts/eval_nextbrain_test.py."""
import argparse, csv, json, random, resource, sys, time
from pathlib import Path
import numpy as np
import torch, torch.nn as nn
from PIL import Image
sys.path.insert(0, ".")
from models import networks

ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--root"); ap.add_argument("--mode", default="timing", choices=["timing", "train"])
ap.add_argument("--epochs", type=int, default=100); ap.add_argument("--out_dir", default="outputs/nextbrain_fold3_he"); ap.add_argument("--smoke_iters", type=int, default=0, help="debug only: truncate each epoch and the validation set"); a = ap.parse_args()
cfg = json.load(open(a.config)); root = Path(a.root or cfg["data_root"]).expanduser()
S = json.load(open(cfg["splits"]))
test_ids = {r["id"] for r in S["test"]}; test_subjects = {r["subject"] for r in S["test"]}
excl = set(cfg["exclude_blocks"])
keep = lambda recs: [r for r in recs if f"{r['subject']}/{r['block']}" not in excl]
train, val = keep(S["train"]), keep(S["val"])
meta = {f"{r['case_id']}/{r['block']}/{r['slice']}": r for r in csv.DictReader(open(cfg["metadata"]))}
N = cfg["image_size"]

for r in train + val:   # test isolation, asserted before any file is opened
    assert r["id"] not in test_ids and r["subject"] not in test_subjects, f"test-case record in train/val: {r['id']}"


def load(rec):
    assert rec["id"] not in test_ids and rec["subject"] not in test_subjects, f"test-case record requested: {rec['id']}"
    m = meta[rec["id"]]; cd = root / f"Case{m['case_number']}"
    he = Image.open(cd / m[f"path_{cfg['target']}"]).convert("RGB"); mri = Image.open(cd / m["path_MRI"]).convert("L")
    mri = mri.resize(he.size, Image.BILINEAR)                   # MRI -> target grid (shape-audit rule)
    s = N / max(he.size); nw, nh = round(he.size[0] * s), round(he.size[1] * s)
    y0, x0 = (N - nh) // 2, (N - nw) // 2
    A = np.zeros((N, N), np.uint8); B = np.zeros((N, N, 3), np.uint8)
    A[y0:y0 + nh, x0:x0 + nw] = np.asarray(mri.resize((nw, nh), Image.BILINEAR))
    B[y0:y0 + nh, x0:x0 + nw] = np.asarray(he.resize((nw, nh), Image.BILINEAR))
    return A, B


random.seed(cfg["seed"]); np.random.seed(cfg["seed"]); torch.manual_seed(cfg["seed"])
dev = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
G = networks.init_net(networks.define_G(1, 3, cfg["ngf"], cfg["netG"], cfg["norm"], cfg["use_dropout"]), "normal", 0.02).to(dev)
D = networks.init_net(networks.define_D(4, cfg["ndf"], cfg["netD"], cfg["n_layers_D"], cfg["norm"]), "normal", 0.02).to(dev)
gan = networks.GANLoss(cfg["gan_mode"]).to(dev); l1 = nn.L1Loss()
oG = torch.optim.Adam(G.parameters(), lr=cfg["lr"], betas=(cfg["beta1"], cfg["beta2"])); oD = torch.optim.Adam(D.parameters(), lr=cfg["lr"], betas=(cfg["beta1"], cfg["beta2"]))
T = lambda A, B: (torch.from_numpy(A)[None, None].float().div(127.5).sub(1).to(dev), torch.from_numpy(B).permute(2, 0, 1)[None].float().div(127.5).sub(1).to(dev))
sync = (lambda: torch.mps.synchronize()) if dev.type == "mps" else (lambda: torch.cuda.synchronize()) if dev.type == "cuda" else (lambda: None)
memnow = (lambda: torch.mps.driver_allocated_memory()) if dev.type == "mps" else (lambda: torch.cuda.max_memory_allocated()) if dev.type == "cuda" else (lambda: 0)

if a.mode == "train":
    import os
    from torch.optim.lr_scheduler import LambdaLR
    E = a.epochs; assert E == cfg["epochs_const"] + cfg["epochs_decay"], "epochs must equal epochs_const + epochs_decay"
    od = Path(a.out_dir); od.mkdir(parents=True, exist_ok=True); LATEST, BEST = od / "ckpt_latest.pt", od / "ckpt_best.pt"
    REF_UNTRAINED = 0.1925   # validation masked L1 after 200 iterations (outputs/nextbrain_timing_with_exclusions.json), not a truly untrained network
    lam = lambda ep: 1.0 - max(0, ep + 1 - cfg["epochs_const"]) / float(cfg["epochs_decay"] + 1)   # upstream pix2pix 'linear' policy (0-based epoch)
    sG, sD = LambdaLR(oG, lam), LambdaLR(oD, lam)
    t0 = time.time(); TA = np.stack([load(r)[0] for r in train]); TB = np.stack([load(r)[1] for r in train])
    VA = np.stack([load(r)[0] for r in val]); VB = np.stack([load(r)[1] for r in val])
    print(f"preloaded train {len(train)} val {len(val)} in {time.time() - t0:.0f}s; device {dev}; excluded {sorted(excl)}", flush=True)
    if a.smoke_iters: VA, VB = VA[:32], VB[:32]
    hist, best_val, best_ep, start = [], float("inf"), 0, 0
    if LATEST.exists():   # resume
        ck = torch.load(LATEST, map_location="cpu", weights_only=False)
        G.load_state_dict(ck["G"]); D.load_state_dict(ck["D"]); oG.load_state_dict(ck["oG"]); oD.load_state_dict(ck["oD"]); sG.load_state_dict(ck["sG"]); sD.load_state_dict(ck["sD"])
        hist, best_val, best_ep, start = ck["hist"], ck["best_val"], ck["best_ep"], ck["epoch"]
        torch.set_rng_state(ck["rng_cpu"])
        try: torch.mps.set_rng_state(ck["rng_mps"]) if dev.type == "mps" and ck.get("rng_mps") is not None else None
        except Exception as e: print("warning: MPS RNG state not restored:", e, flush=True)
        print(f"RESUMED from {LATEST} after epoch {start}; best val {best_val:.4f} at epoch {best_ep}", flush=True)
    try:
        hg = json.load(open("outputs/nextbrain_baselines_harness_grid.json"))["validation"]; ho = json.load(open("outputs/nextbrain_baselines_sensitivity.json"))["3"]["validation"]
        lut_h, lut_o = hg["gray_level_LUT"]["L1"]["mean"], ho["HE|gray_level_LUT"]["L1"]["mean"]
    except Exception as e:
        lut_h = lut_o = float("nan"); print("warning: could not read baseline reference values:", e, flush=True)

    def validate():
        G.eval(); out = []
        with torch.no_grad():
            for i in range(0, len(VA), 16):
                A = torch.from_numpy(VA[i:i + 16])[:, None].float().div(127.5).sub(1).to(dev); B = torch.from_numpy(VB[i:i + 16]).permute(0, 3, 1, 2).float().div(127.5).sub(1).to(dev)
                m = (A > -1).float()   # MRI > 0 on the uint8 grid
                d = (((G(A) + 1) / 2 - (B + 1) / 2).abs() * m).sum((1, 2, 3)) / (3 * m.sum((1, 2, 3)))
                out += d.cpu().tolist()
        G.train(); return float(np.mean(out))

    def curve(ep):
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        xs = [h["epoch"] for h in hist]; fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(xs, [h["val_L1"] for h in hist], label="validation masked L1 (eval mode)"); ax.plot(xs, [h["train_L1"] for h in hist], "--", label="train L1 (train mode, unmasked)")
        for v, nm in ((REF_UNTRAINED, "200-iteration reference 0.1925"), (lut_h, "validation lookup baseline (harness grid)")): ax.axhline(v, color="gray", ls=":", lw=1); ax.text(xs[-1], v, nm, fontsize=7, ha="right", va="bottom")
        ax.set_xlabel("epoch"); ax.set_ylabel("L1 [0,1]"); ax.set_title(f"fold 3 MRI to H&E, through epoch {ep}"); ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(od / f"val_curve_epoch{ep:03d}.png", dpi=120); plt.close(fig)

    G.train(); D.train()
    for ep in range(start, E):
        te0 = time.time(); order = torch.randperm(len(train), generator=torch.Generator().manual_seed(cfg["seed"] + ep)).tolist()
        if a.smoke_iters: order = order[:a.smoke_iters]
        sg = sd = sl = torch.zeros((), device=dev)
        for i in order:
            A, B = T(TA[i], TB[i]); fake = G(A)
            for p in D.parameters(): p.requires_grad = True
            oD.zero_grad(); lD = 0.5 * (gan(D(torch.cat([A, fake.detach()], 1)), False) + gan(D(torch.cat([A, B], 1)), True)); lD.backward(); oD.step()
            for p in D.parameters(): p.requires_grad = False
            oG.zero_grad(); l1v = l1(fake, B); lG = gan(D(torch.cat([A, fake], 1)), True) + l1v * cfg["lambda_L1"]; lG.backward(); oG.step()
            sg = sg + lG.detach(); sd = sd + lD.detach(); sl = sl + l1v.detach()
        n_ = len(order); lr_now = oG.param_groups[0]["lr"]; sG.step(); sD.step()
        v = validate(); improved = v < best_val
        if improved:
            best_val, best_ep = v, ep + 1; torch.save({"G": G.state_dict(), "epoch": ep + 1, "val_L1": v, "cfg": cfg}, str(BEST) + ".tmp"); os.replace(str(BEST) + ".tmp", BEST)
        h = dict(epoch=ep + 1, lr=lr_now, G=float(sg) / n_, D=float(sd) / n_, train_L1=float(sl) / n_, val_L1=v, seconds=time.time() - te0, best=improved); hist.append(h)
        ck = dict(G=G.state_dict(), D=D.state_dict(), oG=oG.state_dict(), oD=oD.state_dict(), sG=sG.state_dict(), sD=sD.state_dict(), hist=hist, best_val=best_val, best_ep=best_ep, epoch=ep + 1, rng_cpu=torch.get_rng_state(),
                  rng_mps=(torch.mps.get_rng_state() if dev.type == "mps" else None))
        torch.save(ck, str(LATEST) + ".tmp"); os.replace(str(LATEST) + ".tmp", LATEST)
        with open(od / "history.csv", "w") as f:
            f.write("epoch,lr,G,D,train_L1,val_L1,seconds,best\n"); [f.write(f"{x['epoch']},{x['lr']:.6g},{x['G']:.5f},{x['D']:.5f},{x['train_L1']:.5f},{x['val_L1']:.5f},{x['seconds']:.1f},{int(x['best'])}\n") for x in hist]
        print(f"epoch {ep + 1:3d}/{E} lr {lr_now:.2e} G {h['G']:.4f} D {h['D']:.4f} L1 {h['train_L1']:.4f} val_L1 {v:.4f} best {best_val:.4f}@{best_ep} sec {h['seconds']:.0f}{' *' if improved else ''}", flush=True)
        if (ep + 1) % 10 == 0: curve(ep + 1)
        if ep + 1 == 10:
            mn = min(x["val_L1"] for x in hist[:10])
            print(f"EPOCH-10 CHECK: val L1 {v:.4f} (min over epochs 1-10 {mn:.4f}) | 200-iteration reference {REF_UNTRAINED:.4f} | validation lookup baseline: harness grid {lut_h:.4f}, original grid {lut_o:.4f}", flush=True)
            if not mn < REF_UNTRAINED:
                (od / "STOPPED_AT_EPOCH_10.txt").write_text(f"validation L1 did not drop below {REF_UNTRAINED} by epoch 10 (min {mn:.4f}); run stopped by rule\n"); print("STOP: rule triggered", flush=True); sys.exit(3)
    (od / "TRAINING_DONE").write_text(f"epochs {E}; best validation L1 {best_val:.6f} at epoch {best_ep}\n"); print(f"DONE: best val {best_val:.4f} at epoch {best_ep}", flush=True); sys.exit(0)

# training order (seeded generator, epoch 0); preload the records the timing test uses so timing excludes disk/JPEG decode
g = torch.Generator().manual_seed(cfg["seed"] + 0)
order = torch.randperm(len(train), generator=g).tolist()[:cfg["timing_iters"]]
t0 = time.time(); cache = [load(train[i]) for i in order]; load_s = (time.time() - t0) / len(order)

G.train(); D.train(); times, mem = [], []; lg = ld = 0.0
for it, (A_, B_) in enumerate(cache):
    A, B = T(A_, B_); sync(); t = time.time()
    fake = G(A)
    for p in D.parameters(): p.requires_grad = True
    oD.zero_grad()
    lD = 0.5 * (gan(D(torch.cat([A, fake.detach()], 1)), False) + gan(D(torch.cat([A, B], 1)), True)); lD.backward(); oD.step()
    for p in D.parameters(): p.requires_grad = False
    oG.zero_grad()
    lG = gan(D(torch.cat([A, fake], 1)), True) + l1(fake, B) * cfg["lambda_L1"]; lG.backward(); oG.step()
    sync(); times.append(time.time() - t); mem.append(memnow()); lg, ld = float(lG), float(lD)
w = cfg["warmup_iters"]; warm = float(np.sum(times[:w])); spi = float(np.mean(times[w:]))

# validation pass (sanity only): masked L1 in [0,1]
G.eval(); vl, vt = [], time.time(); vload = time.time(); V = [load(r) for r in val]; vload = (time.time() - vload) / len(val)
sync(); vt = time.time()
with torch.no_grad():
    for A_, B_ in V:
        A, B = T(A_, B_); pr = (G(A)[0] + 1) / 2; tg = (B[0] + 1) / 2; m = torch.from_numpy(A_ > 0).to(dev)
        vl.append(float((pr - tg).abs()[:, m].mean()))
sync(); val_pass = time.time() - vt

def ntrain(k, ex):
    s = json.load(open(cfg["all_splits_glob"].format(k=k)))
    return len([r for r in s["train"] if f"{r['subject']}/{r['block']}" not in ex]), len([r for r in s["val"] if f"{r['subject']}/{r['block']}" not in ex])
per = {k: ntrain(k, excl) for k in range(1, 6)}
n = len(train); ep = n * spi; vpe = val_pass
est = {"1_epoch_s": ep + vpe, "50_epochs_s": 50 * (ep + vpe), "100_epochs_s": 100 * (ep + vpe)}
tot = sum(100 * (nt * spi + nv * (val_pass / len(val))) for nt, nv in per.values()) * 2
res = dict(device=str(dev), torch=torch.__version__, n_train=n, n_val=len(val), excluded_blocks=sorted(excl), iters=len(times), warmup_s=warm, sec_per_iter=spi,
           sec_per_iter_sd=float(np.std(times[w:], ddof=1)), peak_mem_bytes_sampled=int(max(mem)), mem_stat=("MPS driver_allocated_memory, sampled after each iteration (no peak API)" if dev.type == "mps" else "CUDA max_memory_allocated" if dev.type == "cuda" else "n/a"),
           process_peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), data_load_s_per_record=load_s, val_load_s_per_record=vload,
           val_pass_s=val_pass, val_masked_L1_after_200_iters=float(np.mean(vl)), val_masked_L1_sd=float(np.std(vl, ddof=1)), last_lossG=lg, last_lossD=ld,
           estimates=est, fold_counts_train_val_after_exclusion=per, total_5folds_2stains_100ep_s=tot)
json.dump(res, open(cfg["out_json"], "w"), indent=1); print(json.dumps(res, indent=1))
