# Changelog

All notable changes to the Strata Connector will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-04

### Added
- Reference engine (`reference_engine/`) for local development and protocol testing.
- Expanded data contracts with 8 named schemas and semver versioning.
- Golden fixture files for contract validation testing.
- `SECURITY.md`, `CONTRIBUTING.md`, and issue templates.
- `COMPATIBILITY.md` with version support matrix.
- Path validation, consent review, and input size limits in MCP tools.
- Manifest signature verification and path traversal defense.
- Security test suite (`test_security.py`).
- Reference engine compatibility tests (`test_reference_engine.py`).
- GitHub Actions CI workflow.
- Release audit script updated for §9 rejection checklist.

### Changed
- Renamed `strata_submit_build` → `strata_submit_managed_build`.
- Upgraded contract version from `"1"` to `"1.0"` (semver).
- Renamed contract models: `JobRequest` → `BuildRequest`, `JobResult` → `BuildStatus`, `JobDiagnostics` → `WorldDiagnostics`.
- README rewritten to accurately describe the Connector/Engine boundary.
- Architecture documentation updated with two-component model.

### Security
- Per-session bridge token authentication (already present, verified).
- Structured error responses strip tokens, server paths, and traces.

## [1.0.0] - 2026-09-02

### Added
- Initial public Connector release.
- Blender add-on with chunk paging and bridge authentication.
- Local MCP connector with 10 named tools.
- Versioned data contracts (Pydantic v2).
- Release audit script.
- End-to-end lifecycle test.
