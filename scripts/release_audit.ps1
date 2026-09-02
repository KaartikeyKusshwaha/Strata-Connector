# Strata Connector — Release Audit Script
# Rejects the public connector build if any check fails.
# Run from the Strata-Connector repository root.

param(
    [string]$StagingDir = "."
)

$ErrorCount = 0

Write-Host "`n=== Strata Connector Release Audit ===" -ForegroundColor Cyan
Write-Host "Staging directory: $StagingDir`n"

# ---------------------------------------------------------------------------
# Check 1: No private engine source or credential material
# ---------------------------------------------------------------------------
Write-Host "[CHECK 1] Scanning for private engine source and credentials..." -ForegroundColor Yellow

$ForbiddenPatterns = @(
    'ANVIL_PRIVATE',
    'ENGINE_PRIVATE',
    'BEGIN.*PRIVATE KEY',
    'AWS_SECRET',
    'API[_\-]?KEY\s*='
)

$FilesToCheck = Get-ChildItem -Path $StagingDir -Recurse -File | Where-Object {
    $_.FullName -notmatch '\\tests\\' -and
    $_.FullName -notmatch '\\docs\\' -and
    $_.FullName -notmatch '\\\.git\\' -and
    $_.FullName -notmatch '\\\.venv\\' -and
    $_.FullName -notmatch '\\__pycache__\\' -and
    $_.Extension -ne '.ps1'
}

foreach ($pattern in $ForbiddenPatterns) {
    $matches = $FilesToCheck | Select-String -Pattern $pattern -ErrorAction SilentlyContinue
    if ($matches) {
        Write-Host "  FAIL: Found forbidden pattern '$pattern':" -ForegroundColor Red
        $matches | ForEach-Object { Write-Host "    $($_.Path):$($_.LineNumber) $($_.Line)" -ForegroundColor Red }
        $ErrorCount++
    }
}

# ---------------------------------------------------------------------------
# Check 2: No arbitrary code execution MCP/bridge surface
# ---------------------------------------------------------------------------
Write-Host "[CHECK 2] Scanning for arbitrary code execution surfaces..." -ForegroundColor Yellow

$ExecPatterns = @(
    'execute_python',
    'exec\(',
    'eval\(',
    'subprocess\.run',
    'os\.system'
)

$SourceDirs = @("$StagingDir\connector_mcp", "$StagingDir\addon")

foreach ($dir in $SourceDirs) {
    if (Test-Path $dir) {
        foreach ($pattern in $ExecPatterns) {
            $matches = Get-ChildItem -Path $dir -Recurse -File -Include *.py | Select-String -Pattern $pattern -ErrorAction SilentlyContinue
            if ($matches) {
                Write-Host "  FAIL: Found execution pattern '$pattern':" -ForegroundColor Red
                $matches | ForEach-Object { Write-Host "    $($_.Path):$($_.LineNumber) $($_.Line)" -ForegroundColor Red }
                $ErrorCount++
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Check 3: No strata engine module imports in connector/addon code
# ---------------------------------------------------------------------------
Write-Host "[CHECK 3] Scanning for prohibited strata engine imports..." -ForegroundColor Yellow

$EngineImportPatterns = @(
    'from strata\.',
    'import strata\.',
    'from strata import',
    'import strata '
)

foreach ($dir in $SourceDirs) {
    if (Test-Path $dir) {
        foreach ($pattern in $EngineImportPatterns) {
            $matches = Get-ChildItem -Path $dir -Recurse -File -Include *.py | Select-String -Pattern $pattern -ErrorAction SilentlyContinue
            if ($matches) {
                Write-Host "  FAIL: Found engine import '$pattern':" -ForegroundColor Red
                $matches | ForEach-Object { Write-Host "    $($_.Path):$($_.LineNumber) $($_.Line)" -ForegroundColor Red }
                $ErrorCount++
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Check 4: No reference profile data files
# ---------------------------------------------------------------------------
Write-Host "[CHECK 4] Scanning for reference profile data files..." -ForegroundColor Yellow

$ProfileFiles = Get-ChildItem -Path $StagingDir -Recurse -Include "*profile*.json","*boxscape*.json","*combined*.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.DirectoryName -notmatch 'tests|docs|node_modules|\.venv' }

if ($ProfileFiles) {
    Write-Host "  FAIL: Found reference profile files:" -ForegroundColor Red
    $ProfileFiles | ForEach-Object { Write-Host "    $($_.FullName)" -ForegroundColor Red }
    $ErrorCount++
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "`n=== Audit Summary ===" -ForegroundColor Cyan

if ($ErrorCount -eq 0) {
    Write-Host "ALL CHECKS PASSED. Release is clean." -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAILED: $ErrorCount check(s) failed. Do NOT release." -ForegroundColor Red
    exit 1
}
