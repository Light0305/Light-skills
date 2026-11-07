param(
    [switch]$Register,
    [switch]$Unregister,
    [string]$Time = "03:30",
    [string]$TaskName = "light-crawl-drift"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Drift = Join-Path $PSScriptRoot "drift.ps1"

if (-not (Test-Path $Drift)) {
    throw "Missing drift script: $Drift"
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$Drift`""
$create = "Register-ScheduledTask -TaskName '$TaskName' -Action (New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '$argument' -WorkingDirectory '$Root') -Trigger (New-ScheduledTaskTrigger -Daily -At '$Time') -Description 'light-crawl site-pack drift check' -Force"

if (-not $Register) {
    Write-Host "Dry run. No scheduled task was created."
    Write-Host ""
    Write-Host $create
    Write-Host ""
    Write-Host "To register:  .\scripts\schedule-drift.ps1 -Register"
    Write-Host "To remove:    .\scripts\schedule-drift.ps1 -Unregister"
    exit 0
}

Write-Host "Registering daily drift task '$TaskName' at $Time"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "light-crawl site-pack drift check" -Force | Out-Null
Write-Host "Registered: $TaskName"
