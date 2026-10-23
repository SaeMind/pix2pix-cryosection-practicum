# Slide 9 and 10 values (descriptive; mean absolute pixel difference, 0-255 scale; edge detail = gradient ratio pred/target)

Runs used: R4M, R2M, R5M, R6M. Slices z67, z107, z147 (block centres). Within-animal, one animal; no scoring, no significance claim.

## Slide 9: pairwise mean absolute pixel difference, mean over z67, z107, z147

| | R4M | R2M | R5M | R6M | target |
|---|---|---|---|---|---|
| R4M | - | 4.75 | 5.53 | 6.16 | 10.54 |
| R2M | 4.75 | - | 5.29 | 6.89 | 11.14 |
| R5M | 5.53 | 5.29 | - | 7.07 | 10.96 |
| R6M | 6.16 | 6.89 | 7.07 | - | 10.78 |
| target | 10.54 | 11.14 | 10.96 | 10.78 | - |

## Slide 9: per slice

| pair | z67 | z107 | z147 | mean of 3 |
|---|---|---|---|---|
| R4M vs R2M | 5.62 | 4.56 | 4.07 | 4.75 |
| R4M vs R5M | 5.69 | 5.53 | 5.37 | 5.53 |
| R4M vs R6M | 6.95 | 5.72 | 5.83 | 6.16 |
| R4M vs target | 12.26 | 9.46 | 9.90 | 10.54 |
| R2M vs R5M | 5.49 | 4.95 | 5.42 | 5.29 |
| R2M vs R6M | 7.98 | 6.32 | 6.37 | 6.89 |
| R2M vs target | 13.21 | 9.90 | 10.30 | 11.14 |
| R5M vs R6M | 7.98 | 6.73 | 6.49 | 7.07 |
| R5M vs target | 13.29 | 10.97 | 8.62 | 10.96 |
| R6M vs target | 12.90 | 10.19 | 9.23 | 10.78 |

## Slide 9 SENSITIVITY: mean over all 45 test slices

| pair | mean over 45 slices |
|---|---|
| R4M vs R2M | 4.56 |
| R4M vs R5M | 5.16 |
| R4M vs R6M | 5.87 |
| R4M vs target | 9.78 |
| R2M vs R5M | 4.95 |
| R2M vs R6M | 6.55 |
| R2M vs target | 10.41 |
| R5M vs R6M | 6.60 |
| R5M vs target | 10.15 |
| R6M vs target | 9.93 |

## Slide 10: edge detail (mean luminance gradient magnitude of prediction / of target, whole tile)

| run | z67 | z107 | z147 | mean of 3 |
|---|---|---|---|---|
| R4M | 0.786 | 0.793 | 0.799 | 0.793 |
| R2M | 0.705 | 0.709 | 0.719 | 0.711 |
| R5M | 0.798 | 0.811 | 0.813 | 0.807 |
| R6M | 0.829 | 0.817 | 0.844 | 0.830 |

R6M vs R6bM: not available (R6bM missing).
