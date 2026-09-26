# Strata implementation and deployment plan after clean-device acceptance

Status: implementation plan. Do not call Strata accepted until the gates in
this document pass.

This plan responds to the clean-device report for public Connector commit
`ec1fa63`. That checkout passed 76/76 Python tests, but only as a source and
contract audit. The report found four concrete P0 defects: the Codex plugin
does not bundle its MCP connection, Connector and Blender do not share one
pairing nonce, download success does not write/verify a manifest, and the
result-open path acknowledges a file without verifying or opening it. Blender
scene generation, generated libraries, real managed builds, environmental
renders, and installer/release behavior remain unproven.

Public repository: `https://github.com/KaartikeyKusshwaha/Strata-Connector`

Private repository: `https://github.com/KaartikeyKusshwaha/Strata-Engine`

Never copy private Engine source, customer worlds, Minecraft JARs, texture
packs, credentials, or private generated reference data into Connector or its
public plugin package.

## 1. What an agent can and cannot finish autonomously

### 1.1 Work an implementation agent can complete

With both repositories checked out and no external secrets, an agent can:

1. Implement and unit-test the single-source pairing protocol.
2. Implement manifest/checksum/path validation and truthful local download
   behavior against deterministic synthetic artifacts.
3. Implement Blender bridge manifest validation, library linking, and rollback
   behavior, subject to running Blender for integration verification.
4. Correct plugin packaging, schema validation, staged package tests, and MCP
   launcher/build artifacts.
5. Implement the public installer, version checks, upgrade safety, repair,
   uninstall, and local installer tests.
6. Implement private Engine parsing, generated-library, worker, and artifact
   code once the private checkout is available.
7. Add deterministic fixtures, fake services, headless-Blender scripts, CI,
   release audits, documentation, and acceptance evidence tooling.
8. Build release archives and produce hashes/checklists. A signature can only
   be produced by the authorised release identity.

### 1.2 Work requiring the owner or an authorised operator

| Required input/action | Why it cannot be invented | Owner/operator action |
| --- | --- | --- |
| Private Engine checkout | Public Connector intentionally excludes Engine code. | Grant access or provide a local checkout path. |
| Managed API/worker deployment | Requires host/cloud, storage, queue, database, TLS, and policy. | Choose target and provide a disposable staging endpoint/account. |
| Codex desktop plugin test | Requires a real Codex account and current host/schema. | Install/open Codex on a clean profile and authorise testing. |
| Blender UI/render evidence | Requires Blender 4.5 LTS and an interactive machine/GPU. | Run supplied UI/headless checks and attach evidence. |
| Minecraft/custom assets | Ownership and privacy cannot be inferred. | Supply a tiny legal fixture and transfer/retention consent. |
| Release signing | Private signing key or GitHub OIDC identity must stay private. | Configure signing and run the release workflow. |
| Public push/merge/release | Changes the owner's external repository. | Authorise or perform those commands manually. |

Everything else below is intended to be executable by the coding agent from a
clean clone.

## 2. Non-negotiable implementation rules

1. Start a new branch named `codex/acceptance-remediation` in each repository.
2. Preserve the public/private split. Connector imports no private Engine
   module and no private asset bytes.
3. Keep fixture/reference implementations explicitly named as fixtures. They
   must never report a production upload, download, Blender open, or generated
   library when they only returned a protocol response.
4. Every mutating MCP tool must return a structured failure when work was not
   performed. `ok`/`complete` requires a verifiable side effect.
5. Validate paths before opening, copying, extracting, or deleting anything.
   Reject traversal, absolute paths outside the selected root, Windows device
   names, symlink/reparse escapes, and unsafe archive members.
6. Write downloads and generated scenes to a temporary sibling directory,
   verify everything, then atomically promote it. Failed jobs leave no usable
   partial result.
7. Keep session tokens, pairing nonces, upload IDs, and job IDs short-lived and
   out of normal logs.
8. Test negative paths first: wrong nonce, stale token, missing manifest, bad
   checksum/signature, missing Blender, failed link, and interrupted download.
9. Use synthetic fixtures unless lane-B/C authorization is recorded.

