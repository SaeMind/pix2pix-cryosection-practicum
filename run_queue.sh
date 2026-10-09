#!/usr/bin/env bash
# usage: source pix2pix_env/bin/activate && caffeinate -dims ./run_queue.sh TOTAL_EPOCHS [RUNS]
# RUNS default "R1 R2 R4 R5". Smoke test: ./run_queue.sh 2 R1
set -euo pipefail
E="${1:?total epochs (even number)}"; RUNS="${2:-R1 R2 R4 R5}"
H=$((E/2)); D=datasets/D2_ablation
mkdir -p logs
exec > >(tee -a "logs/queue_$(date +%Y%m%d_%H%M%S).log") 2>&1
run() {  # name dataset input_nc
  echo "=== $1 start $(date)"
  python train.py --dataroot "$D/$2" --name "$1" --model pix2pix --direction AtoB \
    --input_nc "$3" --output_nc 3 --netG unet_256 --preprocess none --batch_size 1 --no_flip \
    --n_epochs "$H" --n_epochs_decay "$H" --save_epoch_freq "$E" --no_html
  python test.py --dataroot "$D/$2" --name "$1" --model pix2pix --direction AtoB \
    --input_nc "$3" --output_nc 3 --netG unet_256 --preprocess none --phase test \
    --num_test 1000 --eval
  echo "=== $1 done $(date)"
}
for r in $RUNS; do
  case "$r" in
    R1) run R1 ct 1 ;;
    R2) run R2 ct 3 ;;
    R3) run R3 pet 1 ;;
    R4) run R4 petct 3 ;;
    R5) run R5 petct_shuf 3 ;;
    *) echo "unknown run $r"; exit 1 ;;
  esac
done
echo "queue finished $(date)"
