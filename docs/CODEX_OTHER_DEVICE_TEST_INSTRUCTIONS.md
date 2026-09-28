# Strata Codex agent: clean-device test instructions

**Audience:** a Codex agent running on a second Windows 10/11 device.

**Goal:** install and exercise the public Strata Connector, Blender add-on,
MCP server, and Codex plugin package. The installer downloads the signed Engine
runtime for the local lane, which performs real Anvil parsing and Blender
artifact generation on loopback with no cloud endpoint. The HTTPS managed-build path is optional and
requires explicit authorization. Do not turn a synthetic fixture into a claim
of Minecraft conversion.

## 1. Choose the test lane before changing anything

Use one of these lanes and record it in the final report:

| Lane | Inputs | What it proves |
| --- | --- | --- |
| A — public Connector | Public GitHub checkout, legal synthetic fixtures, Blender | Installation, plugin/MCP discovery, bridge pairing, procedural library, chunk controls, safety gates, and synthetic artifact verification |
| B — local real build | Lane A plus the signed Engine runtime downloaded by the installer | Real Anvil parsing/culling, headless Blender artifact generation, signed manifest, verified download, and local worker cleanup |
| C — authorised managed build | Lane A plus an Engine HTTPS URL and disposable credentials supplied by the owner | Remote upload, signed manifest, verified download, and retention deletion |

Never clone or request a private Engine repository for Lane A. Never upload a
real world, `.blend`, JAR, or texture pack without explicit owner consent.

## 2. Install prerequisites manually

Install and record versions before cloning Strata:

1. Git for Windows.
2. Python 3.13 with the `py` launcher.
3. Blender 4.5 LTS or newer.
4. Codex desktop; install the Codex CLI only if the CLI plugin lane is being tested.
5. Docker Desktop is optional and is not needed for the local real build.

Verify in PowerShell:

```powershell
git --version
py -3.13 --version
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --version
codex --version
docker --version       # optional remote/deployment lane only
```

If a command is absent, record the test as `BLOCKED` for the dependent feature;
do not silently substitute a fixture or manually register an MCP server when
testing the bundled plugin.

## 3. Prepare private test inputs

Ask the owner for read-only copies outside the checkout:

- a Java world directory containing `level.dat` and `region\*.mca`;
- the original source `.blend` and any linked-library/texture paths;
- the coordinate sheet: Minecraft origin, requested bounds, dimension, chunk
  size, and expected A1 chunk names;
- an authorised custom library `.blend`, if its custom assets are part of the
  acceptance claim;
- an owner-authorised `engine_local` bundle only if testing the offline override;
- for Lane C, the HTTPS Engine URL, enrollment key/device flow, and signing
  verification key.

Keep these files out of Git and never overwrite the source `.blend`.

## 4. Install the public Connector and plugin

```powershell
$workRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector-Codex-Test'
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git $workRoot
Set-Location $workRoot
git checkout main
git rev-parse HEAD
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Install the local add-on/plugin using the repository's installer. Use the
release ZIP path instead when testing a published release:

```powershell
$installDir = Join-Path $env:LOCALAPPDATA 'Strata'
$addonsDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
.\.venv\Scripts\python.exe -m installer.install `
  --source-root $workRoot `
  --install-dir $installDir `
  --blender-addons-dir $addonsDir `
  --register-codex `
  --json
codex plugin marketplace add "$installDir\codex-marketplace"
codex plugin add strata-toolkit@strata-local
```

The default command downloads the pinned `engine-v2026.09.0` release from the
public Connector repository, verifies its Ed25519 signature and SHA-256, and
stages it locally. To test an owner-provided offline bundle instead, add
`--engine-root 'D:\FILES\engine_local'`; this explicitly bypasses downloading.

Restart Codex and Blender. The plugin test passes only when Strata's bundled
MCP declaration is discovered without running `codex mcp add` manually.

## 5. Run the public test gates

```powershell
Set-Location $workRoot
New-Item -ItemType Directory -Force -Path test-tmp | Out-Null
.\.venv\Scripts\python.exe -m pytest tests\connector -q --basetemp=test-tmp
.\.venv\Scripts\python.exe -m pytest tests\installer -q --basetemp=test-tmp
.\.venv\Scripts\python.exe -m pytest tests\blender -q --basetemp=test-tmp
powershell -ExecutionPolicy Bypass -File .\scripts\ci_verify.ps1
```

In Codex, verify that these 12 tools are discoverable: `strata_preflight_world`,
`strata_inspect_library`, `strata_generate_barebones_library`,
`strata_submit_managed_build`, `strata_get_job_status`,
`strata_download_result`, `strata_open_result_in_blender`,
`strata_get_chunk_streaming_status`, `strata_load_chunk_radius`,
`strata_set_interactive_block_state`,
`strata_keyframe_interactive_block_state`, and `strata_pair_blender`.

## 6. Pair and test Blender safely

1. Open a copy of the supplied `.blend`, never the source.
2. Enable the Strata add-on and start its loopback bridge.
3. Complete the displayed nonce pairing from Codex using
   `strata_pair_blender`.
4. Confirm the reported scene/session matches the open Blender copy.
5. Exercise read-only preflight and library inspection before any mutating
   tool. Capture screenshots and sanitized JSON responses.
6. Generate the procedural fallback library, load a small synthetic chunk,
   change chunk radius, and keyframe only a supported interactive block.
7. Confirm unrelated user collections and the source file remain unchanged.

## 7. Lane B: local real Engine build

