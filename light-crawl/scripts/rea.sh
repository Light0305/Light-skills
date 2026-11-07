#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Project-local REA launcher; npx keeps the package in npm's cache.
exec npx -y rea-agents@latest "$@"
