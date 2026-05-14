[CmdletBinding()]
param(
    [switch]$Open,
    [string]$ReviewPackDir = "import_validation_reports\monday_review_pack",
    [string]$WorkbookPath = "import_validation_reports\monday_review_pack\monday_mapping_review.xlsx"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ApiDir = Join-Path $RepoRoot "apps\api"
$PrepScript = Join-Path $ApiDir "scripts\prepare_monday_tiny_sample.py"

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

$reviewPackPath = Resolve-InputPath $ReviewPackDir
$workbookFile = Resolve-InputPath $WorkbookPath
$requiredCsvs = @(
    "unresolved_sites_review.csv",
    "client_status_review.csv",
    "duplicate_sites_review.csv",
    "status_defaults_review.csv"
)

foreach ($fileName in $requiredCsvs) {
    $path = Join-Path $reviewPackPath $fileName
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required review CSV: $path"
    }
}

$pythonExecutable = Get-PythonExecutable

Write-Step "Creating private Monday mapping review workbook only. No database writes, no imports, no provider calls."

$prepArgs = @(
    $PrepScript,
    "--write-review-workbook",
    "--review-pack-dir", $reviewPackPath,
    "--review-workbook-path", $workbookFile
)

& $pythonExecutable @prepArgs
$prepExitCode = $LASTEXITCODE
if ($prepExitCode -ne 0) {
    exit $prepExitCode
}

if (-not (Test-Path -LiteralPath $workbookFile)) {
    throw "Workbook was not created: $workbookFile"
}

Write-Host ""
Write-Host "Monday mapping review workbook"
Write-Host "  Workbook: $workbookFile"
Write-Host "  Source review pack: $reviewPackPath"
Write-Host ""
Write-Host "Safety:"
Write-Host "  Workbook generation only. No database writes, no V1 apply, no CRM import, no provider calls."

if ($Open) {
    Start-Process -FilePath $workbookFile
}

exit 0
