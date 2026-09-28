# Strata Toolkit — Codex Plugin

The **Strata Toolkit** Codex plugin enables AI-native Minecraft world
production in Blender through a bundled MCP server and workflow skill.

## What It Does

- **Inspect** Minecraft worlds: read-only save-layout validation, estimated
  chunk counts, and missing-asset diagnostics. Block-palette counts remain a
  private Engine responsibility.
- **Build** worlds: submit managed builds with explicit consent,
- **Generate** a legal procedural fallback block library in Blender when no
  custom library is available, track progress, and download verified results.
- **Open in Blender**: import signed build results directly into
  a live Blender session via the token-authenticated bridge.
- **Stream chunks**: load and unload world chunks around a center
  point for efficient viewport navigation.
- **Animate blocks**: set and keyframe interactive block states
  (doors, trapdoors, levers, etc.) for cinematics.

## Installation

For the Windows release, install the connector and register its local
marketplace first:

```powershell
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

For a source checkout, run the same command with `--source-root` set to the
repository root. The installer downloads and verifies the signed Engine runtime
and stages it beside the MCP launcher, plugin package, and add-on. Use
`--engine-root` only for an owner-authorised offline bundle. It does not modify
Codex until the marketplace commands above are run.

Then restart Codex and:

1. Enable the Strata add-on in Blender:
   - Edit > Preferences > Add-ons
   - Search for "Strata Toolkit"
   - Enable the add-on
2. Start the bridge and pair with Codex:
   - In Blender, open the Strata panel (View3D > Sidebar > Strata)
   - Click "Start Strata Bridge"
   - Click "Pair with Codex" to get a pairing nonce
   - In Codex, the agent will use the nonce to complete pairing

## Supported Versions

| Component | Version |
|-----------|----------|
| Strata Connector | 1.1.x |
| Contract Version | 1.0 |
| Blender | 4.5 LTS+ |
| Python | 3.10 – 3.13 |
| OS | Windows 10/11 x64 |

## Available MCP Tools

### Read-Only Tools
- `strata_preflight_world` — Validate world and show capability report
- `strata_generate_barebones_library` — Create a procedural fallback library
- `strata_inspect_library` — Inspect custom `.blend` library mappings
- `strata_get_job_status` — Check build progress and status
- `strata_get_chunk_streaming_status` — View loaded chunk state
- `strata_pair_blender` — Complete bridge pairing or check status

### Mutating Tools (require user approval)
- `strata_submit_managed_build` — Submit world for managed build
- `strata_download_result` — Download verified build artifacts
- `strata_open_result_in_blender` — Open result in Blender
- `strata_load_chunk_radius` — Change visible chunk working set
- `strata_set_interactive_block_state` — Set block open/closed state
- `strata_keyframe_interactive_block_state` — Keyframe block state

## Security

- **No arbitrary code execution**: The plugin exposes only named,
  scoped Strata tools. No `eval`, `exec`, or shell commands.
- **Consent before transfer**: Managed builds require explicit user
  approval with full disclosure of files, hashes, and retention.
- **Token-authenticated bridge**: Blender communication uses
  per-session capability tokens with automatic expiry.
- **Signed artifacts**: Build results are verified against signed
  manifests with SHA-256 checksums before opening in Blender.
- **Path security**: All file paths are validated to prevent
  directory traversal and reject reserved device names.

## Architecture & Bundled MCP

This plugin bundles the Strata MCP connection declaration. The release installer
also creates a local marketplace copy whose `strata-local` MCP entry points at
the installed launcher, so users do not need to run `codex mcp add` manually.

### Deployment Modes
- **Local Developer Mode:** Runs the local `stdio` server via the packaged `strata-mcp` entry point, connecting directly to the local Blender bridge.
- **Managed Build Mode:** The local server uses `STRATA_API_MODE=http` and the
  configured authenticated Engine URL for production jobs; without that
  private service it remains in explicit synthetic fixture mode.

