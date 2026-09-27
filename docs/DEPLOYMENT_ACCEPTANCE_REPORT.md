# Strata Deployment & Acceptance Report

## Release Candidate: v1.1.0

**Date**: 2026-09-27
**Connector SHA**: codex/acceptance-remediation (pending merge → main)
**Engine SHA**: codex/acceptance-remediation (pending merge → main)
**Platform**: Windows x64
**Blender**: 4.5.x LTS
**Python**: 3.12 / 3.13
**Contract Version**: 1.0

---

## 1. Component Version Matrix

| Component | Version | Contract | Status |
|---|---|---|---|
| Strata Desktop Connector | 1.1.0 | 1.0 | ✅ Tested |
| Strata MCP Plugin (Codex) | 1.1.0 | 1.0 | ✅ Validated |
| Strata Blender Add-on | 1.1.0 | — | ✅ Headless tested |
| Strata Engine API | 1.0.0 | 1.0 | ✅ Live tested |
| Strata Engine Worker | 1.0.0 | 1.0 | ✅ Unit tested |
| Installer | 1.1.0 | — | ✅ Install/upgrade/uninstall |

## 2. Compatibility Table

| Connector | Plugin | Add-on | Engine API | Worker | Installer |
|---|---|---|---|---|---|
| 1.1.x | 1.1.x | 1.1.x | 1.0.x | 1.0.x | 1.1.x |
| 1.0.x | 1.0.x | 1.0.x | 1.0.x | 1.0.x | 1.0.x |

**Incompatible pairs**: Major version mismatch (e.g., Connector 2.x + Engine 1.x) will
be rejected with: `"Major version upgrade required. Please reinstall both components."`

---

## 3. Test Evidence Summary

### 3.1 Connector Tests (103 passed, 1 skipped)

| Suite | Count | Status |
|---|---|---|
| Plugin package validation | 8 | ✅ PASS |
| MCP tool discovery (11 tools) | 3 | ✅ PASS |
| Pairing & session lifecycle | 12 | ✅ PASS |
| Build submission & status | 15 | ✅ PASS |
| Download & artifact verification | 10 | ✅ PASS |
| Manifest signature crypto | 5 | ✅ PASS |
| Installer install/upgrade/uninstall | 18 | ✅ PASS |
| Blender headless render matrix | 14 | ✅ PASS |
| E2E integration (synthetic) | 8 | ✅ PASS |
| HTTP client live (needs server) | 1 | ⏭️ SKIP |
| Other | 10 | ✅ PASS |

### 3.2 Engine Tests (74 passed)

| Suite | Count | Status |
|---|---|---|
| Pipeline stages | 12 | ✅ PASS |
| Block library & textures | 8 | ✅ PASS |
| Worker job execution | 10 | ✅ PASS |
| API endpoints (FastAPI) | 15 | ✅ PASS |
| Contracts & schemas | 6 | ✅ PASS |
| Asset acquisition & inventory | 8 | ✅ PASS |
| Chunking & culling | 7 | ✅ PASS |
| Environment builders | 5 | ✅ PASS |
| Security gates | 3+ | ✅ PASS (new) |

### 3.3 Live Integration Evidence

| Test | Result |
|---|---|
| Engine API health check | ✅ `{"status": "healthy"}` |
| Engine API readiness | ✅ `{"status": "ready"}` |
| HTTP auth → submit → status → cancel | ✅ Full flow verified |
| Contract version negotiation (1.0) | ✅ Accepted |

---

## 4. Feature Status Classification

### ✅ Available (tested and working)

- MCP plugin discovery (11 tools)
- Desktop Connector pairing with session lifecycle
- Build job submission, status polling, cancellation
- Artifact download with SHA-256 verification
- Manifest signature verification (HMAC-SHA256)
- Plugin package validation (all interface fields)
- Installer: clean install, upgrade check, uninstall
- Headless Blender render matrix (synthetic scenes)
- Engine API: full job lifecycle
- Engine Worker: job execution with manifest
- Security input validation gates

### 🔶 Beta (partially tested, functional)

- Barebones geometry backend (unit tested, not live Blender)
- Generated prototype library (unit tested, not live Blender)
- Chunk streaming (implemented, not E2E tested with real world)
- Docker deployment (Dockerfiles exist, not production deployed)
- Environment rendering (terrain, water, fog, clouds, sky, day/night — synthetic only)

### 📋 Planned (code exists, awaiting prerequisites)

- Public cloud deployment (api.strata.dev)
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
| Release archive | `dist/strata-connector-windows-x64-v1.1.0.zip` | ✅ Built |
| SHA-256 checksum | `dist/strata-connector-windows-x64-v1.1.0.zip.sha256` | ✅ Computed |
| Signed manifest | `dist/release-manifest.json` | ✅ HMAC signed |

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

### Local Development

```powershell
# Start Engine API
cd C:\Users\LENONO\Documents\Strata-Engine
py -3.13 -m uvicorn api.app:app --host 127.0.0.1 --port 8080

# Set connector to use local engine
$env:STRATA_API_URL = "http://127.0.0.1:8080"

# Run connector
cd C:\Users\LENONO\Documents\Strata-Connector
py -3.13 -m connector_mcp.server
```

### Docker Staging

```powershell
cd C:\Users\LENONO\Documents\Strata-Engine
docker compose -f docker-compose.staging.yml build
docker compose -f docker-compose.staging.yml up -d
# Verify: curl http://127.0.0.1:8080/healthz
```
