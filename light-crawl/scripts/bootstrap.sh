#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "light-crawl bootstrap"
echo "root: $ROOT"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[fetchers,dev]"

if [ "${SKIP_BROWSERS:-0}" != "1" ]; then
  scrapling install
fi

light-crawl doctor

cat <<'EOF'

Next:
  light-crawl demo --out runs/demo --force
  light-crawl new-case my-case --target https://example.com --authorized
EOF
