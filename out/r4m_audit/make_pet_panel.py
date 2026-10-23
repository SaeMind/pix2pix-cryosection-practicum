#!/usr/bin/env python3
"""Preview panels for PET-only runs (Addendum 4a). usage (repo root):
  python out/r4m_audit/make_pet_panel.py --run R4M --variant petct --slices 67,107,147 --out out/r4m_audit/preview/test_R4M_panel.png [--compare R2M,R5M]
Main panel: rows = slices; columns = Input (as stored) | <run> prediction | Target | <run> |abs error| x4.
Comparison panel (only with --compare, written to <out>_compare.png): Target | <run> | each --compare run, same slices and crop.
Error definition: identical expression to out/r4m_audit/make_panels_centres.py line 14 (that file runs at import and cannot be imported):
  np.clip(np.abs(pred.astype(int) - target.astype(int)) * 4, 0, 255) on uint8 values, per pixel and channel.
GATE: for R6M / R7M / R6bM the script refuses unless out/r4m/pet_queue_status.txt shows rc=0 for that run's training, infer_score,
score_extra and score_sensitivity, and out/r4m_audit/score_extra_<run>.json and score_sensitivity_<run>.json exist. The gate is
checked before any file under out/r4m/<run> is touched. Read-only on everything except --out."""
import argparse, json, re, sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.dont_write_bytecode = True
O = Path("out/r4m"); AU = Path("out/r4m_audit")
GATED = {"R6M", "R7M", "R6bM"}
LABEL = {"R6M": "R6M (PET only)", "R7M": "R7M (PET shuffled)", "R6bM": "R6bM (PET only, seed 4321)", "R2M": "R2M (CT only)",
         "R4M": "R4M (PET+CT)", "R5M": "R5M (PET+CT, PET shuffled)"}


def gate(name):
    """Return (ok, message). Pure file checks outside out/r4m/<name>."""
    st = O / "pet_queue_status.txt"
    if not st.exists():
        return False, f"{st} missing"
    last = {}
    for l in st.read_text().splitlines():
        m = re.search(r"EXIT (\S+) (train|infer_score|score_extra|score_sensitivity)\b.* rc=(\d+)", l)
        if m:
            last[(m[1], m[2])] = int(m[3])
    need = [(name, s) for s in ("train", "infer_score", "score_extra", "score_sensitivity")]
    bad = [f"{n} {s}: " + ("no EXIT line" if (n, s) not in last else f"rc={last[(n, s)]}") for n, s in need if last.get((n, s)) != 0]
    for j in (f"score_extra_{name}.json", f"score_sensitivity_{name}.json"):
        if not (AU / j).exists():
            bad.append(f"{AU / j} missing")
    return (not bad), ("all gate conditions met" if not bad else "; ".join(bad))


def err4(pred_u8, tgt_u8):
    return np.clip(np.abs(pred_u8.astype(int) - tgt_u8.astype(int)) * 4, 0, 255).astype(np.uint8)   # == make_panels_centres.py:14


def rd(p):
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True); ap.add_argument("--variant", required=True)
    ap.add_argument("--slices", required=True); ap.add_argument("--out", required=True); ap.add_argument("--compare", default="")
    a = ap.parse_args()
    runs = [a.run] + [r for r in a.compare.split(",") if r]
    for r in runs:                                   # gate first, before any run file is opened
        if r in GATED:
            ok, msg = gate(r)
            print(f"GATE {r}: {'PASS' if ok else 'REFUSED'}: {msg}")
            if not ok:
                sys.exit(f"refusing to build a panel that opens {r} output")
        else:
            print(f"GATE {r}: not a gated run")
    zs = [int(s) for s in a.slices.split(",")]
    S = json.loads((O / "split.json").read_text()); V = json.loads((AU / "mask_valid.json").read_text())
    blk = lambda z: next(k for k, v in S["blocks"].items() if z in v)
    inval = {d["z"] for d in V["invalid"]}
    for z in zs:
        assert z in S["test"], f"z{z} is not a test slice"
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    if Path(a.out).exists():
        sys.exit(f"REFUSING to overwrite {a.out}")

    def draw(titles, getters, path, widths=None):
        fig, ax = plt.subplots(len(zs), len(titles), figsize=(2.3 * len(titles) + 0.9, 2.45 * len(zs) + 0.5), squeeze=False)
        for i, z in enumerate(zs):
            for j, g in enumerate(getters):
                ax[i, j].imshow(g(z)); ax[i, j].set_xticks([]); ax[i, j].set_yticks([])
                for s in ax[i, j].spines.values():
                    s.set_visible(False)
                if i == 0:
                    ax[i, j].set_title(titles[j], fontsize=10, fontweight="bold", ha="center")
            ax[i, 0].text(-0.06, 0.5, f"z{z}  block {blk(z)}\nmask {'invalid' if z in inval else 'valid'}", transform=ax[i, 0].transAxes,
                          ha="right", va="center", fontsize=9)
        fig.subplots_adjust(left=0.12, right=0.99, top=0.9 if len(zs) else 1, bottom=0.01, wspace=0.03, hspace=0.04)
        fig.savefig(path, dpi=300); plt.close(fig); print("wrote", path)

    tgt = lambda z: rd(O / "data" / "test_target" / f"{z:03d}.png")
    pred = lambda n: (lambda z: rd(O / n / "pred" / f"{z:03d}.png"))
    inp = lambda z: rd(O / "data" / a.variant / "test_input" / f"{z:03d}.png")      # as stored, 256 x 256 RGB
    draw(["Input", f"{LABEL.get(a.run, a.run)}\nprediction", "Target", f"{a.run} absolute\nerror x4"],
         [inp, pred(a.run), tgt, lambda z: err4(pred(a.run)(z), tgt(z))], a.out)
    if len(runs) > 1:
        cp = str(Path(a.out).with_name(Path(a.out).stem + "_compare.png"))
        if Path(cp).exists():
            sys.exit(f"REFUSING to overwrite {cp}")
        draw(["Target"] + [LABEL.get(r, r) for r in runs], [tgt] + [pred(r) for r in runs], cp)


if __name__ == "__main__":
    main()
