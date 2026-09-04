# Strata Connector — Release Audit Script (§9 Rejection Checklist)
# Rejects the public Connector release if any check fails.
# Run from the Strata-Connector repository root.

param(
    [string]$StagingDir = "."
)

$ErrorCount = 0

Write-Host "`n=== Strata Connector Release Audit (§9 Rejection Checklist) ===" -ForegroundColor Cyan
Write-Host "Staging directory: $StagingDir`n"

# ---------------------------------------------------------------------------
# Check 1: No Engine modules, private build workers, private tests,
#           private reference profiles, real user data, or asset packs
# ---------------------------------------------------------------------------
Write-Host "[CHECK 1] Scanning for private engine source and credentials..." -ForegroundColor Yellow

$ForbiddenPatterns = @(
    'ANVIL_PRIVATE',
    'ENGINE_PRIVATE',
    'BEGIN.*PRIVATE KEY',
    'AWS_SECRET',
    'pre-signed'
)

$FilesToCheck = Get-ChildItem -Path $StagingDir -Recurse -File | Where-Object {
    $_.FullName -notmatch '\\tests\\' -and
    $_.FullName -notmatch '\\docs\\' -and
    $_.FullName -notmatch '\\\.git\\' -and
    $_.FullName -notmatch '\\\.venv\\' -and
    $_.FullName -notmatch '\\\.pytest_cache\\' -and
    $_.FullName -notmatch '\\test-tmp\\' -and
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
# Check 3: No strata engine module imports in connector/addon/reference code
# ---------------------------------------------------------------------------
Write-Host "[CHECK 3] Scanning for prohibited strata engine imports..." -ForegroundColor Yellow

$EngineImportPatterns = @(
    'from strata\.',
    'import strata\.',
    'from strata import',
    'import strata '
)

$CheckDirs = @("$StagingDir\connector_mcp", "$StagingDir\addon", "$StagingDir\reference_engine")

foreach ($dir in $CheckDirs) {
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
    Where-Object { $_.DirectoryName -notmatch 'tests|docs|node_modules|\.venv|fixtures|\.pytest_cache|test-tmp' }

if ($ProfileFiles) {
    Write-Host "  FAIL: Found reference profile files:" -ForegroundColor Red
    $ProfileFiles | ForEach-Object { Write-Host "    $($_.FullName)" -ForegroundColor Red }
    $ErrorCount++
}

# ---------------------------------------------------------------------------
# Check 5: No Minecraft JAR contents, textures, or third-party asset packs
# ---------------------------------------------------------------------------
Write-Host "[CHECK 5] Scanning for Minecraft/third-party assets..." -ForegroundColor Yellow

$AssetExtensions = @("*.jar", "*.mcmeta", "*.nbt", "*.dat", "*.schematic")
foreach ($ext in $AssetExtensions) {
    $found = Get-ChildItem -Path $StagingDir -Recurse -Include $ext -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -notmatch '\.venv|\.git|\.pytest_cache|test-tmp' }
    if ($found) {
        Write-Host "  FAIL: Found restricted asset files ($ext):" -ForegroundColor Red
        $found | ForEach-Object { Write-Host "    $($_.FullName)" -ForegroundColor Red }
        $ErrorCount++
    }
}

# ---------------------------------------------------------------------------
# Check 6: README claims accuracy — must not claim all code is open source
# ---------------------------------------------------------------------------
Write-Host "[CHECK 6] Checking README for accuracy claims..." -ForegroundColor Yellow

$ReadmePath = Join-Path $StagingDir "README.md"
if (Test-Path $ReadmePath) {
    $content = Get-Content $ReadmePath -Raw
    if ($content -match "all.*code.*open.source" -or $content -match "complete.*offline.*import") {
        Write-Host "  FAIL: README makes inaccurate claims about open source or offline importing" -ForegroundColor Red
        $ErrorCount++
    }
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
