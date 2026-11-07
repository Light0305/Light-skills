#!/usr/bin/env bash
set -euo pipefail

SOURCE_PATH=""
REPO_URL="${LIGHT_CRAWL_REPO:-}"
REF="main"
RUNTIME_HOME="${LIGHT_CRAWL_HOME:-$HOME/.light-crawl}"
SKIP_BROWSERS=0
INSTALL_CLAUDE=0
INSTALL_CODEX=0
INSTALL_JS_REVERSE=0
WARM_REA=0
FULL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --source) SOURCE_PATH="$2"; shift 2 ;;
    --repo) REPO_URL="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --runtime-home) RUNTIME_HOME="$2"; shift 2 ;;
    --skip-browsers) SKIP_BROWSERS=1; shift ;;
    --install-claude) INSTALL_CLAUDE=1; shift ;;
    --install-codex) INSTALL_CODEX=1; shift ;;
    --install-js-reverse) INSTALL_JS_REVERSE=1; shift ;;
    --warm-rea) WARM_REA=1; shift ;;
    --full) FULL=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ "$FULL" = "1" ]; then
  INSTALL_CLAUDE=1
  INSTALL_CODEX=1
  INSTALL_JS_REVERSE=1
  WARM_REA=1
fi

resolve_source() {
  if [ -n "$SOURCE_PATH" ]; then
    (cd "$SOURCE_PATH" && pwd)
    return
  fi
  if [ -f "$(dirname "$0")/pyproject.toml" ]; then
    (cd "$(dirname "$0")" && pwd)
    return
  fi
  if [ -z "$REPO_URL" ]; then
    echo "No local source. Pass --repo or --source." >&2
    exit 2
  fi
  local tmp manifest
  tmp="$(mktemp -d)"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$REPO_URL/archive/refs/heads/$REF.zip" -o "$tmp/source.zip"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$REPO_URL/archive/refs/heads/$REF.zip" -O "$tmp/source.zip"
  else
    "$PYTHON_BIN" -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], sys.argv[2])" \
      "$REPO_URL/archive/refs/heads/$REF.zip" "$tmp/source.zip"
  fi
  if command -v unzip >/dev/null 2>&1; then
    unzip -q "$tmp/source.zip" -d "$tmp"
  else
    "$PYTHON_BIN" -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
      "$tmp/source.zip" "$tmp"
  fi
  manifest="$(find "$tmp" -maxdepth 2 -name pyproject.toml -print -quit)"
  [ -n "$manifest" ] || { echo "Downloaded archive has no pyproject.toml." >&2; exit 1; }
  dirname "$manifest"
}

install_js_reverse() {
  if ! command -v npm >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
    echo "Node/npm not found; skipping js-reverse-mcp." >&2
    return
  fi
  echo "Installing js-reverse-mcp (global npm)..."
  npm install -g js-reverse-mcp
  local root entry
  root="$(npm root -g | tr -d '\r')"
  entry="$root/js-reverse-mcp/build/src/index.js"
  [ -f "$entry" ] || { echo "js-reverse entry not found: $entry" >&2; exit 1; }
  if [ -f "$DEST/scripts/register_mcp.py" ]; then
    local register_args=(--node "$(command -v node)" --entry "$entry")
    [ "$INSTALL_CLAUDE" = "1" ] || register_args+=(--skip-claude)
    [ "$INSTALL_CODEX" = "1" ] || register_args+=(--skip-codex)
    "$PYTHON" "$DEST/scripts/register_mcp.py" "${register_args[@]}"
    return
  fi
  if [ "$INSTALL_CLAUDE" = "1" ] && command -v claude >/dev/null 2>&1; then
    if ! claude mcp list 2>&1 | grep -q "js-reverse"; then
      claude mcp add --scope user js-reverse -- "$(command -v node)" "$entry"
    fi
  fi
  if [ "$INSTALL_CODEX" = "1" ] && command -v codex >/dev/null 2>&1; then
    if ! codex mcp list 2>&1 | grep -q "js-reverse"; then
      codex mcp add js-reverse -- "$(command -v node)" "$entry"
    fi
  fi
}

warm_rea() {
  echo "Warming REA npx cache (no global install)..."
  npx -y rea-agents@latest --version
}

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    echo "Python 3.11+ not found. Set PYTHON_BIN." >&2
    exit 2
  fi
fi

SOURCE="$(resolve_source)"
DEST="$RUNTIME_HOME/src/light-crawl"
VENV="$RUNTIME_HOME/venv"
if [ -x "$VENV/bin/python" ]; then
  PYTHON="$VENV/bin/python"
elif [ -x "$VENV/Scripts/python.exe" ]; then
  PYTHON="$VENV/Scripts/python.exe"
else
  PYTHON="$VENV/bin/python"
fi

echo "light-crawl installer"
echo "  source:  $SOURCE"
echo "  runtime: $RUNTIME_HOME"

mkdir -p "$RUNTIME_HOME"
if [ "$SOURCE" != "$DEST" ]; then
  mkdir -p "$DEST"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude .git --exclude .venv --exclude venv --exclude cases \
      --exclude runs --exclude sites --exclude dist --exclude __pycache__ \
      --exclude .pytest_cache --exclude .light-crawl \
      "$SOURCE/" "$DEST/"
  else
    cp -a "$SOURCE/." "$DEST/"
    rm -rf "$DEST/.git" "$DEST/.venv" "$DEST/cases" "$DEST/runs" "$DEST/sites" "$DEST/dist"
  fi
fi

if [ ! -x "$PYTHON" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
  if [ -x "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
  elif [ -x "$VENV/Scripts/python.exe" ]; then
    PYTHON="$VENV/Scripts/python.exe"
  fi
fi

"$PYTHON" -m pip install --upgrade pip >/dev/null
(
  cd "$DEST"
  "$PYTHON" -m pip install -e ".[fetchers]"
  if [ "$SKIP_BROWSERS" = "0" ]; then
    if [ -x "$VENV/bin/scrapling" ]; then
      "$VENV/bin/scrapling" install
    elif [ -x "$VENV/Scripts/scrapling.exe" ]; then
      "$VENV/Scripts/scrapling.exe" install
    fi
  fi
)

if [ "$INSTALL_JS_REVERSE" = "1" ]; then
  install_js_reverse
fi
if [ "$WARM_REA" = "1" ]; then
  warm_rea
fi

if [ "$INSTALL_CLAUDE" = "1" ] || [ "$INSTALL_CODEX" = "1" ]; then
  "$PYTHON" "$DEST/scripts/package.py"
  MARKETPLACE="$DEST/dist/light-crawl-marketplace"
  if [ "$INSTALL_CLAUDE" = "1" ]; then
    claude plugin marketplace add "$MARKETPLACE" --scope user
    claude plugin install light-crawl@light-crawl --scope user
    claude plugin update light-crawl@light-crawl --scope user
  fi
  if [ "$INSTALL_CODEX" = "1" ]; then
    codex plugin marketplace add "$MARKETPLACE"
    codex plugin add light-crawl@light-crawl
  fi
fi

"$PYTHON" "$DEST/run_light_crawl.py" doctor

echo ""
echo "Installed."
echo "  runtime: $RUNTIME_HOME"
echo "  use:     \"$DEST/scripts/light-crawl.sh\" doctor"
