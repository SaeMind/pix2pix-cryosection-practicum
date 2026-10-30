# NextBrain integrity check

Clones: `~/Data/NextBrain/Case1..5` from `https://github.com/UCL/NextBrain-Case-N.git`, `--filter=blob:none`, sparse checkout excluding `histology_hr/` (2-micron data not downloaded). Manifest: `outputs/nextbrain_manifest.csv` (SHA-256 of every checked-out file, `.git` excluded). Raw numbers: `outputs/nextbrain_verify_data.json`. Nothing in `~/Downloads` was modified.

## Clone status

| Case | ID | commit | files hashed | git fsck | git status --porcelain | LFS |
|---|---|---|---|---|---|---|
| 1 | P57-16 | `21b097d599fbeae883119c768ff7897dd438d4d2` | 7679 | clean (rc 0) | 0 lines | none (no .gitattributes) |
| 2 | P41-16 | `9c29e15e2eef6db902296f53de636d57fc5aa6a1` | 7076 | clean (rc 0) | 0 lines | none (no .gitattributes) |
| 3 | P58-16 | `a74f3a7a679df49a2cc62a15268724b4492ad9cd` | 7794 | clean (rc 0) | 0 lines | none (no .gitattributes) |
| 4 | P85-18 | `7cac312e766d603e82928845538f2a2996ec38cb` | 7344 | clean (rc 0) | 0 lines | none (no .gitattributes) |
| 5 | EX9-19 | `91c191c3deddca9ef5393349dc1d55f058599b0e` | 8034 | clean (rc 0) | 0 lines | none (no .gitattributes) |

Error-file search (`*_Error.txt`, `___All_Errors.txt`) under `~/Data/NextBrain`: 0 found.

## Counts per case (histology/*/ slices_MRI, slices_HE, slices_LFB, slices_labels_npz)

| Case | blocks | MRI | HE | LFB | labels_npz | blocks with differing counts | Diana blocks / records | match |
|---|---|---|---|---|---|---|---|---|
| 1 | 45 | 1051 | 1049 | 1049 | 1067 | 2 | 45 / 1,051 | yes |
| 2 | 40 | 942 | 942 | 942 | 942 | 0 | 40 / 942 | yes |
| 3 | 40 | 1045 | 1045 | 1045 | 1045 | 0 | 40 / 1,045 | yes |
| 4 | 41 | 1012 | 1012 | 1012 | 1012 | 0 | unrecorded | n/a (unrecorded; these are the first counts) |
| 5 | 49 | 1110 | 1110 | 1110 | 1110 | 0 | unrecorded | n/a (unrecorded; these are the first counts) |

Case 1 blocks with differing counts [MRI, HE, LFB, labels_npz]: 09: [40, 38, 38, 38]; 42: [18, 18, 18, 36]

Records = slice files in `slices_MRI` (equal to the other three folders where no mismatch is listed). Diana's sheets themselves were not compared (UNVERIFIED); only her recorded counts as given in the task.

## Image checks (20 random records per case, seed 0; all images scanned for black)

| Case | sampled records with matching MRI/HE/LFB height and width (MRI is mode L, HE and LFB are RGB, so channel count is excluded) | black MRI / HE / LFB (of total) | unreadable |
|---|---|---|---|
| 1 | 14 / 20 | 24 / 9 / 9 (of 1051 / 1049 / 1049) | 0 |
| 2 | 20 / 20 | 1 / 2 / 1 (of 942 / 942 / 942) | 0 |
| 3 | 20 / 20 | 0 / 0 / 0 (of 1045 / 1045 / 1045) | 0 |
| 4 | 20 / 20 | 0 / 18 / 0 (of 1012 / 1012 / 1012) | 0 |
| 5 | 17 / 20 | 31 / 2 / 0 (of 1110 / 1110 / 1110) | 0 |

Sampled records (size, mode, dtype):

Case 1:

