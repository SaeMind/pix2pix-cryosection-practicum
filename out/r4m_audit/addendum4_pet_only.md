# METRIC LOCK ADDENDUM 4 (PET-only runs R6-M, R7-M, R6b-M) — DRAFT

Added after primary results were known. Pre-registered relative to R6-M/R7-M scoring only. The primary verdict (PET not credited) is not revised.

Drafted 2026-10-23 (local). The SHA-256 and UTC timestamp of this file are recorded in out/r4m_audit/LOCK_HASHES.txt, not inside this file. No R6-M, R7-M or R6b-M data, training or scoring exists at the time of writing. Framing: retrospective multi-dataset evaluation; within-animal, not generalizable; not clinically validated.

## 1. Run matrix

All runs: DigiMouse, blocked split of out/r4m/split.json (73 train / 30 buffer / 45 test; test blocks A z60-74, B z100-114, C z140-154; 5-slice buffers). Config identical to R4-M/R2-M/R5-M: pix2pix, unet_256 generator, basic PatchGAN (ndf 64, n_layers 3), vanilla GAN, lambda_L1 100, lr 2e-4, 50 + 50 epochs, batch size 1, 256 x 256, preprocess none, --no_flip, CPU (Initialized with device cpu). Percentile 1/99 normalization from the 73 train slices only (same stats as prep_r4m.py).

| run | input encoding (256 x 256 RGB, input_nc 3) | seed | status |
|---|---|---|---|
| R6-M | R = G = B = PET (PET copied into all three channels) | 1234 | planned |
| R7-M | R = G = B = PET from the shuffled slice zp = 34 + ((z - 34) + 74) mod 148 (the R5-M scheme: deterministic roll by half the extent, no RNG), copied into all three channels | 1234 | planned |
| R6b-M | identical to R6-M | 4321 | planned, optional |

Seed 4321 is proposed because it differs from every seed found in the repository (1234 in out/r4m/train_r4m.py; 42 defaults in train_v1.py and digimouse_pix2pix_pipeline_test.py; R4 unseeded).

Reference runs already scored (not rerun): R4-M (PET+CT), R2-M (CT tripled), R5-M (PET+CT, PET rolled), mean-train-image baseline.

## 2. Metric lock

- PRIMARY: L1_maskv2 on all 45 test slices and on the 37 valid slices (valid rule: Addendum 2; valid per block A 7, B 15, C 15). Per block, then mean of the 3 block means. Scorers: out/r4m_audit/score_sensitivity.py (L1_maskv2 all45 / valid) and score_extra.py, unchanged.
- SECONDARY: SSIM_maskv2, PSNR_maskv2 (score_extra.py).
- Baseline: mean training cryosection image, same masks.
- No scorer, mask, valid-slice file or split file is changed for these runs. No p-values: 1 animal, 3 test blocks.

## 3. Decision rules (verbatim)

P1: R6-M below the mean-train-image baseline in 3 of 3 blocks.
P2: R6-M below R7-M in 3 of 3 blocks.
P3: absolute (R6-M minus R7-M) on the all-45 mean exceeds 2 times absolute (R6-M minus R6b-M); if R6b-M is not run, P2 is descriptive only.
P4: report the signed R6-M minus R2-M difference per block; "PET-only worse than CT-only" only if worse in 3 of 3 blocks, otherwise "no difference demonstrable".
P5: complementarity is not credited; the R4-M versus R5-M result is not reopened.

## 4. Limitations

- One animal, no tumor; within-animal, not generalizable.
- One seed per run unless R6b-M is run; seed-to-seed spread is otherwise unknown.
- The body silhouette can drive the metric (L1 inside a body mask rewards getting the outline and overall intensity right).
- PET is reconstructed at 2.2 mm on a 0.1 mm grid (stated in the project record; not re-verified in the files read for this addendum).
- R7-M donor overlap (computed from the shuffle formula and out/r4m/split.json): of the 73 train slices, 17 take PET from a test slice, 20 from a buffer slice, 36 from a train slice; of the 45 test slices, 18 take PET from another test slice and 17 from a train slice. Only PET inputs cross the split, never cryosection targets. The same holds for R5-M.
- Build and run times are not guaranteed to match earlier runs (see section 5).

## 5. Step 1 facts that remain UNVERIFIED

1. Bitwise reproducibility of CPU training (thread count, DataLoader worker seeding) was not tested; seed 1234 reproducibility of R4-M is not demonstrated.
2. The chain seed for R2-M and R5-M is read from their config.json (seed 1234, written by train_r4m.py at run time). That the training process actually applied it was not independently tested.
3. Post hoc baselines (nearest training slice, silhouette-only, intensity map): no script or result was found by a text search of the repository (excluding environments and raw data folders). Absence elsewhere is unverified.
4. Wall-clock of the new runs is an estimate from R4-M/R2-M/R5-M (about 68-73 min each on CPU, from the "Time Taken" lines); contention was not checked.
5. The 2.2 mm PET reconstruction resolution and the roughly 4 mm unexplained PET field-of-view excess in CLAUDE.md are not verified here.
6. CLAUDE.md describes the earlier ablation split (test z54-63, z94-103, z134-143; 78 train slices). The R-M runs use out/r4m/split.json (test z60-74, z100-114, z140-154; 73 train). The two descriptions differ; this addendum uses the latter.
7. out/r4m/checkpoints/<run> holds both 100_net_* and latest_net_* weights (about 436 MB per run), which differs from the CLAUDE.md rule "only the final checkpoint is saved". Consequence for disk only.
8. The pytest checks in out/r4m/test_r4m.py were not rerun for this audit; they cover only the variants petct, ct and petct_shuf and would not cover the new PET variants.
9. Whether the scorer output for R6-M/R7-M/R6b-M is comparable to R4-M/R2-M/R5-M assumes the same pix2pix code state as in commit 35cae65; code drift after that commit was not checked beyond git status showing no tracked-file change in out/r4m.
