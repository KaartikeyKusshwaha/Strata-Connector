# Strata Toolkit — Codex Plugin

The **Strata Toolkit** Codex plugin enables AI-native Minecraft world
production in Blender through a bundled MCP server and workflow skill.

## What It Does

- **Inspect** Minecraft worlds: preflight validation, block counts,
  chunk estimates, and missing asset diagnostics.
- **Build** worlds: submit managed builds with explicit consent,
  track progress, and download verified results.
- **Open in Blender**: import signed build results directly into
  a live Blender session via the token-authenticated bridge.
- **Stream chunks**: load and unload world chunks around a center
  point for efficient viewport navigation.
- **Animate blocks**: set and keyframe interactive block states
  (doors, trapdoors, levers, etc.) for cinematics.

## Installation

1. Install the Strata Toolkit plugin in Codex.
2. Enable the Strata add-on in Blender:
   - Edit > Preferences > Add-ons
   - Search for "Strata Toolkit"
   - Enable the add-on
3. Start the bridge and pair with Codex:
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

## Developer Notes

This plugin bundles the existing `strata-mcp` MCP server from
`connector_mcp/`. It does not duplicate engine logic or embed
private code. The plugin is a distribution and guidance layer.

For development testing, install the Connector in editable mode:
```bash
pip install -e ".[dev]"
```

Then register the MCP server locally:
```bash
codex mcp add strata-connector -- strata-mcp
```
