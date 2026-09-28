# Strata quickstart

This quickstart uses the current Strata MCP tool names. The public Connector
can run a complete synthetic/reference workflow offline. A real Minecraft
conversion uses the authorised local `engine_local` bundle by default, or an
authenticated private HTTPS Engine as an optional remote lane.

## Before you begin

- Windows 10/11 x64, Python 3.13, and Blender 4.5 LTS.
- A copy of a Java world save containing `level.dat` and `region\*.mca`.
- The Strata release installed and its local Codex marketplace registered.
  Follow [LIVE_DEVICE_TEST_SETUP.md](LIVE_DEVICE_TEST_SETUP.md) for the exact
  hash-check and installer commands.
- The private `engine_local` bundle copied to `D:\FILES\engine_local` for a
  real no-cloud conversion.
- Codex restarted after the plugin was installed.

## 1. Start and pair Blender

1. Open Blender and enable **Strata Toolkit** under **Edit > Preferences >
   Add-ons**.
2. Open the 3D Viewport sidebar with `N`, select **Strata**, and click
   **Start Strata Bridge**.
3. Click **Pair with Codex**, approve the displayed request in Blender, and
   have Codex call `strata_pair_blender` with the same nonce.

## 2. Preflight the world

Ask Codex to call `strata_preflight_world` with the absolute path to a copied
world. Check `world_valid`, `level_dat_present`, `region_file_count`, and
`missing_assets`. This is a read-only layout check; the public Connector does
not parse block palettes or Minecraft JAR textures.

## 3. Choose a block library

- With a custom `.blend`, call `strata_inspect_library` and review its report.
- Without one, call `strata_generate_barebones_library` with an absolute
  `.blend` output path. It creates simple procedural colored cubes and a
  `.provenance.json` sidecar for prototyping; it is not a vanilla texture
  extractor.

## 4. Run a build

For an offline smoke test, leave the Connector in fixture mode. For a real
local conversion, set `STRATA_API_MODE=local` (the installed launcher does
this automatically) and use the staged Engine. Configure
`STRATA_API_MODE=http`, a reachable `STRATA_API_URL`, and authentication
variables only for the optional remote lane.

1. Review the consent summary returned by `strata_submit_managed_build` and
   explicitly approve any upload of world or asset data.
2. Poll `strata_get_job_status` until the job succeeds or fails.
3. Call `strata_download_result` into an empty output directory. It must write
   the manifest and artifacts and verify their checksums.
4. Call `strata_open_result_in_blender` only after download verification
   succeeds. The MCP layer and add-on both reject missing or invalid manifests.

## 5. Work with chunks and animation

- `strata_get_chunk_streaming_status` reports loaded and visible chunks.
- `strata_load_chunk_radius` changes the visible working set.
- `strata_set_interactive_block_state` and
  `strata_keyframe_interactive_block_state` control supported block-only rigs.

The old `import_minecraft_world`, `get_scene_status`, and `generate_environment`
names are not shipped MCP tools. Do not use them as examples.

## Expected result

Fixture mode produces verified synthetic files and is useful for testing the
plugin, bridge, manifests, and Blender linking. Only a successful run against
the local or remote real Engine should be described as a converted Minecraft
world.
