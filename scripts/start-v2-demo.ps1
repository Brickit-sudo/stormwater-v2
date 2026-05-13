[CmdletBinding()]
param(
    [switch]$Seed,
    [switch]$ResetSeed,
    [switch]$NoBrowser,
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DemoOrganizationId = "850c47b8-6d32-58a0-8605-955527cadbf3"
$PostgresContainer = "stormwater-v2-postgres"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "apps\api"
$WebDir = Join-Path $RepoRoot "apps\web"
$RuntimeDir = Join-Path $RepoRoot "logs\v2-demo"
$ApiEnvPath = Join-Path $ApiDir ".env"
$WebEnvPath = Join-Path $WebDir ".env.local"

function Write-Step {
    param([string]$Message)
    Write-Host "[stormwater-v2] $Message"
}

function Quote-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string[]]$Lines
    )
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    [System.IO.File]::WriteAllText(
        $Path,
        (($Lines -join [Environment]::NewLine) + [Environment]::NewLine),
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $RepoRoot
    )
    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Assert-RepoRoot {
    if (-not (Test-Path -LiteralPath (Join-Path $ApiDir "app\main.py"))) {
        throw "Could not find apps\api\app\main.py. Run this from the stormwater-v2 repository."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $WebDir "package.json"))) {
        throw "Could not find apps\web\package.json. Run this from the stormwater-v2 repository."
    }

    $gitRoot = (& git -C $RepoRoot rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $gitRoot) {
        throw "This directory is not a Git repository: $RepoRoot"
    }
    $resolvedGitRoot = (Resolve-Path $gitRoot.Trim()).Path.TrimEnd("\")
    $resolvedRepoRoot = (Resolve-Path $RepoRoot).Path.TrimEnd("\")
    if ($resolvedGitRoot -ne $resolvedRepoRoot) {
        throw "Script repo root mismatch. Expected $resolvedRepoRoot but Git reports $resolvedGitRoot."
    }
}

function Assert-CommandExists {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

function Assert-DockerAvailable {
    Assert-CommandExists "docker"
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is installed but not responding. Start Docker Desktop, then rerun this script."
    }
}

function Ensure-PostgresContainer {
    $existing = @(& docker ps -a --filter "name=^/${PostgresContainer}$" --format "{{.Names}}")
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect Docker containers."
    }

    if ($existing -contains $PostgresContainer) {
        $running = (& docker inspect -f "{{.State.Running}}" $PostgresContainer).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect Docker container $PostgresContainer."
        }
        if ($running -eq "true") {
            Write-Step "Postgres container is already running: $PostgresContainer"
        }
        else {
            Write-Step "Starting existing Postgres container: $PostgresContainer"
            Invoke-Checked "docker" @("start", $PostgresContainer)
        }
        return
    }

    Write-Step "Creating safe local Postgres demo container: $PostgresContainer"
    Invoke-Checked "docker" @(
        "run",
        "--name", $PostgresContainer,
        "-e", "POSTGRES_PASSWORD=postgres",
        "-e", "POSTGRES_USER=postgres",
        "-e", "POSTGRES_DB=stormwater_v2",
        "-p", "5432:5432",
        "-d",
        "postgres:16"
    )
}

