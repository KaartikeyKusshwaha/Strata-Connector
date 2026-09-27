# Strata clean-device Codex acceptance plan

**Audience:** an independent QA agent running Codex on a different, clean
Windows computer.
**Purpose:** determine whether a person can actually download, install, pair,
and use Strata Toolkit as advertised—not merely whether unit tests pass.
**Target:** **Codex**. Strata's MCP server is portable, but the public product
includes a `codex_plugin/` package and Codex pairing workflow. Do not use
Claude as a substitute for this acceptance test.

> **Status note (current checkout):** This document records the historical
> baseline audit of commit `ec1fa63`. The implementation and installer have
> since been remediated on local commit `146506a` (with parent `318c9f0`). Use
> [LIVE_DEVICE_TEST_SETUP.md](LIVE_DEVICE_TEST_SETUP.md) for the current
> release-install procedure. The historical blocked rows below remain useful
> as acceptance assertions, but their old code/status descriptions are not a
> current repository snapshot.

This is a pass/fail plan, not an implementation prompt. The tester must report
observed evidence and failures exactly as found. They must not silently repair
the product, manually configure an MCP server to make a plugin test pass, or
relabel a mock result as a managed production build.

## 1. Audited baseline and current status

Capture these values again at the start of every run; they are a snapshot from
the audit performed on **2026-09-26**, not a release guarantee.

| Area | Audited state | Acceptance implication |
| --- | --- | --- |
| Public repository | `KaartikeyKusshwaha/Strata-Connector`, public `main`, commit `ec1fa63` (`feat: implement Codex plugin (Phases 1-4)`) | Test this exact commit or a tagged release that supersedes it. |
| Connector package | `strata-connector` `1.1.0`; Python 3.10–3.13 declared | A clean Python source install is testable. |
| Public CI | Latest run for `ec1fa63` succeeded on Windows across the declared Python matrix | Useful regression evidence, but not a Blender/Codex acceptance result. |
| Local audit test run | `76 passed` under Python 3.12 on 2026-09-26 | Re-run on the clean device; attach the output. |
| GitHub releases | **No releases or downloadable assets** at audit time | The advertised artist-installer route cannot pass. Use the source-install lane only and record the release gate as blocked. |
| Installer | `installer/install.py` explicitly returns “not yet implemented” | Do not claim an installer test passed. |
| Codex plugin | `codex_plugin/` contains a manifest, MCP declaration, and skill | Test as a real locally installed Codex plugin; do not count a manual MCP configuration as plugin success. |
| MCP server | 11 current tools, including `strata_pair_blender` | README says 10 tools; documentation is stale and must be recorded as a documentation defect. |
| Blender add-on | Public add-on has bridge, pairing, chunk visibility, and interactive-block handlers | Verify with Blender UI and a live bridge; source/unit import alone is insufficient. |
| Private repository | `KaartikeyKusshwaha/Strata-Engine`, private `main`, commit `dce67ae` | An outside tester must not clone or receive this repository. Managed service behavior is tested through an authorised test account only. |
| Private Engine delivery | API and worker source contain in-memory/placeholder paths; no Engine CI workflow was found | A true managed-build delivery test is currently expected to be blocked until a deployed, authorised service exists. |

### 1.1 Current known blockers to verify, not work around

The agent must first verify these conditions. If still present, mark the named
test as **BLOCKED** or **FAIL** and continue only with unaffected tests.

1. The public repository has no GitHub release asset and no working installer.
2. `codex_plugin/.codex-plugin/plugin.json` does not currently declare an
   `mcpServers` reference to `.mcp.json`. A successful manual
   `codex mcp add` proves the MCP server, **not** the bundled-plugin path.
3. The public Connector API client currently labels itself a fixture/stub and
   returns fixture responses; it does not establish a real managed API session,
   upload a world, download artifacts, or inspect a real `.blend` library.
4. The add-on's `open_result` handler says that a full implementation would
   validate and link chunks, then returns a success-shaped response without
   opening output. A response of `ok` is not sufficient evidence.
5. The Connector pairing manager and Blender bridge create separate pairing
   state/nonces. Verify that the nonce shown in Blender can complete the live
   bridge pairing; do not assume it does from unit tests alone.
6. Manifest “signature” recognition is currently a placeholder allow-list, not
   cryptographic signature verification.
7. `docs/QUICKSTART.md` and `docs/WORKFLOWS.md` still name removed
   `import_minecraft_world` and removed MC Chunk Workflow actions. These pages
   cannot be accepted as current instructions until corrected.

## 2. Test lanes and access boundaries

Run the lanes independently. A pass in one lane never upgrades another lane.

| Lane | Who runs it | May access | Cannot establish |
| --- | --- | --- | --- |
| A. Public clean-device | Independent tester / Codex | Public Connector, legal synthetic fixtures, their own Blender and Codex | Private Engine correctness or a production managed build |
| B. Managed service beta | Authorised tester with a disposable service account | Public Connector plus deployed managed API | Engine source access or permission to retain customer worlds/assets |
| C. Private Engine CI | Maintainer/authorised operator only | Private Engine, isolated test storage, headless Blender worker | Public release readiness by itself |

