[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PostgresContainer = "stormwater-v2-postgres"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeDir = Join-Path $RepoRoot "logs\v2-demo"
$StatePath = Join-Path $RuntimeDir "state.json"
$ApiEnvPath = Join-Path $RepoRoot "apps\api\.env"
$WebEnvPath = Join-Path $RepoRoot "apps\web\.env.local"

if (Test-Path -LiteralPath $StatePath) {
    try {
        $state = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
        if (-not $PSBoundParameters.ContainsKey("ApiPort") -and $state.api_port) {
            $ApiPort = [int]$state.api_port
        }
        if (-not $PSBoundParameters.ContainsKey("WebPort") -and $state.web_port) {
            $WebPort = [int]$state.web_port
        }
    }
    catch {
        Write-Warning "Could not read runtime state from $StatePath."
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -match "^\s*$([regex]::Escape($Key))=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    return $null
}

function Format-Configured {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return "missing"
    }
    return "configured"
}

function Test-HttpUrl {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return "OK HTTP $($response.StatusCode)"
    }
    catch {
        return "not responding"
    }
}

function Show-TrackedProcess {
    param(
        [string]$Label,
        [string]$PidPath,
        [string]$ExpectedCommandFragment
    )
    if (-not (Test-Path -LiteralPath $PidPath)) {
        Write-Host "$Label tracked PID: none"
        return
    }
    $pidText = (Get-Content -Raw -LiteralPath $PidPath).Trim()
    $pidValue = 0
    if (-not [int]::TryParse($pidText, [ref]$pidValue)) {
        Write-Host "$Label tracked PID: invalid ($pidText)"
        return
    }
    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($process) {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" -ErrorAction SilentlyContinue
        $commandLine = if ($processInfo) { [string]$processInfo.CommandLine } else { "" }
        if ($ExpectedCommandFragment -and $commandLine -notlike "*$ExpectedCommandFragment*") {
            Write-Host "$Label tracked PID: $pidValue stale or not a demo process"
        }
        else {
            Write-Host "$Label tracked PID: $pidValue running ($($process.ProcessName))"
        }
    }
    else {
        Write-Host "$Label tracked PID: $pidValue stale"
    }
}

Write-Section "Repository"
Write-Host "Path: $RepoRoot"
$branch = (& git -C $RepoRoot branch --show-current).Trim()
$latest = (& git -C $RepoRoot log --oneline -1).Trim()
$status = @(& git -C $RepoRoot status --short)
Write-Host "Branch: $branch"
Write-Host "Latest commit: $latest"
if ($status.Count -eq 0) {
    Write-Host "Git status: clean"
}
else {
    Write-Host "Git status:"
    $status | ForEach-Object { Write-Host "  $_" }
}

Write-Section "Environment Files"
Write-Host "apps\api\.env:       $(if (Test-Path -LiteralPath $ApiEnvPath) { 'exists' } else { 'missing' })"
Write-Host "  DATABASE_URL:       $(Format-Configured (Get-EnvValue -Path $ApiEnvPath -Key 'DATABASE_URL'))"
Write-Host "apps\web\.env.local: $(if (Test-Path -LiteralPath $WebEnvPath) { 'exists' } else { 'missing' })"
Write-Host "  API base URL:       $(Format-Configured (Get-EnvValue -Path $WebEnvPath -Key 'NEXT_PUBLIC_API_BASE_URL'))"
Write-Host "  Demo org ID:        $(Format-Configured (Get-EnvValue -Path $WebEnvPath -Key 'NEXT_PUBLIC_DEMO_ORG_ID'))"

Write-Section "Docker / Postgres"
if (Get-Command docker -ErrorAction SilentlyContinue) {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $containerRows = @(& docker ps -a --filter "name=^/${PostgresContainer}$" --format "{{.Names}}|{{.Status}}|{{.Ports}}")
        if ($containerRows.Count -eq 0) {
            Write-Host "Postgres container: missing ($PostgresContainer)"
        }
        else {
            foreach ($row in $containerRows) {
                $parts = $row -split "\|", 3
                Write-Host "Postgres container: $($parts[0])"
                Write-Host "  Status: $($parts[1])"
                Write-Host "  Ports:  $($parts[2])"
            }
        }
    }
    else {
        Write-Host "Docker: installed but not responding"
    }
}
else {
    Write-Host "Docker: not installed or not on PATH"
}

Write-Section "Demo Processes"
Show-TrackedProcess -Label "API" -PidPath (Join-Path $RuntimeDir "api-window.pid") -ExpectedCommandFragment (Join-Path $RuntimeDir "run-api.ps1")
Show-TrackedProcess -Label "Web" -PidPath (Join-Path $RuntimeDir "web-window.pid") -ExpectedCommandFragment (Join-Path $RuntimeDir "run-web.ps1")

Write-Section "HTTP Checks"
$apiHealth = "http://127.0.0.1:${ApiPort}/health"
$webUrl = "http://127.0.0.1:${WebPort}"
Write-Host "API health: $apiHealth - $(Test-HttpUrl -Url $apiHealth)"
Write-Host "Frontend:   $webUrl - $(Test-HttpUrl -Url $webUrl)"

Write-Section "Next Commands"
Write-Host "Start demo:        .\scripts\start-v2-demo.ps1 -Seed"
Write-Host "Fresh seed demo:   .\scripts\start-v2-demo.ps1 -ResetSeed"
Write-Host "Stop app windows:  .\scripts\stop-v2-demo.ps1"
Write-Host "Stop with DB:      .\scripts\stop-v2-demo.ps1 -StopPostgres"
Write-Host "Boss demo URL:     http://127.0.0.1:${WebPort}"
