# Live Blender and Minecraft-world test guide

This is the clean-device acceptance procedure for Strata Connector. A Blender
installation and a Minecraft Java save are required for the no-cloud real
conversion lane. The public Connector installer downloads the pinned, signed
Engine runtime automatically; the private `engine_local` bundle is only an
offline/private override. Fixture mode is deliberately synthetic and must not
be reported as a real world import.

## 1. Install prerequisites

Install the following on a clean Windows account:

1. Git for Windows: <https://git-scm.com/download/win>
2. Python 3.13 (3.12 is also supported): <https://www.python.org/downloads/>.
   Enable **Add python.exe to PATH**.
3. Blender 4.5 LTS: <https://www.blender.org/download/lts/4-5/>.
4. A Java Edition world directory containing `level.dat` and, normally,
   `region\*.mca` files (for example `%APPDATA%\.minecraft\saves\WorldName`).
5. No Engine checkout is required for the public-release lane. Keep any
   owner-authorised `engine_local` override outside GitHub.

Keep the original world read-only or work on a copy. Strata must not modify
the source save.

## 2. Verify and install the release

This release lane is valid only after the v1.1.3 GitHub release has been
published with both assets. Download
`strata-connector-windows-x64-v1.1.3.zip` and its `.sha256` asset from the
[v1.1.3 release](https://github.com/KaartikeyKusshwaha/Strata-Connector/releases/tag/v1.1.3).
If the release page has no archive, stop and use the developer-checkout lane in
Section 4; a local archive is not evidence of a public release.
Run this from PowerShell; do not skip the hash check:

```powershell
$zip = Join-Path $env:USERPROFILE 'Downloads\strata-connector-windows-x64-v1.1.3.zip'
$expected = (Get-Content "$zip.sha256").Split()[0]
$actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
if ($actual -ne $expected.ToLowerInvariant()) { throw 'Strata archive checksum mismatch.' }

$sourceRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector-v1.1.3'
Expand-Archive -LiteralPath $zip -DestinationPath $sourceRoot
Set-Location $sourceRoot
$installDir = Join-Path $env:LOCALAPPDATA 'Strata'
$addonsDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
py -3.13 -m installer.install `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir `
  --register-codex `
  --json
```

For a source-checkout installation (useful for testing this repository before
the release assets are published), replace `$sourceRoot` with the cloned
checkout and run:

```powershell
$sourceRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector'
$installDir = Join-Path $env:LOCALAPPDATA 'Strata'
$addonsDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git $sourceRoot
Set-Location $sourceRoot
py -3.13 -m installer.install `
  --source-root $sourceRoot `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir `
  --register-codex `
  --json
```

This source lane validates installation and workflow behavior, but it does not
replace the signed-release acceptance gate. Both lanes automatically download
and verify the Engine runtime. To test an authorised offline bundle instead,
add `--engine-root 'D:\FILES\engine_local'` to the installer command; that
explicit override disables the download.

The command installs the isolated runtime, launcher, Codex plugin, and Blender
add-on. It also creates a local Codex marketplace at
`$installDir\codex-marketplace`. Register and install it explicitly:

```powershell
codex plugin marketplace add "$installDir\codex-marketplace"
codex plugin add strata-toolkit@strata-local
codex plugin list
```

Restart Codex (or start a new chat) after installing the plugin. In Blender,
enable **Strata Toolkit** under **Edit > Preferences > Add-ons**, open the
**Strata** sidebar tab, click **Start Bridge**, then click **Pair with Codex**
and approve the displayed nonce in Blender. The pairing value must be the same
for both processes; a mismatch is an error.

## 3. Exercise the actual MCP workflow

The shipped 12 tool names are `strata_preflight_world`,
`strata_inspect_library`, `strata_generate_barebones_library`,
`strata_submit_managed_build`,
`strata_get_job_status`, `strata_download_result`,
`strata_open_result_in_blender`, `strata_get_chunk_streaming_status`,
`strata_load_chunk_radius`, `strata_set_interactive_block_state`, and
`strata_keyframe_interactive_block_state`, plus `strata_pair_blender`. Do not
use older names such as `strata_bridge_health`, `strata_inspect_world`, or
`strata_stream_chunks`.

Run the tools in this order:

1. `strata_preflight_world` with the copied world path; record the manifest,
   checksum, `level.dat`, and region-file results.
2. `strata_pair_blender` with the approved Blender nonce; verify that the
   returned session is paired before using mutating bridge tools.
3. `strata_inspect_library`; verify the generated/barebones library and its
   provenance, or capture the reported fallback/error.
4. If no custom library exists, call `strata_generate_barebones_library` and
   verify the `.blend` plus `.provenance.json` sidecar. This is a procedural
   fallback, not Minecraft texture extraction.
5. Confirm user consent for the build, then call
   `strata_submit_managed_build` with the preflight manifest and world path.
6. Poll `strata_get_job_status` until it is `succeeded` or `failed`.
7. Call `strata_download_result`; verify the downloaded result manifest and
   checksums before opening anything.
8. Call `strata_open_result_in_blender`; it must reject missing or invalid
   manifests and then open/link the master scene and chunk scenes.
9. Exercise chunk-radius streaming and one block-state update/keyframe.

For a real local conversion, the installed launcher defaults to
`STRATA_API_MODE=local` and starts the bundled Engine API/worker on loopback.
Set `STRATA_ENGINE_ROOT=$env:LOCALAPPDATA\Strata\engine` and run the opt-in
`tests\connector\test_local_engine_live.py` with the supplied world and
coordinate bounds. An HTTPS endpoint is optional; use `STRATA_API_MODE=http`
only for the remote managed lane. If neither local bundle nor remote service
is available, remain in fixture/offline mode and mark real conversion
**BLOCKED**.

## 4. Developer checkout and tests

```powershell
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git
Set-Location Strata-Connector
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests -q
powershell -ExecutionPolicy Bypass -File .\scripts\ci_verify.ps1
```

The test suite validates contracts and synthetic behavior; it does not replace
the Blender/Engine run above.

## 5. Uninstall / rollback

```powershell
py -3.13 -m installer.install --uninstall `
  --install-dir "$env:LOCALAPPDATA\Strata" `
  --blender-addons-dir "$env:APPDATA\Blender Foundation\Blender\4.5\scripts\addons"
```

This removes Strata files only. It does not delete Minecraft worlds, Blender
projects, custom libraries, or downloaded results.
