param(
    [string]$SourcePath = "",
    [string]$RepoUrl = "",
    [string]$Ref = "main",
    [string]$RuntimeHome = "$HOME\.light-crawl",
    [switch]$SkipBrowsers,
    [switch]$InstallClaude,
    [switch]$InstallCodex,
    [switch]$InstallJsReverse,
    [switch]$WarmRea,
    [switch]$Full
)

$ErrorActionPreference = "Stop"

if ($Full) {
    $InstallClaude = $true
    $InstallCodex = $true
    $InstallJsReverse = $true
    $WarmRea = $true
}

function Resolve-Source {
    param([string]$Path, [string]$Repo, [string]$GitRef)

    if ($Path) {
        $resolved = Resolve-Path $Path
        return $resolved.Path
    }
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "pyproject.toml"))) {
        return $PSScriptRoot
    }
    if (-not $Repo) {
        $Repo = $env:LIGHT_CRAWL_REPO
    }
    if (-not $Repo) {
        throw "No local source found. Pass -SourcePath or -RepoUrl, or set LIGHT_CRAWL_REPO."
    }

    $download = Join-Path $env:TEMP ("light-crawl-download-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force $download | Out-Null
    $zip = Join-Path $download "source.zip"
    $url = "$($Repo.TrimEnd('/'))/archive/refs/heads/$GitRef.zip"
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $download
    $candidate = Get-ChildItem $download -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "pyproject.toml")
    } | Select-Object -First 1
    if (-not $candidate) {
        throw "Downloaded archive did not contain pyproject.toml."
    }
    return $candidate.FullName
}

function Install-JsReverse {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $npm -or -not $node) {
        Write-Warning "Node/npm not found; skipping js-reverse-mcp."
        return
    }
    Write-Host "Installing js-reverse-mcp (global npm)..."
    & npm install -g js-reverse-mcp
    if ($LASTEXITCODE -ne 0) {
        throw "npm install -g js-reverse-mcp failed"
    }
    $globalRoot = (& npm root -g).Trim()
    $entry = Join-Path $globalRoot "js-reverse-mcp\build\src\index.js"
    if (-not (Test-Path $entry)) {
        throw "js-reverse-mcp entry not found: $entry"
    }

    $register = Join-Path $dest "scripts\register_mcp.py"
    if (Test-Path $register) {
        $registerArgs = @($register, "--node", $node.Source, "--entry", $entry)
        if (-not $InstallClaude) { $registerArgs += "--skip-claude" }
        if (-not $InstallCodex) { $registerArgs += "--skip-codex" }
        & $venvPython @registerArgs
        if ($LASTEXITCODE -ne 0) {
            throw "MCP client registration failed"
        }
        return
    }

    if ($InstallClaude -and (Get-Command claude -ErrorAction SilentlyContinue)) {
        $list = (& claude mcp list 2>&1 | Out-String)
        if ($list -notmatch "js-reverse") {
            & claude mcp add --scope user js-reverse -- $node.Source $entry
            if ($LASTEXITCODE -ne 0) { throw "claude mcp add failed" }
        }
    }
    if ($InstallCodex -and (Get-Command codex -ErrorAction SilentlyContinue)) {
        $list = (& codex mcp list 2>&1 | Out-String)
        if ($list -notmatch "js-reverse") {
            & codex mcp add js-reverse -- $node.Source $entry
            if ($LASTEXITCODE -ne 0) { throw "codex mcp add failed" }
        }
    }
}

function Warm-Rea {
    Write-Host "Warming REA npx cache (no global install)..."
    & npx -y rea-agents@latest --version
    if ($LASTEXITCODE -ne 0) {
        throw "npx rea-agents failed"
    }
}

