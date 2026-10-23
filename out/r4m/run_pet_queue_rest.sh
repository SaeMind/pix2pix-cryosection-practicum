#!/usr/bin/env bash
# PET-only queue (Addendum 4): R6M, R7M, R6bM. Run from repo root, e.g.
#   nohup caffeinate -i bash out/r4m/run_pet_queue.sh > out/r4m/pet_queue.log 2>&1 &
# Continues on failure; every stage's exit code goes to out/r4m/pet_queue_status.txt.
# Scorer sequence per run = run_all.sh (infer_score.py), then the audit scorers named in METRIC_LOCK_ADDENDUM*.md / REPORT.md
# (score_extra.py, score_sensitivity.py). No code change is needed for a new run name.
cd "$(dirname "$0")/../.." || exit 1
source pix2pix_env/bin/activate
PY=pix2pix_env/bin/python
ST=out/r4m/pet_queue_status.txt
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$ST"; }

free_gb=$(df -g . | awk 'NR==2 {print $4}')
if [ "${free_gb:-0}" -lt 20 ]; then log "ABORT free disk ${free_gb} GB < 20 GB"; exit 1; fi
for v in pet pet_shuf; do
  [ -d "out/r4m/data/$v/train" ] || { log "ABORT missing out/r4m/data/$v (run prep_pet_variants.py)"; exit 1; }
done

stage() {  # label command...
  local label="$1"; shift
  log "START $label"
  "$@"; local rc=$?
  log "EXIT $label rc=$rc"
  return $rc
}

run() {  # NAME VARIANT SEED
  local N="$1" V="$2" SEED="$3"
  if [ -e "out/r4m/checkpoints/$N" ] || [ -e "out/r4m/$N" ]; then log "SKIP $N: out/r4m/$N or checkpoints/$N already exists"; return 1; fi
  stage "$N train (seed $SEED)" env R4M_SEED="$SEED" $PY out/r4m/train_r4m_seed.py "$N" "$V" 3 > "out/r4m/${N}_train.log" 2>&1 || return 1
  [ -f "out/r4m/checkpoints/$N/100_net_G.pth" ] || { log "FAIL $N: no 100_net_G.pth"; return 1; }
  stage "$N infer_score" $PY out/r4m/infer_score.py "$N" "$V" 3 > "out/r4m/${N}_score.log" 2>&1 || return 1
  stage "$N score_extra" $PY out/r4m_audit/score_extra.py "$N" > "out/r4m_audit/score_extra_${N}.log" 2>&1
  stage "$N score_sensitivity" $PY out/r4m_audit/score_sensitivity.py "$N" > "out/r4m_audit/score_sensitivity_${N}.log" 2>&1
}

log "QUEUE START"
run R7M  pet_shuf 1234
run R6bM pet      4321
log "QUEUE DONE"
