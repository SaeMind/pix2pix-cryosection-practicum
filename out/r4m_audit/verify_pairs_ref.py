#!/usr/bin/env python3
"""Verify that a dataset's input/target files form matched pairs.

    python verify_pairs.py --dataset digimouse --root /data/digimouse

Writes <out>/pairs.csv and <out>/summary.json, prints one PASS/FAIL line, and
exits 0 on PASS, 1 on FAIL, 2 on usage/config errors.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pairverify.adapters import ADAPTERS, ALIASES, REGISTRATION_STATES, get_adapter
import numpy as np

from pairverify.core import (Config, PET_COLUMNS, SPATIAL_COLUMNS, apply_threshold, verify_pair, write_pairs_csv)
from pairverify.qc import write_overlays
from pairverify.rigid import RigidOpts
from pairverify.spatial import SpatialOpts, run_spatial
from pairverify.spatial3 import V03Opts, run_v03
from pairverify.atlas_checks import V04Opts, run_v04

log = logging.getLogger("verify_pairs")
LICENSE_FILE = "LICENSE_SOURCE.txt"
LICENSE_UNSPECIFIED = "UNSPECIFIED"


def read_license(root: Path, explicit: Path | None) -> str:
    """First existing of: --license-source, <root>/LICENSE_SOURCE.txt, ./LICENSE_SOURCE.txt.
    '#' lines are comments; an empty file or one containing only TODO counts as unspecified."""
    for cand in ([explicit] if explicit else [root / LICENSE_FILE, Path(LICENSE_FILE)]):
        if cand and cand.is_file():
            lines = [l.strip() for l in cand.read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]
            keyed = [l.split(":", 1)[1].strip() for l in lines if l.upper().startswith("LICENSE:")]
            text = keyed[0] if keyed else " ".join(lines)  # a LICENSE: line wins; otherwise all non-comment text
            return LICENSE_UNSPECIFIED if not text or text.upper() == "TODO" else text
    return LICENSE_UNSPECIFIED


def _stats(vals):
    if not len(vals):
        return {"n": 0}
    v = np.asarray(vals, float)
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {"n": int(v.size), "min": round(float(v.min()), 4), "q1": round(float(q1), 4), "median": round(float(med), 4),
            "q3": round(float(q3), 4), "iqr": round(float(q3 - q1), 4), "p99": round(float(np.percentile(v, 99)), 4),
            "max": round(float(v.max()), 4)}


FIXED_COMPARISON_THRESHOLD = 1.20
STATUS_EXIT = {"PASS": 0, "FAIL": 1, "WARN": 4}


def run_v04_mode(adapter, specs, layout, root, out, cfg, license_source, o: V04Opts, atlas_dir: Path | None) -> dict:
    """v0.4 path (digimouse): atlas-based checks T1-T4 with pre-registered gates A, B, C."""
    out.mkdir(parents=True, exist_ok=True)
    atlas_path = next(iter(sorted((atlas_dir or root / "atlas_data").glob("*.hdr"))), None)
    if atlas_path is None:
        raise ValueError(f"no atlas .hdr found in {atlas_dir or root / 'atlas_data'}")
    info = run_v04(specs[0], cfg, o, atlas_path, out)
    keep = [k for k in info if k not in ("criteria", "scope")]
    summary = {
        "dataset": adapter.name, "root": str(root), "version": "v0.4", "subject_count": len({s.subject_id for s in specs}),
        "registration_status": layout.registration_status, "license": read_license(root, license_source),
        "status": info.get("status", "FAIL"), "rule": info.get("criteria", []),
        "atlas_note": "atlas labels used only as a measurement reference, never as an input channel",
        **{k: info[k] for k in keep}, "unclassified_units": adapter.unclassified,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def run_v03_mode(adapter, specs, layout, root, out, cfg, license_source, o: V03Opts) -> dict:
    """v0.3 path (digimouse): wide rigid sweep per slice + volume-level z test decide status."""
    out.mkdir(parents=True, exist_ok=True)
    if len(specs) != 1:
        log.warning("v0.3 handles exactly one volume pair; %d pairs found, using the first", len(specs))
    res = run_v03(specs[0], cfg, o, out)
    rows, info = res.rows, res.info
    if "error" in info:
        write_pairs_csv(rows, out / "pairs.csv", SPATIAL_COLUMNS)
    in_scope = [r for r in rows if r.in_scope]
    verified = [r for r in in_scope if r.matched]
    fails = Counter(r.reason_if_not.split(":")[0].split(" ")[0] for r in in_scope if not r.matched)
    fmts = sorted({f for r in rows for f in (r.fmt_in, r.fmt_target) if f})
    mods = sorted({m for r in rows for m in (r.input_modality, r.target_modality)})
    keep = ("G1", "G2", "gates", "extent", "rigid", "z_volume", "masks", "nmi_descriptive", "mask_diagnostic_files", "error")
    summary = {
        "dataset": adapter.name, "root": str(root), "version": "v0.3",
        "subject_count": len({s.subject_id for s in specs}), "candidate_pair_count": len(rows),
        "in_scope_count": len(in_scope), "excluded_out_of_extent": sum(r.reason_if_not == "out_of_extent" for r in rows),
        "verified_pair_count": len(verified), "modalities": mods, "file_format": "+".join(fmts) if fmts else "unknown",
        "registration_status": layout.registration_status, "license": read_license(root, license_source),
        "status": info.get("status", "FAIL"), "rule": info.get("criteria", []),
        "failure_reasons_in_scope": dict(fails), "unclassified_units": adapter.unclassified,
        **{k: info[k] for k in keep if k in info},
        "pet": "not run in v0.3 (v0.2 pairs_pet.csv is unchanged in the v0.2 output directory)" if layout.second_input_token else None,
        "outputs": {k: v for k, v in {"pairs": "pairs.csv", "rigid_sweep": "rigid_sweep.csv", "z_curves": "z_curves.csv",
                                      "diagnostics_plot": "v03_diagnostics.png", "mask_diagnostics": "mask_diagnostics/"}.items()
                    if (out / v).exists()},
        "layout": {k: getattr(layout, k) for k in layout.__dataclass_fields__},
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def run_spatial_mode(adapter, specs, layout, root, out, cfg, license_source, opts) -> dict:
    """v0.2 path (digimouse): extent rule + Dice + offset sweep decide status; NMI is descriptive only."""
    out.mkdir(parents=True, exist_ok=True)
    if len(specs) > 1:
        log.warning("spatial mode handles one volume pair; %d pairs found, sweep files belong to the last one", len(specs))
    rows, pet_rows, info = [], [], {}
    for s in specs:
        res = run_spatial(s, cfg, opts, out)
        rows += res.rows
        pet_rows += res.pet_rows
        info = res.info
    write_pairs_csv(rows, out / "pairs.csv", SPATIAL_COLUMNS)
    if pet_rows:
        write_pairs_csv(pet_rows, out / "pairs_pet.csv", PET_COLUMNS)
    in_scope = [r for r in rows if r.in_scope]
    verified = [r for r in in_scope if r.matched]
    fails = Counter(r.reason_if_not.split(":")[0].split(" ")[0] for r in in_scope if not r.matched)
    status = info.get("status", "FAIL")
    fmts = sorted({f for r in rows + pet_rows for f in (r.fmt_in, r.fmt_target) if f})
    mods = sorted({m for r in rows + pet_rows for m in (r.input_modality, r.target_modality)})
    summary = {
        "dataset": adapter.name, "root": str(root), "version": "v0.2",
        "subject_count": len({s.subject_id for s in specs}),
        "candidate_pair_count": len(rows), "in_scope_count": len(in_scope),
        "excluded_out_of_extent": sum(r.reason_if_not == "out_of_extent" for r in rows),
        "verified_pair_count": len(verified),
        "modalities": mods, "file_format": "+".join(fmts) if fmts else "unknown",
        "registration_status": layout.registration_status, "license": read_license(root, license_source),
        "status": status, "criteria": info.get("criteria", []),
        "failure_reasons_in_scope": dict(fails), "unclassified_units": adapter.unclassified,
        "spatial": {k: v for k, v in info.items() if k not in ("criteria", "nmi_descriptive", "pet", "status")},
        "nmi_descriptive": info.get("nmi_descriptive"), "pet": info.get("pet"),
        "outputs": {"pairs": "pairs.csv", "pairs_pet": "pairs_pet.csv" if pet_rows else None,
                    "sweep_csv": "sweep.csv" if info.get("sweep") else None, "sweep_plot": "sweep.png" if info.get("sweep") else None},
        "layout": {k: getattr(layout, k) for k in layout.__dataclass_fields__},
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def run(dataset: str, root: Path, out: Path, cfg: Config, overrides: dict, license_source: Path | None = None,
        min_pass_fraction: float = 1.0, threshold_rule: str = "fixed", fail_if_indistinguishable: bool = False,
        qc_dir: Path | None = None, qc_n: int = 5, spatial_opts: SpatialOpts | None = None,
        spatial_version: str = "0.3", v03_opts: V03Opts | None = None, v04_opts: V04Opts | None = None,
        atlas_dir: Path | None = None) -> dict:
    adapter = get_adapter(dataset)
    specs, layout = adapter.discover(root, overrides)
    log.info("dataset=%s root=%s input_token=%r target_token=%r", adapter.name, root, layout.input_token, layout.target_token)
    log.info("NMI threshold=%s bins=%d max_grid=%d aspect_tol=%s fov_tol=%s", cfg.nmi_threshold, cfg.nmi_bins,
             cfg.max_grid, cfg.aspect_tol, cfg.fov_tol)
    for rel in adapter.unclassified:
        log.warning("unclassified (matches neither/both tokens): %s", rel)
    if adapter.spatial and spatial_version == "0.4":
        return run_v04_mode(adapter, specs, layout, root, out, cfg, license_source, v04_opts or V04Opts(), atlas_dir)
    if adapter.spatial and spatial_version == "0.3":
        return run_v03_mode(adapter, specs, layout, root, out, cfg, license_source, v03_opts or V03Opts())
    if adapter.spatial:
        return run_spatial_mode(adapter, specs, layout, root, out, cfg, license_source, spatial_opts or SpatialOpts())

    rows = []
    for s in specs:
        rows.extend(verify_pair(s, cfg))
    out.mkdir(parents=True, exist_ok=True)

    # NMI is scored for every slice first; the threshold is applied afterwards so a data-driven rule can use the scores.
    scored = [r for r in rows if r.nmi is not None]
    matched_nmi = _stats([r.nmi for r in scored])
    null_nmi = _stats([r.null_nmi for r in scored])
    chosen = cfg.nmi_threshold
    if threshold_rule == "midpoint" and scored:
        chosen = round((null_nmi["p99"] + matched_nmi["median"]) / 2, 4)
        log.info("threshold rule midpoint: (null p99 %.4f + matched median %.4f)/2 = %.4f", null_nmi["p99"],
                 matched_nmi["median"], chosen)
    apply_threshold(rows, chosen)
    indistinguishable = bool(scored) and matched_nmi["median"] <= null_nmi["p99"]
    if indistinguishable:
        log.error("matched NMI median %.4f <= rolled-null p99 %.4f: pairs indistinguishable from null",
                  matched_nmi["median"], null_nmi["p99"])
    write_pairs_csv(rows, out / "pairs.csv")

    verified = [r for r in rows if r.matched]
    fmts = sorted({f for r in rows for f in (r.fmt_in, r.fmt_target) if f})
    mods = sorted({m for r in rows for m in (r.input_modality, r.target_modality)})
    reasons = Counter(r.reason_if_not.split(":")[0].split(" ")[0] for r in rows if not r.matched)
    frac = len(verified) / len(rows) if rows else 0.0
    passed = bool(rows) and frac >= min_pass_fraction and not (fail_if_indistinguishable and indistinguishable)
    summary = {
        "dataset": adapter.name,
        "root": str(root),
        "subject_count": len({s.subject_id for s in specs}),
        "verified_pair_count": len(verified),
        "candidate_pair_count": len(rows),
        "modalities": mods,
        "file_format": "+".join(fmts) if fmts else "unknown",
        "registration_status": layout.registration_status,
        "license": read_license(root, license_source),
        "status": ("FAIL-INDISTINGUISHABLE" if fail_if_indistinguishable and indistinguishable
                   else "PASS" if passed else "FAIL"),
        "min_pass_fraction": min_pass_fraction,
        "failure_reasons": dict(reasons),
        "unclassified_units": adapter.unclassified,
        "nmi": {"threshold": chosen, "threshold_rule": threshold_rule + (
                    " = (rolled-null p99 + matched median) / 2" if threshold_rule == "midpoint" else ""),
                "bins": cfg.nmi_bins, "max_grid": cfg.max_grid, "aspect_tol": cfg.aspect_tol, "fov_tol": cfg.fov_tol,
                "matched_nmi": matched_nmi,  # NMI of the candidate pairs (every scored slice)
                "rolled_null_nmi": null_nmi,  # same pairs, target rolled by half a frame in both axes
                "verified_at_chosen_threshold": sum(r.nmi > chosen for r in scored),
                "verified_at_1.20": sum(r.nmi > FIXED_COMPARISON_THRESHOLD for r in scored),
                "unscored_slices": len(rows) - len(scored),
                "matched_median_exceeds_null_p99": (not indistinguishable) if scored else None,
                "verified": _stats([r.nmi for r in verified]),
                "all_scored": _stats([r.nmi for r in rows if r.nmi is not None]),
                "null_shifted_target": _stats([r.null_nmi for r in rows if r.null_nmi is not None])},
        "layout": {k: getattr(layout, k) for k in layout.__dataclass_fields__},
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if qc_dir and not indistinguishable and specs:
        first = next((s for s in specs if s.input_path and s.target_path), None)
        if first:
            summary["qc_files"] = [str(x) for x in write_overlays(first, rows, qc_dir, qc_n, cfg.mat_var)]
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True, help=f"one of {sorted(ADAPTERS)} (aliases with '-' accepted)")
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", type=Path, help="output dir (default: out/<dataset>)")
    ap.add_argument("--nmi-threshold", type=float, default=Config.nmi_threshold,
                    help="pair needs NMI strictly above this (range 1..2); default 1.20 was calibrated on synthetic "
                         "phantoms only; recalibrate on real data using null_shifted_target in summary.json")
    ap.add_argument("--nmi-bins", type=int, default=Config.nmi_bins)
    ap.add_argument("--max-grid", type=int, default=Config.max_grid)
    ap.add_argument("--aspect-tol", type=float, default=Config.aspect_tol)
    ap.add_argument("--fov-tol", type=float, default=Config.fov_tol)
    ap.add_argument("--threshold-rule", choices=("fixed", "midpoint"), default="fixed",
                    help="fixed: use --nmi-threshold; midpoint: (rolled-null p99 + matched median)/2 from this run's scores")
    ap.add_argument("--fail-if-indistinguishable", action="store_true",
                    help="print FAIL-INDISTINGUISHABLE and exit 3 (no QC overlays) if matched NMI median <= rolled-null p99")
    ap.add_argument("--qc-dir", type=Path, help="write overlay PNGs + montage here (skipped when indistinguishable)")
    ap.add_argument("--qc-n", type=int, default=5)
    ap.add_argument("--extent-cutoff", type=float, default=SpatialOpts.extent_cutoff,
                    help="digimouse: min body foreground fraction in BOTH CT and cryosection for a slice to be in scope")
    ap.add_argument("--dice-min", type=float, default=SpatialOpts.dice_min)
    ap.add_argument("--dice-marginal", type=float, default=SpatialOpts.dice_marginal)
    ap.add_argument("--sweep-z", type=int, default=SpatialOpts.sweep_z)
    ap.add_argument("--sweep-px", type=int, default=SpatialOpts.sweep_px)
    ap.add_argument("--no-sweep", action="store_true")
    ap.add_argument("--spatial-version", choices=("0.2", "0.3", "0.4"), default="0.3", help="digimouse spatial check version")
    ap.add_argument("--atlas-shift-px", type=int, default=V04Opts.shift_px)
    ap.add_argument("--atlas-shift-z", type=int, default=V04Opts.shift_z)
    ap.add_argument("--boot", type=int, default=V04Opts.boot)
    ap.add_argument("--overlay-z", default=",".join(map(str, V04Opts.overlay_z)))
    ap.add_argument("--atlas-dir", type=Path, help="v0.4: folder with the atlas .hdr/.img (default <root>/atlas_data)")
    ap.add_argument("--rigid-px", type=int, default=RigidOpts.max_px, help="v0.3 max |dx|,|dy| searched (px)")
    ap.add_argument("--rigid-deg", type=int, default=RigidOpts.max_deg, help="v0.3 max |theta| searched (deg)")
    ap.add_argument("--nmi-step-px", type=int, default=RigidOpts.nmi_step_px)
    ap.add_argument("--tol-px", type=int, default=V03Opts.tol_px)
    ap.add_argument("--tol-deg", type=float, default=V03Opts.tol_deg)
    ap.add_argument("--z-range", type=int, default=V03Opts.z_range)
    ap.add_argument("--diag-slices", help="comma-separated z list for mask diagnostic overlays")
    ap.add_argument("--second-input-token"), ap.add_argument("--second-input-modality")
    ap.add_argument("--min-pass-fraction", type=float, default=1.0,
                    help="fraction of candidate rows that must verify for PASS (default 1.0 = all)")
    ap.add_argument("--input-token"), ap.add_argument("--target-token")
    ap.add_argument("--input-modality"), ap.add_argument("--target-modality")
    ap.add_argument("--subject-regex")
    ap.add_argument("--stack-dirs", action="store_true", default=None, help="treat dirs of >=2 2D TIFFs as volumes")
    ap.add_argument("--transpose-input", action="store_true", help="swap the input's in-plane axes")
    ap.add_argument("--registration-status", choices=REGISTRATION_STATES,
                    help="what the dataset's documentation says; never inferred from the images")
    ap.add_argument("--mat-var", help="variable to read from .mat files (default: largest numeric array)")
    ap.add_argument("--license-source", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    out = a.out or Path("out") / ALIASES.get(a.dataset, a.dataset)
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(out / "verify.log", mode="w")],
                        force=True)
    if not a.root.is_dir():
        print(f"ERROR root is not a directory: {a.root}", file=sys.stderr)
        return 2
    cfg = Config(nmi_threshold=a.nmi_threshold, nmi_bins=a.nmi_bins, max_grid=a.max_grid,
                 aspect_tol=a.aspect_tol, fov_tol=a.fov_tol, mat_var=a.mat_var)
    overrides = dict(input_token=a.input_token, target_token=a.target_token, input_modality=a.input_modality,
                     target_modality=a.target_modality, subject_regex=a.subject_regex, stack_dirs=a.stack_dirs,
                     registration_status=a.registration_status, transpose_input=True if a.transpose_input else None,
                     second_input_token=a.second_input_token, second_input_modality=a.second_input_modality)
    sopts = SpatialOpts(extent_cutoff=a.extent_cutoff, dice_min=a.dice_min, dice_marginal=a.dice_marginal,
                        sweep_z=a.sweep_z, sweep_px=a.sweep_px, sweep=not a.no_sweep)
    v03 = V03Opts(extent_cutoff=a.extent_cutoff, rigid=RigidOpts(max_px=a.rigid_px, max_deg=a.rigid_deg,
                                                              nmi_step_px=a.nmi_step_px),
                  tol_px=a.tol_px, tol_deg=a.tol_deg, z_range=a.z_range,
                  diag_slices=tuple(int(x) for x in a.diag_slices.split(",")) if a.diag_slices else V03Opts.diag_slices)
    try:
        s = run(a.dataset, a.root, out, cfg, overrides, a.license_source, a.min_pass_fraction, a.threshold_rule,
                a.fail_if_indistinguishable, a.qc_dir, a.qc_n, sopts, a.spatial_version, v03, V04Opts(extent_cutoff=a.extent_cutoff, shift_px=a.atlas_shift_px, shift_z=a.atlas_shift_z, boot=a.boot,
                                    tol_px=a.tol_px, overlay_z=tuple(int(x) for x in a.overlay_z.split(","))),
                a.atlas_dir)
    except (KeyError, ValueError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    if s.get("version") == "v0.4":
        d = s.get("gate_detail", {})
        t1, t2 = s.get("T1_skeleton_vs_ct_bone", {}), s.get("T2_lungs_vs_ct_air", {})
        print(f"{s['status']} {s['dataset']} v0.4: gates {d.get('gates')}, T1 shift {t1.get('best_shift')}, T2 shift {t2.get('best_shift')}, "
              f"organs within tolerance {d.get('B_organs_within_tolerance')}, registration={s['registration_status']}, license={s['license'][:60]}")
        for line in s["rule"]:
            print("  rule:", line)
        return STATUS_EXIT[s["status"]]
    if s.get("version") == "v0.3":
        g1, g2 = s.get("G1", {}), s.get("G2", {})
        print(f"{s['status']} {s['dataset']} v0.3: G1 {g1.get('n_in_tolerance')}/{g1.get('n_in_scope')} in-scope slices within "
              f"tolerance ({g1.get('fraction_in_tolerance')}) [{s.get('gates', {}).get('G1')}], G2 volume z peak "
              f"{g2.get('volume_3d_peak_offset')} [{s.get('gates', {}).get('G2')}], {s['excluded_out_of_extent']} out_of_extent excluded, "
              f"registration={s['registration_status']}, license={s['license'][:60]}")
        for line in s["rule"]:
            print("  rule:", line)
        return STATUS_EXIT[s["status"]]
    if s.get("version") == "v0.2":
        sp, d = s["spatial"], s["spatial"].get("dice", {})
        z = sp.get("sweep", {}).get("z", {})
        print(f"{s['status']} {s['dataset']}: {s['verified_pair_count']}/{s['in_scope_count']} in-scope slices verified "
              f"({s['excluded_out_of_extent']} out_of_extent excluded), Dice median {d.get('median')} min {d.get('min')}, "
              f"z-sweep peak {z.get('peak_offset_by_mean_dice')}, registration={s['registration_status']}, "
              f"license={s['license'][:60]}")
        for line in s["criteria"]:
            print("  criteria:", line)
        return STATUS_EXIT[s["status"]]
    n = s["nmi"]
    if s["status"] == "FAIL-INDISTINGUISHABLE":
        print(f"FAIL-INDISTINGUISHABLE {s['dataset']}: matched NMI median {n['matched_nmi']['median']} <= "
              f"rolled-null p99 {n['rolled_null_nmi']['p99']}; stopped (no QC overlays)")
        return 3
    print(f"{s['status']} {s['dataset']}: {s['verified_pair_count']}/{s['candidate_pair_count']} pairs verified, "
          f"{s['subject_count']} subject(s), nmi>{n['threshold']}, registration={s['registration_status']}, "
          f"license={s['license'][:60]}")
    return 0 if s["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
