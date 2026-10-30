#!/usr/bin/env python3
"""Build per-slice NextBrain metadata (pre-registered in outputs/nextbrain_prereg.md).

usage: python scripts/build_nextbrain_metadata.py --root <dir with Case1..Case5> [--out outputs/nextbrain_metadata]
                                                  [--cases 1 2 3 4 5] [--config cfg.json]
A config JSON may supply {"root": ..., "out": ...}; CLI arguments win. Read-only on the data.
Records are matched by filename stem across slices_MRI, slices_HE, slices_LFB, slices_labels_npz.
"""
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image

MODS = [("MRI", "slices_MRI", ".jpg"), ("HE", "slices_HE", ".jpg"), ("LFB", "slices_LFB", ".jpg"), ("labels_npz", "slices_labels_npz", ".npz")]
COLS = ["case_id", "case_number", "block", "slice", "original_block_identifier",
        "path_MRI", "path_HE", "path_LFB", "path_labels_npz",
        "size_MRI", "mode_MRI", "size_HE", "mode_HE", "size_LFB", "mode_LFB", "sizes_match_MRI_HE_LFB",
        "correspondence_status", "is_black_MRI", "is_black_HE", "is_black_LFB", "complete_nonempty_triplet",
        "slice_spacing_um", "key_slices_for_block", "sha256_MRI", "visual_qc_status"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def probe(p):
    """-> (size 'WxH', mode, is_black) or (None, None, None) if missing/unreadable."""
    if not p.exists():
        return None, None, None
    try:
        im = Image.open(p)
        size, mode = f"{im.size[0]}x{im.size[1]}", im.mode
        return size, mode, bool(np.asarray(im).max() == 0)
    except Exception as e:  # unreadable counts as not complete
        return "UNREADABLE", str(e)[:40], None


def build_case(cdir, n):
    case_dir = next(d for d in cdir.iterdir() if d.is_dir() and (d / "histology").is_dir())
    cid = case_dir.name
    mapping = {int(r["BLOCK_NUM"]): r["BLOCK_NAME"] for r in csv.DictReader(open(case_dir / "block2slab_mapping.csv"))}
    key = json.load(open(case_dir / "histologyDimensionsKey.json"))
    rows = []
    for b in sorted(p for p in (case_dir / "histology").iterdir() if p.is_dir()):
        stems = set()
        for _, sub, ext in MODS:
            if (b / sub).is_dir():
                stems |= {f.stem for f in (b / sub).iterdir() if f.suffix == ext}
        for st in sorted(stems):
            r = dict(case_id=cid, case_number=n, block=b.name, slice=st, original_block_identifier=mapping.get(int(b.name), "UNVERIFIED"))
            miss, info = [], {}
            for m, sub, ext in MODS:
                p = b / sub / (st + ext)
                r[f"path_{m}"] = str(p.relative_to(cdir)) if p.exists() else ""
                if not p.exists():
                    miss.append(m)
                if m != "labels_npz":
                    info[m] = probe(p)
                    r[f"size_{m}"], r[f"mode_{m}"] = info[m][0] or "", info[m][1] or ""
                    r[f"is_black_{m}"] = "" if info[m][2] is None else info[m][2]
            sz = {info[m][0] for m in ("MRI", "HE", "LFB")}
            r["sizes_match_MRI_HE_LFB"] = len(sz) == 1 and None not in sz
            r["correspondence_status"] = "complete" if not miss else "missing:" + "+".join(miss)
            ok = all(info[m][2] is False for m in ("MRI", "HE", "LFB"))
            r["complete_nonempty_triplet"] = ok
            r["slice_spacing_um"] = "UNVERIFIED"   # key JSON has width/height/slices/orientation only; README gives 250 or 500 um per block class without assignment
            r["key_slices_for_block"] = key.get(str(int(b.name)), {}).get("slices", "")
            r["sha256_MRI"] = sha256(b / "slices_MRI" / (st + ".jpg")) if (b / "slices_MRI" / (st + ".jpg")).exists() else ""
            r["visual_qc_status"] = "NOT_REVIEWED"
            rows.append(r)
    return cid, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--out"); ap.add_argument("--config")
    ap.add_argument("--cases", type=int, nargs="*", default=[1, 2, 3, 4, 5])
    a = ap.parse_args()
    cfg = json.load(open(a.config)) if a.config else {}
    root = Path(a.root or cfg.get("root") or "").expanduser()
    out = Path(a.out or cfg.get("out") or "outputs/nextbrain_metadata")
    if not root.is_dir():
        raise SystemExit("need --root (or config 'root') pointing at the directory holding Case1..Case5")
    out.mkdir(parents=True, exist_ok=True)
    allrows = []
    for n in a.cases:
        cid, rows = build_case(root / f"Case{n}", n)
        with open(out / f"nextbrain_case{n}_{cid}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, COLS); w.writeheader(); w.writerows(rows)
        allrows += rows
        print(f"case {n} {cid}: {len(rows)} records -> {out}/nextbrain_case{n}_{cid}.csv")
    with open(out / "nextbrain_all_cases.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, COLS); w.writeheader(); w.writerows(allrows)
    print(f"combined: {len(allrows)} records -> {out}/nextbrain_all_cases.csv")


if __name__ == "__main__":
    main()
