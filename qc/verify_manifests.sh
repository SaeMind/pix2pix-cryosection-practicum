#!/usr/bin/env bash
# Verify every datasets/manifests/*_sha256.txt entry. Paths are relative to datasets/.
# usage: qc/verify_manifests.sh   (exit 1 on any failure or missing file)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)/datasets"
rc=0
for m in manifests/*_sha256.txt; do
  echo "== $m"
  grep -v '^#' "$m" | grep -v '^[[:space:]]*$' | shasum -a 256 -c - || rc=1
done
exit $rc