| block | slice | MRI | HE | LFB | shapes match |
|---|---|---|---|---|---|
| 34 | slice_25.jpg | (212, 223) L uint8 | (212, 222) RGB uint8 | (212, 222) RGB uint8 | False |
| 37 | slice_21.jpg | (1004, 928) L uint8 | (1004, 928) RGB uint8 | (1004, 928) RGB uint8 | True |
| 05 | slice_10.jpg | (919, 624) L uint8 | (919, 624) RGB uint8 | (919, 624) RGB uint8 | True |
| 24 | slice_06.jpg | (761, 935) L uint8 | (761, 935) RGB uint8 | (761, 935) RGB uint8 | True |
| 45 | slice_35.jpg | (858, 611) L uint8 | (858, 611) RGB uint8 | (858, 611) RGB uint8 | True |
| 44 | slice_01.jpg | (885, 654) L uint8 | (885, 654) RGB uint8 | (885, 654) RGB uint8 | True |
| 36 | slice_08.jpg | (849, 630) L uint8 | (849, 630) RGB uint8 | (849, 630) RGB uint8 | True |
| 27 | slice_19.jpg | (1013, 1008) L uint8 | (1013, 1008) RGB uint8 | (1013, 1008) RGB uint8 | True |
| 43 | slice_00.jpg | (887, 610) L uint8 | (887, 610) RGB uint8 | (887, 610) RGB uint8 | True |
| 33 | slice_06.jpg | (593, 859) L uint8 | (593, 859) RGB uint8 | (593, 859) RGB uint8 | True |
| 19 | slice_10.jpg | (1013, 954) L uint8 | (1013, 954) RGB uint8 | (1013, 954) RGB uint8 | True |
| 45 | slice_21.jpg | (858, 611) L uint8 | (858, 611) RGB uint8 | (858, 611) RGB uint8 | True |
| 13 | slice_02.jpg | (375, 393) L uint8 | (374, 393) RGB uint8 | (374, 393) RGB uint8 | False |
| 25 | slice_34.jpg | (966, 837) L uint8 | (966, 837) RGB uint8 | (966, 837) RGB uint8 | True |
| 13 | slice_03.jpg | (375, 393) L uint8 | (374, 393) RGB uint8 | (374, 393) RGB uint8 | False |
| 09 | slice_13.jpg | (222, 309) L uint8 | (222, 308) RGB uint8 | (222, 308) RGB uint8 | False |
| 23 | slice_07.jpg | (939, 716) L uint8 | (939, 716) RGB uint8 | (939, 716) RGB uint8 | True |
| 13 | slice_17.jpg | (375, 393) L uint8 | (374, 393) RGB uint8 | (374, 393) RGB uint8 | False |
| 28 | slice_12.jpg | (961, 705) L uint8 | (961, 705) RGB uint8 | (961, 705) RGB uint8 | True |
| 09 | slice_21.jpg | (222, 309) L uint8 | (222, 308) RGB uint8 | (222, 308) RGB uint8 | False |

Case 2:

