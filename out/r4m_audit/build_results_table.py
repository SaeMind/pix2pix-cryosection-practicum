#!/usr/bin/env python3
"""Step 4 table. Reads score_extra_<N>.json, score_sensitivity_<N>.json, out/r4m/<N>/metrics.json (chain). No interpretation."""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
A = Path("out/r4m_audit"); names = ["R4M", "R2M", "R5M"]
rows = []
def row(label, ex, se, ch):
    return {"row": label, "L1_maskv2_all45": se["L1_maskv2_all45"]["mean_of_block_means"], "L1_maskv2_valid": se["L1_maskv2_valid_only"]["mean_of_block_means"],
            "L1_body": ex["mean"]["L1_body"], "L1_fov_chain": ch["mean"]["L1_fov"], "L1_full": ex["mean"]["L1_full"],
            "PSNR_maskv2": ex["mean"]["PSNR_maskv2"], "SSIM_maskv2": ex["mean"]["SSIM_maskv2"],
            "PSNR_full_chain": ch["mean"]["PSNR"], "SSIM_full_chain": ch["mean"]["SSIM"],
            "L1_maskv2_A": ex["blocks"]["A"]["L1_maskv2"], "L1_maskv2_B": ex["blocks"]["B"]["L1_maskv2"], "L1_maskv2_C": ex["blocks"]["C"]["L1_maskv2"]}
for n in names:
    ex = json.load(open(A / f"score_extra_{n}.json")); se = json.load(open(A / f"score_sensitivity_{n}.json"))
    ch = json.load(open(Path("out/r4m") / n / "metrics.json"))
    rows.append(row(n, ex["model"], se["model"], ch["model"]))
    if n == "R4M":
        base = row("baseline_mean_train_cryo", ex["baseline_mean_train_cryo"], se["baseline_mean_train_cryo"], ch["baseline_mean_train_cryo"])
rows.append(base)
cols = [k for k in rows[0] if k != "row"]
md = "# Results table (mean of 3 block means; no interpretation)\n\n| row | " + " | ".join(cols) + " |\n|" + "---|" * (len(cols) + 1) + "\n"
for r in rows: md += f"| {r['row']} | " + " | ".join(f"{r[c]:.5f}" for c in cols) + " |\n"
md += "\nL1_fov_chain, PSNR_full_chain, SSIM_full_chain: chain metrics.json (PSNR/SSIM unmasked). Others: score_extra.py / score_sensitivity.py. 1 animal, 3 blocks, no p-values; within-animal, not generalizable.\n"
(A / "results_table.md").write_text(md); (A / "results_table.json").write_text(json.dumps(rows, indent=1)); print(md)