## 3. Baseline and branch setup

Run from a parent directory in PowerShell. Replace only repository paths; do
not put token or secret values in committed files.

```powershell
$workRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Remediation'
$connectorRoot = Join-Path $workRoot 'Strata-Connector'
$engineRoot = Join-Path $workRoot 'Strata-Engine'
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git $connectorRoot
Set-Location $connectorRoot
git fetch --all --tags --prune
git switch -c codex/acceptance-remediation origin/main
git rev-parse HEAD
git status --short --branch
```

If private access is authorised, clone Engine separately; never make it a
Connector submodule:

```powershell
git clone https://github.com/KaartikeyKusshwaha/Strata-Engine.git $engineRoot
Set-Location $engineRoot
git fetch --all --tags --prune
git switch -c codex/acceptance-remediation origin/main
git rev-parse HEAD
git status --short --branch
```

Record both SHAs. Without Engine access, complete Sections 4–8 and leave the
Engine/deployment sections blocked with the exact missing-access reason.

## 4. P0-A — make the Codex plugin bundle MCP correctly

### 4.1 Defect and target

`codex_plugin/.codex-plugin/plugin.json` declares the skill but does not wire
the MCP connection in the form recognised by the current Codex plugin host.
`.mcp.json` exists, but a sidecar ignored by the package loader is not a
working bundle. The README's `codex mcp add` instruction masks this defect and
cannot count as acceptance.

The finished plugin must install on a clean profile, start its own named
`strata-connector` stdio MCP server, list all 11 tools, and work after the
source checkout is moved.

### 4.2 Implementation steps

1. Read the current official Codex plugin schema and run its validator; do not
   invent an unsupported manifest key.
2. Update `codex_plugin/.codex-plugin/plugin.json` and/or `.mcp.json` using the
   supported bundled-MCP format.
3. Choose and document a runtime distribution model. A clean plugin install
   cannot assume a global pip package. Use either a signed platform launcher
   bundled with the plugin, a signed runtime installed atomically before plugin
   activation with a deterministic path, or another host-supported executable
   mechanism.
4. Do not use an absolute maintainer path, global virtual environment, shell
   command assembled from user input, or manual `codex mcp add`.
5. Add a staging builder that includes only the plugin, allowed launcher/runtime,
   license, metadata, and skill. Fail on keys, tokens, JAR/NBT data, `.blend`
   fixtures, or files outside the stage.
6. Add package tests for exact MCP wiring, launcher architecture, relative
   paths, package manifest, and no-private-data rules.
7. Add a subprocess smoke test that starts the staged command, completes the
   MCP handshake, lists all tools, and exits cleanly.
8. Update `codex_plugin/README.md`, `docs/SETUP.md`, and release notes to remove
   manual-registration instructions; retain any developer diagnostic as such.
9. Run the current Codex/plugin validator in CI and upload its output.

### 4.3 Acceptance

Install only the staged plugin on a fresh Codex profile. Confirm the MCP server
appears, 11 tools are discoverable, the skill activates, disabling the plugin
removes the tools in a new chat, and moving the source checkout does not break
the plugin.

## 5. P0-B — replace split pairing state with one live protocol

### 5.1 Defect

`connector_mcp/pairing.py` creates one nonce while
`addon/bridge_server.py` creates another. The MCP side can accept its own
nonce while the live Blender socket rejects it.

### 5.2 Required protocol

1. Blender starts the bridge and creates one random, short-lived pairing nonce.
2. Blender displays it and waits for explicit user approval. Remove the current
   auto-approval in `STRATA_OT_pair_codex`; retain a separate approval button.
3. Connector obtains the displayed request/status and never generates another
   nonce.
4. `strata_pair_blender(nonce)` forwards that exact nonce to the live socket.
5. Blender validates and consumes it once, creates the session token, and
   returns token, expiry, session ID, and protocol version.
6. Connector stores exactly that returned token in the active `BridgeClient`.
   `PairingManager` may track state, but must adopt bridge state rather than
   generating independent credentials.
7. Stop/restart/disconnect/expiry/new-request invalidates both sides.
8. Status never exposes a reusable token; nonce is absent from ordinary logs.

