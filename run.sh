#!/usr/bin/env bash
# Ekatra (UKIS 2026 P-003) — one command per stage. Every stage is deterministic from the seed and safe to re-run.
#   ./run.sh build [district]     generate -> standardise -> link -> findings -> warehouse (default: both districts, ~16 min)
#   ./run.sh serve                API + interface on http://127.0.0.1:8003 (needs ui/dist: run ./run.sh ui once)
#   ./run.sh test                 unit and API tests (API tests need a built warehouse)
#   ./run.sh ui                   build the interface into ui/dist
#   ./run.sh dev                  Vite dev server on http://127.0.0.1:5183 (proxies /api to 8003)
#   ./run.sh eval                 linkage and findings accuracy against the planted truth
#   ./run.sh ui-check [url]       Playwright check of every page for every role (npm install && npx playwright install chromium first)
#   ./run.sh scrape [district]    live pension counts from ssp.uk.gov.in (Chromium; ~40 min per district; optional, counts are committed)
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] && source .venv/bin/activate
DISTRICTS=("Almora" "Udham Singh Nagar")
[ $# -ge 2 ] && DISTRICTS=("${@:2}")

# Playwright scripts run with the repo's own node_modules; a global launcher is used only as a fallback.
pw() {
  if [ -d node_modules/playwright ]; then node "$@"
  elif [ -x "$HOME/.claude/browser/run.sh" ]; then "$HOME/.claude/browser/run.sh" "$@"
  else echo "Playwright is not installed here. Run:  npm install && npx playwright install chromium"; exit 1; fi
}

case "${1:-serve}" in
  scrape)
    for d in "${DISTRICTS[@]}"; do pw scraper/ssp_counts.js --districts "$d"; done ;;
  build)
    for d in "${DISTRICTS[@]}"; do
      echo "== $d"
      (cd pipeline && python generate.py --district "$d" | tail -3)
      (cd pipeline && python standardise.py --district "$d")
      (cd pipeline && python link.py --district "$d" 2>&1 | tail -1)
    done
    (cd pipeline && python findings.py)
    python eval/report.py                         # accuracy figures for the Method page (numbers only)
    (cd pipeline && python warehouse.py)
    python pipeline/samples.py
    ;;
  eval)
    python eval/report.py ;;
  serve)
    [ -d ui/dist ] || echo "ui/dist missing: the API will run without the interface (./run.sh ui builds it)"
    exec uvicorn api.main:app --app-dir . --host 127.0.0.1 --port "${PORT:-8003}" ;;
  test)
    exec python -m pytest -q tests ;;
  ui)
    (cd ui && npm install --silent && npm run build) ;;
  dev)
    (cd ui && npm install --silent && exec npm run dev) ;;
  ui-check)
    pw ui/check/ui_check.cjs "${2:-http://127.0.0.1:8003}" ;;
  *)
    echo "usage: ./run.sh [build|serve|test|ui|dev|eval|ui-check|scrape] [district...]"; exit 1 ;;
esac