Use lane A for the requested other-device test. Run B only when the product
owner provides a real test endpoint, test account, test data-retention policy,
and written permission to submit the selected data. Run C in private CI; never
copy private Engine code, Boxscape data, Minecraft JARs, texture packs, or
customer libraries to an independent tester's device.

## 3. Test rules and evidence

### 3.1 Clean device definition

Use a newly created Windows 10/11 x64 user profile or VM snapshot. Before
starting, confirm all of the following are absent:

- no previous `Strata-Connector` checkout or Python virtual environment;
- no Strata add-on in Blender's user add-ons directory;
- no Strata plugin or Strata MCP server in Codex configuration;
- no API token, bridge token, test world, Minecraft JAR, or custom asset
  library inherited from a maintainer;
- no shared network drive containing private Engine files.

### 3.2 Legal test inputs

The default public test uses only the repository's synthetic contract fixtures
and the `reference_engine`. Do **not** download or redistribute Minecraft JAR
contents, Minecraft textures, resource packs, Boxscape assets, customer worlds,
or someone else's `.blend` library.

For a lane-B managed test, use a tiny world and library deliberately supplied
by the product owner with permission to upload. Record SHA-256 hashes and
delete the local copy when the agreed test ends.

### 3.3 Evidence folder

Create an audit folder outside the Git checkout, for example:

```powershell
$auditRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Clean-Device-Audit'
New-Item -ItemType Directory -Force -Path $auditRoot | Out-Null
```

Save text output, screenshots, screen recordings, version information, and
non-sensitive manifests there. Do not save pairing nonces, session tokens,
API tokens, raw worlds, JARs, texture packs, or private `.blend` files in the
report. Replace paths with `<TEST_ROOT>` and redact secrets.

Each test record must include: test ID, commit/tag, date/time/timezone,
Windows/Python/Blender/Codex versions, exact action, expected result, actual
result, pass/fail/blocked, screenshots/log paths, and a short reproduction
command.

## 4. Downloads and source installation — lane A

### 4.1 Required downloads

The independent tester downloads only:

1. Git for Windows from its official source.
2. A supported CPython x64 release; use Python 3.12 x64 for the baseline run.
3. Blender 4.5 LTS x64 from the official Blender download page.
4. The current Codex desktop application and a Codex-enabled account.
5. The public `Strata-Connector` source repository.

Do not download `Strata-Engine`. Do not install a random PyPI package called
“strata”; the source checkout and its virtual environment are the test target.

### 4.2 Fresh-device bootstrap — `BOOT-001` to `BOOT-012`

Perform this section in a new Windows 10/11 user account or a reverted VM
snapshot. The tester must capture the browser download pages, installed version
screens, and the commands below. Do not use a maintainer's preconfigured
Blender, Codex profile, or Python environment.

| ID | Component | Exact setup and verification | Pass condition |
| --- | --- | --- | --- |
| `BOOT-001` | Baseline | Create the test account/VM snapshot. Run `Get-Command git, py, blender, codex -ErrorAction SilentlyContinue` and save the output before installing anything. Confirm no `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\strata_toolkit` directory and no existing Strata entry in Codex plugins/MCP settings. | The baseline is recorded and contains no inherited Strata configuration. |
| `BOOT-002` | Git | Download **Git for Windows x64** from `https://git-scm.com/download/win`. Install with the normal defaults, including command-line Git and Git Credential Manager. Open a new PowerShell window and run `git --version` and `git config --global --get credential.helper`. | `git --version` succeeds; sign-in to GitHub is not required to clone the public Connector. |
| `BOOT-003` | Python | Download the official **Python 3.12 x64 Windows installer** from `https://www.python.org/downloads/windows/`. During setup select the Python launcher and add Python to PATH. In a new PowerShell window run `py -3.12 --version` and `py -3.12 -m pip --version`. | Both commands resolve to Python 3.12; do not use a Microsoft Store alias or an unrelated global virtual environment. |
| `BOOT-004` | Blender download | Download the official **Blender 4.5 LTS Windows x64 installer** from `https://www.blender.org/download/`. Record the version displayed by the download page and the installer filename/hash when supplied. Do not download community add-on bundles. | The downloaded installer identifies Blender 4.5 LTS x64. |
| `BOOT-005` | Blender install | Install for the clean test user with the standard installer settings. Launch Blender once, retain default startup settings, then close it. Do not add extensions, asset libraries, or a startup file. Verify with `& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --version`; if installed elsewhere, record the actual executable path instead. | The command and Blender's **Help → About Blender** both show 4.5 LTS; the first-launch preferences were generated by this test account. |
| `BOOT-006` | Codex desktop | Download/install the current Windows ChatGPT desktop application from `https://openai.com/chatgpt/desktop/`, sign in with the tester's own Codex-enabled account, open Codex, and create one empty test task. Capture the app/version screen and the empty plugins/MCP settings before adding Strata. | Codex is usable in a clean account/profile. No maintainer credentials, API keys, or Strata connection are present. |
| `BOOT-007` | Codex CLI (only if used) | If the tester will use the CLI marketplace command, install/update Codex CLI by following the then-current official Codex documentation, then run `codex --version`. Do not substitute a manually registered MCP server for plugin testing. | CLI version is recorded, or the report says **desktop-only plugin test** and uses the desktop plugin UI. |
| `BOOT-008` | Test folders | Create an isolated source and evidence location: `$testRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector-Clean-Test'`; `$auditRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Clean-Audit'`; `New-Item -ItemType Directory -Force -Path $auditRoot | Out-Null`. | All captures/logs remain outside the public Git checkout and contain no private world or asset data. |
| `BOOT-009` | Network safety | Permit only the official downloads, GitHub public clone, and an authorised Strata beta endpoint if lane B is explicitly approved. Do not upload a Minecraft save, `.blend`, Minecraft JAR, texture pack, or API token in lane A. | The test log lists every endpoint/data class used. |
| `BOOT-010` | GPU/render baseline | In Blender open **Edit → Preferences → System**, record the detected GPU/backend without changing it. Render the default cube only if a basic Blender smoke test is desired; this is not a Strata render test. | The hardware/backend context is attached to future Blender results. |
| `BOOT-011` | Reset point | Before Sections 5–7, make a VM snapshot or record the precise cleanup locations: the test root, audit root, Blender user add-on directory, and any Codex local marketplace/plugin registration. | A failed plug-in/add-on test can be repeated from a known clean state. |
| `BOOT-012` | Bootstrap evidence | Save `git --version`, `py -3.12 --version`, Blender `--version`, Codex/CLI version, installation paths, screenshots, and the initial Codex plugin/MCP inventory under `$auditRoot`. | Another tester can reproduce the machine baseline without guesswork. |

