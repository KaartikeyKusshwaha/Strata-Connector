---
name: strata-toolkit
description: Inspect, build, stream, and animate Minecraft worlds with Strata in Blender.
trigger: Requests to inspect, import, build, open, stream, or animate a Minecraft world with Strata in Blender.
---

# Strata Toolkit

Use this skill when the user wants to work with Minecraft worlds in Blender
using Strata. This covers inspection, managed builds, Blender import, chunk
streaming, and interactive block animation.

## Prerequisites

- The Strata MCP server must be running (bundled with this plugin).
- Blender must be open with the Strata add-on enabled.
- The Blender bridge must be paired with Codex.

## Workflow

Follow these steps in order. Do not skip steps or proceed without
explicit user confirmation where noted.

### Step 1 — Confirm Environment

1. Verify the Strata MCP tools are available by checking tool discovery.
2. Ask the user for the local project/output directory where results
   will be saved.
3. If the bridge is not paired, guide the user:
   - Open Blender
   - Go to View3D > Sidebar > Strata
   - Click "Start Strata Bridge"
   - Click "Pair with Codex" to get a pairing nonce
   - Use `strata_pair_blender` with the nonce to complete pairing

### Step 2 — Preflight World

1. Use `strata_preflight_world` with the user's world path.
2. Summarize the results clearly:
   - Supported data and block counts
   - Estimated chunk count and work
   - Missing or unsupported assets
   - Privacy implications (what data is involved)
3. If the world does not exist or has errors, help the user resolve
   the issue before proceeding.

### Step 3 — Inspect Custom Library (if applicable)

1. If the user has a custom `.blend` library, use `strata_inspect_library`.
2. Show the mapping of library objects to Minecraft block IDs.
3. Highlight any diagnostic implications:
   - Unmapped block IDs that will use fallback geometry
   - Library objects that don't correspond to known block IDs
4. Let the user decide whether to proceed with the custom library.

If no custom library is available, ask where the user wants a library saved and
use `strata_generate_barebones_library`. Explain that it creates simple
procedural colored cubes plus a provenance sidecar; it does not extract
Minecraft JAR textures and is a fallback for testing/prototyping.

### Step 4 — Consent and Submit Managed Build

> **IMPORTANT**: This step uploads user data. Require explicit confirmation.

1. Before calling `strata_submit_managed_build`, tell the user:
   - Exactly which files (world and assets) will leave the device
   - Why they are being uploaded (chunk generation by the managed Engine)
   - The stated data retention behavior (e.g., "delete after download")
   - The estimated upload size
2. **Wait for explicit user confirmation** in the conversation.
3. Only then call `strata_submit_managed_build` with:
   - `world_path`: the validated world path
   - `output_directory`: the user's chosen output directory
   - `library_blend_path`: custom library path (if any)
   - `missing_asset_policy`: user's preference ("generate" or "error")
   - `chunk_size`: default 16 unless user specifies otherwise
   - `retention`: user's preference (default "delete_after_download")

### Step 5 — Monitor Build Progress

1. Use `strata_get_job_status` to check build progress.
2. Report **only actionable changes**:
   - Status transitions (queued → processing → completed)
   - Progress percentage milestones
   - Errors or failures with clear descriptions
3. Do **not** invent progress or poll excessively. Check status
   only when the user asks or at reasonable intervals.

### Step 6 — Download, Verify, and Open in Blender

1. When the build is complete, use `strata_download_result` to
   download the signed artifacts to the output directory.
2. Report the verification result (manifest signature, checksums).
3. Only after verification succeeds, ask the user if they want to
   open the result in Blender.
4. If approved, use `strata_open_result_in_blender` with the
   manifest path.

### Step 7 — Chunk Streaming and Interactive Blocks

These tools work only on the active verified scene in Blender:

1. **View chunk status**: Use `strata_get_chunk_streaming_status`
   to see loaded/pinned chunks and object counts.
2. **Load chunks**: Use `strata_load_chunk_radius` to change the
   visible working set around a center coordinate.
3. **Set block state**: Use `strata_set_interactive_block_state`
   to change a block's open/closed state (0.0–1.0).
4. **Keyframe block state**: Use `strata_keyframe_interactive_block_state`
   to animate a block state at a specific frame.

### Step 8 — Troubleshooting

If the Blender bridge is unavailable or pairing fails:

1. Do **not** retry blindly or expose a generic bridge command.
2. Guide the user through these recovery steps:
   - Ensure Blender is running
   - Check that the Strata add-on is enabled (Edit > Preferences > Add-ons)
   - Click "Start Strata Bridge" in the Strata sidebar panel
   - Click "Pair with Codex" to generate a new nonce
   - Use `strata_pair_blender` with the new nonce
3. If the session token has expired, the user needs to re-pair.

## Tool Approval Policy

| Tool | Type | Default Approval |
|------|------|------------------|
| `strata_preflight_world` | Read-only | Normal |
| `strata_inspect_library` | Read-only | Normal |
| `strata_generate_barebones_library` | Mutating (files/Blender) | User approval required |
| `strata_get_job_status` | Read-only | Normal |
| `strata_get_chunk_streaming_status` | Read-only | Normal |
| `strata_pair_blender` | Local pairing | Normal |
| `strata_submit_managed_build` | Mutating (upload) | User approval required |
| `strata_download_result` | Mutating (files) | User approval required |
| `strata_open_result_in_blender` | Mutating (Blender) | User approval required |
| `strata_load_chunk_radius` | Mutating (scene) | User approval required |
| `strata_set_interactive_block_state` | Mutating (property) | User approval required |
| `strata_keyframe_interactive_block_state` | Mutating (keyframe) | User approval required |

## References

- [Strata Architecture](../../docs/ARCHITECTURE.md)
- [Chunk Format](../../docs/CHUNKS.md)
- [Animation Guide](../../docs/ANIMATION.md)
- [Compatibility Matrix](../../docs/COMPATIBILITY.md)
