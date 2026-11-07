param(
    [switch]$Write,
    [int]$StaleDays = 30,
    [switch]$Online
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$runtimeHome = if ($env:LIGHT_CRAWL_HOME) { $env:LIGHT_CRAWL_HOME } else { Join-Path $HOME ".light-crawl" }
$light = Join-Path $runtimeHome "venv\Scripts\light-crawl.exe"
if (-not (Test-Path $light)) {
    $light = Join-Path $Root ".venv\Scripts\light-crawl.exe"
}
if (-not (Test-Path $light)) {
    throw "light-crawl not found. Run install.ps1 or scripts\bootstrap.ps1 first."
}

$packs = & $light site list --json --stale-days $StaleDays | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "site list failed"
}

$results = @()
foreach ($pack in $packs) {
    if (-not $pack.has_verify) {
        continue
    }
    $stamp = Get-Date -Format "yyyyMMddTHHmmssZ"
    $slug = Split-Path -Leaf $pack.path
    $out = $null
    if ($Online -and $pack.has_spider) {
        $out = "runs\drift-$slug-$stamp.jsonl"
        $runArgs = @("site", "run", $pack.path, "--out", $out, "--json")
        $raw = & $light @runArgs
        $exit = $LASTEXITCODE
        try {
            $result = $raw | ConvertFrom-Json
        } catch {
            $result = [pscustomobject]@{ passed = $false; items = 0; expected_items = $null; verify_returncode = $null }
        }
        $result | Add-Member -NotePropertyName "online" -NotePropertyValue $true -Force
    } else {
        $checkArgs = @("site", "check", $pack.path, "--json")
        if ($Write) {
            $checkArgs += "--write"
        }
        $raw = & $light @checkArgs
        $exit = $LASTEXITCODE
        $result = $raw | ConvertFrom-Json
        $result | Add-Member -NotePropertyName "online" -NotePropertyValue $false -Force
    }
    $result | Add-Member -NotePropertyName "exit_code" -NotePropertyValue $exit -Force
    $result | Add-Member -NotePropertyName "domain" -NotePropertyValue $pack.domain -Force
    $result | Add-Member -NotePropertyName "stale" -NotePropertyValue $pack.stale -Force
    $results += $result
    $mark = if ($result.passed) { "PASS" } else { "FAIL" }
    $stale = if ($pack.stale) { "STALE" } else { "ok" }
    $mode = if ($result.online) { "online" } else { "offline" }
    Write-Host ("[{0}] {1,-24} {2,-8} {3,-7} {4}" -f $mark, $pack.domain, $stale, $mode, $out)
}

$report = @{
    generated_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    stale_days = $StaleDays
    write_timestamps = [bool]$Write
    online = [bool]$Online
    results = $results
}
New-Item -ItemType Directory -Force "runs" | Out-Null
$reportPath = Join-Path "runs" ("drift-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")
$report | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding utf8
Write-Host ""
Write-Host "Report: $reportPath"

$failed = @($results | Where-Object { -not $_.passed }).Count
if ($failed -gt 0) {
    Write-Host "Drift failures: $failed" -ForegroundColor Red
    exit 1
}
Write-Host "Drift check PASS" -ForegroundColor Green