Set `STRATA_API_MODE=local` and `STRATA_ENGINE_ROOT=$installDir\engine`.
Use the bounds from the supplied coordinate manifest for the first run:

```powershell
$env:STRATA_API_MODE = 'local'
$env:STRATA_ENGINE_ROOT = (Join-Path $installDir 'engine')
$env:STRATA_TEST_LOCAL_ENGINE = '1'
$env:STRATA_TEST_WORLD_PATH = 'D:\FILES\minecraft_world\WORLD_1_REQUIRED'
$env:STRATA_BLENDER_EXE = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$env:STRATA_WORLD_X_MIN = '669'; $env:STRATA_WORLD_X_MAX = '854'
$env:STRATA_WORLD_Y_MIN = '48';  $env:STRATA_WORLD_Y_MAX = '120'
$env:STRATA_WORLD_Z_MIN = '-753'; $env:STRATA_WORLD_Z_MAX = '-552'
$env:STRATA_MAX_BLOCKS = '2000000'
$env:STRATA_LOCAL_TEST_TIMEOUT = '600'
.\.venv\Scripts\python.exe -m pytest tests\connector\test_local_engine_live.py -q --basetemp=test-tmp\local-engine
```

Require `1 passed`, `synthetic_fallback: false`, a non-empty `World.blend`,
chunk files, generated fallback library, and manifest checksum verification.
Docker and an HTTPS endpoint are not required for this lane.

## 8. Lane C: remote managed Engine build

Do this only with the owner-provided HTTPS endpoint and consented tiny world.
Set these before starting the MCP server/Codex:

```powershell
$env:STRATA_API_MODE = 'http'
$env:STRATA_API_URL = 'https://<owner-approved-engine-host>'
$env:STRATA_ENROLLMENT_KEY = '<owner-provided-enrollment-key>'
$env:STRATA_SIGNING_KEYS = '<owner-provided-manifest-signing-key>'
$env:STRATA_TEST_LIVE_URL = $env:STRATA_API_URL
$env:STRATA_TEST_WORLD_PATH = 'C:\private-test\world'
$env:STRATA_TEST_OUTPUT_PATH = 'C:\private-test\strata-output'
```

The world path must be a directory, not a `.blend`. Run preflight and inspect
the consent/hash summary. Submit only after explicit approval. Then verify:

- authentication and `/healthz`/`/readyz` succeed;
- upload progress reaches `queued`/`running`/`completed`;
- diagnostics report `synthetic_fallback: false`;
- the manifest is signed and lists non-empty `World.blend`, A1 chunk files,
  diagnostics, and the prototype/custom library;
- Connector checksum/signature verification succeeds before Blender opens the
  result;
- the downloaded master and chunks open in Blender and match the coordinate
  sheet;
- `delete_after_download` reports `retention_status: deleted` and the remote
  job is no longer available.

Run the live client test when the endpoint is authorised:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\connector\test_http_client_live.py -q --basetemp=test-tmp\live
```

## 9. Optional owner-operated manual Engine staging

If the owner supplied an authorised private Engine checkout, use its
`deploy\DEPLOYMENT.md`. Docker is optional. The native Windows route is:

```powershell
Set-Location C:\path\to\Strata-Engine
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
New-Item -ItemType Directory -Force -Path data | Out-Null
$env:STRATA_JOB_ROOT = (Join-Path $PWD 'data')
$env:STRATA_MANIFEST_SIGNING_SECRET = '<private-random-secret>'
$env:STRATA_ENROLLMENT_KEY = '<different-private-random-key>'
$env:STRATA_REQUIRE_SIGNING = 'true'
$env:STRATA_REQUIRE_WORKER = 'true'
$env:STRATA_BLENDER_EXE = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$env:PYTHONPATH = (Get-Location).Path
```

Run the API in one terminal and the worker in another, with the same
environment values:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8080
.\.venv\Scripts\python.exe -m blender_worker.service
```

Then verify `/healthz` and `/readyz` before pointing the Connector at
`http://127.0.0.1:8080`.

The containerized route is:

```powershell
Set-Location C:\path\to\Strata-Engine
Copy-Item deploy\config_template.env .env
# Fill .env with unique STRATA_MANIFEST_SIGNING_SECRET and STRATA_ENROLLMENT_KEY.
docker compose -f docker-compose.staging.yml --env-file .env build
docker compose -f docker-compose.staging.yml --env-file .env up -d
curl.exe -fsS http://127.0.0.1:8080/healthz
curl.exe -fsS http://127.0.0.1:8080/readyz
```

`/readyz` must not pass until the worker heartbeat is fresh. The worker image
installs Blender 4.5.3. Docker image builds must be recorded separately from
the public Connector test because they require the private Engine checkout and
secrets.

## 9. Acceptance evidence and report

Save evidence outside Git: versions, commit SHA, tool inventory, pairing
result, preflight/consent JSON, manifest, checksum result, Blender screenshots,
and sanitized logs. Do not save tokens, raw worlds, private library bytes, JARs,
or proprietary textures in the report.

Use this status rule:

- `PASS`: observable behavior and evidence match the assertion;
- `FAIL`: the feature was available but incorrect;
- `BLOCKED`: the required Blender/Codex/Docker/Engine prerequisite was absent;
- `NOT APPLICABLE`: the feature is outside the selected lane.

The final report must separate Lane A synthetic/reference results from Lane B
real-world conversion. A successful fixture download is never evidence of a
Minecraft world import.
