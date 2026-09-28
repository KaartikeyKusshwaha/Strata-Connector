# Strata clean-device feature test runbook

**Audience:** an independent tester on a different Windows device.

**Purpose:** test every feature currently advertised by the public Strata
Connector, Blender add-on, MCP server, Codex plugin package, installer, and
the optional managed Engine path without confusing synthetic reference output
with a real Minecraft conversion.

**Latest Connector commit to test:** `8d7199b3e5d03f472dd5e99944d5958d6271bd79`
(`fix: honor configured Strata Engine endpoint`). The GitHub CI run for this
commit passed Python 3.12, Python 3.13, MCP discovery, and plugin validation.
The published `v1.1.1` archive predates this commit; use the source-checkout
lane below when testing the latest endpoint fix.

## 0. Read this before testing

Strata has two deliberately separate execution modes:

| Mode | What it proves | What it does not prove |
|---|---|---|
| Public/reference mode | Installation, contracts, security gates, MCP registration, Blender bridge, procedural fallback library, synthetic artifacts, and Blender-side visibility/render behavior | A real Java world parser, Minecraft block/material resolution, or production world-to-Blender conversion |
| Managed Engine mode | Real upload/authentication, private parsing/culling/chunk planning, worker output, verified result download, and real-world Blender hand-off | Nothing beyond the exact Engine deployment and test world authorised for the run |

The public repository does **not** contain the production parser, private asset
profiles, Minecraft JAR contents, or a deployed cloud Engine. A test that only
installs Blender and supplies a world save must be marked **BLOCKED for real
conversion** unless a reachable, authenticated private Engine endpoint is also
provided. Never call a synthetic fixture result a Minecraft import.

The current local Engine source can be used by the owner for API connectivity
checks, but its checked-in API is an in-memory lifecycle server and its worker
artifacts are placeholders. It is not evidence of production conversion.

## 1. Status and evidence rules

Use exactly one status for every test:

- **PASS** — the stated observable result was produced and evidence was saved.
- **FAIL** — the feature was expected in this lane but behaved incorrectly.
- **BLOCKED** — a required external prerequisite or authorised Engine service
  was unavailable. Do not work around it by changing the product or manually
  adding an MCP server.
- **NOT APPLICABLE** — the selected lane excludes the feature.

Create an evidence directory outside the repository:

```powershell
$testRoot = Join-Path $env:USERPROFILE 'Desktop\Strata-Clean-Device-Acceptance'
New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $testRoot 'logs') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $testRoot 'screenshots') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $testRoot 'outputs') | Out-Null
```

Do not put raw worlds, API tokens, pairing nonces, private `.blend` files,
Minecraft JARs, or proprietary textures in GitHub, the repository, or the
evidence archive. Save only hashes, manifests, screenshots, sanitized logs,
and the final status table.

For every test record the date/time, device/OS, software versions, exact
commit, test lane, command or MCP tool, expected result, actual result, status,
and an evidence filename.

## 2. Manual installations

Install these items manually before the test:

1. **Windows 10/11 x64.** The current installer and documented UI lane target
   Windows.
2. **Git for Windows:** <https://git-scm.com/download/win>.
3. **Python 3.13** (3.12 is also supported by CI), from
   <https://www.python.org/downloads/>. Install the `py` launcher and put
   `python.exe` on PATH. Verify `py -3.13 --version`.
4. **Blender 4.5 LTS or later:**
   <https://www.blender.org/download/lts/4-5/>.
5. **Codex desktop**, signed in to an account that can install local plugins.
   Install the `codex` CLI too if the command-line plugin lane is used; verify
   `codex --version`. If the desktop build has no CLI, use its plugin UI and
   record that route.
6. **Optional Docker Desktop** only for an owner-authorised private Engine
   staging test. It is not needed for public Connector tests.

Minecraft Java itself, a Minecraft JAR, vanilla textures, and third-party
assets are not required. The tester receives an authorised Java save folder.
Allow Blender/Python on loopback only if Windows Firewall asks: the bridge must
remain on `127.0.0.1:9877`, never a public interface.

## 3. Inputs the owner must provide

Transfer these privately and separately from GitHub:

- A **read-only copy** of the Minecraft Java world directory containing
  `level.dat` and relevant `region\*.mca` files, including dimension folders if
  needed.
- The source `.blend` scene used in the original Blender project, copied
  read-only. It must never be overwritten.
- The exact coordinate sheet used in that project: Minecraft origin, requested
  center, expected bounds, dimension, chunk size, and known A1 chunk names.
- Optionally, an authorised custom library `.blend`, textures/linked libraries,
  and exporter settings.
- For a real managed run only: a reachable HTTPS Engine URL, disposable device
  identity/auth flow, tiny authorised world, and retention/deletion approval.