function Wait-PostgresReady {
    Write-Step "Waiting for Postgres readiness..."
    for ($attempt = 1; $attempt -le 45; $attempt++) {
        & docker exec $PostgresContainer pg_isready -U postgres -d stormwater_v2 *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Postgres is ready."
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "Postgres did not become ready in time. Check Docker Desktop and the $PostgresContainer logs."
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

function Ensure-ApiEnv {
    if (Test-Path -LiteralPath $ApiEnvPath) {
        Write-Step "Keeping existing API env file: apps\api\.env"
        if (-not (Get-EnvValue -Path $ApiEnvPath -Key "DATABASE_URL")) {
            Write-Warning "apps\api\.env exists but DATABASE_URL is blank or missing."
        }
        return
    }

    Write-Step "Creating apps\api\.env with safe local demo defaults."
    Write-Utf8NoBom -Path $ApiEnvPath -Lines @(
        "APP_NAME=Stormwater V2 API",
        "ENVIRONMENT=local",
        "",
        "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2",
        "CORS_ORIGINS=http://localhost:${WebPort},http://127.0.0.1:${WebPort}",
        "",
        "MICROSOFT_TENANT_ID=",
        "MICROSOFT_CLIENT_ID=",
        "MICROSOFT_CLIENT_SECRET=",
        "MICROSOFT_REDIRECT_URI=http://localhost:${ApiPort}/v1/outlook/auth/callback",
        "MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0",
        "TOKEN_ENCRYPTION_KEY=",
        "",
        "OPENAI_API_KEY=",
        "OPENAI_MODEL=gpt-4.1-mini",
        "AI_FEATURES_ENABLED=",
        "",
        "GOOGLE_CLIENT_ID=",
        "GOOGLE_API_KEY="
    )
}

function Ensure-WebEnv {
    if (Test-Path -LiteralPath $WebEnvPath) {
        Write-Step "Keeping existing web env file: apps\web\.env.local"
        if (-not (Get-EnvValue -Path $WebEnvPath -Key "NEXT_PUBLIC_DEMO_ORG_ID")) {
            Write-Warning "apps\web\.env.local exists but NEXT_PUBLIC_DEMO_ORG_ID is blank or missing."
        }
        return
    }

    Write-Step "Creating apps\web\.env.local with safe local demo defaults."
    Write-Utf8NoBom -Path $WebEnvPath -Lines @(
        "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:${ApiPort}",
        "NEXT_PUBLIC_DEMO_ORG_ID=${DemoOrganizationId}",
        "NEXT_PUBLIC_GOOGLE_CLIENT_ID=",
        "NEXT_PUBLIC_GOOGLE_API_KEY=",
        "NEXT_PUBLIC_GOOGLE_APP_ID="
    )
}

function Get-PythonExecutable {
    $venvPython = Join-Path $ApiDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    $pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }
    throw "Python was not found. Create apps\api\.venv and install apps\api\requirements.txt."
}

function Assert-WebDependencies {
    Assert-CommandExists "npm"
    $nextCommand = Join-Path $WebDir "node_modules\.bin\next.cmd"
    if (-not (Test-Path -LiteralPath $nextCommand)) {
        throw "Web dependencies are missing. Run: cd apps\web; npm install"
    }
}

function Test-TcpPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Test-HttpUrl {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Remove-StalePidFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $pidText = (Get-Content -Raw -LiteralPath $Path).Trim()
    $pidValue = 0
    if ([int]::TryParse($pidText, [ref]$pidValue) -and (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        return
    }
    Remove-Item -LiteralPath $Path -Force
}

function New-RunnerScript {
    param(
        [string]$Path,
        [string[]]$Lines
    )
    Write-Utf8NoBom -Path $Path -Lines $Lines
}

function Start-ApiWindow {
    param(
        [string]$PythonExecutable,
        [string]$RunnerPath,
        [string]$LogPath,
        [string]$PidPath
    )
    $healthUrl = "http://127.0.0.1:${ApiPort}/health"
    if (Test-HttpUrl -Url $healthUrl) {
        Write-Step "API already responds at $healthUrl. Skipping duplicate API window."
        return $null
    }
    if (Test-TcpPort -Port $ApiPort) {
        throw "Port $ApiPort is already in use, but the API health check did not respond. Use -ApiPort or stop the process using that port."
    }

    New-RunnerScript -Path $RunnerPath -Lines @(
        '$ErrorActionPreference = "Stop"',
        'Set-StrictMode -Version Latest',
        '$Host.UI.RawUI.WindowTitle = "Stormwater V2 API Demo"',
        "Set-Location -LiteralPath $(Quote-PowerShellLiteral $ApiDir)",
        '$env:STORMWATER_V2_DEMO = "api"',
        '$env:PYTHONUNBUFFERED = "1"',
        'Write-Host "Stormwater V2 API Demo"',
        "Write-Host ""Log: $LogPath""",
        "& $(Quote-PowerShellLiteral $PythonExecutable) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $ApiPort *> $(Quote-PowerShellLiteral $LogPath)"
    )

    $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $RunnerPath
    ) -PassThru
    Set-Content -LiteralPath $PidPath -Value $process.Id
    Write-Step "Started API window PID $($process.Id)."
    return $process.Id
}

function Start-WebWindow {
    param(
        [string]$RunnerPath,
        [string]$LogPath,
        [string]$PidPath
    )
    $webUrl = "http://127.0.0.1:${WebPort}"
    if (Test-HttpUrl -Url $webUrl) {
        Write-Step "Frontend already responds at $webUrl. Skipping duplicate web window."
        return $null
    }
    if (Test-TcpPort -Port $WebPort) {
        throw "Port $WebPort is already in use, but the frontend did not respond. Use -WebPort or stop the process using that port."
    }

    New-RunnerScript -Path $RunnerPath -Lines @(
        '$ErrorActionPreference = "Stop"',
        'Set-StrictMode -Version Latest',
        '$Host.UI.RawUI.WindowTitle = "Stormwater V2 Web Demo"',
        "Set-Location -LiteralPath $(Quote-PowerShellLiteral $WebDir)",
        '$env:STORMWATER_V2_DEMO = "web"',
        'Write-Host "Stormwater V2 Web Demo"',
        "Write-Host ""Log: $LogPath""",
        "& npm.cmd run dev -- --hostname 127.0.0.1 --port $WebPort *> $(Quote-PowerShellLiteral $LogPath)"
    )

    $process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-File", $RunnerPath
    ) -PassThru
    Set-Content -LiteralPath $PidPath -Value $process.Id
    Write-Step "Started web window PID $($process.Id)."
    return $process.Id
}

