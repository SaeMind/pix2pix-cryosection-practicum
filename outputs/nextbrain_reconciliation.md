# NextBrain count reconciliation

| Case | blocks (ours / recorded) | records with MRI file (ours / recorded) | records, union of 4 folders (ours) | complete nonempty triplets (ours / recorded) | status |
|---|---|---|---|---|---|
| 1 | 45 / 45 | 1051 / 1,051 | 1069 | 1018 / 1,018 | match |
| 2 | 40 / 40 | 942 / 942 | 942 | 938 / 938 | match |
| 3 | 40 / 40 | 1045 / 1,045 | 1045 | 1045 / 1,045 | match |
| 4 | 41 / unrecorded | 1012 / unrecorded | 1012 | 994 / unrecorded | first counts |
| 5 | 49 / unrecorded | 1110 / unrecorded | 1110 | 1077 / unrecorded | first counts |

Recorded counts are the collaborator's, as given in the task. Records not complete-nonempty are listed with block and slice:

Case 1: 51 records not complete-nonempty. Reasons: {'black:HE+LFB': 7, 'missing:HE+LFB+labels_npz': 2, 'black:MRI': 22, 'black:MRI+HE+LFB': 2, 'missing:MRI+HE+LFB': 18}
Block/slice: 09/slice_00 (black:HE+LFB); 09/slice_38 (missing:HE+LFB+labels_npz); 09/slice_39 (missing:HE+LFB+labels_npz); 15/slice_00 (black:MRI); 15/slice_01 (black:MRI); 15/slice_02 (black:MRI); 15/slice_03 (black:MRI); 15/slice_04 (black:MRI); 15/slice_05 (black:MRI); 15/slice_06 (black:MRI); 15/slice_07 (black:MRI); 15/slice_08 (black:MRI); 15/slice_09 (black:MRI); 15/slice_10 (black:MRI); 15/slice_11 (black:MRI); 15/slice_12 (black:MRI); 15/slice_13 (black:MRI); 15/slice_14 (black:MRI); 15/slice_15 (black:MRI); 15/slice_16 (black:MRI); 15/slice_17 (black:MRI); 15/slice_18 (black:MRI); 15/slice_19 (black:MRI); 15/slice_20 (black:MRI); 15/slice_21 (black:MRI); 34/slice_00 (black:MRI+HE+LFB); 34/slice_01 (black:MRI+HE+LFB); 34/slice_02 (black:HE+LFB); 34/slice_03 (black:HE+LFB); 34/slice_04 (black:HE+LFB); 34/slice_05 (black:HE+LFB); 34/slice_06 (black:HE+LFB); 34/slice_07 (black:HE+LFB); 42/slice_18 (missing:MRI+HE+LFB); 42/slice_19 (missing:MRI+HE+LFB); 42/slice_20 (missing:MRI+HE+LFB); 42/slice_21 (missing:MRI+HE+LFB); 42/slice_22 (missing:MRI+HE+LFB); 42/slice_23 (missing:MRI+HE+LFB); 42/slice_24 (missing:MRI+HE+LFB); 42/slice_25 (missing:MRI+HE+LFB); 42/slice_26 (missing:MRI+HE+LFB); 42/slice_27 (missing:MRI+HE+LFB); 42/slice_28 (missing:MRI+HE+LFB); 42/slice_29 (missing:MRI+HE+LFB); 42/slice_30 (missing:MRI+HE+LFB); 42/slice_31 (missing:MRI+HE+LFB); 42/slice_32 (missing:MRI+HE+LFB); 42/slice_33 (missing:MRI+HE+LFB); 42/slice_34 (missing:MRI+HE+LFB); 42/slice_35 (missing:MRI+HE+LFB)

Case 2: 4 records not complete-nonempty. Reasons: {'black:MRI': 1, 'black:HE': 2, 'black:LFB': 1}
Block/slice: 15/slice_21 (black:MRI); 30/slice_16 (black:HE); 30/slice_17 (black:HE); 38/slice_32 (black:LFB)

Case 3: 0 records not complete-nonempty. Reasons: {}
none

Case 4: 18 records not complete-nonempty. Reasons: {'black:HE': 18}
Block/slice: 04/slice_07 (black:HE); 05/slice_35 (black:HE); 07/slice_35 (black:HE); 07/slice_36 (black:HE); 08/slice_14 (black:HE); 08/slice_15 (black:HE); 11/slice_00 (black:HE); 27/slice_00 (black:HE); 41/slice_00 (black:HE); 41/slice_01 (black:HE); 41/slice_02 (black:HE); 41/slice_03 (black:HE); 41/slice_04 (black:HE); 41/slice_05 (black:HE); 41/slice_06 (black:HE); 41/slice_07 (black:HE); 41/slice_08 (black:HE); 41/slice_09 (black:HE)

Case 5: 33 records not complete-nonempty. Reasons: {'black:HE': 2, 'black:MRI': 31}
Block/slice: 18/slice_37 (black:HE); 18/slice_38 (black:HE); 49/slice_00 (black:MRI); 49/slice_01 (black:MRI); 49/slice_02 (black:MRI); 49/slice_03 (black:MRI); 49/slice_04 (black:MRI); 49/slice_05 (black:MRI); 49/slice_06 (black:MRI); 49/slice_07 (black:MRI); 49/slice_08 (black:MRI); 49/slice_09 (black:MRI); 49/slice_10 (black:MRI); 49/slice_11 (black:MRI); 49/slice_12 (black:MRI); 49/slice_13 (black:MRI); 49/slice_14 (black:MRI); 49/slice_15 (black:MRI); 49/slice_16 (black:MRI); 49/slice_17 (black:MRI); 49/slice_18 (black:MRI); 49/slice_19 (black:MRI); 49/slice_20 (black:MRI); 49/slice_21 (black:MRI); 49/slice_22 (black:MRI); 49/slice_23 (black:MRI); 49/slice_24 (black:MRI); 49/slice_25 (black:MRI); 49/slice_26 (black:MRI); 49/slice_27 (black:MRI); 49/slice_28 (black:MRI); 49/slice_29 (black:MRI); 49/slice_30 (black:MRI)
