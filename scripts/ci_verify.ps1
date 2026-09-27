# Strata Connector CI Verification Script (§12.1)
$ErrorActionPreference = "Stop"

Write-Host "=== Step 1: Running pytest suite ===" -ForegroundColor Cyan
py -3.13 -m pytest tests/connector tests/installer tests/blender -q --basetemp=test-tmp --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Error "Pytest suite failed!"
    exit 1
}

Write-Host "=== Step 2: Running plugin package validation ===" -ForegroundColor Cyan
py -3.13 -m pytest tests/connector/test_plugin_package.py -q --basetemp=test-tmp --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Error "Plugin package test failed!"
    exit 1
}

Write-Host "=== Step 3: Running security gates tests ===" -ForegroundColor Cyan
py -3.13 -m pytest tests/connector/test_security_gates.py -q --basetemp=test-tmp --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Error "Security gate tests failed!"
    exit 1
}

Write-Host "=== Step 4: Running release package build and verification ===" -ForegroundColor Cyan
$env:STRATA_RELEASE_SIGNING_SECRET = "ci-local-$([guid]::NewGuid().ToString('N'))"
py -3.13 scripts/build_release_package.py
$env:STRATA_RELEASE_SIGNING_SECRET = $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Release package build failed!"
    exit 1
}

Write-Host "=== All Connector CI verifications PASSED ===" -ForegroundColor Green
exit 0
