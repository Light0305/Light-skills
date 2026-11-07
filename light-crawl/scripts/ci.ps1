param(
    [switch]$Online,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
$light = Join-Path $Root ".venv\Scripts\light-crawl.exe"
if (-not (Test-Path $venvPython)) {
    throw "Missing .venv. Run scripts\bootstrap.ps1 first."
}
if (-not (Test-Path $light)) {
    $light = $venvPython
}

function Invoke-Check {
    param(
        [string]$Label,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "== $Label ==" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Invoke-Check "unit tests" { & $venvPython -m pytest -q }
Invoke-Check "benchmark" { & $light benchmark --source-cases cases }
Invoke-Check "quotes pack verify" { & $venvPython "examples\site-packs\quotes\verify.py" }
Invoke-Check "books pack verify" { & $venvPython "examples\site-packs\books\verify.py" }
Invoke-Check "github api pack verify" { & $venvPython "examples\site-packs\github-api\verify.py" }
Invoke-Check "signed local pack verify" { & $venvPython "examples\site-packs\signed-local\verify.py" }
Invoke-Check "login local pack verify" { & $venvPython "examples\site-packs\login-local\verify.py" }

if (-not $SkipBrowser) {
    Invoke-Check "l3 browser capture" { & $venvPython "benchmarks\l3_capture_check.py" }
}

if ($Online) {
    Invoke-Check "quotes site run" { & $light site run "examples\site-packs\quotes" --max-pages 1 --out "runs\ci-quotes.jsonl" }
    Invoke-Check "books site run" { & $light site run "examples\site-packs\books" --out "runs\ci-books.jsonl" }
    Invoke-Check "github api site run" { & $light site run "examples\site-packs\github-api" --out "runs\ci-github.jsonl" }
}

Write-Host ""
Write-Host "CI PASS" -ForegroundColor Green