The documented default is a 16-block chunk size and Minecraft `(x, y, z)` to
Blender `(x, z, y)`, but the tester must compare the actual preflight/manifest
values with the supplied coordinate sheet rather than assume them.

## 4. Acquire the exact Connector

Use the latest pushed source commit for this acceptance run:

```powershell
$workRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Clean-Device'
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git $workRoot
Set-Location $workRoot
git checkout 8d7199b3e5d03f472dd5e99944d5958d6271bd79
git rev-parse HEAD
```

The printed SHA must match the SHA in this document. The public `v1.1.1`
archive is earlier than this commit; record its archive hash if that lane is
used and do not call it the latest-commit test.

## 5. Install and run the package gates

```powershell
Set-Location $workRoot
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -c "import connector_mcp, contracts, reference_engine; print('imports: PASS')"
New-Item -ItemType Directory -Force -Path 'test-tmp' | Out-Null
.\.venv\Scripts\python.exe -m pytest tests\connector -q --basetemp=test-tmp --tb=short
.\.venv\Scripts\python.exe -m pytest tests\installer -q --basetemp=test-tmp --tb=short
.\.venv\Scripts\python.exe -m pytest tests\blender -q --basetemp=test-tmp --tb=short
powershell -ExecutionPolicy Bypass -File .\scripts\ci_verify.ps1
```

A Blender test skipped because Blender is absent is **BLOCKED/NOT APPLICABLE**,
not a pass.

## 6. Install the add-on, launcher, and Codex plugin

```powershell
$installDir = Join-Path $env:LOCALAPPDATA 'Strata'
$addonsDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
.\.venv\Scripts\python.exe -m installer.install `
  --source-root $workRoot `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir `
  --register-codex `
  --json | Tee-Object (Join-Path $testRoot 'logs\install.json')
```

Verify the install JSON reports success and these paths exist:

```powershell
Test-Path (Join-Path $installDir 'runtime')
Test-Path (Join-Path $installDir 'bin\strata-mcp.cmd')
Test-Path (Join-Path $installDir 'codex-plugin')
Test-Path (Join-Path $addonsDir 'strata_toolkit')
Test-Path (Join-Path $installDir 'codex-marketplace\marketplace.json')
```

Register the installed local marketplace and then restart Codex:

```powershell
codex plugin marketplace add (Join-Path $installDir 'codex-marketplace')
codex plugin add strata-toolkit@strata-local
codex plugin list
```

The plugin test must pass without a manual `codex mcp add`. Manual MCP
registration tests the standalone server only, not the bundled plugin path.

## 7. Plugin and MCP discovery

| ID | Action | Expected evidence |
|---|---|---|
| `PLG-001` | Install `strata-toolkit` from the local marketplace | Plugin is installed and its bundled MCP entry is present |
| `PLG-002` | Inspect installed `plugin.json` and `.mcp.json` | Required interface fields, skills, and MCP declaration are present |
| `PLG-003` | Start the installed `strata-mcp` launcher | stdio server starts and exits cleanly |
| `MCP-001` | Ask Codex to list Strata tools | Current 12 named tools are discoverable |
| `MCP-002` | Check for removed/old names | No `strata_bridge_health`, `strata_inspect_world`, or `strata_stream_chunks` |
| `MCP-003` | Call one read-only tool with an approved path | Structured response includes `contract_version` and `operation_id` |
| `SEC-001` | Try traversal/out-of-root paths and oversized input | Structured security error; no filesystem escape |
| `SEC-002` | Inspect output/logs | No token, nonce, or private server path is leaked |

For a managed lane, set these before launching MCP/Codex and use the owner-
provided URL, not the placeholder domain:

```powershell
$env:STRATA_API_MODE = 'http'
$env:STRATA_API_URL = 'https://<authorised-engine-host>'
```

## 8. Blender add-on and scene-safety tests

1. Open a copy of the supplied `.blend` with automatic Python execution
   disabled for the first inspection. Check linked libraries and missing image
   paths before changing anything.
2. Save a new working copy under the evidence/output directory and keep the
   `.blend1` backup. Never save over the owner source.
3. Enable **Strata Toolkit** under **Edit > Preferences > Add-ons**.
4. In the 3D Viewport press `N`, open **Strata**, and verify the bridge panel
   shows **Start Strata Bridge**, **Stop Strata Bridge**, **Pair with Codex**,
   and **Approve Pairing** when applicable.
5. Confirm these intentionally removed controls are absent: **Rig Chunk**,
   **Rig + Neighbors**, **Select Steve Rig**, **Block Edit Tools**, **Pick Block
   by Screen Box**, and **Pick Block by Ray**.
6. Register/unregister the add-on and confirm the source copy's meshes,
   materials, textures, linked libraries, and world data are unchanged.