### 5.3 Implementation steps

1. Add one shared protocol model for session ID, nonce, approval state, expiry,
   and protocol version; use it in Connector and add-on.
2. Change `BridgeServer` status to expose state and nonce-present information;
   only an explicit user action may reveal the displayed nonce.
3. Make the MCP pairing call query/forward the exact bridge nonce and remove
   random nonce generation from its path.
4. Change `PairingManager` to adopt bridge requests/tokens or remove it if the
   shared state model makes it unnecessary.
5. Store the token in one session object; all chunk/state/open calls read it.
6. Add structured errors for unavailable bridge, approval required, mismatch,
   expired request, consumed request, and stale token.
7. Use constant-time comparison for nonce/token equality.
8. Add fake-socket and real-localhost tests for the report's sequence: Blender
   nonce → exact MCP nonce → accepted live token → authenticated read command.
9. Add two-client, restart, expiry, race, wrong-nonce, repeated-nonce, and
   mid-command-stop tests.
10. Update the plugin skill and acceptance plan to require explicit approval.

### 5.4 Acceptance

The tester starts Blender bridge, explicitly approves pairing, gives Codex the
displayed nonce, runs a read-only status tool, then a chunk-status command.
Wrong/old nonces, stopped bridge, restarted Blender, and expired tokens fail
truthfully.

## 6. P0-C — implement truthful download and verification

### 6.1 Defect

`StrataAPIClient.download_result()` returns a manifest path but does not create
the output directory, write artifacts, or verify checksums.

### 6.2 Result contract

Use one contract for fixture and managed clients:

```text
result-root/
  strata-world-manifest.json
  World.blend
  Strata_PrototypeLibrary.blend       (when used)
  chunks/<safe-relative-chunk-file>.blend
  diagnostics.json
```

The manifest contains contract version, job ID, relative file list, SHA-256 for
each file, signature metadata, chunk coordinates/A1 names, provenance, and
retention status. It contains no absolute source paths or secrets.

### 6.3 Implementation steps

1. Split `StrataAPIClient` into explicit `FixtureAPIClient` and real
   `HTTPStrataAPIClient`; never silently fall back to fixtures.
2. Require authenticated completed job and approved output root.
3. Stream manifest/artifacts into a temporary sibling directory with bounded
   memory, timeout, retry, size, and cancellation handling.
4. Validate manifest JSON/schema/major version before reading file entries.
5. Reject traversal, absolute paths, duplicates, symlinks, missing files, and
   unsafe archive members.
6. Verify the real cryptographic signature with configured public key; replace
   the current known-string allow-list and document key rotation.
7. Compute SHA-256 for every file and compare with manifest.
8. Atomically promote only after all checks pass; return the actual manifest
   path and verified file list. On failure remove only the temp directory.
9. Report retention/deletion only after service confirmation.
10. Add tests for valid write, malformed/missing manifest, bad signature/hash,
    truncation, retry, cancellation, traversal, duplicate path, collision,
    and no-partial-output behavior.
11. Replace e2e assertions with `Path.exists()`, non-zero sizes, parsed manifest,
    checksum verification, and no-partial-output assertions.

### 6.4 Acceptance

Download a completed synthetic result to an empty directory, inspect every
file, tamper one byte, and repeat. Valid output is usable; tampered output is
rejected and never passed to Blender.

## 7. P0-D — verify and genuinely open results in Blender

### 7.1 Defect

`addon/__init__.py::_handle_open_result()` returns an acknowledgement without
reading a manifest or linking `.blend` data. Connector also forwards the path
without the documented verification.

### 7.2 Implementation steps

1. Connector calls shared manifest/checksum validation before the bridge call.
2. Add-on independently validates manifest and all relative paths; it does not
   trust MCP merely because the bridge token is valid.
3. Require a valid master scene and reject empty manifests/no loadable scene.
4. Resolve only under the verified result root; reject symlink/reparse escapes.
5. Use Blender's library API to link/append master scene, prototype library, and
   chunk collections according to manifest mode.
6. Preserve the user's scene; create Strata root/metadata only after validation.
7. On link failure remove only objects/collections created by this operation and
   return the failing file/diagnostic.
