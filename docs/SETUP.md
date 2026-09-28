# Strata Connector Setup Guide

This guide covers the installation and configuration of the Strata Connector, local MCP server, and Blender add-on.

## 1. Requirements

| Requirement | Supported Version | Note |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 x64 | Primary platform |
| **Python** | 3.10 – 3.13 | Required for the connector and MCP server |
| **Blender** | 4.5 LTS+ | Required for the Strata add-on |
| **Git** | Latest | For cloning the repository |

---

## 2. Installation

### Release archive (recommended for artists, after publication)

After a v1.1.1 release has been published, download the ZIP and `.sha256` file
from the GitHub releases page, verify the hash, extract the archive, and run
the bundled installer from PowerShell:

```powershell
$sourceRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector-v1.1.1'
Set-Location $sourceRoot
$installDir = Join-Path $env:LOCALAPPDATA 'Strata'
$addonsDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
py -3.13 -m installer.install `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir `
  --register-codex `
  --json
codex plugin marketplace add "$installDir\codex-marketplace"
codex plugin add strata-toolkit@strata-local
```

The installer places the add-on in Blender's 4.5 user add-ons directory and
uses an isolated runtime for the MCP server. Restart Codex after installing
the plugin. The full hash-verification and pairing procedure is in
[LIVE_DEVICE_TEST_SETUP.md](LIVE_DEVICE_TEST_SETUP.md).

### Developer checkout

Follow these steps to set up the Strata Connector:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git
   cd Strata-Connector
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install the package (with development and test dependencies):**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify the installation:**
   ```bash
   python -c "import connector_mcp, contracts, reference_engine; print('Strata Connector ready')"
   pytest tests -q --basetemp=.pytest_cache/test-tmp
   ```

---

## 3. Install the Blender Add-on

The Strata add-on provides chunk paging, viewport visibility controls, and a localhost bridge for AI-driven workflows.

1. For a release install, the installer has already copied the add-on. For a
   source checkout, navigate to **Edit > Preferences > Add-ons**.
2. Click the drop-down arrow in the top right and select **Install from Disk...** (or install the `addon` directory).
3. Enable **Strata Toolkit**.
4. In the 3D Viewport N-panel, open the **Strata** tab.
5. Click **Start Strata Bridge** to start the token-authenticated localhost server.

---

## 4. Configure the MCP Server

The local Model Context Protocol (MCP) server allows AI assistants (like Codex, Claude, or Antigravity) to manage builds, stream chunks, and adjust interactive block states.

### Running Directly
```bash
strata-mcp
```

### Configuring Claude Desktop / Antigravity
Add the following to your MCP client configuration (`claude_desktop_config.json` or Antigravity MCP settings):

```json
{
  "mcpServers": {
    "strata-connector": {
      "command": "C:\\path\\to\\Strata-Connector\\.venv\\Scripts\\strata-mcp.exe",
      "args": []
    }
  }
}
```

---

## 5. Build Modes

The Connector supports two workflows:
- **Managed Build**: Connects to the private Strata Engine service after explicit consent review. Generates production-quality A1 streamed chunks and signed manifests.
- **Reference Engine (Developer/Test)**: Uses the built-in `reference_engine` with synthetic fixtures for offline testing, protocol development, and CI.

For a clean Windows installation from a release archive, use
[LIVE_DEVICE_TEST_SETUP.md](LIVE_DEVICE_TEST_SETUP.md). The public archive
does not include the private world parser/worker or a production Engine URL;
installing Blender and supplying a world save alone therefore produces only a
preflight report (or synthetic fixture output), not a real conversion.

### Maintainer release build

Release signing is fail-closed. Set the owner-managed secret in the process
environment (never commit it), then run `py -3.13
scripts/build_release_package.py`. CI uses an ephemeral validation key; a
published release must be rebuilt with the production signing configuration and
its public verification key configured for the deployed Connector.

---

## 6. Troubleshooting

| Error / Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'connector_mcp'` | Package not installed in the active environment. | Activate `.venv` and run `pip install -e .` |
| `Cannot connect to Blender bridge` | Bridge server is not running or Blender is closed. | Open Blender, enable the Strata add-on, and start the bridge. |
| `Session token is required` / `TokenInvalidError` | Mismatched or missing ephemeral session token. | Ensure the bridge is running and the token was generated by the active session. |
| `ManifestValidationError: Contract major version mismatch` | The manifest was generated with an incompatible contract major version. | Check [COMPATIBILITY.md](COMPATIBILITY.md) and update the Connector. |
| `PathSecurityError: Output path escapes result directory` | A file in the manifest attempted directory traversal. | Reject the unverified artifact. Do not open in Blender. |
