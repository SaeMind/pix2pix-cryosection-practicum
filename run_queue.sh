#!/usr/bin/env bash
# usage: source pix2pix_env/bin/activate && caffeinate -dims ./run_queue.sh TOTAL_EPOCHS ["RUNS"]
# default RUNS: "R2 R4 R5 R1 R2b R4b"   (R2b and R4b are replicates of R2 and R4)
# smoke test: ./run_queue.sh 2 "R4 R2b"
set -euo pipefail
E="${1:?total epochs (even number)}"; RUNS="${2:-R2 R4 R5 R1 R2b R4b}"
H=$((E/2)); D=datasets/D2_ablation
mkdir -p logs
exec > >(tee -a "logs/queue_$(date +%Y%m%d_%H%M%S).log") 2>&1
run() {  # name dataset input_nc
  if [ -d "results/$1" ] || [ -d "checkpoints/$1" ]; then
    echo "results/$1 or checkpoints/$1 already exists; move it first"; exit 1
  fi
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
    R1)      run "$r" ct 1 ;;
    R2|R2b)  run "$r" ct 3 ;;
    R3)      run "$r" pet 1 ;;
    R4|R4b)  run "$r" petct 3 ;;
    R5)      run "$r" petct_shuf 3 ;;
    *) echo "unknown run $r"; exit 1 ;;
  esac
done
echo "queue finished $(date)"
