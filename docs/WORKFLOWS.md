# Strata workflows

These workflows describe the tools shipped by the current public Connector.
For installation and pairing, see [SETUP.md](SETUP.md) and
[LIVE_DEVICE_TEST_SETUP.md](LIVE_DEVICE_TEST_SETUP.md).

## 1. Verified world-build workflow

**Purpose:** Convert a Minecraft Java save through the private Engine and open
the verified result in Blender.

1. Start Blender's Strata Bridge and pair it with Codex.
2. Run `strata_preflight_world` on a read-only copy of the world.
3. Inspect a custom library with `strata_inspect_library`, or generate a
   procedural fallback using `strata_generate_barebones_library`.
4. Show the consent summary from `strata_submit_managed_build` and wait for
   explicit approval before any upload.
5. Poll `strata_get_job_status` until the job reaches a terminal state.
6. Download with `strata_download_result`; check the manifest and checksums.
7. Open with `strata_open_result_in_blender` only after verification succeeds.

The public Connector does not contain the world parser or production worker.
With the default fixture client, this workflow creates synthetic artifacts and
must not be described as a real world conversion.

## 2. Offline reference workflow

Use this for contributor and plugin testing without private services:

1. Leave `STRATA_API_MODE` unset (fixture mode).
2. Pair Blender if you want to test bridge operations; the build artifacts can
   also be verified outside Blender.
3. Submit a synthetic job, mark it complete in a test harness, download it,
   and open the verified manifest.
4. Run the chunk and interactive-block tools against the paired Blender scene.

The reference engine is deterministic and legal for CI. It is not a Java
blockstate/model/texture importer.

## 3. Custom and fallback library workflow

1. Use `strata_inspect_library` for a user-supplied `.blend` path. The source
   library is read-only and is never overwritten.
2. If no library exists, use `strata_generate_barebones_library` with an
   absolute `.blend` path. The add-on creates simple colored cube prototypes,
   attaches block-ID metadata, and writes a provenance sidecar.
3. Treat the fallback as a prototyping library. Vanilla Minecraft textures,
   custom texture packs, and model inheritance require the private Engine or
   an explicitly supplied legal asset pipeline.

## 4. Chunk viewport workflow

Once a verified result is linked into Blender:

1. Call `strata_get_chunk_streaming_status` to inspect loaded and visible
   chunks.
2. Call `strata_load_chunk_radius` around the working center to show or hide
   collections outside the current working set.
3. Keep source results and the user's master scene separate; do not edit the
   original Minecraft save.

## 5. Interactive block animation

For supported block-only rigs:

1. Call `strata_set_interactive_block_state` with the object name and a value
   from `0.0` (closed) to `1.0` (open).
2. Call `strata_keyframe_interactive_block_state` at the desired frame.
3. Confirm the change in Blender before rendering.

The public tool surface does not expose arbitrary Python execution or a
generic scene command.

## 6. Environment and render validation

The repository's Blender headless gate validates a synthetic scene containing
terrain, water geometry/materials, fog/mist volume, cloud proxies, a Nishita
sky, day/night lighting, visibility toggles, and the procedural fallback
library. These checks prove Blender-side integration only; they do not prove
that a private Engine generated a world.

## 7. Common mistakes

- Using a folder without `level.dat` or region files as a Minecraft world.
- Calling the old `import_minecraft_world`, `get_scene_status`, or
  `generate_environment` names; they are not shipped tools.
- Opening a result before `strata_download_result` verifies its manifest.
- Assuming fixture output contains real Minecraft geometry or textures.
- Uploading a source world without reviewing the consent and retention policy.
