#!/usr/bin/env python3
"""Export single 256x256 tiles for slide use, slice z107 only. Run from repo root after the R6M gate passed:
  python out/r4m_audit/preview/export_tiles_z107.py
Predictions and target are byte copies of the existing files (no resize). Error tiles use the expression of
out/r4m_audit/make_panels_centres.py line 14. Writes only out/r4m_audit/preview/tiles/ (refuses if it exists).
Also checks r4m_err.png against the R4M error column of out/r4m_audit/panels_centres.png (z107 = second row)."""
import hashlib, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
sys.path.insert(0, "out/r4m_audit")
Z = 107
O = Path("out/r4m"); T = Path("out/r4m_audit/preview/tiles")
if T.exists():
    sys.exit(f"REFUSING: {T} exists")
f = f"{Z:03d}.png"
src = {"r4m_pred": O / "R4M/pred" / f, "r2m_pred": O / "R2M/pred" / f, "r6m_pred": O / "R6M/pred" / f, "target": O / "data/test_target" / f}
rd = lambda p: np.asarray(Image.open(p).convert("RGB"))
err = lambda p, t: np.clip(np.abs(p.astype(int) - t.astype(int)) * 4, 0, 255).astype(np.uint8)    # make_panels_centres.py:14
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
T.mkdir(parents=True)
man = []
for k, p in src.items():
    shutil.copyfile(p, T / f"{k}.png")
    assert sha(p) == sha(T / f"{k}.png")
    man.append((f"{k}.png", f"copy of {p}"))
tg = rd(src["target"])
for r in ("r4m", "r2m", "r6m"):
    Image.fromarray(err(rd(src[f"{r}_pred"]), tg)).save(T / f"{r}_err.png")
    man.append((f"{r}_err.png", f"derived: clip(|{src[f'{r}_pred']} - {src['target']}| * 4, 0, 255), as make_panels_centres.py:14"))
for n in T.glob("*.png"):
    a = Image.open(n); assert a.size == (256, 256) and a.mode == "RGB", n
ref = np.asarray(Image.open("out/r4m_audit/panels_centres.png").convert("RGB"))
y = 16 + 1 * 272 + 16                                  # header 16, row 1 (z107), row label 16; error column starts x = 5*256
same = np.array_equal(ref[y:y + 256, 1280:1536], rd(T / "r4m_err.png"))
print("r4m_err.png equals panels_centres.png R4M error column for z107 pixel for pixel:", same)
(T / "MANIFEST.txt").write_text("".join(f"{sha(T / n)}  {n}  <- {s}\n" for n, s in sorted(man)))
print((T / "MANIFEST.txt").read_text())
sys.exit(0 if same else 1)
