#!/usr/bin/env python3
"""Results table and mechanical Addendum 4 rules. usage (repo root): python out/r4m/build_results_table_pet.py [--out PATH] [--dir SCORER_JSON_DIR]
Reads ONLY out/r4m_audit/score_extra_<N>.json and score_sensitivity_<N>.json (N in R4M R2M R5M R6M R7M R6bM); never the chain
metrics.json, score logs or predictions. Does not edit build_results_table.py. Missing runs are shown as n/a.
Rules are evaluated on L1_maskv2 over all 45 test slices (per block A/B/C, strict inequalities); the same comparison on the
37 valid slices is printed beside it as information. No p-values: 1 animal, 3 test blocks."""
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path("out/r4m_audit")
RUNS = ["R4M", "R2M", "R5M", "R6M", "R7M", "R6bM"]
BL = ["A", "B", "C"]
LOCKED = {"R4M": 0.06115, "R2M": 0.06580, "R5M": 0.06185, "baseline_mean_train_cryo": 0.09262}   # results_table.md, L1_maskv2_all45


def load(n):
    pe, ps = A / f"score_extra_{n}.json", A / f"score_sensitivity_{n}.json"
    if not (pe.exists() and ps.exists()):
        return None
    return json.loads(pe.read_text()), json.loads(ps.read_text())


def pull(ex, se, tag):
    e, s = ex[tag], se[tag]
    return dict(all45=s["L1_maskv2_all45"]["mean_of_block_means"], valid=s["L1_maskv2_valid_only"]["mean_of_block_means"],
                ssim=e["mean"]["SSIM_maskv2"], psnr=e["mean"]["PSNR_maskv2"],
                blk45={b: e["blocks"][b]["L1_maskv2"] for b in BL}, blkv={b: s["L1_maskv2_valid_only"]["blocks"][b] for b in BL})


def main():
    global A
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(A / "results_table_pet.md")); ap.add_argument("--dir", default=str(A)); a = ap.parse_args()
    A = Path(a.dir)
    D = {n: load(n) for n in RUNS}
    R = {n: pull(*D[n], "model") for n in RUNS if D[n]}
    base = pull(*D["R4M"], "baseline_mean_train_cryo")
    for n in R:                                    # the baseline must be the same object for every run
        b2 = pull(*D[n], "baseline_mean_train_cryo")
        assert abs(b2["all45"] - base["all45"]) < 1e-9, f"baseline differs for {n}"
    f = lambda x: f"{x:.5f}"
    L = ["# Results table, PET-only comparison (mean of 3 block means; Addendum 4)", "",
         "| row | L1_maskv2 all45 | L1_maskv2 valid37 | SSIM_maskv2 | PSNR_maskv2 | gain vs baseline A | B | C | (valid37) A | B | C |", "|" + "---|" * 11]
    for n in RUNS + ["baseline_mean_train_cryo"]:
        r = base if n.startswith("baseline") else R.get(n)
        if r is None:
            L.append(f"| {n} | n/a |" + " |" * 9); continue
        g = lambda k: [" - " if n.startswith("baseline") else f(base[k][b] - r[k][b]) for b in BL]
        L.append(f"| {n} | {f(r['all45'])} | {f(r['valid'])} | {f(r['ssim'])} | {f(r['psnr'])} | " + " | ".join(g("blk45") + g("blkv")) + " |")
    L += ["", "gain vs baseline = baseline block L1 minus run block L1 (positive = run better). Within-animal, not generalizable; no p-values.", ""]

    rules = []
    def blocks_lt(x, y, key):    # strict x < y in all 3 blocks
        d = {b: x[key][b] - y[key][b] for b in BL}
        return all(v < 0 for v in d.values()), d
    fm = lambda d: ", ".join(f"{b} {v:+.5f}" for b, v in d.items())
    if "R6M" in R:
        r6 = R["R6M"]
        ok, d = blocks_lt(r6, base, "blk45"); okv, dv = blocks_lt(r6, base, "blkv")
        rules.append(("P1", "PASS" if ok else "FAIL", f"R6M minus baseline per block (all45): {fm(d)}; valid37: {fm(dv)} -> {'PASS' if okv else 'FAIL'}"))
        if "R7M" in R:
            ok, d = blocks_lt(r6, R["R7M"], "blk45"); okv, dv = blocks_lt(r6, R["R7M"], "blkv")
            rules.append(("P2", "PASS" if ok else "FAIL", f"R6M minus R7M per block (all45): {fm(d)}; valid37: {fm(dv)} -> {'PASS' if okv else 'FAIL'}"))
        else:
            rules.append(("P2", "N/A", "R7M missing"))
        if "R6bM" in R and "R7M" in R:
            lhs, rhs = abs(r6["all45"] - R["R7M"]["all45"]), 2 * abs(r6["all45"] - R["R6bM"]["all45"])
            rules.append(("P3", "PASS" if lhs > rhs else "FAIL", f"|R6M-R7M| = {lhs:.5f} vs 2*|R6M-R6bM| = {rhs:.5f} (all45 mean)"))
        else:
            rules.append(("P3", "N/A", "R6bM or R7M missing; P2 is descriptive only"))
        if "R2M" in R:
            ok_w, d = blocks_lt(R["R2M"], r6, "blk45")      # PET-only worse = R6M L1 higher than R2M in every block
            claim = "PET-only worse than CT-only" if ok_w else "no difference demonstrable"
            rules.append(("P4", "N/A", f"descriptive rule; signed R6M minus R2M per block (all45): {fm({b: -v for b, v in d.items()})} -> \"{claim}\""))
        else:
            rules.append(("P4", "N/A", "R2M missing"))
    else:
        rules += [(p, "N/A", "R6M missing") for p in ("P1", "P2", "P3", "P4")]
    rules.append(("P5", "N/A", "standing rule: complementarity is not credited; R4-M versus R5-M not reopened"))
    L += ["## Addendum 4 rules (mechanical)", ""] + [f"- {p}: **{s}**: {t}" for p, s, t in rules]
    Path(a.out).write_text("\n".join(L) + "\n"); print("\n".join(L))

    print("\n## Reproduction check against locked L1_maskv2 all45 (5 decimals)")
    ok_all = True
    for n, want in LOCKED.items():
        got = base["all45"] if n.startswith("baseline") else (R[n]["all45"] if n in R else None)
        if got is None:
            print(f"{n:26s} missing"); ok_all = False; continue
        same = f"{got:.5f}" == f"{want:.5f}"; ok_all &= same
        print(f"{n:26s} computed {got:.5f}  locked {want:.5f}  {'OK' if same else 'MISMATCH'}")
    print("REPRODUCTION", "OK" if ok_all else "FAILED")


if __name__ == "__main__":
    main()
