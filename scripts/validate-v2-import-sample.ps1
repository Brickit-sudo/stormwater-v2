[CmdletBinding()]
param(
    [string]$ClientsPath,
    [string]$SitesPath,
    [string]$OutputDir = "import_validation_reports",
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "apps\api"
$ValidatorPath = Join-Path $ApiDir "scripts\validate_import_templates.py"
$PrivateDir = Join-Path $RepoRoot "docs\import_templates\v2\private"
$DefaultClientsPath = Join-Path $PrivateDir "clients_tiny_sample.csv"
$DefaultSitesPath = Join-Path $PrivateDir "sites_tiny_sample.csv"

function Write-Step {
    param([string]$Message)
    Write-Host "[stormwater-v2-import] $Message"
}

function Resolve-InputPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $PathValue))
}

function Assert-RepoRoot {
    if (-not (Test-Path -LiteralPath (Join-Path $ApiDir "app\main.py"))) {
        throw "Could not find apps\api\app\main.py. Run this from the stormwater-v2 repository."
    }
    if (-not (Test-Path -LiteralPath $ValidatorPath)) {
        throw "Could not find apps\api\scripts\validate_import_templates.py."
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

function Show-MissingSampleInstructions {
    param(
        [string]$ClientsFile,
        [string]$SitesFile
    )

    Write-Host ""
    Write-Host "Tiny private sample files are not ready yet. Nothing was validated."
    Write-Host ""
    Write-Host "Create private CSVs here:"
    Write-Host "  $ClientsFile"
    Write-Host "  $SitesFile"
    Write-Host ""
    Write-Host "Suggested setup from repo root:"
    Write-Host "  New-Item -ItemType Directory -Force docs\import_templates\v2\private | Out-Null"
    Write-Host "  Copy-Item docs\import_templates\v2\clients_template.csv docs\import_templates\v2\private\clients_tiny_sample.csv"
    Write-Host "  Copy-Item docs\import_templates\v2\sites_template.csv docs\import_templates\v2\private\sites_tiny_sample.csv"
    Write-Host ""
    Write-Host "Then replace the fake rows with 3 to 5 real clients and 5 to 10 real sites."
    Write-Host "Keep the files private and ignored. This helper validates only; it never imports data."
}

function As-Array {
    param($Value)
    if ($null -eq $Value) {
        return @()
    }
    return @($Value)
}

Assert-RepoRoot

if (-not (Test-Path -LiteralPath $PrivateDir)) {
    New-Item -ItemType Directory -Path $PrivateDir -Force | Out-Null
    Write-Step "Created ignored private sample folder: docs\import_templates\v2\private"
}

$clientsFile = if ($ClientsPath) { Resolve-InputPath $ClientsPath } else { $DefaultClientsPath }
$sitesFile = if ($SitesPath) { Resolve-InputPath $SitesPath } else { $DefaultSitesPath }

if (-not (Test-Path -LiteralPath $clientsFile) -or -not (Test-Path -LiteralPath $sitesFile)) {
    Show-MissingSampleInstructions -ClientsFile $clientsFile -SitesFile $sitesFile
    exit 0
}

$outputRoot = Resolve-InputPath $OutputDir
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputJson = Join-Path $outputRoot "tiny-sample-validation-$stamp.json"
$outputMd = Join-Path $outputRoot "tiny-sample-validation-$stamp.md"
$pythonExecutable = Get-PythonExecutable

Write-Step "Running Clients/Sites validation only. No database writes, no imports, no provider calls."

$validatorArgs = @(
    $ValidatorPath,
    "--clients", $clientsFile,
    "--sites", $sitesFile,
    "--output-json", $outputJson,
    "--output-md", $outputMd
)

& $pythonExecutable @validatorArgs
$validatorExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $outputJson)) {
    throw "Validator did not produce JSON report: $outputJson"
}
if (-not (Test-Path -LiteralPath $outputMd)) {
    throw "Validator did not produce Markdown report: $outputMd"
}

$report = Get-Content -Raw -LiteralPath $outputJson | ConvertFrom-Json
$totals = $report.totals
$stopConditions = As-Array $report.stop_conditions
$unresolvedSummary = As-Array $report.unresolved_reference_summary

Write-Host ""
Write-Host "V2 tiny Clients/Sites sample validation"
Write-Host "  Ready:                 $(if ($report.ready) { 'YES' } else { 'NO' })"
Write-Host "  Safe to proceed:       $(if ($report.safe_to_proceed) { 'YES - validation is clean, still no import has run' } else { 'NO - fix stop conditions first' })"
Write-Host "  Total rows:            $($totals.total_rows)"
Write-Host "  Valid rows:            $($totals.valid_rows)"
Write-Host "  Invalid rows:          $($totals.invalid_rows)"
Write-Host "  Duplicate rows:        $($totals.duplicate_rows)"
Write-Host "  Unresolved references: $($totals.unresolved_references)"
Write-Host "  JSON report:           $outputJson"
Write-Host "  Markdown report:       $outputMd"
Write-Host ""
Write-Host "Recommended next action:"
Write-Host "  $($report.recommended_next_action)"

if ($stopConditions.Count -gt 0) {
    Write-Host ""
    Write-Host "Stop conditions:"
    foreach ($condition in $stopConditions) {
        Write-Host "  - $condition"
    }
}

if ($unresolvedSummary.Count -gt 0) {
    Write-Host ""
    Write-Host "Unresolved reference summary:"
    foreach ($item in $unresolvedSummary) {
        $rows = (As-Array $item.rows) -join ", "
        Write-Host "  - $($item.import_type) $($item.field) -> $($item.target_type) '$($item.target_external_id)' on row(s): $rows"
    }
}

Write-Host ""
Write-Host "Safety:"
Write-Host "  Validation only. No database writes, no V1 apply, no CRM import, no provider calls."

if ($OpenReport) {
    Start-Process $outputMd
}

exit $validatorExitCode

