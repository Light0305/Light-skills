param(
    [switch]$SkipDemo
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

Write-Host "== unittest ==" -ForegroundColor Cyan
& $python -m unittest discover -s tests -v

if (-not $SkipDemo) {
    Write-Host "== demo ==" -ForegroundColor Cyan
    & $python run_light_crawl.py demo --out runs\demo --force
}

Write-Host "== doctor ==" -ForegroundColor Cyan
& $python run_light_crawl.py doctor

Write-Host "smoke complete" -ForegroundColor Green
