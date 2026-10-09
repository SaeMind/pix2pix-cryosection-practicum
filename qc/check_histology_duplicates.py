#!/usr/bin/env python3
"""SHA-256 of every .img inside the D1 histology archives, grouped by hash,
plus pairwise Pearson r for MBP and NF volumes. Nothing is extracted."""
import hashlib, io, itertools, zipfile
from pathlib import Path
import numpy as np
import nibabel as nib

RAW = Path("datasets/D1_virtual_mouse_brain/raw")


def sha(z, info):
    h = hashlib.sha256()
    with z.open(info) as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(z, base):
    fm = {"header": nib.FileHolder(fileobj=io.BytesIO(z.read(base + ".hdr"))),
          "image": nib.FileHolder(fileobj=io.BytesIO(z.read(base + ".img")))}
    return np.squeeze(nib.AnalyzeImage.from_file_map(fm).get_fdata(dtype=np.float32))


for name in ("MBP_to_MRI.zip", "NF_to_MRI.zip", "Nissl_to_MRI.zip"):
    with zipfile.ZipFile(RAW / name) as z:
        imgs = [i for i in z.infolist() if i.filename.endswith(".img")]
        groups = {}
        for i in imgs:
            groups.setdefault(sha(z, i), []).append((i.filename, i.file_size))
        print(f"\n{name}: {len(imgs)} .img files, {len(groups)} distinct hashes")
        for h, members in groups.items():
            print(f"  {h[:12]}  " + " | ".join(f"{n} ({s})" for n, s in members))
        if name != "Nissl_to_MRI.zip":
            bases = [i.filename[:-4] for i in imgs]
            vols = {b: load(z, b).ravel() for b in bases}
            for a, b in itertools.combinations(bases, 2):
                r = np.corrcoef(vols[a], vols[b])[0, 1]
                print(f"  r={r:.4f}  {Path(a).name} vs {Path(b).name}")