8. Return actual root/chunk/object/material counts, manifest hash, and operation
   ID instead of an acknowledgement string.
9. Add a headless Blender test that opens a synthetic package, saves/reopens it,
   and verifies collections, objects, paths, and untouched user sentinel data.
10. Add negative tests for bad signature/hash, missing chunk, invalid path,
    malformed manifest, and library-load exception.

### 7.3 Acceptance

The MCP tool must visibly create a Strata root and at least one verified
chunk/library in Blender. Invalid input leaves the original scene unchanged.

## 8. P1-A — implement the generated barebones asset-library path

This work belongs primarily in the private Engine. Public Connector may carry
schemas, fixture metadata, and the request/response contract, but not private
world or texture bytes.

### 8.1 Engine implementation targets

In the private checkout, inspect and then implement the corresponding code in:

- `engine/plugins/geometry_backends/barebones_backend.py`
- `engine/pipeline.py` or the current pipeline entry point
- `assets/acquire.py`
- `minecraft_java/models/`, `minecraft_java/blockstates/`, and texture extraction
- texture-stack/library-source resolution modules
- `blender_worker/worker.py`
- the Engine manifest/provenance/signing writer

Do not assume paths that differ in the private repository; record actual paths
in the Engine change log before editing.

### 8.2 Required behavior

1. `missing_asset_policy=generate` creates a real
   `Strata_PrototypeLibrary.blend`, not only metadata or a state flag.
2. Each generated block has deterministic grid-aligned geometry, UVs, a
   material, and a legal image/colour fallback. Custom properties and manifest
   provenance record block ID, model source, texture source/hash, generation
   reason, and backend version.
3. Implement parent model inheritance, cube elements, texture variables,
   variants, multipart blockstates, rotations, and deterministic transforms.
4. Implement texture precedence exactly as documented: user pack, selected
   pack, then approved JAR. Hash selected bytes and do not emit private paths.
5. Fix texture extraction/import errors and test malformed/missing textures.
6. `missing_asset_policy=error` stops before partial output and names every
   missing block ID.
7. A user `.blend` library and explicit block map win over generated/reference
   assets. Hash source before and after; never modify it.
8. Two identical runs produce identical names, topology, material assignments,
   hashes, diagnostics, and A1 chunk references; only allowed timestamps vary.
9. Build a small chunk using only the generated library, save/reopen it in
   Blender 4.5, and prove it needs no original fixture path.
10. Exclude Steve/Alex/mob/item candidates from terrain generation and report
    them unsupported; do not invent character-rig behavior.

### 8.3 Required tests

Implement `LIB-001` through `LIB-012` from
`docs/CLEAN_DEVICE_CODEX_ACCEPTANCE_PLAN.md`, replacing every expected-fail
assertion with real output assertions. Include generated mesh/material checks,
red/blue/green texture precedence, custom-library authority, error-vs-generate
policy, parent/multipart models, deterministic rerun, and save/reopen proof.

## 9. P1-B — deploy a real managed Engine service

The public Connector cannot pass a managed-build claim while its API client is
a fixture. Deployment remains private and exposes only the versioned contract.

### 9.1 Required components

1. Authenticated API with device/OAuth flow, scoped job tokens, rate and input
   limits, idempotency keys, cancellation, and health checks.
2. Durable job database/queue with authorized transitions: accepted, uploading,
   queued, running, cancelling, completed, failed, cancelled, deleting,
   deleted.
3. Private encrypted object storage with lifecycle deletion.
4. Pinned Engine + Blender 4.5 headless worker image with resource/time limits.
5. Signed artifact writer using the release public key and canonical manifests.
6. Diagnostics that redact local paths, tokens, world names, and asset bytes.

### 9.2 Agent-authored deployment assets

In the private Engine repo, add/update these using its existing framework names:

- `Dockerfile.api` and `Dockerfile.worker` with pinned dependencies;
- `docker-compose.staging.yml` for disposable local integration;
- `deploy/` health/readiness/config templates without secret values;
- job/retention database migrations;
- worker entrypoint and Blender executable self-check;
- signed-manifest/key-ID configuration;
- local object-store/queue substitute integration tests;
- CI workflow for unit, security, worker, and contract tests;
- operator runbook for deploy, rollback, deletion, and incidents.

