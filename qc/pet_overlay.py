#!/usr/bin/env python3
"""qc/pet_overlay.py: PET alignment check against CT and cryosection.
Uses the winning flags (ud=0, lr=0, zrev=0). Output: qc/overlays_pet/"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, "qc")
import prep_d2_ablation as P

ct = P.load_vol(P.EXT / "ct_data")
pet = P.load_vol(P.EXT / "pet_data")
cryo = P.load_cryo(P.EXT / "cryo_data")
out = Path("qc/overlays_pet")
out.mkdir(parents=True, exist_ok=True)
lo, hi = np.percentile(pet, [1, 99.5])

for z in (10, 40, 80, 110, 140, 170, 195):
    p8 = P.norm_u8(P.ct_slice(pet, z, True), lo, hi)
    c = P.ct_slice(ct, z, True)
    c8 = P.norm_u8(c, *np.percentile(c, [1, 99]))
    g = cryo[z]
    heat = np.stack([p8, p8 // 3, np.zeros_like(p8)], -1).astype(np.float32)
    pet_on_ct = np.clip(np.stack([c8] * 3, -1) * 0.7 + heat * 0.9, 0, 255).astype(np.uint8)
    pet_on_cryo = np.clip(g * 0.6 + heat * 0.9, 0, 255).astype(np.uint8)
    panel = np.concatenate([g, np.stack([p8] * 3, -1), pet_on_ct, pet_on_cryo], 1)
    Image.fromarray(panel).save(out / f"pet_overlay_z{z:03d}.png")
    print("wrote", out / f"pet_overlay_z{z:03d}.png")
