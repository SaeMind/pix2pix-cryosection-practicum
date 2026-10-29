# Matched-pair imaging-to-cryosection translation with Pix2Pix

Retrospective multi-dataset evaluation of Pix2Pix for translating registered imaging volumes
(CT, PET, MRI) into matched cryosection or histology-like images. This is a research code
repository for a course practicum. It is a fork of
[junyanz/pytorch-CycleGAN-and-pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix)
(BSD license, retained in `LICENSE`); the upstream README is kept at `docs/README_upstream.md`.

Nothing in this repository is clinically validated, and no result here supports a clinical claim.

## What is in the repository

| Path | Contents |
|---|---|
| `models/`, `data/`, `options/`, `util/`, `train.py`, `test.py` | Upstream Pix2Pix/CycleGAN code (the top-level `data/` directory is source code, not data) |
| `qc/` | Dataset preparation and QC scripts (`prep_d2_ablation.py`, `pet_overlay.py`, `metrics.py`, `verify_manifests.sh`) |
| `out/r4m/` | Ablation scripts: data prep, training, inference and scoring (`prep_r4m.py`, `prep_pet_variants.py`, `train_r4m.py`, `train_r4m_seed.py`, `infer_score.py`, run scripts) and the fixed split (`split.json`) |
| `out/r4m_audit/` | Metric-lock documents, hash log (`LOCK_HASHES.txt`), scoring and audit scripts, result tables |
| `fetch_datasets.sh` | Downloads dataset archives and logs SHA-256 to `datasets/manifests/` |
| `CLAUDE.md` | Project rules (split protocol, leakage rule, wording) |

Data, model weights, volumes, archives and logs are excluded by `.gitignore`.

## Datasets

| ID | Dataset | Source | License |
|---|---|---|---|
| D2 | DigiMouse (CT, PET, cryosection, atlas; one animal) | USC mouse atlas, http://neuroimage.usc.edu/mouse_atlas | CC BY-SA 4.0, per the LICENSE.txt shipped in the D2 zips (read on disk; the authors' own terms page is UNVERIFIED) |
| D1 | Virtual Mouse Brain | Dryad, doi:10.5061/dryad.1vhhmgqv8 | UNVERIFIED |
| - | Blockface imaging and other local archives referenced by early scripts | Local | UNVERIFIED |

D1 and D2 are pipeline-development sets, not forecasting training sets. D2 contains a single
animal, so every D2 result is within-animal and does not generalize. Atlas labels are never used
as an input channel.

No data are redistributed here. Obtain each dataset from its source and check its license yourself.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`environment.yml` is the upstream conda environment and is unchanged. The versions in
`requirements.txt` were read from the local `pix2pix_env` environment; they were not tested on
another machine (UNVERIFIED).

## How to run

All commands are run from the repository root. Paths inside the scripts are relative to it.

```bash
# 1. Fetch D2 archives and log SHA-256 (use ROOT=/path/to/datasets to relocate)
ROOT=./datasets ./fetch_datasets.sh priority

# 2. Prepare the ablation data and the fixed blocked split
python qc/prep_d2_ablation.py --write
python out/r4m/prep_r4m.py
python out/r4m/prep_pet_variants.py

# 3. Train and score one run: <name> <variant> <n>
python out/r4m/train_r4m.py R2M ct 3
python out/r4m/infer_score.py R2M ct 3
```

`out/r4m/run_all.sh` and `out/r4m/run_pet_queue.sh` show the full run order. The exact variants
and arguments for each run are defined in those scripts and in `out/r4m_audit/METRIC_LOCK*.md`.
I did not execute these commands as part of preparing this repository for upload (UNVERIFIED
that they run end to end on a clean checkout).

## Evaluation protocol

- Blocked, interleaved split by slice with gaps between train and test blocks; never random slice splits.
- Percentile normalization uses training slices only.
- Metric definitions and decision rules were fixed in the `METRIC_LOCK*.md` files and hashed in
  `out/r4m_audit/LOCK_HASHES.txt` before the corresponding results were generated.
- No significance claims are made (n = 1 animal).

## Known limitations

- One animal (D2); results are within-animal and not generalizable.
- D1 and D2 are not longitudinal and not tumor data; they validate the pipeline only.
- Some audit scripts import `pairverify`, which lives in a separate clone and is not in this repository.
- Licenses for D1 and other local archives are unverified; license for this project's own code is TBD (see `LICENSE_PROJECT_TBD.md`).
- Reported numbers come from single training runs per condition plus the replicates listed in the audit files.
- No clinical validation of any kind.
