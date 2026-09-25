#!/usr/bin/env bash
# acceptance check: everything from the committed seed and portal counts, nothing reused
set -euo pipefail
cd "$(dirname "$0")"
start=$(date +%s)
rm -rf data/gen data/tmp
./run.sh build
echo "REBUILD_DONE in $(( $(date +%s) - start ))s"
