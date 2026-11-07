param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Project-local REA launcher. No global npm install is required: npx keeps the
# package in npm's cache. The first run may download; later runs reuse the cache.
& npx -y rea-agents@latest @Rest
exit $LASTEXITCODE
