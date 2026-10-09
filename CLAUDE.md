{\rtf1\ansi\ansicpg1252\cocoartf2907
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 # Practicum: Pix2Pix development (Stage 0)\
\
## Scope\
- Capstone: multi-dataset Pix2Pix forecasting of future brain tumor MRI from prior scans (due Dec 17, 2026).\
- D1 (Virtual Mouse Brain, Dryad doi:10.5061/dryad.1vhhmgqv8) and D2 (DigiMouse) are Stage 0 pipeline-development sets, NOT forecasting training sets. They are not longitudinal and not tumor data. D2 is n=1.\
\
## Rules\
- Raw archives are read-only after checksum. Never modify files in */raw.\
- Log SHA-256 for every download in datasets/manifests/.\
- Splits: blocked and interleaved by slice (train 20, gap 5, test 10, gap 5). Never random slice splits. Report that D2 results are within-animal, not generalizable.\
- Do NOT use the atlas labels as an input channel (leakage).\
- Wording: "retrospective multi-dataset evaluation"; never "clinically validated".\
- Mark anything unverified as unverified.\
\
## Released (Andrew, Oct 8, 2026)
- The CT+PET ablation (R1, R2, R4, R5; R3 optional) is released to run tonight. Exit condition 1 (Diana's metadata) is waived for D2: its content is SHA-256-identical to the official USC zips.
- Gates still in force, in order: (a) R1 runs first under the blocked split; (b) Andrew reviews the PET/CT-to-cryosection overlays before any run launches.
- Splits: blocked (train 20, gap 5, test 10, gap 5), fixed once, never revised after seeing test results. Percentile normalization uses training slices only.
- No significance claims: only 5 test blocks. Report per-block values and sign consistency.
- Atlas labels are never an input channel.
- Disk: keep at least 20 GB free. Only the final checkpoint is saved. Do not extract MRI_C57_data.zip or MRI_Shiverer.zip in full.