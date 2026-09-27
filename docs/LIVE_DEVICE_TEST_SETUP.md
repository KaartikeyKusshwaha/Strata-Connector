# Live Blender & World Test Setup Guide for Clean Device

This guide outlines the exact prerequisites and steps for testing Strata on the target device.

---

## 1. Prerequisites (Software to Install)

1. **Git for Windows**: [git-scm.com](https://git-scm.com/download/win)
2. **Python 3.13 (or 3.12)**: [python.org](https://www.python.org/downloads/) (ensure **"Add python.exe to PATH"** is checked)
3. **Blender 4.5 LTS**: [blender.org/download/lts/4-5/](https://www.blender.org/download/lts/4-5/)
4. **Minecraft Java Edition World Save**:
   - Any valid Java Edition world directory (containing `level.dat` and `region/*.mca` files).
   - Typically located in `%APPDATA%\.minecraft\saves\<WorldName>`

---

## 2. Option A: Install from Official GitHub Release (Recommended)

1. Download `strata-connector-windows-x64-v1.1.0.zip` from:
   👉 **[Strata Connector v1.1.0 Release](https://github.com/KaartikeyKusshwaha/Strata-Connector/releases/tag/v1.1.0)**

2. Extract the ZIP into a clean folder, e.g. `C:\Strata-Connector`.

3. Open PowerShell inside the extracted directory and run the installer:
   ```powershell
   py -3.13 -m installer.install
   ```

4. Verify that:
   - The launcher is installed at `%LOCALAPPDATA%\Strata\bin\strata-mcp.cmd`
   - The Blender add-on is installed in `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\strata_toolkit\`

---

## 3. Option B: Developer / Git Checkout

1. Clone the repository:
   ```powershell
   git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git
   cd Strata-Connector
   ```

2. Install dev dependencies:
   ```powershell
   py -3.13 -m pip install -e ".[dev]"
   ```

3. Run verification suite:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\ci_verify.ps1
   ```

---

## 4. Enabling the Blender Add-on & Pairing

1. Open **Blender 4.5**.
2. Go to **Edit > Preferences > Add-ons**.
3. Search for **Strata** (or **Strata Toolkit**) and check the box to enable it.
4. Press `N` in the 3D Viewport to reveal the side panel, and click the **Strata** tab.
5. Click **Start Bridge**.
6. The panel will display a **Pairing Nonce** (6 digits or token).
7. Approve the pairing dialog in Blender.

---

## 5. Running the Full World Import Pipeline

Once the bridge is running:

1. **Option 1: Using MCP / Codex Desktop**
   - Codex will detect the local MCP tools (`strata_bridge_health`, `strata_inspect_world`, `strata_stream_chunks`, etc.).
   - Ask Codex:
     > *"Inspect world at `C:\path\to\world` and stream chunks around coordinates (0, 64, 0) into Blender."*

2. **Option 2: Direct Add-on UI**
   - In the Blender Strata panel, select the World path (`C:\path\to\world`).
   - Select Chunk Radius (e.g. `3`).
   - Click **Import Chunks**.
   - Chunks, geometry, materials, and lighting will generate in the active Blender scene.