| block | slice | MRI | HE | LFB | shapes match |
|---|---|---|---|---|---|
| 39 | slice_00.jpg | (684, 977) L uint8 | (684, 977) RGB uint8 | (684, 977) RGB uint8 | True |
| 16 | slice_19.jpg | (201, 345) L uint8 | (201, 345) RGB uint8 | (201, 345) RGB uint8 | True |
| 36 | slice_01.jpg | (585, 863) L uint8 | (585, 863) RGB uint8 | (585, 863) RGB uint8 | True |
| 41 | slice_05.jpg | (837, 624) L uint8 | (837, 624) RGB uint8 | (837, 624) RGB uint8 | True |
| 18 | slice_02.jpg | (948, 867) L uint8 | (948, 867) RGB uint8 | (948, 867) RGB uint8 | True |
| 02 | slice_23.jpg | (845, 615) L uint8 | (845, 615) RGB uint8 | (845, 615) RGB uint8 | True |
| 11 | slice_02.jpg | (849, 580) L uint8 | (849, 580) RGB uint8 | (849, 580) RGB uint8 | True |
| 22 | slice_05.jpg | (590, 872) L uint8 | (590, 872) RGB uint8 | (590, 872) RGB uint8 | True |
| 20 | slice_13.jpg | (881, 524) L uint8 | (881, 524) RGB uint8 | (881, 524) RGB uint8 | True |
| 17 | slice_03.jpg | (850, 612) L uint8 | (850, 612) RGB uint8 | (850, 612) RGB uint8 | True |
| 41 | slice_34.jpg | (837, 624) L uint8 | (837, 624) RGB uint8 | (837, 624) RGB uint8 | True |
| 37 | slice_09.jpg | (720, 941) L uint8 | (720, 941) RGB uint8 | (720, 941) RGB uint8 | True |
| 38 | slice_20.jpg | (129, 230) L uint8 | (129, 230) RGB uint8 | (129, 230) RGB uint8 | True |
| 13 | slice_11.jpg | (840, 1024) L uint8 | (840, 1024) RGB uint8 | (840, 1024) RGB uint8 | True |
| 20 | slice_04.jpg | (881, 524) L uint8 | (881, 524) RGB uint8 | (881, 524) RGB uint8 | True |
| 15 | slice_13.jpg | (900, 949) L uint8 | (900, 949) RGB uint8 | (900, 949) RGB uint8 | True |
| 26 | slice_11.jpg | (1006, 1027) L uint8 | (1006, 1027) RGB uint8 | (1006, 1027) RGB uint8 | True |
| 41 | slice_07.jpg | (837, 624) L uint8 | (837, 624) RGB uint8 | (837, 624) RGB uint8 | True |
| 41 | slice_23.jpg | (837, 624) L uint8 | (837, 624) RGB uint8 | (837, 624) RGB uint8 | True |
| 08 | slice_13.jpg | (902, 643) L uint8 | (902, 643) RGB uint8 | (902, 643) RGB uint8 | True |

Case 3:

| block | slice | MRI | HE | LFB | shapes match |
|---|---|---|---|---|---|
| 30 | slice_13.jpg | (1069, 822) L uint8 | (1069, 822) RGB uint8 | (1069, 822) RGB uint8 | True |
| 33 | slice_11.jpg | (850, 609) L uint8 | (850, 609) RGB uint8 | (850, 609) RGB uint8 | True |
| 04 | slice_07.jpg | (985, 739) L uint8 | (985, 739) RGB uint8 | (985, 739) RGB uint8 | True |
| 21 | slice_37.jpg | (206, 360) L uint8 | (206, 360) RGB uint8 | (206, 360) RGB uint8 | True |
| 39 | slice_28.jpg | (173, 208) L uint8 | (173, 208) RGB uint8 | (173, 208) RGB uint8 | True |
| 32 | slice_18.jpg | (927, 680) L uint8 | (927, 680) RGB uint8 | (927, 680) RGB uint8 | True |
| 25 | slice_09.jpg | (1013, 738) L uint8 | (1013, 738) RGB uint8 | (1013, 738) RGB uint8 | True |
| 39 | slice_09.jpg | (173, 208) L uint8 | (173, 208) RGB uint8 | (173, 208) RGB uint8 | True |
| 28 | slice_21.jpg | (945, 744) L uint8 | (945, 744) RGB uint8 | (945, 744) RGB uint8 | True |
| 18 | slice_07.jpg | (674, 896) L uint8 | (674, 896) RGB uint8 | (674, 896) RGB uint8 | True |
| 40 | slice_27.jpg | (904, 671) L uint8 | (904, 671) RGB uint8 | (904, 671) RGB uint8 | True |
| 10 | slice_35.jpg | (1036, 1082) L uint8 | (1036, 1082) RGB uint8 | (1036, 1082) RGB uint8 | True |
| 23 | slice_07.jpg | (921, 617) L uint8 | (921, 617) RGB uint8 | (921, 617) RGB uint8 | True |
| 10 | slice_36.jpg | (1036, 1082) L uint8 | (1036, 1082) RGB uint8 | (1036, 1082) RGB uint8 | True |
| 07 | slice_21.jpg | (960, 638) L uint8 | (960, 638) RGB uint8 | (960, 638) RGB uint8 | True |
| 21 | slice_20.jpg | (206, 360) L uint8 | (206, 360) RGB uint8 | (206, 360) RGB uint8 | True |
| 11 | slice_10.jpg | (988, 717) L uint8 | (988, 717) RGB uint8 | (988, 717) RGB uint8 | True |
| 25 | slice_23.jpg | (1013, 738) L uint8 | (1013, 738) RGB uint8 | (1013, 738) RGB uint8 | True |
| 07 | slice_29.jpg | (960, 638) L uint8 | (960, 638) RGB uint8 | (960, 638) RGB uint8 | True |
| 06 | slice_18.jpg | (1010, 741) L uint8 | (1010, 741) RGB uint8 | (1010, 741) RGB uint8 | True |

