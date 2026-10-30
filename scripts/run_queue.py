#!/usr/bin/env python3
"""usage (from the repo root): nohup python3 scripts/run_queue.py >> outputs/queue.log 2>&1 &
Waits until the fold 3 H&E run is complete (outputs/nextbrain_fold3_he/TRAINING_DONE exists AND its process has exited), then runs the H&E runs of folds 1, 2, 4, 5 in that order:
for each fold, (1) verifies every entry of out/r4m_audit/LOCK_HASHES.txt and that the fold's config and harness-grid baseline outputs are locked, (2) trains with
`nohup caffeinate -i <python> scripts/train_nextbrain_fold.py --config configs/nextbrain_fold{k}_he.json --root <data> --mode train --epochs 100 --out_dir outputs/nextbrain_fold{k}_he`
(same flags as fold 3; resumable from ckpt_latest.pt; best-validation checkpoint; epoch-10 rule inside the training script: stop unless min validation L1 over epochs 1-10 < 0.1925),
(3) reports the epoch-10 comparison against that fold's own validation baselines, (4) runs scripts/eval_nextbrain_test_fold.py once.
State: outputs/queue_state.json. No LFB run is queued. Fold 3's own test evaluation is NOT done here. A rule stop (exit 3), a lock mismatch or any failure aborts the whole queue.
Rerunning the script resumes: finished folds are skipped, an interrupted fold resumes from its latest checkpoint."""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

PY = "pix2pix_env/bin/python"; DATA = os.path.expanduser("~/Data/NextBrain"); FOLDS = [1, 2, 4, 5]; TARGET = "HE"; REF = 0.1925
STATE = Path("outputs/queue_state.json"); LOCK = Path("out/r4m_audit/LOCK_HASHES.txt"); F3 = Path("outputs/nextbrain_fold3_he")
POLL = float(os.environ.get("QUEUE_POLL_S", "30"))   # seconds between polls (tests set a small value)
now = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
log = lambda *m: print(now(), *m, flush=True)


def save(st):
    st["updated_utc"] = now(); tmp = str(STATE) + ".tmp"; json.dump(st, open(tmp, "w"), indent=1); os.replace(tmp, STATE)


def verify_locks():
    ok = bad = 0; entries = {}
    for l in open(LOCK):
        l = l.rstrip("\n")
        if not l or l.startswith("#"): continue
        h, _, p = l.partition("  ")
        entries[p] = h
        if Path(p).exists() and hashlib.sha256(open(p, "rb").read()).hexdigest() == h: ok += 1
        else: bad += 1; log("LOCK MISMATCH/MISSING:", p)
    return ok, bad, entries


def alive(pattern):
    return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0


st = json.load(open(STATE)) if STATE.exists() else {"folds": {}, "note": "H&E only; no LFB run is queued"}
st["queue_pid"] = os.getpid(); save(st)

# 1) wait for fold 3
pat = os.environ.get("QUEUE_F3_PATTERN", "train_nextbrain.py --config configs/nextbrain_fold3_he.json")   # override only in the sandbox test
log("waiting for fold 3 (TRAINING_DONE and process exit)")
while True:
    done = (F3 / "TRAINING_DONE").exists(); run = alive(pat)
    if (F3 / "STOPPED_AT_EPOCH_10.txt").exists(): st["status"] = "aborted: fold 3 stopped by the epoch-10 rule"; save(st); sys.exit(2)
    if done and not run: break
    if not done and not run:
        st["status"] = "aborted: fold 3 process is not running and TRAINING_DONE is absent"; save(st); log(st["status"]); sys.exit(2)
    st["status"] = "waiting for fold 3"; save(st); time.sleep(2 * POLL)
log("fold 3 complete; starting queue"); st["fold3_complete_utc"] = now(); save(st)

for k in FOLDS:
    fs = st["folds"].setdefault(str(k), {}); cfg = f"configs/nextbrain_fold{k}_he.json"; od = Path(f"outputs/nextbrain_fold{k}_he"); od.mkdir(parents=True, exist_ok=True)
    if fs.get("status") == "evaluated": log(f"fold {k} already evaluated; skipping"); continue
    ok, bad, entries = verify_locks(); log(f"lock check before fold {k}: entries ok={ok} mismatch/missing={bad}")
    need = [cfg, f"outputs/nextbrain_baselines_harness_grid_fold{k}.json", f"outputs/nextbrain_baselines_harness_grid_fold{k}.md", f"splits/nextbrain_fold{k}.json"]
    missing = [p for p in need if p not in entries]
    if bad or missing:
        fs["status"] = f"aborted: lock mismatch={bad}, not locked={missing}"; save(st); log(fs["status"]); sys.exit(2)
    if not (od / "TRAINING_DONE").exists():
        if (od / "STOPPED_AT_EPOCH_10.txt").exists(): fs["status"] = "stopped_by_epoch10_rule"; save(st); sys.exit(3)
        for attempt in range(1, 4):   # a crash is retried by resuming from ckpt_latest.pt
            cmd = ["nohup", "caffeinate", "-i", PY, "-W", "ignore", "scripts/train_nextbrain_fold.py", "--config", cfg, "--root", DATA, "--mode", "train", "--epochs", "100", "--out_dir", str(od)]
            fs.update(status="training", attempt=attempt, started_utc=fs.get("started_utc", now()), command=" ".join(cmd)); save(st); log("launch:", " ".join(cmd))
            with open(od / "train.log", "a") as lg: p = subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT, start_new_session=True)
            while p.poll() is None:
                time.sleep(POLL)
                h = od / "history.csv"
                if not fs.get("epoch10_report") and h.exists():
                    rows = [r.split(",") for r in open(h).read().strip().splitlines()[1:]]
                    if len(rows) >= 10:
                        v = [float(r[5]) for r in rows[:10]]; b = json.load(open(f"outputs/nextbrain_baselines_harness_grid_fold{k}.json"))["validation"]
                        fs["epoch10_report"] = dict(val_L1_epoch10=v[9], min_val_L1_epochs_1_10=min(v), reference_200_iter_fold3=REF, lookup_val_L1_harness=b["gray_level_LUT"]["L1"]["mean"],
                                                    mean_target_val_L1_harness=b["mean_train_target"]["L1"]["mean"], note="the 0.1925 reference is the fold-3 200-iteration value; applied unchanged to this fold (UNVERIFIED as an appropriate bar)")
                        log(f"EPOCH-10 CHECK fold {k}:", fs["epoch10_report"]); save(st)
            rc = p.returncode; fs["last_returncode"] = rc; save(st)
            if rc == 0 and (od / "TRAINING_DONE").exists(): break
            if rc == 3: fs["status"] = "stopped_by_epoch10_rule"; save(st); log(f"fold {k} stopped by the epoch-10 rule; queue aborted"); sys.exit(3)
            log(f"fold {k} training exited with {rc}; attempt {attempt}")
        else:
            fs["status"] = "failed_training"; save(st); sys.exit(1)
    fs.update(status="trained", trained_utc=now()); save(st)
    if not (od / "results.json").exists():
        with open(od / "eval.log", "a") as lg:
            rc = subprocess.run([PY, "-W", "ignore", "scripts/eval_nextbrain_test_fold.py", "--config", cfg, "--root", DATA, "--out_dir", str(od)], stdout=lg, stderr=subprocess.STDOUT).returncode
        if rc != 0: fs["status"] = f"failed_eval_rc{rc}"; save(st); log(fs["status"]); sys.exit(1)
    fs.update(status="evaluated", evaluated_utc=now()); save(st); log(f"fold {k} evaluated")
st["status"] = "all folds finished"; save(st); log("queue finished")
