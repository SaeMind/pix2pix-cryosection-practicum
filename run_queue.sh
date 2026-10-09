#!/usr/bin/env bash
# usage: caffeinate -dims ./run_queue.sh TOTAL_EPOCHS   (even number)
set -euo pipefail
E="${1:?total epochs}"; H=$((E/2)); D=datasets/D2_ablation
run() {  # name dataset input_nc
  python train.py --dataroot "$D/$2" --name "$1" --model pix2pix --direction AtoB \
    --input_nc "$3" --output_nc 3 --netG unet_256 --preprocess none --batch_size 1 \
    --n_epochs "$H" --n_epochs_decay "$H" --save_epoch_freq "$E" --display_id 0 --no_html
  python test.py --dataroot "$D/$2" --name "$1" --model pix2pix --direction AtoB \
    --input_nc "$3" --output_nc 3 --netG unet_256 --preprocess none --phase test \
    --num_test 50 --eval
}
run R1 ct 1
run R2 ct 3
run R4 petct 3
run R5 petct_shuf 3
if [ "${INCLUDE_R3:-0}" = 1 ]; then run R3 pet 1; fi
echo "queue finished"
