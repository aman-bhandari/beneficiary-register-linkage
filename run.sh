#!/usr/bin/env bash
# One command per stage. Every stage is deterministic from the seed and safe to re-run.
#   ./run.sh scrape               live pension counts from ssp.uk.gov.in (Chromium; ~40 min per district)
#   ./run.sh build [district]     generate -> standardise -> link -> findings -> warehouse (default: both districts)
#   ./run.sh eval                 linkage and findings accuracy against the planted truth
#   ./run.sh serve                API + interface on http://127.0.0.1:8003
#   ./run.sh test                 unit and API tests
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
DISTRICTS=("Almora" "Udham Singh Nagar")
[ $# -ge 2 ] && DISTRICTS=("${@:2}")

case "${1:-serve}" in
  scrape)
    for d in "${DISTRICTS[@]}"; do ~/.claude/browser/run.sh scraper/ssp_counts.js --districts "$d"; done ;;
  build)
    for d in "${DISTRICTS[@]}"; do
      echo "== $d"
      (cd pipeline && python generate.py --district "$d" | tail -3)
      (cd pipeline && python standardise.py --district "$d")
      (cd pipeline && python link.py --district "$d" 2>&1 | tail -1)
    done
    [ -f pipeline/findings.py ] && (cd pipeline && python findings.py)
    [ -f pipeline/warehouse.py ] && (cd pipeline && python warehouse.py)
    ;;
  eval)
    for d in "${DISTRICTS[@]}"; do python eval/linkage_eval.py --district "$d" --detail; done
    [ -f eval/findings_eval.py ] && python eval/findings_eval.py
    ;;
  serve)
    exec uvicorn api.main:app --app-dir . --host 127.0.0.1 --port "${PORT:-8003}" ;;
  test)
    exec python -m pytest -q tests ;;
  *)
    echo "usage: ./run.sh [scrape|build|eval|serve|test] [district...]"; exit 1 ;;
esac
