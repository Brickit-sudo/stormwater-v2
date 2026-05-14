[CmdletBinding()]
param(
    [string]$WorkbookPath = "import_validation_reports\monday_review_pack\monday_mapping_assisted_review.xlsx",
    [string]$ReviewPackDir = "import_validation_reports\monday_review_pack"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "apps\api"
$PrepScript = Join-Path $ApiDir "scripts\prepare_monday_tiny_sample.py"

function Write-Step {
    param([string]$Message)
    Write-Host "[stormwater-v2-assisted-review] $Message"
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

Assert-RepoRoot

$workbookFile = Resolve-InputPath $WorkbookPath
$reviewPackPath = Resolve-InputPath $ReviewPackDir

if (-not (Test-Path -LiteralPath $workbookFile)) {
    Write-Host "NOT READY"
    throw "Missing assisted reviewed workbook: $workbookFile"
}

$pythonExecutable = Get-PythonExecutable

Write-Step "Writing explicit assisted review decisions back to private review CSVs. No database writes, no imports, no provider calls."

$prepArgs = @(
    $PrepScript,
    "--apply-assisted-review-workbook",
    "--assisted-review-workbook-path", $workbookFile,
    "--review-pack-dir", $reviewPackPath
)

& $pythonExecutable @prepArgs
$prepExitCode = $LASTEXITCODE
if ($prepExitCode -ne 0) {
    Write-Host ""
    Write-Host "NOT READY"
    Write-Host "Assisted review is incomplete or unsafe. Fill explicit grouped decisions, save the workbook, and rerun this helper."
    exit $prepExitCode
}

Write-Host ""
Write-Host "Assisted Monday review decisions applied"
Write-Host "  Workbook: $workbookFile"
Write-Host "  Review pack: $reviewPackPath"
Write-Host ""
Write-Host "Safety:"
Write-Host "  Review CSV update only. No database writes, no V1 apply, no CRM import, no provider calls."
Write-Host "  Next step: run the reviewed mapping workbook/sample workflow; still no import."

exit 0