function Copy-Source {
    param([string]$From, [string]$To)

    $fromFull = (Resolve-Path $From).Path.TrimEnd('\')
    $toFull = [System.IO.Path]::GetFullPath($To).TrimEnd('\')
    if ($fromFull -ieq $toFull) {
        return
    }
    New-Item -ItemType Directory -Force $To | Out-Null
    & robocopy $fromFull $toFull /E /XD ".git" ".venv" "venv" "cases" "runs" "sites" "dist" "__pycache__" ".pytest_cache" ".light-crawl" /XF "*.pyc" | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed with exit code $LASTEXITCODE"
    }
}

$source = Resolve-Source -Path $SourcePath -Repo $RepoUrl -GitRef $Ref
$dest = Join-Path $RuntimeHome "src\light-crawl"
$venv = Join-Path $RuntimeHome "venv"
$venvPython = Join-Path $venv "Scripts\python.exe"

Write-Host "light-crawl installer"
Write-Host "  source: $source"
Write-Host "  runtime: $RuntimeHome"

New-Item -ItemType Directory -Force $RuntimeHome | Out-Null
Copy-Source -From $source -To $dest

if (-not (Test-Path $venvPython)) {
    $created = $false
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3.11 -m venv $venv
        $created = Test-Path $venvPython
    }
    if (-not $created) {
        & python -m venv $venv
    }
}
if (-not (Test-Path $venvPython)) {
    throw "Could not create a Python virtual environment at $venv."
}

Write-Host "Installing Python package and Scrapling..."
& $venvPython -m pip install --upgrade pip | Out-Null
Push-Location $dest
try {
    & $venvPython -m pip install -e ".[fetchers]"
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed"
    }
    if (-not $SkipBrowsers) {
        $scrapling = Join-Path $venv "Scripts\scrapling.exe"
        if (Test-Path $scrapling) {
            Write-Host "Installing Scrapling browser dependencies..."
            & $scrapling install
            if ($LASTEXITCODE -ne 0) {
                throw "scrapling install failed"
            }
        }
    }
} finally {
    Pop-Location
}

if ($InstallJsReverse) {
    Install-JsReverse
}
if ($WarmRea) {
    Warm-Rea
}

if ($InstallClaude -or $InstallCodex) {
    Write-Host "Building plugin marketplace..."
    & $venvPython (Join-Path $dest "scripts\package.py")
    if ($LASTEXITCODE -ne 0) {
        throw "package build failed"
    }
    $marketplace = Join-Path $dest "dist\light-crawl-marketplace"
    if ($InstallClaude) {
        Write-Host "Installing Claude Code plugin..."
        & claude plugin marketplace add $marketplace --scope user
        if ($LASTEXITCODE -ne 0) { throw "claude marketplace add failed" }
        & claude plugin install light-crawl@light-crawl --scope user
        if ($LASTEXITCODE -ne 0) { throw "claude plugin install failed" }
        & claude plugin update light-crawl@light-crawl --scope user
        if ($LASTEXITCODE -ne 0) { throw "claude plugin update failed" }
    }
    if ($InstallCodex) {
        Write-Host "Installing Codex plugin..."
        & codex plugin marketplace add $marketplace
        if ($LASTEXITCODE -ne 0) { throw "codex marketplace add failed" }
        & codex plugin add light-crawl@light-crawl
        if ($LASTEXITCODE -ne 0) { throw "codex plugin add failed" }
    }
}

Write-Host "Running doctor..."
& $venvPython (Join-Path $dest "run_light_crawl.py") doctor

Write-Host ""
Write-Host "Installed:" -ForegroundColor Green
Write-Host "  runtime: $RuntimeHome"
Write-Host "  CLI:     $venvPython $dest\run_light_crawl.py"
Write-Host ""
Write-Host "Use:"
Write-Host "  & `"$dest\scripts\light-crawl.ps1`" doctor"
Write-Host "  & `"$dest\scripts\light-crawl.ps1`" site run examples\site-packs\quotes"
Write-Host ""
Write-Host "Optional: set LIGHT_CRAWL_HOME=$RuntimeHome for the plugin wrapper."
