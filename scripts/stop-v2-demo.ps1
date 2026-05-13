[CmdletBinding()]
param(
    [switch]$StopPostgres
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PostgresContainer = "stormwater-v2-postgres"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeDir = Join-Path $RepoRoot "logs\v2-demo"

function Write-Step {
    param([string]$Message)
    Write-Host "[stormwater-v2] $Message"
}

function Get-DescendantProcessIds {
    param([int]$RootPid)

    $allProcesses = @(Get-CimInstance Win32_Process)
    $childrenByParent = @{}
    foreach ($process in $allProcesses) {
        $parentPid = [int]$process.ParentProcessId
        if (-not $childrenByParent.ContainsKey($parentPid)) {
            $childrenByParent[$parentPid] = [System.Collections.Generic.List[int]]::new()
        }
        $childrenByParent[$parentPid].Add([int]$process.ProcessId)
    }

    $result = [System.Collections.Generic.List[int]]::new()
    $stack = [System.Collections.Generic.List[int]]::new()
    $stack.Add($RootPid)
    while ($stack.Count -gt 0) {
        $index = $stack.Count - 1
        $current = $stack[$index]
        $stack.RemoveAt($index)
        if (-not $childrenByParent.ContainsKey($current)) {
            continue
        }
        foreach ($childPid in $childrenByParent[$current]) {
            $result.Add($childPid)
            $stack.Add($childPid)
        }
    }

    return $result.ToArray()
}

function Stop-TrackedProcess {
    param(
        [string]$Label,
        [string]$PidPath,
        [string]$ExpectedCommandFragment
    )

    if (-not (Test-Path -LiteralPath $PidPath)) {
        Write-Step "$Label was not tracked."
        return @()
    }

    $pidText = (Get-Content -Raw -LiteralPath $PidPath).Trim()
    $rootPid = 0
    if (-not [int]::TryParse($pidText, [ref]$rootPid)) {
        Remove-Item -LiteralPath $PidPath -Force
        Write-Step "$Label PID file was invalid and has been removed."
        return @()
    }

    $rootProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $rootPid" -ErrorAction SilentlyContinue
    if (-not $rootProcessInfo) {
        Remove-Item -LiteralPath $PidPath -Force
        Write-Step "$Label PID file was stale and has been removed."
        return @()
    }

    $commandLine = [string]$rootProcessInfo.CommandLine
    if ($ExpectedCommandFragment -and $commandLine -notlike "*$ExpectedCommandFragment*") {
        Remove-Item -LiteralPath $PidPath -Force
        Write-Warning "$Label PID $rootPid does not look like a Stormwater V2 demo process. Removed stale PID file without stopping it."
        return @()
    }

    $processIds = @()
    $processIds += Get-DescendantProcessIds -RootPid $rootPid
    $processIds += $rootPid
    $processIds = @($processIds | Sort-Object -Descending -Unique)
    $stopped = @()

    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if (-not $process) {
            continue
        }
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            $stopped += "${Label}:${processId}"
        }
        catch {
            Write-Warning "Could not stop ${Label} process ${processId}: $($_.Exception.Message)"
        }
    }

    Remove-Item -LiteralPath $PidPath -Force
    if ($stopped.Count -eq 0) {
        Write-Step "$Label was not running."
    }
    else {
        Write-Step "Stopped $Label process tree: $($stopped -join ', ')"
    }
    return $stopped
}

$stoppedItems = @()
$stoppedItems += Stop-TrackedProcess -Label "API" -PidPath (Join-Path $RuntimeDir "api-window.pid") -ExpectedCommandFragment (Join-Path $RuntimeDir "run-api.ps1")
$stoppedItems += Stop-TrackedProcess -Label "Web" -PidPath (Join-Path $RuntimeDir "web-window.pid") -ExpectedCommandFragment (Join-Path $RuntimeDir "run-web.ps1")

if ($StopPostgres) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $container = @(& docker ps -a --filter "name=^/${PostgresContainer}$" --format "{{.Names}}")
        if ($container -contains $PostgresContainer) {
            & docker stop $PostgresContainer | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Step "Stopped Postgres container: $PostgresContainer"
            }
            else {
                Write-Warning "Docker reported a failure while stopping $PostgresContainer."
            }
        }
        else {
            Write-Step "Postgres container was not found: $PostgresContainer"
        }
    }
    else {
        Write-Warning "Docker is not available, so Postgres was not inspected."
    }
}
else {
    Write-Step "Leaving Postgres running. Use -StopPostgres to stop the local container."
}

if ($stoppedItems.Count -eq 0 -and -not $StopPostgres) {
    Write-Step "Nothing tracked was stopped."
}

Write-Host ""
Write-Host "Status: .\scripts\status-v2-demo.ps1"
