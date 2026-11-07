param(
    [switch]$SkipBrowsers,
    [switch]$NoDev
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "light-crawl bootstrap" -ForegroundColor Cyan
Write-Host "root: $Root"

$venv = Join-Path $Root ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3.11 -m venv $venv
    } else {
        & python -m venv $venv
    }
}

if (-not (Test-Path $venvPython)) {
    throw "Could not create .venv. Install Python 3.11+ and retry."
}

& $venvPython -m pip install --upgrade pip
if ($NoDev) {
    & $venvPython -m pip install -e ".[fetchers]"
} else {
    & $venvPython -m pip install -e ".[fetchers,dev]"
}

if (-not $SkipBrowsers) {
    $scrapling = Join-Path $venv "Scripts\scrapling.exe"
    if (Test-Path $scrapling) {
        Write-Host "Installing Scrapling browsers..." -ForegroundColor Yellow
        & $scrapling install
    } else {
        Write-Warning "scrapling.exe not found; skipping browser install."
    }
}

$light = Join-Path $venv "Scripts\light-crawl.exe"
if (Test-Path $light) {
    & $light doctor
} else {
    & $venvPython run_light_crawl.py doctor
}

Write-Host ""
Write-Host "Next:" -ForegroundColor Green
Write-Host "  .venv\Scripts\light-crawl.exe demo --out runs\demo --force"
Write-Host "  .venv\Scripts\light-crawl.exe new-case my-case --target https://example.com --authorized"
