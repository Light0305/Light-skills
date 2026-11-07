#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_HOME="${LIGHT_CRAWL_HOME:-$HOME/.light-crawl}"

if [ -f "$RUNTIME_HOME/src/light-crawl/run_light_crawl.py" ]; then
  if [ -x "$RUNTIME_HOME/venv/bin/python" ]; then
    exec "$RUNTIME_HOME/venv/bin/python" "$RUNTIME_HOME/src/light-crawl/run_light_crawl.py" "$@"
  elif [ -x "$RUNTIME_HOME/venv/Scripts/python.exe" ]; then
    exec "$RUNTIME_HOME/venv/Scripts/python.exe" "$RUNTIME_HOME/src/light-crawl/run_light_crawl.py" "$@"
  fi
fi

if [ -x "$ROOT/.venv/bin/python" ]; then
  exec "$ROOT/.venv/bin/python" "$ROOT/run_light_crawl.py" "$@"
elif [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
  exec "$ROOT/.venv/Scripts/python.exe" "$ROOT/run_light_crawl.py" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/run_light_crawl.py" "$@"
fi
exec python "$ROOT/run_light_crawl.py" "$@"