## 9. Live bridge and pairing

| ID | Action | Expected result |
|---|---|---|
| `BRIDGE-001` | Click **Start Strata Bridge** | Loopback `127.0.0.1:9877` listens; panel says awaiting pairing |
| `BRIDGE-002` | Click **Pair with Codex** | Blender displays one short-lived nonce |
| `BRIDGE-003` | Approve it in Blender, then call `strata_pair_blender` with that exact nonce | MCP reports `paired` with live session state |
| `BRIDGE-004` | Call `strata_get_chunk_streaming_status` | Response comes from the live Blender session |
| `BRIDGE-005` | Stop/restart bridge or expire the session | Old token is rejected; re-pair is required |
| `BRIDGE-006` | Submit a wrong/stale nonce | Pairing is rejected; no command is authorised |

If the nonce accepted by MCP differs from Blender's displayed nonce, mark
**FAIL**. Do not create a second manual pairing state to hide it.

## 10. World and coordinate preflight

Use a read-only world copy:

```powershell
$world = Join-Path $testRoot 'inputs\world'
if (-not (Test-Path (Join-Path $world 'level.dat'))) { throw 'level.dat missing' }
$regionFiles = @(
  Get-ChildItem (Join-Path $world 'region') -Filter '*.mca' -File -ErrorAction SilentlyContinue
  Get-ChildItem (Join-Path $world 'DIM-1\region') -Filter '*.mca' -File -ErrorAction SilentlyContinue
  Get-ChildItem (Join-Path $world 'DIM1\region') -Filter '*.mca' -File -ErrorAction SilentlyContinue
)
"region_files=$($regionFiles.Count)"
```

Call `strata_preflight_world` and save its response. Require `world_exists`,
`world_valid`, `level_dat_present`, and a stable `world_sha256`; compare region
count, dimension, chunk size, and coordinate mapping to the owner's sheet.
Preflight inventories/fingerprints the save; it does not parse block palettes.

## 11. Custom and generated asset-library tests

### Custom library

1. Call `strata_inspect_library` on the read-only custom `.blend`.
2. Record object names, linked libraries, image availability, and provenance.
3. Confirm the source library is not overwritten.
4. Report missing/unsupported assets explicitly; never assume vanilla textures
   are downloaded.

### Procedural fallback library

1. In paired Blender call `strata_generate_barebones_library` with an absolute
   `.blend` path.
2. Verify the `.blend` and `.provenance.json` sidecar are non-empty.
3. Open it and confirm the procedural stone, dirt, grass, oak planks, glass,
   and water profiles exist with materials.
4. Confirm provenance says procedural fallback and no Minecraft JAR/third-party
   texture source was used.
5. Repeat to check idempotent names; request an unsupported block ID and expect
   an explicit error with no partial output.

This is a legal geometry/material fallback, not Minecraft texture extraction.

## 12. Managed real-world build (only with an authorised Engine)

Without a reachable authenticated Engine, mark this section **BLOCKED**, not
PASS. The public fixture client is not a world converter.

1. Set HTTP mode/URL before MCP starts; verify `/healthz` and `/readyz`.
2. Authenticate with a disposable device identity; do not save the token.
3. Preflight the tiny authorised world and review consent, hashes, purpose, and
   retention.
4. Call `strata_submit_managed_build` only after approval.
5. Poll `strata_get_job_status` to a documented terminal state. A job that
   remains queued without worker progress is a deployment defect.
6. Call `strata_download_result`. Require a manifest, valid contract major,
   bytes for every checksum-listed artifact, and successful signature/checksum
   verification. A URL or success-shaped JSON without files fails.
7. Call `strata_open_result_in_blender`; it must verify first, then link the
   master/chunk scenes and report real object/collection counts.
8. Compare chunk names, bounds, dimensions, origin, and axis mapping with the
   supplied coordinate sheet. Confirm custom assets and source scenes remain
   unchanged.
9. Verify documented retention/deletion after download or cancellation.

Placeholder bytes, empty chunks, fixture manifests, or an HTTP 200 without
valid Blender geometry are **FAIL** for real conversion.

## 13. Artifact and hand-off failure tests

These can use synthetic fixtures to test validation logic, but only an Engine
result proves world conversion:

| ID | Action | Expected result |
|---|---|---|
| `ART-001` | Download a completed result | Atomic promotion happens only after manifest/checksum validation |
| `ART-002` | Remove manifest/artifact | Truthful error; no partial output |
| `ART-003` | Change one artifact byte | Checksum mismatch; Blender is not touched |
| `ART-004` | Put `..` or an absolute path in a manifest | Path traversal rejection |
| `ART-005` | Open missing/empty/malformed manifest | Structured error; scene unchanged |
| `ART-006` | Open valid real result | Verified master/chunk collections link with counts/hash |