### 9.3 Operator-only deployment

1. Create staging account, private registry, encrypted bucket, database, queue,
   DNS, and TLS certificate.
2. Create separate staging secrets for auth, storage, queue, database, and
   signing identity in the platform secret manager.
3. Build/scan images and pin their digests.
4. Apply migrations and deploy API on private networking.
5. Deploy workers with Blender runtime policy, CPU/RAM/time quotas, and no
   public inbound port.
6. Run health/readiness checks, then submit only the synthetic tiny world.
7. Confirm authorization, job isolation, cancellation, signing, retention, and
   audit-log redaction.
8. Give the clean-device tester a disposable endpoint/account with no Engine
   source or another user's data.

An uncredentialed agent must stop before these operations. Never put staging
secrets, signing keys, endpoint credentials, or real customer files in logs or
public release assets.

## 10. P1-C — prove terrain, water, fog, clouds, sky, and lighting

Passing configuration/unit tests is not render acceptance. Add a legal
synthetic scene and headless Blender scripts in a test-only location, never in
the user's A1 `.blend`.

| ID | Required proof |
| --- | --- |
| `RENDER-TERRAIN` | Non-empty A1 chunks, correct XZY coordinates, culling, materials, save/reopen. |
| `RENDER-WATER` | Water geometry/material, no surface holes, reflection/transparency, day/night difference. |
| `RENDER-FOG` | Reproducible depth falloff; disabling fog removes only fog. |
| `RENDER-CLOUDS` | Cloud objects/shader/compositor, stable rerender, independently disableable. |
| `RENDER-SKY` | Sky/HDRI/background and sun direction recorded and preserved after reopen. |
| `RENDER-LIGHT-DAY` | Day render with terrain/materials and deterministic exposure/color settings. |
| `RENDER-LIGHT-NIGHT` | Night render with water/fog/cloud behavior and no daylight fallback. |
| `RENDER-TOGGLE` | Each environment component toggles without changing unrelated collections. |

Execution:

1. Start an empty Blender 4.5 file and synthetic 3×3×3 chunk.
2. Run Engine build and open output through the add-on.
3. Record object/collection/material/node counts before rendering.
4. Render day/night in Eevee and the supported Cycles smoke case; do not claim
   unsupported Unreal/Litematica paths.
5. Save/reopen every candidate.
6. Compare JSON audits and image metrics with checked-in golden tolerances.
7. Attach outputs to private CI/report when restricted assets are involved.

## 11. P1-D — implement a real installer and signed release

### 11.1 Installer behavior

Implement `installer/install.py` and `installer/config.py` as an atomic,
versioned installer:

1. Validate OS, Blender version, disk, target ownership, and package signature.
2. Stage runtime/launcher, plugin, and add-on in a temporary directory.
3. Verify component compatibility and one version/contract matrix.
4. Stop only the Strata bridge owned by this installation.
5. Move staged components into versioned install directories.
6. Register a reversible uninstall record; do not delete unrelated data.
7. Run launcher handshake, plugin validation, add-on import, Blender version,
   and bridge-start post-install checks.
8. Roll back only files created by this transaction on failure.
9. Upgrade by staging new version, preserving only policy-approved settings,
   and removing obsolete owned files.
10. Uninstall by stopping owned bridge, removing owned components, revoking
    local session state, and leaving worlds/output untouched.

### 11.2 Release artifact

Build a platform-specific signed archive/installer with component versions and
hashes. The release pipeline must:

1. Run public tests, plugin tests, installer tests, and artifact audit.
2. Build from a clean checkout.
3. Reject private files and unreproducible absolute paths.
4. Generate SHA-256 hashes and sign with the authorised identity.
5. Publish only after human review of the staging report.
6. Test fresh install, upgrade, repair, uninstall, and reboot in a Windows VM.
7. Attach source SHAs, Blender range, contract version, and rollback steps.

## 12. CI and local command sequence

### 12.1 Connector verification