Case 4:

| block | slice | MRI | HE | LFB | shapes match |
|---|---|---|---|---|---|
| 35 | slice_05.jpg | (1098, 937) L uint8 | (1098, 937) RGB uint8 | (1098, 937) RGB uint8 | True |
| 17 | slice_03.jpg | (1078, 878) L uint8 | (1078, 878) RGB uint8 | (1078, 878) RGB uint8 | True |
| 32 | slice_24.jpg | (1012, 827) L uint8 | (1012, 827) RGB uint8 | (1012, 827) RGB uint8 | True |
| 36 | slice_20.jpg | (368, 406) L uint8 | (368, 406) RGB uint8 | (368, 406) RGB uint8 | True |
| 19 | slice_05.jpg | (964, 643) L uint8 | (964, 643) RGB uint8 | (964, 643) RGB uint8 | True |
| 02 | slice_07.jpg | (737, 933) L uint8 | (737, 933) RGB uint8 | (737, 933) RGB uint8 | True |
| 11 | slice_14.jpg | (791, 826) L uint8 | (791, 826) RGB uint8 | (791, 826) RGB uint8 | True |
| 40 | slice_05.jpg | (1042, 722) L uint8 | (1042, 722) RGB uint8 | (1042, 722) RGB uint8 | True |
| 23 | slice_05.jpg | (1119, 999) L uint8 | (1119, 999) RGB uint8 | (1119, 999) RGB uint8 | True |
| 22 | slice_11.jpg | (991, 732) L uint8 | (991, 732) RGB uint8 | (991, 732) RGB uint8 | True |
| 18 | slice_06.jpg | (1024, 743) L uint8 | (1024, 743) RGB uint8 | (1024, 743) RGB uint8 | True |
| 37 | slice_11.jpg | (805, 988) L uint8 | (805, 988) RGB uint8 | (805, 988) RGB uint8 | True |
| 33 | slice_14.jpg | (973, 748) L uint8 | (973, 748) RGB uint8 | (973, 748) RGB uint8 | True |
| 34 | slice_28.jpg | (708, 968) L uint8 | (708, 968) RGB uint8 | (708, 968) RGB uint8 | True |
| 14 | slice_07.jpg | (283, 387) L uint8 | (283, 387) RGB uint8 | (283, 387) RGB uint8 | True |
| 40 | slice_08.jpg | (1042, 722) L uint8 | (1042, 722) RGB uint8 | (1042, 722) RGB uint8 | True |
| 22 | slice_02.jpg | (991, 732) L uint8 | (991, 732) RGB uint8 | (991, 732) RGB uint8 | True |
| 16 | slice_08.jpg | (942, 693) L uint8 | (942, 693) RGB uint8 | (942, 693) RGB uint8 | True |
| 26 | slice_08.jpg | (920, 615) L uint8 | (920, 615) RGB uint8 | (920, 615) RGB uint8 | True |
| 36 | slice_22.jpg | (368, 406) L uint8 | (368, 406) RGB uint8 | (368, 406) RGB uint8 | True |

Case 5:

