#!/usr/bin/env bash
# fetch_datasets.sh  usage: ./fetch_datasets.sh [priority|extended|full]
set -euo pipefail
MODE="${1:-priority}"
ROOT="${ROOT:-$(git rev-parse --show-toplevel)/datasets}"
D1="$ROOT/D1_virtual_mouse_brain/raw"
D2="$ROOT/D2_digimouse/raw"
MAN="$ROOT/manifests"
mkdir -p "$D1" "$D2" "$ROOT/D1_virtual_mouse_brain/processed" "$ROOT/D2_digimouse/processed" "$MAN"

# fetch URL DEST EXPECTED_BYTES(0=skip) TOLERANCE MANIFEST_TAG
fetch() {
  curl -L --fail --retry 5 --retry-delay 5 -C - -o "$2" "$1"
  local got; got=$(stat -f%z "$2")
  if [ "$3" -gt 0 ]; then
    awk -v g="$got" -v e="$3" -v t="$4" -v f="$2" \
      'BEGIN{r=g/e; if(r<1-t||r>1+t){print "SIZE MISMATCH: " f " got=" g " expected~" e; exit 1}; print "size ok: " f " (" g " bytes)"}'
  fi
  echo "$1 -> $2" >> "$MAN/${5}_sources.txt"
  shasum -a 256 "$2" | tee -a "$MAN/${5}_sha256.txt"
}

DRY="https://datadryad.org/downloads/file_stream"
USC="http://neuroimage.usc.edu/mouse_atlas"

# priority tier
fetch "$DRY/1248407" "$D1/README.txt"        3040        0.10 D1
fetch "$DRY/1248405" "$D1/MBP_to_MRI.zip"    33910000    0.03 D1
fetch "$DRY/1248406" "$D1/NF_to_MRI.zip"     23780000    0.03 D1
fetch "$DRY/1248408" "$D1/Nissl_to_MRI.zip"  1210000000  0.03 D1
for f in pet_data ct_data cryo_data atlas; do
  fetch "$USC/$f.zip" "$D2/$f.zip" 0 0 D2
done

# extended tier
if [ "$MODE" = "extended" ] || [ "$MODE" = "full" ]; then
  fetch "$DRY/1248404" "$D1/AF_data.zip.zip" 343020000 0.03 D1
  fetch "$USC/pet_raw_data.zip"     "$D2/pet_raw_data.zip"     8000000    0.50 D2
  fetch "$USC/ct_raw_data.zip"      "$D2/ct_raw_data.zip"      900000000  0.30 D2
  fetch "$USC/raw_cryosections.zip" "$D2/raw_cryosections.zip" 600000000  0.30 D2
fi

# full tier
if [ "$MODE" = "full" ]; then
  fetch "$DRY/1248409" "$D1/MRI_C57_data.zip"  10700000000 0.03 D1
  fetch "$DRY/1248410" "$D1/MRI_Shiverer.zip"   6470000000 0.03 D1
fi

echo "Done. Verify later: shasum -a 256 -c $MAN/D1_sha256.txt"