```powershell
Set-Location $connectorRoot
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp (Join-Path $env:TEMP 'strata-remediation')
.\.venv\Scripts\python.exe -m pytest tests\connector\test_plugin_package.py -q
.\.venv\Scripts\python.exe -m pytest tests\connector\test_pairing.py tests\connector\test_e2e.py -q
powershell -ExecutionPolicy Bypass -File .\scripts\release_audit.ps1 -StagingDir .
```

E2e tests must assert files and side effects, not only status strings.

### 12.2 Authorised Engine verification

```powershell
Set-Location $engineRoot
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Run the Engine worker, `LIB-*`, and render suites. If Blender is not on PATH,
pass the recorded absolute Blender 4.5 path through the worker setting; never
silently use another version.

### 12.3 Disposable staging service

```powershell
Set-Location $engineRoot
docker compose -f .\docker-compose.staging.yml config
docker compose -f .\docker-compose.staging.yml build --pull
docker compose -f .\docker-compose.staging.yml up -d
docker compose -f .\docker-compose.staging.yml ps
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8080/healthz'
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8080/readyz'
```

These commands may use synthetic local secrets/storage only; never point them
at production without lane-B authorization.

## 13. Clean-device deployment and acceptance sequence

After fixes are merged into a tagged candidate, use a new Windows user/VM:

1. Install Git for Windows, Python 3.12 x64, Blender 4.5 LTS, and current
   Codex desktop from official sources.
2. Clone Connector at the candidate tag. Do not clone Engine.
3. Install the signed Strata package. If none exists, mark release install
   blocked; do not create a manual substitute.
4. Verify launcher handshake and plugin package before opening Blender.
5. Enable the Strata add-on and record its version.
6. Start bridge, explicitly approve pairing, and complete the exact live nonce.
7. Run read-only preflight/library inspection with legal synthetic fixtures.
8. Run fixture download and prove files/checksums before opening.
9. Open verified package in Blender and record actual scene changes plus a
   saved/reopened copy.
10. If managed staging is authorised, submit the tiny world only after consent
    lists files, hashes, destination, and retention.
11. Run chunk streaming and one supported interactive block/keyframe.
12. Run terrain/water/fog/cloud/sky/day/night render rows.
13. Tamper a manifest and artifact; both must be rejected before scene changes.
14. Disable plugin and restart Codex; tools disappear in a new chat. Restart
    Blender; the previous token fails.
15. Report every ID, SHA, version, command, screenshot/log, and blocked input.

## 14. Definition of done and release gate

Do not call Strata accepted or artist-ready until all are true:

- plugin-only installation discovers MCP without manual registration;
- live Blender nonce/token flow passes, including restart/expiry negatives;
- downloads write verified files and leave no partial output on failure;
- verified results visibly open/link in Blender and survive save/reopen;
- generated barebones libraries contain deterministic meshes/materials and
  texture/provenance evidence;
- private staging produces non-empty signed world/chunk output and respects
  cancellation/retention without leaking private data;
- terrain, water, fog/mist, clouds, sky, day, and night have evidence;
- installer install/upgrade/repair/uninstall passes in a clean Windows VM;
- public CI, private CI, security, package, and release audits pass at the same
  recorded candidate SHAs.

Unavailable prerequisites are **BLOCKED**, with the owner/action recorded.
Never convert a fixture response, Python unit pass, or acknowledgement string
into a feature pass.

## 15. Suggested commit sequence

1. `test: add acceptance regressions for plugin pairing download open`
2. `fix: bundle and validate Strata MCP plugin runtime`
3. `fix: unify live Blender pairing session`
4. `fix: implement verified artifact download`
5. `fix: verify and open result manifests in Blender`
6. `feat(engine): generate deterministic barebones prototype library`
7. `feat(engine): run signed managed worker artifacts`
8. `test(blender): add headless terrain and environment render matrix`
9. `feat: implement atomic installer and upgrade rollback`
10. `ci: add package, Blender, Engine, and release gates`
11. `docs: publish clean-device deployment and acceptance report`

Each commit must pass relevant local tests and contain no secrets. Push, merge,
deploy, and sign only after the owner authorises those external actions.
