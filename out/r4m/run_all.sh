#!/usr/bin/env bash
set -euo pipefail
PY=pix2pix_env/bin/python
while [ ! -f out/r4m/checkpoints/R4M/100_net_G.pth ]; do sleep 30; done
sleep 20
$PY out/r4m/infer_score.py R4M petct 3 > out/r4m/R4M_score.log 2>&1
$PY out/r4m/test_r4m.py > out/r4m/tests.log 2>&1
# Step 6 (Steps 1-5 complete)
$PY out/r4m/train_r4m.py R2M ct 3 > out/r4m/R2M_train.log 2>&1
$PY out/r4m/infer_score.py R2M ct 3 > out/r4m/R2M_score.log 2>&1
$PY out/r4m/train_r4m.py R5M petct_shuf 3 > out/r4m/R5M_train.log 2>&1
$PY out/r4m/infer_score.py R5M petct_shuf 3 > out/r4m/R5M_score.log 2>&1
echo ALLDONE > out/r4m/ALLDONE
