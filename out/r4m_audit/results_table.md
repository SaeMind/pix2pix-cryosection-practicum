# Results table (mean of 3 block means; no interpretation)

| row | L1_maskv2_all45 | L1_maskv2_valid | L1_body | L1_fov_chain | L1_full | PSNR_maskv2 | SSIM_maskv2 | PSNR_full_chain | SSIM_full_chain | L1_maskv2_A | L1_maskv2_B | L1_maskv2_C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R4M | 0.06115 | 0.06150 | 0.05720 | 0.05700 | 0.03837 | 22.13348 | 0.46355 | 25.11489 | 0.70154 | 0.05589 | 0.05634 | 0.07123 |
| R2M | 0.06580 | 0.06585 | 0.06241 | 0.06229 | 0.04083 | 21.56008 | 0.44990 | 24.57222 | 0.70021 | 0.06161 | 0.06054 | 0.07524 |
| R5M | 0.06185 | 0.06215 | 0.05781 | 0.05749 | 0.03980 | 21.94071 | 0.44518 | 24.91007 | 0.68967 | 0.05996 | 0.06138 | 0.06422 |
| baseline_mean_train_cryo | 0.09262 | 0.09410 | 0.10787 | 0.10979 | 0.05990 | 19.02529 | 0.39166 | 21.69426 | 0.64353 | 0.09611 | 0.10250 | 0.07923 |

L1_fov_chain, PSNR_full_chain, SSIM_full_chain: chain metrics.json (PSNR/SSIM unmasked). Others: score_extra.py / score_sensitivity.py. 1 animal, 3 blocks, no p-values; within-animal, not generalizable.
