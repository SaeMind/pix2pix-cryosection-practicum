# NextBrain image-size audit

Scope: complete nonempty triplets from `outputs/nextbrain_metadata/nextbrain_all_cases.csv` (5,072 records). Image headers only (PIL `Image.open(...).size`, no pixel loading), by `scripts/nextbrain_shape_audit.py --root ~/Data/NextBrain`; per-record data in `outputs/nextbrain_shape_audit.json`. No DigiMouse file was read; no data or split was modified.

dH and dW are height and width differences in pixels. Pair A = MRI vs HE; pair B = HE vs LFB.

## Per case, pair A (MRI vs HE)

| case | records | dH=dW=0 | max abs dH | max abs dW | 0 | 1 | 2 | 3-5 | 6-10 | >10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 (P57-16) | 1018 | 872 | 1 | 1 | 872 | 146 | 0 | 0 | 0 | 0 |
| 2 (P41-16) | 938 | 938 | 0 | 0 | 938 | 0 | 0 | 0 | 0 | 0 |
| 3 (P58-16) | 1045 | 1045 | 0 | 0 | 1045 | 0 | 0 | 0 | 0 | 0 |
| 4 (P85-18) | 994 | 956 | 608 | 421 | 956 | 0 | 0 | 0 | 0 | 38 |
| 5 (EX9-19) | 1077 | 1001 | 556 | 760 | 1001 | 42 | 0 | 0 | 0 | 34 |

## Per case, pair B (HE vs LFB)

| case | records | dH=dW=0 | max abs dH | max abs dW | 0 | 1 | 2 | 3-5 | 6-10 | >10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 (P57-16) | 1018 | 1018 | 0 | 0 | 1018 | 0 | 0 | 0 | 0 | 0 |
| 2 (P41-16) | 938 | 938 | 0 | 0 | 938 | 0 | 0 | 0 | 0 | 0 |
| 3 (P58-16) | 1045 | 1045 | 0 | 0 | 1045 | 0 | 0 | 0 | 0 | 0 |
| 4 (P85-18) | 994 | 994 | 0 | 0 | 994 | 0 | 0 | 0 | 0 | 0 |
| 5 (EX9-19) | 1077 | 1077 | 0 | 0 | 1077 | 0 | 0 | 0 | 0 | 0 |

HE vs LFB are identical in size in all 5,072 records. All differences come from the MRI image.

## 20 worst records by max(abs dH, abs dW)

| case | block | slice | MRI (W x H) | HE (W x H) | LFB (W x H) | max diff MRI-HE | max diff HE-LFB | MRI path (relative to `~/Data/NextBrain/CaseN/`) |
|---|---|---|---|---|---|---|---|---|
| 5 | 48 | slice_00 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_00.jpg` |
| 5 | 48 | slice_01 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_01.jpg` |
| 5 | 48 | slice_02 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_02.jpg` |
| 5 | 48 | slice_03 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_03.jpg` |
| 5 | 48 | slice_04 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_04.jpg` |
| 5 | 48 | slice_05 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_05.jpg` |
| 5 | 48 | slice_06 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_06.jpg` |
| 5 | 48 | slice_07 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_07.jpg` |
| 5 | 48 | slice_08 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_08.jpg` |
| 5 | 48 | slice_09 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_09.jpg` |
| 5 | 48 | slice_10 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_10.jpg` |
| 5 | 48 | slice_11 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_11.jpg` |
| 5 | 48 | slice_12 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_12.jpg` |
| 5 | 48 | slice_13 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_13.jpg` |
| 5 | 48 | slice_14 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_14.jpg` |
| 5 | 48 | slice_15 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_15.jpg` |
| 5 | 48 | slice_16 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_16.jpg` |
| 5 | 48 | slice_17 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_17.jpg` |
| 5 | 48 | slice_18 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_18.jpg` |
| 5 | 48 | slice_19 | 289x436 | 1049x992 | 1049x992 | 760 | 0 | `EX9-19/histology/48/slices_MRI/slice_19.jpg` |

## Possible misalignment (any record over 10 pixels)

72 records exceed 10 pixels, all in two whole blocks:

| case | block | records | MRI (W x H) | HE (W x H) | MRI aspect W/H | HE aspect W/H | role in fold 3 |
|---|---|---|---|---|---|---|---|
| 4 (P85-18) | 28 | 38 | 754x1036 | 333x428 | 0.728 | 0.778 | val |
| 5 (EX9-19) | 48 | 34 | 289x436 | 1049x992 | 0.663 | 1.057 | train |

Both blocks are flagged as POSSIBLE MISALIGNMENT. In Case 5 block 48 the MRI and HE aspect ratios differ strongly (0.663 vs 1.058), so the images are not the same field of view at different scales. In Case 4 block 28 the ratios are closer (0.728 vs 0.778) but the MRI is 2.3x larger. Whether the content is aligned is UNVERIFIED (no image was viewed). The other mismatches are 1 pixel only (Case 1: 146 records; Case 5: 42 records), which are rounding-level.

## Resize rule recommended for equal-sized training pairs (not implemented)

1. For each record, resample the MRI to the H&E grid (`size = HE.size`) with bilinear interpolation. The LFB needs no resampling because it already equals the HE size in every record.
2. Then scale the pair with aspect preserved so the longer side is 256 (bilinear) and center-pad with zeros to 256x256, as in `outputs/nextbrain_prereg.md`. The tissue mask is the resampled MRI > 0.
3. For the 1-pixel cases step 1 is a scale change of about 0.1 to 0.5 percent and is effectively lossless. It must not be applied silently to the two flagged blocks: forcing a 289x436 MRI onto a 1049x992 grid would distort it anisotropically.
4. The two flagged blocks need a decision before training (visual QC, then exclude or correct). That would be a change to the inclusion rule and therefore needs a dated addendum to the pre-registration; it has not been made. Until then the baselines in `outputs/nextbrain_baselines.md` include these blocks (the baselines resized each modality independently and did not use this rule).

## Licensing safeguard (git)

Checked in `~/Documents/.../pytorch-CycleGAN-and-pix2pix` on 2026-10-29 with `git ls-files` and `git log --all --name-only` (refs: master, origin/dev, origin/master, origin/pytorch0.3.1, private-origin/master):

- Tracked files matching .jpg/.jpeg/.png/.npz/.nii/.tif or the string NextBrain: only the upstream `imgs/edges2cats.jpg`.
- Any path in any history containing NextBrain, a case ID (P57-16, P41-16, P58-16, P85-18, EX9-19) or a Data/NextBrain prefix: 0.
- Image paths in history besides the upstream image: the 9 DigiMouse-derived preview PNGs under `out/r4m_audit/preview/` (already reported; removed from the index in commit `5ddaa9a` but still in earlier commits). None is NextBrain.
- Not matched by the filter but upstream: `imgs/horse2zebra.gif` (extension .gif).
- The private remote `private-origin/master` is at `5ddaa9a`, same as local; it contains no NextBrain path.
- Untracked NextBrain-derived working files that must stay out of git: `outputs/nextbrain_*` (ignored via `outputs/`) and `splits/nextbrain_fold*.json` (NOT ignored; they hold record ids and MRI SHA-256 values, not images). `scripts/*nextbrain*.py` are untracked code. Nothing was committed in this task.

Licence statements in the README section were supplied in the task. That the article is CC BY-NC-ND 4.0 and that the quoted data-record field belongs to the dataset were not verified by me: UNVERIFIED.