Reopen a valid result copy with autoexec disabled and confirm linked collections
survive the reopen.

## 14. A1 chunk streaming and coordinates

Use the owner's exact coordinates, not invented examples:

1. Call `strata_get_chunk_streaming_status` and record loaded/pinned/center and
   object counts.
2. Call `strata_load_chunk_radius` around the supplied center with a small
   radius.
3. Confirm only expected `Chunk_x<sign><coord>_y<sign><coord>_z<sign><coord>`
   collections are visible in viewport/render; outside chunks are hidden.
4. Move the center and repeat; confirm no duplicate working set is created.
5. Restore initial visibility and save a copy.
6. Compare names, bounds, and object positions with the coordinate sheet; any
   axis inversion or offset is **FAIL**.

## 15. Interactive block-state tests

Use an object that the supplied scene/Engine declares as a supported interactive
block rig; do not invent a Steve rig.

1. Set `strata_open` to 0.0, then 1.0 using
   `strata_set_interactive_block_state` and inspect Blender's custom property.
2. Call `strata_keyframe_interactive_block_state` at two frames and inspect the
   F-curve/keyframes.
3. Use an unknown object name and require a structured error.
4. Save/reopen and verify the intended keyframes survive.

If the supplied world has no supported interactive rig, mark this feature
**NOT APPLICABLE** and retain the response evidence.

## 16. Synthetic Blender environment/render gates

Run the repository gate after installing Blender:

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
& $blender -b --python (Join-Path $workRoot 'scripts\blender_headless_verify.py')
Get-Content (Join-Path $workRoot 'test-tmp\renders\render_audit.json')
```

Require `PASS` for `RENDER-TERRAIN`, `RENDER-WATER`, `RENDER-FOG`,
`RENDER-CLOUDS`, `RENDER-SKY`, `RENDER-LIGHT-DAY`, `RENDER-LIGHT-NIGHT`,
`RENDER-TOGGLE`, and `ASSET-LIBRARY`. These are deterministic Blender-side
synthetic gates. Repeat equivalent visual checks on a real Engine result before
claiming terrain, water, fog/mist, clouds, sky, lighting, or day/night behavior
for the supplied Minecraft world.

## 17. Installer lifecycle

In a disposable account or VM:

1. Fresh install succeeds and writes only documented Strata directories.
2. `install_manifest.json` lists runtime, launcher, plugin, marketplace, and
   add-on components.
3. Same-major reinstall/upgrade preserves worlds, source `.blend`, libraries,
   and results.
4. A failed install rolls back without a half-installed runtime.
5. Uninstall removes Strata only, never worlds/projects/assets/results.

```powershell
.\.venv\Scripts\python.exe -m installer.install --uninstall `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir
```

## 18. Final traceability matrix

| Feature/claim | Required evidence | Lane | Status |
|---|---|---|---|
| Source install and CI gates | Sections 4–6 | Public |  |
| Bundled Codex plugin/MCP | Sections 6–7 | Public |  |
| 12 named tools and security errors | Section 7 | Public |  |
| Java world layout preflight | Section 10 | Public |  |
| Real Java parsing/culling/chunk planning | Section 12 | Managed Engine |  |
| Custom library inspection | Section 11 | Public + supplied library |  |
| Barebones library/provenance | Section 11 and `ASSET-LIBRARY` | Public |  |
| Add-on UI and removed-control regression | Section 8 | Public + Blender |  |
| Bridge, exact nonce, expiry | Section 9 | Public + Blender |  |
| Submit/status/cancel | Section 12 | Managed Engine |  |
| Manifest/checksum/signature/open | Section 13 | Public logic + Engine |  |
| A1 coordinates and chunk visibility | Section 14 | Blender + supplied coordinates |  |
| Interactive state/keyframes | Section 15 | Blender |  |
| Terrain/water/fog/cloud/sky/lighting gates | Section 16 | Blender synthetic + Engine for real claim |  |
| Installer upgrade/uninstall and preservation | Section 17 | Public |  |

## 19. Report template and release decision

Save `acceptance-report.md` in the evidence directory with: environment and
versions, exact commit, lane, input hashes, coordinate-sheet version, custom
assets, PASS/FAIL/BLOCKED/NOT APPLICABLE counts, the completed matrix, evidence
filenames, blocking defects, and cleanup confirmation.

The public Connector lane may pass without the private Engine. **Real Minecraft
conversion may be marked passed only when an authorised Engine produces
non-empty valid Blender output from the supplied world, the coordinates/assets
match, the manifest verifies, and the result is opened and visually checked.**
Without that endpoint or Blender evidence, write **BLOCKED — prerequisite
unavailable**, not a fixture-based success.