Assert-RepoRoot
Assert-DockerAvailable
Assert-WebDependencies

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

$apiPidPath = Join-Path $RuntimeDir "api-window.pid"
$webPidPath = Join-Path $RuntimeDir "web-window.pid"
Remove-StalePidFile -Path $apiPidPath
Remove-StalePidFile -Path $webPidPath

Ensure-PostgresContainer
Wait-PostgresReady
Ensure-ApiEnv
Ensure-WebEnv

$pythonExecutable = Get-PythonExecutable

Write-Step "Running Alembic upgrade head."
Invoke-Checked $pythonExecutable @("-m", "alembic", "upgrade", "head") $ApiDir

if ($ResetSeed) {
    Write-Step "Resetting and reseeding deterministic demo data."
    Invoke-Checked $pythonExecutable @("scripts\seed_dev.py", "--reset-seed") $ApiDir
}
elseif ($Seed) {
    Write-Step "Seeding deterministic demo data."
    Invoke-Checked $pythonExecutable @("scripts\seed_dev.py") $ApiDir
}
else {
    Write-Step "Skipping seed. Use -Seed or -ResetSeed for deterministic demo rows."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$apiLogPath = Join-Path $RuntimeDir "api-$stamp.log"
$webLogPath = Join-Path $RuntimeDir "web-$stamp.log"
$apiRunnerPath = Join-Path $RuntimeDir "run-api.ps1"
$webRunnerPath = Join-Path $RuntimeDir "run-web.ps1"

$apiPid = Start-ApiWindow -PythonExecutable $pythonExecutable -RunnerPath $apiRunnerPath -LogPath $apiLogPath -PidPath $apiPidPath
$webPid = Start-WebWindow -RunnerPath $webRunnerPath -LogPath $webLogPath -PidPath $webPidPath

$state = [ordered]@{
    started_at = (Get-Date).ToString("o")
    repo_root = $RepoRoot
    api_port = $ApiPort
    web_port = $WebPort
    api_window_pid = $apiPid
    web_window_pid = $webPid
    api_log = $apiLogPath
    web_log = $webLogPath
}
$state | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $RuntimeDir "state.json")

Write-Host ""
Write-Host "Stormwater V2 demo URLs"
Write-Host "  API health:  http://127.0.0.1:${ApiPort}/health"
Write-Host "  App:         http://127.0.0.1:${WebPort}"
Write-Host "  Clients:     http://127.0.0.1:${WebPort}/crm/clients"
Write-Host "  Sites:       http://127.0.0.1:${WebPort}/crm/sites"
Write-Host "  Jobs:        http://127.0.0.1:${WebPort}/crm/jobs"
Write-Host "  Schedule:    http://127.0.0.1:${WebPort}/schedule"
Write-Host "  Map:         http://127.0.0.1:${WebPort}/map"
Write-Host "  Work Hub:    http://127.0.0.1:${WebPort}/work"
Write-Host "  Search:      http://127.0.0.1:${WebPort}/search"
Write-Host ""
Write-Host "Logs are under: $RuntimeDir"
Write-Host "Use demo/seed data only unless auth and hosting are configured."
Write-Host ""
Write-Host "Stop:   .\scripts\stop-v2-demo.ps1"
Write-Host "Status: .\scripts\status-v2-demo.ps1"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:${WebPort}"
}
