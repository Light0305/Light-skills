param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Missing .venv. Run scripts\bootstrap.ps1 first."
}

if (-not $SkipTests) {
    Write-Host "== tests ==" -ForegroundColor Cyan
    & $venvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "tests failed"
    }
}

Write-Host "== package ==" -ForegroundColor Cyan
& $venvPython scripts\package.py
if ($LASTEXITCODE -ne 0) {
    throw "package failed"
}

Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Green
Get-ChildItem dist -File | Select-Object Name, @{ Name = "MB"; Expression = { [math]::Round($_.Length / 1MB, 2) } } | Format-Table -AutoSize
