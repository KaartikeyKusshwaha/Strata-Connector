# Strata Setup Guide

This guide covers the installation and configuration of the Strata pipeline and its components.

## 1. Requirements

| Requirement | Version | Note |
| :--- | :--- | :--- |
| **Python** | 3.11+ | Required for the core SDK and MCP server. |
| **Blender** | 4.0+ | Required for the MC Chunk Workflow addon. |
| **Git** | Latest | For cloning the repository. |
| **Disk Space** | ~500MB | Minimum space required for installation. |

## 2. Installation

Follow these steps to install the Strata Python package.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/strata.git
   cd strata
   ```

2. **Install the package (with development dependencies):**
   ```bash
   pip install -e ".[dev]"
   ```
   *Expected output: A successful installation message ending with `Successfully installed strata...`*

3. **Verify the installation:**
   ```bash
   python -c "import strata; print(strata.__version__)"
   ```
   *Expected output: The current version number, e.g., `0.1.0`*

## 3. Install the Blender Addon

You must install the MC Chunk Workflow addon into Blender to use Strata's scene management features.

**Option A: One-Command Installer**
Run the automated installation script from the repository root:
```bash
blender --background --python scripts/install_addon.py
```
*Expected output: `Addon 'mc_chunk_workflow' installed successfully.`*

**Option B: Manual Zip Install**
1. Zip the `addons/mc_chunk_workflow` directory.
2. Open Blender.
3. Go to `Edit > Preferences > Add-ons`.
4. Click `Install...` and select the generated zip file.
5. Check the box to enable the "MC Chunk Workflow" addon.

## 4. Configuration

Strata requires a specific directory structure to function correctly.

### Expected Directory Structure
```text
project_root/
├── data/
│   └── block_map.json      # Maps voxel IDs to Blender assets
├── assets/
│   └── strata_library.blend # Core material and asset library
└── scenes/
    └── current_shot.blend
```

### Block Map Example (`block_map.json`)
```json
{
  "minecraft:stone": {
    "material": "mat_stone",
    "collection": "assets_stone"
  },
  "minecraft:dirt": {
    "material": "mat_dirt",
    "collection": "assets_dirt"
  }
}
```

### Blender Asset Library Location
By default, the Strata addon will look for the core library at `assets/strata_library.blend` relative to your current project root. Ensure this file exists before running the pipeline.

## 5. Start the MCP Server

The Model Context Protocol (MCP) server allows AI agents to interact with your Strata pipeline.

1. **Start the server:**
   ```bash
   strata-mcp
   ```
   *Expected output: `Strata MCP Server running on stdio...`*

2. **Configure Claude Desktop / Antigravity:**
   Add the following configuration to your MCP settings file to register the Strata server:
   ```json
   {
     "mcpServers": {
       "strata": {
         "command": "strata-mcp",
         "args": []
       }
     }
   }
   ```

## 6. Troubleshooting

| Error Message | Cause | Fix |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'strata'` | The package wasn't installed in the current environment. | Ensure you activated your virtual environment and ran `pip install -e .` |
| `addon not found: mc_chunk_workflow` | Blender cannot find the addon. | Reinstall using `scripts/install_addon.py` or check Blender Preferences. |
| `FileNotFoundError: block_map.json` | Missing configuration file. | Ensure `data/block_map.json` exists in your project root. |
| `Cannot connect to MCP server` | The `strata-mcp` command is not in your PATH. | Verify Python bin/Scripts directory is in your system PATH. |
| `Blender: Unsupported version` | You are using a Blender version older than 4.0. | Upgrade Blender to 4.0 or higher. |
