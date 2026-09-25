#!/usr/bin/env bash
# findings -> evaluation -> warehouse -> sample file, logged; safe to re-run. Args: districts for findings (default all)
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
args=(); for d in "$@"; do args+=(--district "$d"); done
(cd pipeline && python -u findings.py "${args[@]}")
python -u eval/report.py
(cd pipeline && python -u warehouse.py)
python -u pipeline/samples.py
echo POST_DONE