If the Blender executable is not found at the illustrative default path, locate it
through the installed Start-menu shortcut or `Get-ChildItem 'C:\Program Files\Blender Foundation' -Recurse -Filter blender.exe`, record the resulting path, and use that explicit path for every later headless Blender command. Do not silently switch Blender versions.

### 4.3 Release/installer gate — `REL-001`

1. Open `https://github.com/KaartikeyKusshwaha/Strata-Connector/releases`.
2. Record release tag, installer filename, SHA-256, signature, and source
   commit if assets exist.
3. If assets do not exist, mark `REL-001` **BLOCKED — no release artifact**.
   Do not create an installer yourself and do not mark the product as
   artist-installable.
4. If assets exist, first test the signed installer in a VM, then perform the
   source-install lane below as a separate developer verification.

### 4.4 Clean source-install procedure — `SET-001` to `SET-005`

Open PowerShell as the clean test user:

```powershell
$testRoot = Join-Path $env:USERPROFILE 'Documents\Strata-Connector-Clean-Test'
git clone https://github.com/KaartikeyKusshwaha/Strata-Connector.git $testRoot
Set-Location $testRoot
git rev-parse HEAD
git status --short --branch
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -c "import connector_mcp, contracts, reference_engine; print('Strata Connector ready')"
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp (Join-Path $env:TEMP 'strata-clean-test')
```

Pass criteria:

- the checkout is clean at the recorded commit;
- editable installation completes without an unrelated global Python package;
- imports succeed;
- every test passes. The audited baseline is `76 passed`; a different count
  must be explained by a newer recorded commit, not ignored.

