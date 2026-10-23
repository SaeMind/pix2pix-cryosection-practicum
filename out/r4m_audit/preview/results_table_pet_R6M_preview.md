# Results table, PET-only comparison (mean of 3 block means; Addendum 4)

| row | L1_maskv2 all45 | L1_maskv2 valid37 | SSIM_maskv2 | PSNR_maskv2 | gain vs baseline A | B | C | (valid37) A | B | C |
|---|---|---|---|---|---|---|---|---|---|---|
| R4M | 0.06115 | 0.06150 | 0.46355 | 22.13348 | 0.04022 | 0.04616 | 0.00801 | 0.04363 | 0.04616 | 0.00801 |
| R2M | 0.06580 | 0.06585 | 0.44990 | 21.56008 | 0.03450 | 0.04197 | 0.00400 | 0.03876 | 0.04197 | 0.00400 |
| R5M | 0.06185 | 0.06215 | 0.44518 | 21.94071 | 0.03615 | 0.04112 | 0.01501 | 0.03971 | 0.04112 | 0.01501 |
| R6M | 0.06196 | 0.06208 | 0.45151 | 22.01379 | 0.03829 | 0.04156 | 0.01213 | 0.04235 | 0.04156 | 0.01213 |
| R7M | n/a | | | | | | | | | |
| R6bM | n/a | | | | | | | | | |
| baseline_mean_train_cryo | 0.09262 | 0.09410 | 0.39166 | 19.02529 |  -  |  -  |  -  |  -  |  -  |  -  |

gain vs baseline = baseline block L1 minus run block L1 (positive = run better). Within-animal, not generalizable; no p-values.

## Addendum 4 rules (mechanical)

- P1: PASS: R6M minus baseline per block (all45): A -0.03829, B -0.04156, C -0.01213; valid37: A -0.04235, B -0.04156, C -0.01213 -> PASS
- P2: not yet evaluable (R7M, R6bM pending)
- P3: not yet evaluable (R7M, R6bM pending)
- P4: signed R6M minus R2M per block (all45): A -0.00379, B +0.00041, C -0.00813
- P5: **N/A**: standing rule: complementarity is not credited; R4-M versus R5-M not reopened
(Output of out/r4m/build_results_table_pet.py with P2-P4 lines reworded per the preview rule of Addendum 4a: R7M and R6bM not yet run.)