| block | slice | MRI | HE | LFB | shapes match |
|---|---|---|---|---|---|
| 37 | slice_10.jpg | (217, 315) L uint8 | (216, 314) RGB uint8 | (216, 314) RGB uint8 | False |
| 40 | slice_08.jpg | (961, 655) L uint8 | (961, 655) RGB uint8 | (961, 655) RGB uint8 | True |
| 03 | slice_29.jpg | (1015, 1052) L uint8 | (1015, 1052) RGB uint8 | (1015, 1052) RGB uint8 | True |
| 24 | slice_04.jpg | (1010, 820) L uint8 | (1010, 820) RGB uint8 | (1010, 820) RGB uint8 | True |
| 48 | slice_02.jpg | (289, 436) L uint8 | (1049, 992) RGB uint8 | (1049, 992) RGB uint8 | False |
| 46 | slice_03.jpg | (1029, 887) L uint8 | (1029, 887) RGB uint8 | (1029, 887) RGB uint8 | True |
| 38 | slice_09.jpg | (988, 766) L uint8 | (988, 766) RGB uint8 | (988, 766) RGB uint8 | True |
| 27 | slice_04.jpg | (949, 1070) L uint8 | (949, 1070) RGB uint8 | (949, 1070) RGB uint8 | True |
| 45 | slice_17.jpg | (941, 703) L uint8 | (941, 703) RGB uint8 | (941, 703) RGB uint8 | True |
| 34 | slice_07.jpg | (993, 753) L uint8 | (993, 753) RGB uint8 | (993, 753) RGB uint8 | True |
| 20 | slice_07.jpg | (964, 719) L uint8 | (964, 719) RGB uint8 | (964, 719) RGB uint8 | True |
| 47 | slice_23.jpg | (1018, 737) L uint8 | (1018, 737) RGB uint8 | (1018, 737) RGB uint8 | True |
| 15 | slice_04.jpg | (203, 248) L uint8 | (203, 248) RGB uint8 | (203, 248) RGB uint8 | True |
| 25 | slice_09.jpg | (959, 668) L uint8 | (959, 668) RGB uint8 | (959, 668) RGB uint8 | True |
| 15 | slice_05.jpg | (203, 248) L uint8 | (203, 248) RGB uint8 | (203, 248) RGB uint8 | True |
| 10 | slice_02.jpg | (959, 654) L uint8 | (959, 654) RGB uint8 | (959, 654) RGB uint8 | True |
| 23 | slice_04.jpg | (989, 760) L uint8 | (989, 760) RGB uint8 | (989, 760) RGB uint8 | True |
| 49 | slice_11.jpg | (170, 214) L uint8 | (153, 205) RGB uint8 | (153, 205) RGB uint8 | False |
| 15 | slice_19.jpg | (203, 248) L uint8 | (203, 248) RGB uint8 | (203, 248) RGB uint8 | True |
| 28 | slice_08.jpg | (1057, 940) L uint8 | (1057, 940) RGB uint8 | (1057, 940) RGB uint8 | True |

## License search

- Case 1: LICENSE/COPYING files: NOT FOUND; license text in README.md: NOT FOUND
- Case 2: LICENSE/COPYING files: NOT FOUND; license text in README.md: NOT FOUND
- Case 3: LICENSE/COPYING files: NOT FOUND; license text in README.md: NOT FOUND
- Case 4: LICENSE/COPYING files: NOT FOUND; license text in README.md: NOT FOUND
- Case 5: LICENSE/COPYING files: NOT FOUND; license text in README.md: NOT FOUND

The READMEs link the source data repository (rdr.ucl.ac.uk, Registered histology, MRI and manual annotations of over 300 brain regions in 5 human hemispheres); its license was not checked here: UNVERIFIED. No license permitting redistribution has been confirmed for these data.

## ~/Downloads copies are partial

The copies in `~/Downloads` (`NextBrain_Case1.zip`, `NextBrain-Case-2..5.zip`, extracted `NextBrain-Case-2/`) are throttled partial downloads and must not be used. Each contains per-file `*_Error.txt` markers and a `___All_Errors.txt`.

| Case | `*_Error.txt` files in ~/Downloads copy |
|---|---|
| 1 | 5,971 |
| 2 | 56 |
| 3 | 6,932 |
| 4 | 6,621 |
| 5 | 4,912 |

Counts for cases 1, 3, 4 and 5 were taken from read-only zip listings; case 2 from both the extracted folder and its zip. ~/Downloads was not deleted or modified.