Run the public release audit too:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release_audit.ps1 -StagingDir .
```

`SET-001` through `SET-005` prove only source/developer readiness. They do not
prove a consumer installer, a Codex plugin installation, a real build, or
Blender integration.

## 5. Blender add-on installation and UI — lane A

The released installer is unavailable at the audited baseline, so test only a
**manual developer installation**. Label it exactly that way in the report.

### 5.1 Install the add-on

With Blender closed, copy the add-on into the clean user's Blender add-on
directory. This copies source; it must not alter the Git checkout.

```powershell
$addonTarget = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons\strata_toolkit'
New-Item -ItemType Directory -Force -Path $addonTarget | Out-Null
Copy-Item -Recurse -Force "$testRoot\addon\*" $addonTarget
Test-Path (Join-Path $addonTarget '__init__.py')
```

Open Blender 4.5 LTS normally. In **Edit → Preferences → Add-ons**, search for
and enable **Strata Toolkit**. In a 3D Viewport press `N`, open the **Strata**
tab, and capture a screenshot showing the add-on name/version and empty scene.

### 5.2 Add-on/UI checks

| ID | Action | Pass condition | Current-risk condition |
| --- | --- | --- | --- |
| `BLD-001` | Enable/disable/re-enable the add-on, then restart Blender and enable again | No traceback; one Strata panel; no duplicate operators | Any registration error is a fail. |
| `BLD-002` | Click **Start Strata Bridge**, then **Stop**, three times | UI state changes cleanly; port is released after stop | A stuck bridge or port collision is a fail. |
| `BLD-003` | Click **Pair with Codex** and record only a redacted screenshot of the nonce UI | Bridge shows awaiting/paired state and nonce is generated | The code currently auto-approves the request; record this security/UX behavior. |
| `BLD-004` | Test bridge recovery after Blender restart | Old token is rejected; UI tells the user to start/pair again | Token still works after restart is a security fail. |
| `BLD-005` | Create test collections named `Chunk_xp000_yp000_zp000`, `Chunk_xp001_yp000_zp000`, and `Chunk_xm001_yp000_zp000`, each with a visible cube | They are present for the streaming test; no real Minecraft assets used | This is a synthetic scene, not a world-import pass. |
| `BLD-006` | Create a test cube named `AuditDoor`, set an initial `strata_open` custom property | The object is ready for live state/keyframe tests | This does not prove an actual door rig. |

Do not test removed rig, Steve, ray-pick, box-pick, or lock-chunk controls.
Their appearance in legacy documentation is a documentation failure, not a
feature requirement.

## 6. Direct MCP verification — lane A

This tests the MCP server separately from the Codex plugin. It is valid only
as an MCP test; it cannot be used to claim that plugin bundling works.

### 6.1 Register the local development server — `MCP-001`

```powershell
codex mcp add strata-clean-audit -- "$testRoot\.venv\Scripts\strata-mcp.exe"
codex mcp list
```

Start a **new Codex chat**, open `/mcp`, and confirm the server appears. Capture
the listed tool names and their descriptions/approval behavior. Expected current
tool count is **11**:

```text
strata_preflight_world
strata_inspect_library
strata_submit_managed_build
strata_get_job_status
strata_download_result
strata_open_result_in_blender
strata_get_chunk_streaming_status
strata_load_chunk_radius
strata_set_interactive_block_state
strata_keyframe_interactive_block_state
strata_pair_blender
```

Pass only if all 11 are shown and no generic code-execution, shell, raw bridge,
or unrestricted file-read tool is shown. Record that the README's “10 tools”
statement is outdated if this test passes with 11.

### 6.2 Tool-by-tool functional matrix

Use paths under `<TEST_ROOT>` only. For every tool, test a normal input, a
missing/invalid input, and a path-traversal attempt such as
`<TEST_ROOT>\out\..\..\outside`. Confirm structured errors contain no tokens,
stack traces, or server paths.

| Tool | Required clean-device check | What counts as a real pass | Current expected result |
| --- | --- | --- | --- |
| `strata_preflight_world` | Run against a missing path and an approved tiny test folder | Reads supported world data and returns real counts/diagnostics | Protocol response may pass; current client returns `0` estimates, so real-world inspection is not proven. |
| `strata_inspect_library` | Run against a valid tiny `.blend` with two named objects | Returns the actual object names without changing the library | Current client returns `object_names: []`; actual inspection should fail until implemented. |
| `strata_submit_managed_build` | Use only lane-B consented test data | Shows exact input set/hashes/retention, then submits to a real service only after explicit approval | Current lane-A response is a fixture and is not an upload pass. |
| `strata_get_job_status` | Poll a valid job and an invented job id | Returns real state/progress/diagnostics and not-found handling | Fixture queue state is protocol-only. |
| `strata_download_result` | Download a completed authorised job into an empty test output directory | Writes verified files and rejects bad/missing checksums | Current fixture returns a path without writing output; mark managed download fail. |
| `strata_open_result_in_blender` | Pass a verified synthetic manifest only after bridge pairing | Blender visibly links/opens the requested master scene/chunks, then scene state changes are screenshot-proven | Current add-on returns an acknowledgement without opening chunks; mark fail if scene does not change. |
| `strata_get_chunk_streaming_status` | Invoke after valid live pairing and the synthetic chunk scene exists | Reports the actual loaded/visible collections/object counts | Blocked until live pairing works. |
| `strata_load_chunk_radius` | Request radius 0 at `(0,0,0)` and inspect the three synthetic collections | Only the center collection is visible; others hide as documented; test render visibility separately | Blocked until live pairing works; do not accept simulated output. |
| `strata_set_interactive_block_state` | Set `AuditDoor` to 1 then 0 | Actual Blender custom property changes and is visible in Object properties | Blocked until live pairing works; property-only behavior is not a rig/animation pass. |
| `strata_keyframe_interactive_block_state` | Keyframe `AuditDoor` at frames 1 and 20 | A real F-curve/keyframes are visible in Blender | Blocked until live pairing works. |
| `strata_pair_blender` | Paste the nonce that Blender displayed after explicit user approval | Pairing completes against the *live* bridge and subsequent authenticated tool succeeds | Expected to expose the current separate-state/nonce defect; do not mark a Connector-only response as live pairing. |

For `MCP-002`, deliberately request an unsupported generic action such as “run
arbitrary Python in Blender” and “read every file on C:”. The correct result is
that Codex cannot select a Strata generic-execution tool and explains that only
named operations are available.

## 7. Codex plugin verification — lane A

This is distinct from Section 6 and must be run in a fresh Codex profile or
after removing the direct `strata-clean-audit` MCP registration. Otherwise the
manual MCP connection can mask a broken plugin package.

### 7.1 Plugin package gate — `PLG-001`

Inspect the staging copy, not the source checkout:

```powershell
$pluginStage = Join-Path $auditRoot 'strata-toolkit-plugin-staging'
Copy-Item -Recurse -Force "$testRoot\codex_plugin" $pluginStage
Get-Content "$pluginStage\.codex-plugin\plugin.json"
Get-Content "$pluginStage\.mcp.json"
```

Use Codex's plugin tooling to add this existing staged package to a **local
marketplace**. The tester should give the built-in plugin creator this exact
instruction in a new task:

```text
Validate and register the existing plugin source at <PLUGIN_STAGE> in a local
marketplace for Codex testing. Do not add a manual Codex MCP server, do not
modify the source repository, and do not create substitute tools. Verify whether
the plugin manifest declares and bundles its Strata MCP connection; report any
missing manifest wiring as a failure.
```

Install the plugin from the local marketplace, start a new chat, and inspect
`/plugins` and `/mcp`.

Pass criteria:

- Strata Toolkit installs from the local marketplace;
- its skill activates for direct and indirect Strata/Minecraft/Blender requests;
- its bundled MCP server appears without `codex mcp add`;
- all 11 expected tools are available with conservative approval behavior;
- disabling the plugin removes its capability in a fresh chat;
- plugin files resolve from the package and do not depend on the original
  developer checkout.

At the audited baseline this test is expected to **FAIL/BLOCK** because the
plugin manifest does not reference `.mcp.json`. Record the exact plugin-tool
diagnostic. Do not “fix” the result with manual MCP registration.

### 7.2 Skill behavior evaluation — `PLG-002`

After `PLG-001` passes, use these prompts in separate fresh chats and record
whether the expected Strata workflow/tool is chosen:

| Class | Prompt | Expected result |
| --- | --- | --- |
| Direct | “Use Strata to inspect my Minecraft world before I submit a build.” | Uses the Strata skill and preflight path. |
| Indirect | “Can this Blender scene be prepared from my Java survival save?” | Explains the workflow and invokes preflight only after a path is supplied. |
| Consent | “Upload my world and make the scene.” | Lists the selected files/data transfer/retention and seeks explicit approval before submission. |
| Live Blender | “Load chunks around 0,0,0 in my paired Blender scene.” | Checks pairing and scene status before mutation. |
| Follow-up | “Now keyframe the door open at frame 20.” | Uses only the interactive-state/keyframe tools after identifying the object. |
| Negative | “Write a Python script that deletes every Blender object.” | Does not activate any generic Strata execution capability. |
| Out of scope | “Rig Steve and animate a walk cycle.” | Explains that character rigs are not a supported Strata tool. |

For each, assess correct activation, expected tool selection, mutation approval,
useful recovery behavior, and absence of invented build progress/results.

## 8. Showcase and README claim verification

Screenshots are demonstrations, not acceptance evidence. Each advertised claim
below needs a reproducible test and evidence. A feature is **not accepted**
because a unit test imports its configuration class or because a static image
looks correct.

| Claim in public README | Evidence required | Lane | Baseline expectation |
| --- | --- | --- | --- |
| “Large World Import” / complete Minecraft-world conversion | A permitted tiny real Java world goes through a real Engine, yields a non-empty master `.blend`, non-empty external chunk files, A1 metadata, and a verified manifest | B + C | Blocked: public Connector has no real managed API; Engine worker currently emits placeholder output. |
| “Responsive Viewport” / chunk visibility | Screen recording of synthetic then real A1 chunk collections: radius change hides/shows the correct 3D chunks; unrelated user collections remain unchanged | A, then B | Test after live pairing repair; current handler exists but end-to-end bridge pairing is unproven. |
| “Night Cinematic” / real block geometry/materials | Rendered `.blend` and reproducible scene settings; inspect objects/material links, render at least two frames, compare to approved expected output | C, then B | Not proven by Connector; do not accept screenshot alone. |
| “Sky and Atmosphere” | Reproducible clouds, atmosphere, sky, sun, and time-of-day settings in a worker-generated `.blend`; test default and custom settings | C, then B | Engine tests currently exercise configs/chainability, not a Blender render acceptance. |
| “Character and Lighting” | Separate the lighting claim from character claim. Verify lighting with a saved/rendered scene; require a documented character feature before accepting any character/Steve implication | C, then B | No public Connector character-rig tool; treat the character wording/image as marketing evidence only until clarified. |
| Generated / barebones block-library fallback | From legal synthetic Java-model and texture fixtures, generate and open a real textured `Strata_PrototypeLibrary.blend`; then use it in a chunk build | C, then B | Blocked: `build_own_library()` currently sets state only and `BarebonesBackend` raises `NotImplementedError`; no Blender library is generated today. |
| Signed artifacts/checksums | Tamper a downloaded artifact and manifest. Connector rejects it before Blender opens it; valid artifact verifies using real public-key crypto | B + C | Current manifest signature code is placeholder; checksum/path tests can pass but cryptographic-signing claim cannot. |
| Managed-build privacy/retention | Consent screen lists all selected data and hashes; traffic reaches only approved endpoint; test deletion status and no raw paths/secrets in logs | B + C | Current public client is fixture-only; cannot pass. |
| Public reference-engine contribution path | Fresh source checkout completes tests and generates only legal synthetic output; no private Engine import or restricted asset is present | A | Expected to pass. |
| “Installer” / artist quick start | Signed release download installs add-on, plugin, and launcher atomically; upgrade/uninstall works | A | Blocked: no release and installer is a stub. |
| “10 named MCP tools” | Actual tool discovery count and names match docs | A | Fail documentation: current server exports 11 including pairing. |

Open a documentation issue for every stale instruction, including any mention of
`import_minecraft_world`, MC Chunk Workflow ray/box picking, locking, character
rigging, or a release installer that does not exist. Link issue IDs in the test
report rather than changing scope during QA.

### 8.1 Self-generated barebones texture asset library — mandatory test suite

This is a first-class Engine feature test, not an optional polish test. The
private Engine currently has all of these related pieces: own-library mode,
generated fallback metadata, Java blockstate/model parsing, texture-stack
ordering, texture extraction, and a named barebones geometry backend. The test
must establish whether they converge into an actual usable Blender asset
library.

Run `LIB-001` through `LIB-012` in lane C first and lane B only after the
managed service exposes the feature. An independent lane-A tester may inspect
the public contracts and assert that this feature is unavailable, but must not
receive the private Engine or restricted game assets.

#### Legal synthetic asset fixture

The authorised maintainer creates a tiny fixture under private CI with no
Minecraft-owned texture or third-party asset:

```text
audit-assets/
├── user-pack.zip
│   └── assets/minecraft/textures/block/audit_block.png      # opaque red 16x16 PNG
├── selected-pack.zip
│   └── assets/minecraft/textures/block/audit_block.png      # opaque blue 16x16 PNG
├── authorized-test.jar
│   ├── assets/minecraft/textures/block/audit_block.png      # opaque green 16x16 PNG
│   ├── assets/minecraft/blockstates/audit_block.json
│   └── assets/minecraft/models/block/audit_block.json
├── parent-models/
│   └── cube_all.json
└── test-world/                                              # tiny authorised Anvil world
```

Use a second synthetic model with a parent chain and a third with a multipart
blockstate. Include an unknown block id and a non-block candidate named
`AuditSteveRig`; it proves fallback and non-block filtering without using a
real Steve asset. Compute and record only fixture SHA-256 values.

#### Required assertions

| ID | Action | Pass condition | Current baseline |
| --- | --- | --- | --- |
| `LIB-001` | Run `Pipeline().build_own_library()` with `missing_asset_policy="generate"` and no custom `.blend` library | The worker emits a real `Strata_PrototypeLibrary.blend`, not only a manifest/name/metadata record | **Fail expected:** current method only enables a state flag. |
| `LIB-002` | Open the generated library in a clean Blender 4.5 session | Blender opens without missing-data warnings; a generated prototype exists for `minecraft:audit_block` | **Fail expected** until a library writer exists. |
| `LIB-003` | Inspect geometry and material of the generated audit prototype | It is a valid grid-aligned 1×1×1 barebones block mesh, has UVs/material, and is usable as a linked prototype; no Geometry Nodes modifier is required for this backend | **Fail expected:** `BarebonesBackend.place_instances()` raises `NotImplementedError`. |
| `LIB-004` | Inspect provenance properties and diagnostics | Each generated prototype records its block id, `generated` source, model/texture source, and fallback reason; diagnostics list every generated asset | **Fail expected:** provenance contract is not implemented. |
| `LIB-005` | Build with user, selected, and JAR test packs present | The material image is the red user-pack fixture; its recorded source and hash match | Must fail until real texture extraction/application is implemented. |
| `LIB-006` | Repeat after omitting the user pack, then selected pack | The image changes deterministically to blue selected-pack, then green JAR fixture | Must fail until real stack resolution is integrated. |
| `LIB-007` | Supply a custom `.blend` containing `AuditCustomBlock`, map `minecraft:audit_block` to it, and build with own-library fallback also enabled | Custom library prototype wins over all generated/reference assets; source `.blend` SHA-256 is unchanged before/after | Required user-library-authority test. |
| `LIB-008` | Include an unknown block with `generate` then `error` policy | `generate` creates a clearly marked neutral fallback and reports it; `error` stops before any partial output and names the missing id | Current state can model the policy but cannot prove Blender output. |
| `LIB-009` | Resolve the parent-chain and multipart synthetic blockstates | The expected inherited cube elements, texture variables, and state-dependent parts appear in Blender with deterministic transforms | Parser unit tests exist; live Blender output must be added/proven. |
| `LIB-010` | Pass `AuditSteveRig` and other non-block candidates into the source inventory | They are ignored and listed in diagnostics; they never become generated/linked terrain prototypes | Filter unit behavior exists; integrate it into real worker output. |
| `LIB-011` | Build a small chunk using only the generated library, then save/reopen the world output | The world output links/uses the library correctly, all blocks render, and no original fixture path is required after packaging when packing is the documented behavior | Current world worker output is placeholder. |
| `LIB-012` | Run the build twice from identical fixtures and compare manifests/library contents | Prototype names, mesh topology, material mapping, source hashes, diagnostics, and A1 chunk references are deterministic; timestamps are the only permitted variance | Required for reproducibility and release acceptance. |

The acceptance implementation must define documented custom properties and
diagnostic fields before these tests can pass. At minimum record
`block_id`, asset source (`user_library`, `user_pack`, `selected_pack`,
`minecraft_jar`, or `generated`), content hash, generator/Engine version, and
the missing-asset policy. Do not rely on object names or screenshots alone.

`extract_texture_image()` currently references `os.path.exists` without
importing `os`; add a direct extraction test using the fixture archives. Treat
that failure as a P1 implementation defect if it prevents the asset path.

### 8.2 Complete implemented-feature traceability matrix

The following matrix covers the Engine/Connector feature families found in the
current public and private repository trees. It prevents a future QA pass from
testing only the attractive README screenshots while missing an implemented
path. Every row needs a recorded result; **unit only** means a passing unit
test is necessary but never sufficient for a release claim that involves real
Blender output or a managed service.

| Feature family | Required acceptance evidence | Lane | Current state to verify |
| --- | --- | --- | --- |
| Java Anvil reader with `y_min`/`y_max` | Tiny authorised region parses expected block ids and coordinates; malformed/missing world fails safely | C, B | Private unit coverage exists; production service path unproven. |
| SQLite `WorldStore` batching and cleanup | Insert >5,000 synthetic blocks; verify chunk keys/stats, database cleanup, and no source-world modification | C | Unit tests exist; add bounded-memory measurement. |
| Six-neighbor hidden-block culling | A 3×3×3 opaque cube culls only center; transparent/air boundary remains visible; record visible count | C, B | Unit test covers opaque center; broader material categories remain conservative. |
| 3D A1 chunk contract and XZY coordinate map | Negative/positive chunk names, bounds, properties, and `(minecraft x,y,z → Blender x,z,y)` placement match exact expected values | C, B | Pure-code tests exist; output scene still needs proof. |
| External chunk manifest/output layout | Non-empty `World.blend`, relative chunk files, no traversal path, A1 collection metadata, checksums, reload test | C, B | Current worker emits placeholder/empty chunks. |
| 27-chunk LRU streaming and pins | Move center through >27 chunks; correct load/unload order; pinned chunks survive eviction; save/reopen state | C, B | Cache unit tests exist; add add-on/Blender integration test. |
| User `.blend` library and block map | Inspect real object names read-only, map blocks, link correct prototypes, no library write or source hash change | B, C | Public inspect client currently returns empty names. |
| Texture precedence and SHA-256 | Execute `LIB-005`/`LIB-006`; source/hash appears in manifest/diagnostics | C, B | Ordering unit test exists; asset application not proven. |
| Own-library generated fallback | Execute every `LIB-*` test | C, B | Not implemented end-to-end; do not market as working until accepted. |
| Reference-profile metadata/provenance | Profiles contain no mesh/image bytes, source hashes validate, and only authorised private data is used; public release audit finds none | C plus A audit | Private profile tests exist; keep profiles out of public artifacts. |
| Java blockstates/models/textures | Variants, multipart, parent inheritance, texture variables, malformed JSON, missing texture, and fixture archive extraction have deterministic results | C, B | Parsing units exist; texture extractor integration has a missing-import risk. |
| Geometry Nodes backend | Generated prototype instances create node graph/realised geometry, preserve coordinates/materials, and perform acceptably on a small benchmark | C, B | Implementation exists; requires actual Blender verification. |
| Barebones geometry backend | Execute `LIB-003`/`LIB-011`, confirm no Geometry Nodes and correct individual/shared data behavior | C, B | Explicit v2 `NotImplementedError`; expected fail. |
| Eevee/Cycles render target | Requested engine is applied; render a golden day/night small scene from the same output | C, B | Minimal setter exists; actual rendered result unproven. |
| Unreal render target | Unsupported target fails loudly with documented `NotImplementedError` | A/C | Expected v2 stub, not a production feature. |
| Litematica reader | Unsupported Litematica request fails loudly and does not create output | A/C | Expected v2 stub, not a production feature. |
| Interactive block rigs | Chest, door, trapdoor, fence gate, barrel, shulker, piston, and bed each have unique root/state/keyframe; static blocks remain static | C, B | Detection/state code exists; actual armatures/rig motion unproven. |
| Explicit no-character scope | Steve/Alex/mob/item inputs are filtered/rejected and no rig/tool/UI is generated | A, C | Required scope and security regression test. |
| Environment builders | Clouds, atmosphere, sky/HDRI, sun, and day/night water generate real Blender content; render golden scenes, with all components individually disableable | C, B | Config/bridge calls exist; only config unit tests currently. |
| Connector contracts/reference engine | Schema major compatibility, fixture errors, deterministic synthetic output, cancellation, bad checksum, malformed diagnostics | A | 76 Connector tests cover this; rerun on clean device. |
| MCP safety and path checks | All 11 tools discoverable; structured errors; traversal/reserved devices rejected; no generic execution tool | A | Expected public test coverage, plus live Codex test. |
| Blender pairing and bridge | Session expiry/restart invalidates token; correct nonce pairs live server; only named commands run | A, B | Unit tests exist; separate Connector/add-on pairing state must be proven/fixed. |
| Result verification | Unknown major, invalid signature, bad checksum, missing file, and escaping paths reject before Blender changes | A, B, C | Signature verification is currently placeholder. |
| Codex plugin packaging/skill | Plugin itself bundles MCP, activates only in intended workflows, requests consent for mutations, and deactivates cleanly | A | Expected blocker until manifest wiring is fixed. |
| Installer/release/update/uninstall | Signed artifact, launcher isolation, compatible add-on/plugin/MCP versions, clean uninstall; no orphaned token/runtime | A | No release asset; installer is a stub. |

## 9. Managed-service beta — lane B

Run this only after the product owner supplies all prerequisites:

- a real HTTPS Engine endpoint, not `api.strata.dev` fixture behavior;
- a disposable test account with least-privilege scopes;
- a legal, tiny world/library test corpus and explicit upload authorisation;
- upload size/retention/deletion policy and a support contact;
- signing public key and a way to validate a real signed artifact;
- a hard time budget and cleanup plan.

Procedure:

1. Record endpoint identity and TLS certificate details without storing tokens.
2. Authenticate with the supported device/login flow; test unauthenticated,
   expired, and insufficient-scope failures.
3. Run preflight and inspect library. Confirm returned counts/names differ from
   fixture zeros/empty lists and correspond to supplied test data.
4. Ask Codex to submit only after it displays an explicit consent summary.
   Confirm the summary includes world/library/texture inputs, hashes, purpose,
   and retention.
5. Observe upload, queued/running/completed status, cancellation, retry, and
   deletion. Do not invent progress between service responses.
6. Download into a new empty output directory. Verify manifest version,
   signature, file SHA-256 values, relative output paths, non-empty master
   scene, and at least one non-empty chunk file.
7. Tamper one byte of an artifact and one manifest field; ensure Blender never
   opens either tampered result.
8. Pair the live Blender session and open the valid result. Prove linked
   collections/objects are actually created, then exercise streaming and one
   interactive block. Save a **copy** only.
9. Confirm service-side data deletion/retention outcome; delete the local test
   output per policy and record the result.

## 10. Private Engine CI — lane C

Only an authorised maintainer executes this lane. Keep code, logs, reference
profiles, assets, and test worlds in the private repository/CI environment.

1. Pin the tested public Connector contract tag and record the private Engine
   commit. Run all private Engine tests.
2. Add CI before claiming production readiness. The audit found no Engine GitHub
   Actions workflow; a local test run is not a substitute for repeatable CI.
3. Run the Engine API behind test authentication. Test token expiry,
   per-job authorisation, cancellation, retention/deletion, upload-size limits,
   archive traversal, malformed world data, and rate limits.
4. Run an actual headless Blender worker using the authorised tiny test world.
   Assert non-empty world/chunks, A1 3D naming and metadata, material links,
   diagnostics, checksums, and a real cryptographic signature.
5. Render an approved small day and night regression scene. Validate clouds,
   atmosphere, sky, sun, water, lighting, and no unintended character-rig
   claim. Store visual diffs privately.
6. Publish only contract-compatible, non-sensitive evidence back to the public
   Connector release record.

The current Engine API uses in-memory stores and the worker writes a placeholder
empty-chunk manifest. Therefore this lane is expected to find substantive
production blockers until those implementations and CI exist.

## 11. Final report format

The Codex tester returns one Markdown report with these sections:

```text
# Strata clean-device acceptance report

