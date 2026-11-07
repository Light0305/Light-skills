param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RuntimeHome = if ($env:LIGHT_CRAWL_HOME) { $env:LIGHT_CRAWL_HOME } else { Join-Path $HOME ".light-crawl" }
$RuntimePython = Join-Path $RuntimeHome "venv\Scripts\python.exe"
$RuntimeEntry = Join-Path $RuntimeHome "src\light-crawl\run_light_crawl.py"

if ((Test-Path $RuntimePython) -and (Test-Path $RuntimeEntry)) {
    & $RuntimePython $RuntimeEntry @Rest
    exit $LASTEXITCODE
}

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython (Join-Path $Root "run_light_crawl.py") @Rest
} else {
    & python (Join-Path $Root "run_light_crawl.py") @Rest
}
exit $LASTEXITCODE
