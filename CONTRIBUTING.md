# Contributing to Strata Connector

Thank you for your interest in contributing! This document explains how to get involved.

## Getting Started

1. Fork the repository and clone your fork.
2. Install Python 3.13 and create an isolated environment:
   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -e ".[dev]"
   ```
3. Run the complete test suite:
   ```powershell
   python -m pytest tests -q --basetemp (Join-Path $env:TEMP 'strata-contributor-tests')
   ```
4. If Blender 4.5 is installed, run the headless scene and asset-library gate:
   ```powershell
   python -m pytest tests/blender -q
   ```

## What You Can Contribute

- **Bug fixes** for the Connector, MCP tools, or Blender bridge.
- **Contract schema improvements** (backward-compatible additions).
- **Documentation** improvements and corrections.
- **Test coverage** for MCP tools, bridge authentication, manifest validation, and reference engine compatibility.
- **Reference engine** scenarios and synthetic fixture improvements.
- **Procedural fallback library** improvements that remain legal and do not
  bundle Minecraft JARs or third-party textures.

## What This Repository Does NOT Contain

The private Strata Engine (world parsing, culling, chunk planning, asset resolution) lives in a separate private repository. Contributions to engine algorithms cannot be accepted here.

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes with clear, descriptive commit messages.
3. Ensure all tests pass: `python -m pytest tests -q`
4. Validate the Codex package:
   ```powershell
   py -3.13 C:\Users\LENONO\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py codex_plugin
   ```
   (Use the equivalent path to your local Codex plugin validator.)
5. Run `powershell -ExecutionPolicy Bypass -File .\scripts\release_audit.ps1 -StagingDir .`.
6. For the full local release gate, run
   `powershell -ExecutionPolicy Bypass -File .\scripts\ci_verify.ps1`.
7. Open a pull request with a description of what changed and why.

The public test suite uses synthetic/reference-engine data. It cannot prove a
production Minecraft conversion; that requires an authorised private Engine
endpoint and a separate consented integration run. Never commit world saves,
`.blend` projects, texture packs, credentials, signing secrets, or generated
test output.

## Code Style

- Python 3.10+ with type annotations.
- Docstrings for all public functions and classes.
- No engine module imports in `connector_mcp/` or `addon/`.

## Reporting Issues

- Use the issue templates provided for bug reports and feature requests.
- For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0-or-later license.
