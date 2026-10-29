#!/usr/bin/env python3
"""Step 7 panels at fixed block centres z=67,107,147. Columns: input | R4M | R2M | R5M | target | R4M abs error x4 (clipped)."""
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.dont_write_bytecode = True
R = "out/r4m/"; cols = ["input PET+CT", "R4M pred", "R2M pred", "R5M pred", "target", "R4M |err| x4"]
rows = []
for z in (67, 107, 147):
    f = f"{z:03d}.png"
    inp = np.asarray(Image.open(R + f"data/petct/test_input/{f}").convert("RGB"))[:, :256]
    tg = np.asarray(Image.open(R + f"data/test_target/{f}").convert("RGB"))
    p = {n: np.asarray(Image.open(R + f"{n}/pred/{f}").convert("RGB")) for n in ("R4M", "R2M", "R5M")}
    err = np.clip(np.abs(p["R4M"].astype(int) - tg.astype(int)) * 4, 0, 255).astype(np.uint8)
    print(z, inp.shape, tg.shape, p["R4M"].shape)
    rows.append(np.concatenate([inp, p["R4M"], p["R2M"], p["R5M"], tg, err], 1))
H = 16
img = Image.new("RGB", (256 * 6, (256 + H) * 3 + H), (255, 255, 255)); d = ImageDraw.Draw(img)
for i, c in enumerate(cols): d.text((i * 256 + 4, 2), c, fill=(0, 0, 0))
for r, (z, a) in enumerate(zip((67, 107, 147), rows)):
    y = H + r * (256 + H); d.text((4, y + 2), f"z={z}", fill=(0, 0, 0)); img.paste(Image.fromarray(a), (0, y + H))
img.save("out/r4m_audit/panels_centres.png"); print(img.size)
