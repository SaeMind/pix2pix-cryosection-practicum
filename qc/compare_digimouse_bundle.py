"""Compare Digimouse_Cryosection.zip against the official USC D2 zips by SHA-256.

Extracts both sides to a temp dir outside the repo (never into raw/), compares by
relative file name after dropping the bundle prefix and collapsing doubled nesting
(atlas/atlas -> atlas), then deletes the temp dir. Inputs are not modified.

usage: python -I qc/compare_digimouse_bundle.py BUNDLE_ZIP RAW_DIR
exit 0 only if every file is identical and none is one-sided.
"""
import hashlib, os, shutil, sys, tempfile, zipfile

NAMES = ["atlas", "cryo_data", "ct_data", "pet_data"]


def sha256(path):
    m = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            m.update(b)
    return m.hexdigest()


def walk(root, strip_bundle):
    out = {}
    for dp, _, fs in os.walk(root):
        for fn in fs:
            p = os.path.join(dp, fn)
            parts = os.path.relpath(p, root).split(os.sep)
            if strip_bundle and parts[0] == "Digimouse_Cryosection":
                parts = parts[1:]
            if len(parts) > 1 and parts[0] == parts[1]:
                parts = parts[1:]
            out["/".join(parts)] = sha256(p)
    return out


def main(bundle, raw):
    tmp = tempfile.mkdtemp(prefix="d2cmp_")
    try:
        zipfile.ZipFile(bundle).extractall(os.path.join(tmp, "bundle"))
        for n in NAMES:
            zipfile.ZipFile(os.path.join(raw, n + ".zip")).extractall(os.path.join(tmp, "official"))
        b = walk(os.path.join(tmp, "bundle"), True)
        o = walk(os.path.join(tmp, "official"), False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    both = set(b) & set(o)
    diff = sorted(k for k in both if b[k] != o[k])
    bo, oo = sorted(set(b) - set(o)), sorted(set(o) - set(b))
    print(f"compared={len(both)} identical={len(both) - len(diff)} differing={len(diff)} "
          f"bundle_only={len(bo)} official_only={len(oo)}")
    for label, xs in (("differing", diff), ("bundle only", bo), ("official only", oo)):
        if xs:
            print(label + ":", xs)
    return 0 if not (diff or bo or oo) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