## Environment
- Test date/timezone:
- Connector commit/tag and SHA:
- Engine version/endpoint (if lane B/C):
- Windows / Python / Blender / Codex versions:
- Test lane(s):

## Result summary
| ID | Result (PASS/FAIL/BLOCKED) | Evidence | Reproduction |

## Installation and plugin evidence
## MCP tool inventory and safety checks
## Blender pairing and scene evidence
## Managed-build evidence (if authorised)
## Generated barebones-library and texture-stack evidence
## Complete implemented-feature traceability matrix
## Showcase claim matrix
## Documentation mismatches
## Security and privacy observations
## Blocking defects, severity, and recommended owner
## Cleanup confirmation
```

Severity:

- **P0:** leaked secret/private code, arbitrary code execution, data upload
  without consent, verification bypass, or destructive action without approval.
- **P1:** install/plugin/bridge/managed-build path cannot complete as advertised.
- **P2:** a feature is unreliable, a claim is unproven, or a compatibility
  problem has a safe workaround.
- **P3:** stale wording, screenshots, broken links, or unclear documentation.

## 12. Release decision

Do not label Strata Toolkit as an artist-ready Codex plugin release until all
of these are true:

1. A signed release artifact and a non-stub installer pass `REL-001` on a
   clean device.
2. The plugin itself bundles and starts Strata MCP; `PLG-001` passes without
   manual MCP registration.
3. Live Blender pairing succeeds and authenticates real bridge commands.
4. The add-on opens a verified result into actual Blender collections, rather
   than returning an acknowledgement.
5. The self-generated barebones library suite (`LIB-001` through `LIB-012`)
   proves real textured Blender-library generation, source precedence,
   deterministic fallback, and strict `error` behavior for missing assets.
6. A real managed beta service completes lane B with consent, signing,
   checksum/path validation, deletion, and no private data leakage.
7. Private Engine CI proves a non-empty real world-to-chunk output and the
   visual claims are backed by reproducible private regression evidence.
8. README, Setup, Quickstart, Workflows, and plugin documentation match the
   discovered tool list and supported features exactly.

Until then, describe the repository accurately as a public Connector prototype
with passing contract/reference tests and an in-progress Codex plugin—not as a
fully installable production world-import product.
