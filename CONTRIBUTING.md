# Contributing to Strata Connector

Thank you for your interest in contributing! This document explains how to get involved.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   pip install -e ".[dev]"
   ```
3. Run the test suite to verify your setup:
   ```bash
   pytest tests -q --basetemp=.pytest_cache/test-tmp
   ```

## What You Can Contribute

- **Bug fixes** for the Connector, MCP tools, or Blender bridge.
- **Contract schema improvements** (backward-compatible additions).
- **Documentation** improvements and corrections.
- **Test coverage** for MCP tools, bridge authentication, manifest validation, and reference engine compatibility.
- **Reference engine** scenarios and synthetic fixture improvements.

## What This Repository Does NOT Contain

The private Strata Engine (world parsing, culling, chunk planning, asset resolution) lives in a separate private repository. Contributions to engine algorithms cannot be accepted here.

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes with clear, descriptive commit messages.
3. Ensure all tests pass: `pytest tests -q`
4. Run the release audit: `powershell scripts/release_audit.ps1`
5. Open a pull request with a description of what changed and why.

## Code Style

- Python 3.10+ with type annotations.
- Docstrings for all public functions and classes.
- No engine module imports in `connector_mcp/` or `addon/`.

## Reporting Issues

- Use the issue templates provided for bug reports and feature requests.
- For security vulnerabilities, see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0-or-later license.
