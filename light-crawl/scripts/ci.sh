#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="$ROOT/.venv/bin/python"
LIGHT="$ROOT/.venv/bin/light-crawl"
if [ ! -x "$PYTHON" ]; then
  echo "Missing .venv. Run scripts/bootstrap.sh first." >&2
  exit 1
fi
if [ ! -x "$LIGHT" ]; then
  LIGHT="$PYTHON"
fi

run_check() {
  local label="$1"
  shift
  echo ""
  echo "== $label =="
  "$@"
}

run_check "unit tests" "$PYTHON" -m pytest -q
run_check "benchmark" "$LIGHT" benchmark --source-cases cases
run_check "quotes pack verify" "$PYTHON" examples/site-packs/quotes/verify.py
run_check "books pack verify" "$PYTHON" examples/site-packs/books/verify.py
run_check "github api pack verify" "$PYTHON" examples/site-packs/github-api/verify.py
run_check "signed local pack verify" "$PYTHON" examples/site-packs/signed-local/verify.py
run_check "login local pack verify" "$PYTHON" examples/site-packs/login-local/verify.py

if [ "${SKIP_BROWSER:-0}" != "1" ]; then
  run_check "l3 browser capture" "$PYTHON" benchmarks/l3_capture_check.py
fi

if [ "${ONLINE:-0}" = "1" ]; then
  run_check "quotes site run" "$LIGHT" site run examples/site-packs/quotes --max-pages 1 --out runs/ci-quotes.jsonl
  run_check "books site run" "$LIGHT" site run examples/site-packs/books --out runs/ci-books.jsonl
  run_check "github api site run" "$LIGHT" site run examples/site-packs/github-api --out runs/ci-github.jsonl
fi

echo ""
echo "CI PASS"
