[CmdletBinding()]
param(
    [string]$WorkbookPath = "import_validation_reports\monday_review_pack\monday_mapping_review.xlsx",
    [string]$ReviewPackDir = "import_validation_reports\monday_review_pack",
    [string]$OutputClients = "docs\import_templates\v2\private\clients_reviewed_sample.csv",
    [string]$OutputSites = "docs\import_templates\v2\private\sites_reviewed_sample.csv"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "apps\api"
$PrepScript = Join-Path $ApiDir "scripts\prepare_monday_tiny_sample.py"
$ValidatorPath = Join-Path $ApiDir "scripts\validate_import_templates.py"
$ReviewedReportDir = Join-Path $RepoRoot "import_validation_reports\reviewed_sample"
$ValidationJson = Join-Path $ReviewedReportDir "reviewed_sample_validation.json"
$ValidationMd = Join-Path $ReviewedReportDir "reviewed_sample_validation.md"

function Write-Step {
    param([string]$Message)
    Write-Host "[stormwater-v2-review] $Message"
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
    if (-not (Test-Path -LiteralPath $PrepScript)) {
        throw "Could not find apps\api\scripts\prepare_monday_tiny_sample.py."
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

function As-Array {
    param($Value)
    if ($null -eq $Value) {
        return @()
    }
    return @($Value)
}

Assert-RepoRoot

$workbookFile = Resolve-InputPath $WorkbookPath
$reviewPackPath = Resolve-InputPath $ReviewPackDir
$outputClientsFile = Resolve-InputPath $OutputClients
$outputSitesFile = Resolve-InputPath $OutputSites

if (-not (Test-Path -LiteralPath $workbookFile)) {
    Write-Host "NOT READY"
    throw "Missing reviewed workbook: $workbookFile"
}

$pythonExecutable = Get-PythonExecutable

Write-Step "Exporting reviewed workbook tabs to private review CSVs. No database writes, no imports, no provider calls."
$workbookArgs = @(
    $PrepScript,
    "--apply-review-workbook",
    "--review-workbook-path", $workbookFile,
    "--review-pack-dir", $reviewPackPath
)
& $pythonExecutable @workbookArgs
$workbookExitCode = $LASTEXITCODE
if ($workbookExitCode -ne 0) {
    Write-Host ""
    Write-Host "NOT READY"
    Write-Host "Workbook review is incomplete or unsafe. Fill explicit approved rows, save the workbook, and rerun this helper."
    exit $workbookExitCode
}

Write-Step "Generating reviewed private Clients/Sites sample from approved review CSV rows only."
$applyArgs = @(
    $PrepScript,
    "--apply-reviewed-mappings",
    "--review-pack-dir", $reviewPackPath,
    "--reviewed-report-dir", $ReviewedReportDir,
    "--output-clients", $outputClientsFile,
    "--output-sites", $outputSitesFile
)
& $pythonExecutable @applyArgs
$applyExitCode = $LASTEXITCODE
if ($applyExitCode -ne 0) {
    Write-Host ""
    Write-Host "NOT READY"
    Write-Host "Reviewed sample was not generated safely. Fill the workbook decisions, save it, and rerun this helper."
    Write-Host "  Clients CSV: $outputClientsFile"
    Write-Host "  Sites CSV:   $outputSitesFile"
    Write-Host "  Reports:     $ReviewedReportDir"
    exit $applyExitCode
}

Write-Step "Running explicit validator against reviewed private sample."
New-Item -ItemType Directory -Path $ReviewedReportDir -Force | Out-Null
$validatorArgs = @(
    $ValidatorPath,
    "--clients", $outputClientsFile,
    "--sites", $outputSitesFile,
    "--output-json", $ValidationJson,
    "--output-md", $ValidationMd
)
$validatorOutput = & $pythonExecutable @validatorArgs 2>&1
$validatorExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ValidationJson)) {
    Write-Host ""
    Write-Host "NOT READY"
    throw "Validator did not produce JSON report: $ValidationJson"
}
if (-not (Test-Path -LiteralPath $ValidationMd)) {
    Write-Host ""
    Write-Host "NOT READY"
    throw "Validator did not produce Markdown report: $ValidationMd"
}

$report = Get-Content -Raw -LiteralPath $ValidationJson | ConvertFrom-Json
$totals = $report.totals
$summary = $report.summary
$stopConditions = @(As-Array $report.stop_conditions)
$readyLabel = if ($report.ready) { "READY" } else { "NOT READY" }

Write-Host ""
Write-Host $readyLabel
Write-Host "Reviewed Monday workbook application"
Write-Host "  Clients rows:          $($summary.clients.total_rows)"
Write-Host "  Sites rows:            $($summary.sites.total_rows)"
Write-Host "  Total rows:            $($totals.total_rows)"
Write-Host "  Valid rows:            $($totals.valid_rows)"
Write-Host "  Invalid rows:          $($totals.invalid_rows)"
Write-Host "  Duplicate rows:        $($totals.duplicate_rows)"
Write-Host "  Unresolved references: $($totals.unresolved_references)"
Write-Host "  Clients CSV:           $outputClientsFile"
Write-Host "  Sites CSV:             $outputSitesFile"
Write-Host "  JSON report:           $ValidationJson"
Write-Host "  Markdown report:       $ValidationMd"

if ($stopConditions.Count -gt 0) {
    Write-Host ""
    Write-Host "Stop conditions were found. Open the Markdown report for row-level details."
}

Write-Host ""
Write-Host "Safety:"
Write-Host "  Review CSV/sample generation and validation only."
Write-Host "  No database writes, no V1 apply, no CRM import, no git staging, no provider calls."

if ($validatorExitCode -ne 0) {
    exit $validatorExitCode
}

exit 0
