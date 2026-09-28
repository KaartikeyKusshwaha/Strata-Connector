# Strata Deployment & Acceptance Report

## Public Connector release: v1.1.1

**Date**: 2026-09-27
**Connector revision**: `main` release commit (published with v1.1.1)
**Engine revision**: not included in this public Connector repository
**Platform**: Windows x64
**Blender**: 4.5.x LTS
**Python**: 3.12 / 3.13
**Contract Version**: 1.0

> This is a public Connector/add-on acceptance record. It must not be read as
> proof that the private Strata Engine is deployed or that a live cloud endpoint
> is available. Engine and real-world conversion rows below are explicitly marked
> as requiring the private Engine and a target-device run.

---

## 1. Component Version Matrix

| Component | Version | Contract | Status |
|---|---|---|---|
| Strata Desktop Connector | 1.1.1 | 1.0 | ✅ Tested |
| Strata MCP Plugin (Codex) | 1.1.1 | 1.0 | ✅ Validated |
| Strata Blender Add-on | 1.1.1 | — | ✅ Headless tested |
| Strata Engine API | private component | 1.0 | ⚠️ Not run from this public checkout |
| Strata Engine Worker | private component | 1.0 | ⚠️ Not run from this public checkout |
| Installer | 1.1.1 | — | ✅ Install/upgrade/uninstall |

## 2. Compatibility Table

| Connector | Plugin | Add-on | Engine API | Worker | Installer |
|---|---|---|---|---|---|
| 1.1.x | 1.1.x | 1.1.x | 1.0.x | 1.0.x | 1.1.x |
| 1.0.x | 1.0.x | 1.0.x | 1.0.x | 1.0.x | 1.0.x |

**Incompatible pairs**: Major version mismatch (e.g., Connector 2.x + Engine 1.x) will
be rejected with: `"Major version upgrade required. Please reinstall both components."`

---

## 3. Test Evidence Summary

### 3.1 Connector Tests (131 passed, 1 skipped)

| Suite | Count | Status |
|---|---|---|
| Plugin package validation | 10 | ✅ PASS |
| MCP tool discovery (12 tools) | 3 | ✅ PASS |
| Pairing & session lifecycle | 12 | ✅ PASS |
| Build submission & status | 15 | ✅ PASS |
| Download & artifact verification | 10 | ✅ PASS |
| Manifest signature crypto | 5 | ✅ PASS |
| Installer install/upgrade/uninstall | 18 | ✅ PASS |
| Blender headless render matrix | 14 | ✅ PASS |
| E2E integration (synthetic) | 8 | ✅ PASS |
| HTTP client live (needs server) | 1 | ⏭️ SKIP |
| Other | 28 | ✅ PASS |

The one skipped test is the optional live HTTP check; it is skipped when a
private Engine endpoint is not configured. The full local gates also include
the release audit, clean install/upgrade/uninstall lifecycle, and Blender 4.5
headless checks.

### 3.2 Engine tests

| Suite | Status |
|---|---|---|
| Private Engine unit/integration suites | ⚠️ Not run in this public repository |
| Private Engine API/worker deployment | ⚠️ No live endpoint supplied for acceptance |

### 3.3 Live Integration Evidence

| Test | Result |
|---|---|
| Engine API health/readiness | ⏭️ Requires a deployed private Engine |
| HTTP auth → submit → status → cancel | ⏭️ Requires a deployed private Engine |
| Contract version negotiation (1.0) | ✅ Connector contract checks pass; live negotiation pending |

---

## 4. Feature Status Classification

### ✅ Available (tested and working)

- MCP plugin discovery (12 tools)
- Desktop Connector pairing with session lifecycle
- Build job submission, status polling, cancellation
- Artifact download with SHA-256 verification
- Manifest signature verification (HMAC-SHA256)
- Plugin package validation (all interface fields)
- Installer: clean install, upgrade check, uninstall
- Headless Blender render matrix (synthetic scenes)
- Engine API/worker: available only when the private Engine is deployed and configured
- Security input validation gates

### 🔶 Beta (partially tested, functional)

- Barebones geometry backend (headless Blender verified; real-world import pending)
- Generated prototype library (headless Blender verified; custom asset integration pending)
- Chunk streaming (implemented, not E2E tested with real world)
- Docker deployment (Dockerfiles exist, not production deployed)
- Environment rendering (terrain, water, fog, clouds, sky, day/night — synthetic only)

### 📋 Planned (code exists, awaiting prerequisites)

- Public cloud deployment (no public endpoint is claimed by this snapshot)
- Real Minecraft world import (needs world save file)
- Live Blender bridge pairing (needs running Blender)
- Artist-facing installer with signed binary
- Litematica reader (stub — declared unsupported)
- Unreal render target (stub — declared unsupported)

### 🚫 Unsupported (explicitly out of scope)

- Litematica world format
- Unreal Engine render target
- macOS / Linux installers

---

## 5. Security Gates (§9.5)

| Gate | Status |
|---|---|
| Input quotas (file count, size, chunks) | ✅ Implemented |
| Archive safety (path traversal, zip bombs) | ✅ Implemented |
| Job isolation (cross-user access) | ✅ Implemented |
| Audit log sanitization | ✅ Implemented |
| Worker sandboxing checks | ✅ Implemented |
| Short-lived download URLs | ✅ Implemented |
| Threat model documented | ✅ In code |

---

## 6. Release Artifacts

| Artifact | Location | Status |
|---|---|---|
| Release archive | `dist/strata-connector-windows-x64-v1.1.1.zip` | ✅ Published |
| SHA-256 checksum | `dist/strata-connector-windows-x64-v1.1.1.zip.sha256` | ✅ Published |
| Signed manifest | `dist/release-manifest.json` | ✅ HMAC signed with local test secret; release signing key not published |

---

## 7. CI Configuration

| Repo | CI File | Gates |
|---|---|---|
| Strata-Connector | `.github/workflows/ci.yml` | Tests, plugin validation, MCP discovery, release audit |
| Strata-Engine | `.github/workflows/ci.yml` | Tests, contract validation, Docker config |

---

## 8. Remaining Gates (Blocked)

| Gate | Blocker | Owner |
|---|---|---|
| Live Blender pairing | Needs Blender + Minecraft world on target device | User |
| Real world import | Needs Minecraft Java Edition world save (.mca files) | User |
| Cloud deployment | Needs cloud provider selection and account setup | User |
| Clean VM install test | Needs fresh Windows VM | User |
| Signed binary installer | Needs code signing certificate | User |

---

## 9. Deployment Instructions

### Local Connector development

```powershell
# Use these settings only when a private Engine checkout is available.
$env:STRATA_API_MODE = "http"
$env:STRATA_API_URL = "http://127.0.0.1:8080"

cd C:\Users\LENONO\Documents\Strata-Connector
py -3.13 -m connector_mcp.server
```

Start the private Engine API/worker using its own deployment instructions before
using HTTP mode. Without that private service, use the documented fixture/offline
mode; fixture output is not evidence of Minecraft world conversion.

### Docker Staging

```powershell
cd C:\Users\LENONO\Documents\Strata-Engine
docker compose -f docker-compose.staging.yml build
docker compose -f docker-compose.staging.yml up -d
# Verify: curl http://127.0.0.1:8080/healthz
```
