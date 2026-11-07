param(
    [string]$NodePath = (Get-Command node -ErrorAction SilentlyContinue).Source,
    [string]$EntryPath = "",
    [string]$HomeRoot = $HOME,
    [string]$AppDataRoot = $env:APPDATA,
    [switch]$SkipClaude,
    [switch]$SkipCodex
)

$ErrorActionPreference = "Stop"

if (-not $NodePath) { throw "NodePath is required." }
if (-not $EntryPath -or -not (Test-Path $EntryPath)) { throw "EntryPath not found: $EntryPath" }

$stamp = Get-Date -Format "yyyyMMddTHHmmssZ"
$backupRoot = Join-Path $HomeRoot ".light-crawl\backups\mcp-$stamp"
New-Item -ItemType Directory -Force $backupRoot | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Read-JsonObject {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return [pscustomobject]@{} }
    try {
        $data = Get-Content $Path -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $data) { return [pscustomobject]@{} }
        return $data
    } catch {
        throw "Invalid JSON in ${Path}: $($_.Exception.Message)"
    }
}

function Write-JsonFile {
    param([string]$Path, [object]$Data)
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force $dir | Out-Null }
    [System.IO.File]::WriteAllText($Path, ($Data | ConvertTo-Json -Depth 30), $utf8)
}

function Backup-File {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $name = ($Path -replace '[\\/:*?"<>|]', '_')
    Copy-Item $Path (Join-Path $backupRoot $name) -Force
}

function Set-Server {
    param(
        [string]$Path,
        [string]$RootKey,
        [object]$Server
    )
    if (-not (Test-Path (Split-Path -Parent $Path))) { return $false }
    Backup-File $Path
    $data = Read-JsonObject $Path
    if ($data.PSObject.Properties.Name -notcontains $RootKey) {
        $data | Add-Member -NotePropertyName $RootKey -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $data.$RootKey | Add-Member -NotePropertyName "js-reverse" -NotePropertyValue $Server -Force
    Write-JsonFile $Path $data
    return $true
}

$updated = @()
$stdio = [pscustomobject]@{ command = $NodePath; args = @($EntryPath) }
$vscode = [pscustomobject]@{ type = "stdio"; command = $NodePath; args = @($EntryPath) }
$opencode = [pscustomobject]@{ type = "local"; command = @($NodePath, $EntryPath); enabled = $true }

$jsonTargets = @(
    @{ Path = (Join-Path $HomeRoot ".cursor\mcp.json"); Root = "mcpServers"; Server = $stdio; Name = "Cursor" },
    @{ Path = (Join-Path $HomeRoot ".codeium\windsurf\mcp_config.json"); Root = "mcpServers"; Server = $stdio; Name = "Windsurf" },
    @{ Path = (Join-Path $HomeRoot ".config\opencode\opencode.json"); Root = "mcp"; Server = $opencode; Name = "OpenCode" },
    @{ Path = (Join-Path $HomeRoot ".gemini\settings.json"); Root = "mcpServers"; Server = $stdio; Name = "Gemini CLI" },
    @{ Path = (Join-Path $HomeRoot ".gemini\antigravity\mcp_config.json"); Root = "mcpServers"; Server = $stdio; Name = "Antigravity" },
    @{ Path = (Join-Path $HomeRoot ".copilot\mcp-config.json"); Root = "mcpServers"; Server = $stdio; Name = "Copilot CLI" },
    @{ Path = (Join-Path $AppDataRoot "Code\User\mcp.json"); Root = "servers"; Server = $vscode; Name = "VS Code" }
)

foreach ($target in $jsonTargets) {
    if (Set-Server -Path $target.Path -RootKey $target.Root -Server $target.Server) {
        $updated += $target.Name
    }
}

if (-not $SkipClaude -and (Get-Command claude -ErrorAction SilentlyContinue)) {
    $list = (& claude mcp list 2>&1 | Out-String)
    if ($list -notmatch "js-reverse") {
        & claude mcp add --scope user js-reverse -- $NodePath $EntryPath
        if ($LASTEXITCODE -eq 0) { $updated += "Claude Code" }
    } else {
        $updated += "Claude Code"
    }
}

if (-not $SkipCodex -and (Get-Command codex -ErrorAction SilentlyContinue)) {
    $list = (& codex mcp list 2>&1 | Out-String)
    if ($list -notmatch "js-reverse") {
        & codex mcp add js-reverse -- $NodePath $EntryPath
        if ($LASTEXITCODE -eq 0) { $updated += "Codex" }
    } else {
        $updated += "Codex"
    }
}

Write-Output ("updated: " + ($updated -join ", "))
Write-Output "backup: $backupRoot"
