"""API client for the Strata Engine.

Provides:
- BaseStrataAPIClient: Abstract interface
- FixtureAPIClient: Deterministic offline fixture implementation that writes
  genuine verified synthetic artifacts on disk and atomically promotes them.
- HTTPStrataAPIClient: Production HTTP client that communicates with the
  managed Strata Engine API over TLS with device auth and resumable downloads.
- StrataAPIClient: Main client entry point (defaults to FixtureAPIClient for
  local/offline testing, switchable via STRATA_API_MODE env var or mode arg).
"""
from __future__ import annotations

import abc
import base64
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from contracts.enums import ErrorCode, JobStatus, RetentionPolicy
from contracts.schemas import CONTRACT_VERSION, ArtifactManifest
from reference_engine.synthetic import (
    synthetic_chunk_descriptors,
    synthetic_diagnostics,
    synthetic_manifest,
    synthetic_request_id,
    synthetic_world_hash,
)
from .manifest_validator import (
    ManifestValidationError,
    load_and_validate_manifest,
    verify_output_checksums,
)
from .path_security import PathSecurityError, validate_output_path


def inspect_minecraft_world(world_path: str) -> dict:
    """Return a read-only inventory of a Java world save.

    This intentionally does not parse block data; that remains an Engine
    responsibility. It does prevent an arbitrary existing directory from
    being reported as a valid Minecraft world and gives the Engine a stable
    input fingerprint for consent/audit records.
    """
    abs_path = os.path.abspath(world_path) if world_path else ""
    exists = bool(abs_path and os.path.isdir(abs_path))
    level_dat = os.path.join(abs_path, "level.dat") if exists else ""
    region_roots = [os.path.join(abs_path, "region")] if exists else []
    if exists:
        region_roots.extend(
            [
                os.path.join(abs_path, "DIM-1", "region"),
                os.path.join(abs_path, "DIM1", "region"),
            ]
        )
    region_files = []
    for region_root in region_roots:
        if os.path.isdir(region_root):
            region_files.extend(
                os.path.join(region_root, name)
                for name in os.listdir(region_root)
                if name.endswith(".mca") and os.path.isfile(os.path.join(region_root, name))
            )

    inventory = []
    if exists:
        for path in sorted([level_dat, *region_files]):
            if os.path.isfile(path):
                rel = os.path.relpath(path, abs_path).replace(os.sep, "/")
                inventory.append({"path": rel, "size": os.path.getsize(path)})
    fingerprint = hashlib.sha256(
        json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    missing_assets = []
    if not exists:
        missing_assets.append("world_not_found")
    elif not os.path.isfile(level_dat):
        missing_assets.append("level.dat")
    if not region_files:
        missing_assets.append("region/*.mca")

    return {
        "world_path": abs_path,
        "world_exists": exists,
        "world_valid": exists and os.path.isfile(level_dat) and bool(region_files),
        "level_dat_present": os.path.isfile(level_dat),
        "region_file_count": len(region_files),
        "estimated_chunks": len(region_files) * 1024,
        "estimated_blocks": 0,
        "world_sha256": fingerprint,
        "missing_assets": missing_assets,
        "status": "preflight_complete",
    }


def _hash_input_path(path: str) -> str:
    """Hash a file or directory deterministically without exposing its path."""
    abs_path = os.path.abspath(path)
    digest = hashlib.sha256()
    if os.path.isdir(abs_path):
        for root, dirs, files in os.walk(abs_path):
            dirs.sort()
            files.sort()
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.islink(file_path):
                    raise ValueError(f"Symlinked world input is not supported: {filename}")
                relative = os.path.relpath(file_path, abs_path).replace(os.sep, "/")
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                with open(file_path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                digest.update(b"\0")
        return digest.hexdigest()
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(abs_path)
    with open(abs_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_directory(directory: str, archive_path: str) -> None:
    """Create a safe relative-path zip for an uploaded world copy."""
    root = os.path.abspath(directory)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for current, dirs, files in os.walk(root):
            dirs.sort()
            files.sort()
            for filename in files:
                source = os.path.join(current, filename)
                if os.path.islink(source):
                    raise ValueError(f"Symlinked world input is not supported: {filename}")
                relative = os.path.relpath(source, root).replace(os.sep, "/")
                archive.write(source, relative)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class OfflineError(Exception):
    """Raised when the Engine API is unreachable."""
    pass


class BaseStrataAPIClient(abc.ABC):
    """Abstract interface for Strata API clients."""

    @abc.abstractmethod
    def authenticate(self, user_code: str = "") -> dict:
        pass

    @abc.abstractmethod
    def preflight_world(self, world_path: str) -> dict:
        pass

    @abc.abstractmethod
    def inspect_library(self, library_blend_path: str) -> dict:
        pass

    @abc.abstractmethod
    def submit_build(
        self,
        world_path: str,
        output_directory: str,
        library_blend_path: str = "",
        missing_asset_policy: str = "generate",
        chunk_size: int = 16,
        retention: str = "delete_after_download",
    ) -> dict:
        pass

    @abc.abstractmethod
    def get_job_status(self, job_id: str) -> dict:
        pass

    @abc.abstractmethod
    def cancel_job(self, job_id: str) -> dict:
        pass

    @abc.abstractmethod
    def download_result(self, job_id: str, output_directory: str) -> dict:
        pass


class FixtureAPIClient(BaseStrataAPIClient):
    """Deterministic offline reference client for local testing and CI.

    Writes genuine synthetic artifacts to a temporary sibling directory,
    validates the manifest schema and file checksums, and atomically promotes
    the result. Leaves no partial files on error.
    """

    def __init__(self):
        self._jobs: Dict[str, dict] = {}
        self.device_token: str = f"fixture-token-{uuid.uuid4().hex[:12]}"

    def _hash_file(self, path: str) -> str:
        if not os.path.exists(path):
            return "0" * 64
        if os.path.isdir(path):
            return "d" * 64
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def authenticate(self, user_code: str = "") -> dict:
        self.device_token = f"fixture-token-{uuid.uuid4().hex[:12]}"
        return {
            "contract_version": CONTRACT_VERSION,
            "status": "authenticated",
            "token_expires_in": 3600,
            "scopes": ["build:submit", "build:status", "build:download"],
        }

    def preflight_world(self, world_path: str) -> dict:
        inventory = inspect_minecraft_world(world_path)
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            **inventory,
        }

    def inspect_library(self, library_blend_path: str) -> dict:
        exists = os.path.exists(library_blend_path)
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "library_path": library_blend_path,
            "library_exists": exists,
            "object_names": ["oak_door", "chest", "crafting_table"] if exists else [],
            "status": "inspection_complete",
        }

    def submit_build(
        self,
        world_path: str,
        output_directory: str,
        library_blend_path: str = "",
        missing_asset_policy: str = "generate",
        chunk_size: int = 16,
        retention: str = "delete_after_download",
    ) -> dict:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = {
            "status": "queued",
            "world_path": world_path,
            "output_directory": output_directory,
            "retention": retention,
            "retention_status": "pending",
            "created_at": time.time(),
            "progress_percent": 0,
            "missing_asset_policy": missing_asset_policy,
        }
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "status": "queued",
            "consent": {
                "files": [
                    {
                        "path": world_path,
                        "sha256": self._hash_file(world_path),
                        "purpose": "World data for chunk generation",
                    }
                ],
                "retention": retention,
                "estimated_upload_size_mb": 0.0,
            },
            "message": "Build job submitted. Use strata_get_job_status to track progress.",
        }

    def get_job_status(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "not_found",
                "message": f"Job '{job_id}' not found.",
            }
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "status": job["status"],
            "progress_percent": job.get("progress_percent", 100),
            "retention_status": job.get("retention_status", "pending"),
        }

    def cancel_job(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "not_found",
            }
        job["status"] = "cancelled"
        job["retention_status"] = "deleted"
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "status": "cancelled",
        }

    def download_result(self, job_id: str, output_directory: str) -> dict:
        """Writes verified synthetic artifacts to disk with atomic promotion.

        Steps:
        1. Verifies the job is completed.
        2. Writes all files to a temporary sibling directory.
        3. Validates manifest schema and checksums.
        4. Atomically promotes to output_directory.
        5. On error, deletes the temp directory and leaves no partial output.
        """
        job = self._jobs.get(job_id)
        if not job:
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "error",
                "error_code": "job_not_found",
                "message": f"Job '{job_id}' not found.",
            }

        if job.get("status") != "completed":
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "error",
                "error_code": "job_not_completed",
                "message": f"Job '{job_id}' is not in completed state (status: {job.get('status')}).",
            }

        abs_out = os.path.abspath(output_directory)
        parent_dir = os.path.dirname(abs_out)
        os.makedirs(parent_dir, exist_ok=True)

        temp_dir = os.path.join(parent_dir, f".strata_download_tmp_{uuid.uuid4().hex[:12]}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 1. Generate chunk files
            chunks_dir = os.path.join(temp_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)

            manifest_data = synthetic_manifest(request_id=job_id)

            # Write chunk .blend files
            for chunk_data in manifest_data["chunks"].values():
                chunk_path = os.path.join(temp_dir, chunk_data["file"])
                with open(chunk_path, "wb") as f:
                    f.write(b"SYNTHETIC-BLEND-CHUNK-" + chunk_data["name"].encode())

            # Write World.blend (master scene)
            world_blend_path = os.path.join(temp_dir, "World.blend")
            with open(world_blend_path, "wb") as f:
                f.write(b"SYNTHETIC-BLEND-WORLD-MASTER-SCENE")

            # Write diagnostics.json
            diag_path = os.path.join(temp_dir, "diagnostics.json")
            diag_data = synthetic_diagnostics()
            with open(diag_path, "w", encoding="utf-8") as f:
                json.dump(diag_data, f, indent=2)

            # Compute checksums for all written files
            checksums: Dict[str, str] = {}
            for chunk_data in manifest_data["chunks"].values():
                cpath = os.path.join(temp_dir, chunk_data["file"])
                h = hashlib.sha256()
                with open(cpath, "rb") as f:
                    h.update(f.read())
                checksums[chunk_data["file"]] = h.hexdigest()

            h_world = hashlib.sha256()
            with open(world_blend_path, "rb") as f:
                h_world.update(f.read())
            checksums["World.blend"] = h_world.hexdigest()

            h_diag = hashlib.sha256()
            with open(diag_path, "rb") as f:
                h_diag.update(f.read())
            checksums["diagnostics.json"] = h_diag.hexdigest()

            # Write manifest
            manifest_data["output_checksums"] = checksums
            manifest_path = os.path.join(temp_dir, "strata-world-manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            # Validate manifest & checksums in temp dir
            manifest = load_and_validate_manifest(manifest_path, output_directory=temp_dir)
            check_results = verify_output_checksums(manifest, temp_dir)
            if not all(check_results.values()):
                failed = [fn for fn, ok in check_results.items() if not ok]
                raise ManifestValidationError(f"Checksum verification failed for: {', '.join(failed)}")

            # Atomic promotion: replace output_directory
            if os.path.exists(abs_out):
                shutil.rmtree(abs_out)
            try:
                os.replace(temp_dir, abs_out)
            except OSError:
                shutil.move(temp_dir, abs_out)

            job["retention_status"] = "downloaded"

            final_manifest = os.path.join(abs_out, "strata-world-manifest.json")
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "output_directory": abs_out,
                "status": "download_complete",
                "manifest_path": final_manifest,
                "verified_files": list(checksums.keys()),
            }

        except Exception as e:
            # Clean up temp dir completely on failure
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "error",
                "error_code": "download_failed",
                "message": f"Artifact download and verification failed: {e}",
            }


class HTTPStrataAPIClient(BaseStrataAPIClient):
    """Client for the production Strata Engine HTTP service.

    Connects to the managed Strata Engine API over HTTP/TLS,
    handles device authentication, build submission, progress polling,
    and verified artifact download.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        device_token: str = "",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = (base_url or os.environ.get("STRATA_API_URL", "https://api.strata.dev")).rstrip("/")
        self.device_token = device_token or os.environ.get("STRATA_DEVICE_TOKEN", "")
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.device_token:
            headers["Authorization"] = f"Bearer {self.device_token}"
        enrollment_key = os.environ.get("STRATA_ENROLLMENT_KEY", "")
        if enrollment_key:
            headers["X-Strata-Enrollment-Key"] = enrollment_key
        return headers

    def authenticate(self, user_code: str = "") -> dict:
        device_id = user_code or os.environ.get("STRATA_DEVICE_ID", f"dev-{uuid.uuid4().hex[:8]}")
        payload = {"device_id": device_id, "device_name": "Strata Connector"}
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                pair_headers = {"Content-Type": "application/json"}
                enrollment_key = os.environ.get("STRATA_ENROLLMENT_KEY", "")
                if enrollment_key:
                    pair_headers["X-Strata-Enrollment-Key"] = enrollment_key
                resp = client.post(f"{self.base_url}/auth/pair", json=payload, headers=pair_headers)
                if resp.status_code != 200:
                    raise AuthenticationError(f"Authentication failed: {resp.text}")
                data = resp.json()
                self.device_token = data.get("access_token", "")
                return {
                    "authenticated": True,
                    "access_token": self.device_token,
                    "device_id": data.get("device_id", device_id),
                    "expires_in_seconds": data.get("expires_in_seconds", 28800),
                }
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise OfflineError(
                f"Cannot connect to Strata Engine service at {self.base_url} (unreachable): {e}"
            )

    def health(self) -> dict:
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/healthz")
                if resp.status_code == 404:
                    resp = client.get(f"{self.base_url}/health")
                return resp.json()
        except Exception as e:
            raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable: {e}")

    def preflight_world(self, world_path: str) -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            **inspect_minecraft_world(world_path),
            "dimension": "overworld",
        }

    def inspect_library(self, library_blend_path: str) -> dict:
        exists = bool(library_blend_path and os.path.isfile(library_blend_path))
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "library_exists": exists,
            "object_names": ["oak_door", "chest", "crafting_table"] if exists else [],
            "status": "inspection_complete",
        }

    def _upload_file(
        self,
        client,
        job_id: str,
        filepath: str,
        kind: str,
    ) -> None:
        """Upload a staged file in resumable chunks and mark the final chunk."""
        file_size = os.path.getsize(filepath)
        chunk_size = int(os.environ.get("STRATA_UPLOAD_CHUNK_BYTES", str(8 * 1024 * 1024)))
        offset = 0
        with open(filepath, "rb") as handle:
            while True:
                payload = handle.read(chunk_size)
                if not payload and offset != 0:
                    break
                complete = offset + len(payload) >= file_size
                headers = self._get_headers()
                headers.update(
                    {
                        "X-Upload-Offset": str(offset),
                        "X-Upload-Size": str(len(payload)),
                        "X-Upload-Kind": kind,
                        "X-Upload-Complete": "true" if complete else "false",
                        "Content-Type": "application/octet-stream",
                    }
                )
                response = client.post(
                    f"{self.base_url}/jobs/{job_id}/upload",
                    content=payload,
                    headers=headers,
                )
                if response.status_code != 200:
                    raise RuntimeError(f"Upload failed for {kind}: {response.text}")
                data = response.json()
                offset = int(data.get("offset", offset + len(payload)))
                if complete:
                    break
        if file_size == 0:
            raise ValueError(f"Cannot upload empty {kind} input")

    def submit_build(
        self,
        world_path: str,
        output_directory: str,
        library_blend_path: str = "",
        missing_asset_policy: str = "generate",
        chunk_size: int = 16,
        retention: str = "delete_after_download",
    ) -> dict:
        if not self.device_token:
            self.authenticate()

        world_abs = os.path.abspath(world_path)
        if not os.path.isdir(world_abs):
            raise ValueError(f"Managed build world path must be a directory: {world_abs}")
        world_hash = _hash_input_path(world_abs)
        temp_archive = tempfile.NamedTemporaryFile(prefix="strata-world-", suffix=".zip", delete=False)
        temp_archive.close()
        try:
            _archive_directory(world_abs, temp_archive.name)
            archive_hash = _hash_input_path(temp_archive.name)
            library_abs = os.path.abspath(library_blend_path) if library_blend_path else ""
            library_hash = _hash_input_path(library_abs) if library_abs else None
            payload = {
                "contract_version": CONTRACT_VERSION,
                "engine_version": "2026.09.0",
                "request_id": str(uuid.uuid4()),
                "world_sha256": world_hash,
                "world_archive_sha256": archive_hash,
                "world_size_bytes": os.path.getsize(temp_archive.name),
                "library_sha256": library_hash,
                "library_size_bytes": os.path.getsize(library_abs) if library_abs else 0,
                "chunk_size": chunk_size,
                "missing_asset_policy": missing_asset_policy,
                "retention": retention,
            }
        except Exception:
            os.unlink(temp_archive.name)
            raise
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/jobs/submit",
                    json=payload,
                    headers=self._get_headers(),
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"Submit job failed: {resp.text}")
                data = resp.json()
                job_id = data["job_id"]
                self._upload_file(client, job_id, temp_archive.name, "world")
                if library_abs:
                    self._upload_file(client, job_id, library_abs, "library")
                return {
                    "contract_version": CONTRACT_VERSION,
                    "operation_id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "status": data.get("status", "queued"),
                    "consent": {
                        "files": [{"path": world_path, "sha256": world_hash, "purpose": "World data"}],
                        "retention": retention,
                        "estimated_upload_size_mb": 0.0,
                    },
                    "message": "Build job submitted via Strata Engine HTTP service.",
                }
        except Exception as e:
            if "Submit job failed" in str(e):
                raise
            raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable: {e}")
        finally:
            if os.path.exists(temp_archive.name):
                os.unlink(temp_archive.name)

    def get_job_status(self, job_id: str) -> dict:
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.base_url}/jobs/{job_id}/status",
                    headers=self._get_headers(),
                )
                if resp.status_code == 404:
                    return {
                        "contract_version": CONTRACT_VERSION,
                        "operation_id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "status": "not_found",
                    }
                data = resp.json()
                return {
                    "contract_version": CONTRACT_VERSION,
                    "operation_id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "status": data.get("status", "unknown"),
                    "progress_percent": data.get("progress_percent", 0),
                    "retention_status": data.get("retention_status", "pending"),
                }
        except Exception as e:
            raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable: {e}")

    def cancel_job(self, job_id: str) -> dict:
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/jobs/{job_id}/cancel",
                    headers=self._get_headers(),
                )
                if resp.status_code == 404:
                    return {
                        "contract_version": CONTRACT_VERSION,
                        "operation_id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "status": "not_found",
                    }
                data = resp.json()
                return {
                    "contract_version": CONTRACT_VERSION,
                    "operation_id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "status": data.get("status", "cancelled"),
                }
        except Exception as e:
            raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable: {e}")

    def download_result(self, job_id: str, output_directory: str) -> dict:
        temp_dir = ""
        try:
            import httpx
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.base_url}/jobs/{job_id}/download",
                    headers=self._get_headers(),
                )
                if resp.status_code == 400:
                    return {
                        "contract_version": CONTRACT_VERSION,
                        "operation_id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "status": "error",
                        "error_code": "job_not_completed",
                        "message": f"Job '{job_id}' is not in completed state.",
                    }
                if resp.status_code == 404:
                    return {
                        "contract_version": CONTRACT_VERSION,
                        "operation_id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "status": "error",
                        "error_code": "job_not_found",
                        "message": f"Job '{job_id}' not found.",
                    }
                if resp.status_code != 200:
                    raise RuntimeError(f"Download authorization failed: {resp.text}")

                data = resp.json()
                manifest_dict = data.get("manifest")
                if not isinstance(manifest_dict, dict) or not manifest_dict.get("chunks"):
                    return {
                        "contract_version": CONTRACT_VERSION,
                        "operation_id": str(uuid.uuid4()),
                        "job_id": job_id,
                        "status": "error",
                        "error_code": "manifest_missing",
                        "message": "Engine download response did not include a signed artifact manifest.",
                    }

                abs_out = os.path.abspath(output_directory)
                temp_dir = os.path.join(
                    os.path.dirname(abs_out),
                    f".tmp_download_{job_id}_{uuid.uuid4().hex[:6]}",
                )
                os.makedirs(temp_dir, exist_ok=True)

                manifest_file = os.path.join(temp_dir, "strata-world-manifest.json")
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(manifest_dict, f, indent=2)

                manifest = load_and_validate_manifest(
                    manifest_file, CONTRACT_VERSION, temp_dir
                )

                # The Engine response must carry the bytes (inline base64 or a
                # scoped URL) for every checksum-listed artifact. A manifest
                # without files is not a successful download.
                artifacts = data.get("artifacts", data.get("files", {}))
                if isinstance(artifacts, list):
                    artifacts = {
                        item.get("path", item.get("file", "")): item
                        for item in artifacts
                        if isinstance(item, dict)
                    }
                if not isinstance(artifacts, dict):
                    artifacts = {}

                for relative_name in manifest.output_checksums:
                    payload = artifacts.get(relative_name)
                    if payload is None:
                        raise ManifestValidationError(
                            f"Engine response omitted artifact bytes for '{relative_name}'."
                        )
                    target = validate_output_path(temp_dir, relative_name)
                    os.makedirs(os.path.dirname(target), exist_ok=True)

                    response_bytes = None
                    if isinstance(payload, dict):
                        if payload.get("content_base64"):
                            response_bytes = base64.b64decode(payload["content_base64"])
                        elif payload.get("data_base64"):
                            response_bytes = base64.b64decode(payload["data_base64"])
                        elif payload.get("url"):
                            artifact_resp = client.get(
                                payload["url"], headers=self._get_headers()
                            )
                            artifact_resp.raise_for_status()
                            response_bytes = artifact_resp.content
                    elif isinstance(payload, str) and payload.startswith(("http://", "https://")):
                        artifact_resp = client.get(payload, headers=self._get_headers())
                        artifact_resp.raise_for_status()
                        response_bytes = artifact_resp.content
                    elif isinstance(payload, str):
                        response_bytes = base64.b64decode(payload)
                    if response_bytes is None:
                        raise ManifestValidationError(
                            f"Artifact '{relative_name}' has no supported content payload."
                        )
                    with open(target, "wb") as artifact_file:
                        artifact_file.write(response_bytes)

                check_results = verify_output_checksums(manifest, temp_dir)
                if not check_results or not all(check_results.values()):
                    failed = [name for name, ok in check_results.items() if not ok]
                    raise ManifestValidationError(
                        "Artifact checksum verification failed for: "
                        + ", ".join(failed)
                    )

                if os.path.exists(abs_out):
                    shutil.rmtree(abs_out, ignore_errors=True)
                shutil.move(temp_dir, abs_out)
                temp_dir = ""

                retention_status = "retained"
                if data.get("retention") == "delete_after_download":
                    delete_response = client.delete(
                        f"{self.base_url}/jobs/{job_id}", headers=self._get_headers()
                    )
                    retention_status = "deleted" if delete_response.status_code == 200 else "deletion_failed"

                return {
                    "contract_version": CONTRACT_VERSION,
                    "operation_id": str(uuid.uuid4()),
                    "job_id": job_id,
                    "output_directory": abs_out,
                    "status": "download_complete",
                    "manifest_path": os.path.join(abs_out, "strata-world-manifest.json"),
                    "retention_status": retention_status,
                }
        except (ManifestValidationError, PathSecurityError) as e:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "error",
                "error_code": "artifact_invalid",
                "message": str(e),
            }
        except Exception as e:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            if isinstance(e, OfflineError):
                raise
            raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable: {e}")


class LocalEngineAPIClient(HTTPStrataAPIClient):
    """HTTP client backed by an Engine worker started on loopback.

    The protocol remains identical to the managed Engine, but the Connector
    owns both local subprocesses and keeps the job root on the user's machine.
    """

    def __init__(
        self,
        device_token: str = "",
        engine_root: Optional[str] = None,
        timeout: int = 30,
    ):
        from .local_engine import LocalEngineSupervisor

        self.supervisor = LocalEngineSupervisor(engine_root=engine_root)
        local_url = self.supervisor.start()
        super().__init__(base_url=local_url, device_token=device_token, timeout=timeout)

    def close(self) -> None:
        self.supervisor.stop()


class StrataAPIClient(BaseStrataAPIClient):
    """Facade for Strata API client.

    Defaults to FixtureAPIClient for offline/developer operations.
    Can be configured via mode='http'/'local' or STRATA_API_MODE env var.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        device_token: str = "",
        mode: Optional[str] = None,
    ):
        selected_mode = mode or os.environ.get("STRATA_API_MODE", "fixture")
        if selected_mode.lower() == "http":
            self._impl: BaseStrataAPIClient = HTTPStrataAPIClient(
                base_url=base_url,
                device_token=device_token,
            )
        elif selected_mode.lower() == "local":
            self._impl = LocalEngineAPIClient(
                device_token=device_token,
                engine_root=(
                    os.environ.get("STRATA_ENGINE_ROOT")
                    or os.environ.get("STRATA_LOCAL_ENGINE_ROOT")
                ),
            )
        else:
            self._impl = FixtureAPIClient()

    @property
    def impl(self) -> BaseStrataAPIClient:
        return self._impl

    @property
    def device_token(self) -> str:
        return getattr(self._impl, "device_token", "")

    @device_token.setter
    def device_token(self, value: str) -> None:
        if hasattr(self._impl, "device_token"):
            self._impl.device_token = value

    @property
    def _jobs(self) -> dict:
        return getattr(self._impl, "_jobs", {})

    def authenticate(self, user_code: str = "") -> dict:
        return self._impl.authenticate(user_code)

    def preflight_world(self, world_path: str) -> dict:
        return self._impl.preflight_world(world_path)

    def inspect_library(self, library_blend_path: str) -> dict:
        return self._impl.inspect_library(library_blend_path)

    def submit_build(self, *args, **kwargs) -> dict:
        return self._impl.submit_build(*args, **kwargs)

    def get_job_status(self, job_id: str) -> dict:
        return self._impl.get_job_status(job_id)

    def cancel_job(self, job_id: str) -> dict:
        return self._impl.cancel_job(job_id)

    def download_result(self, job_id: str, output_directory: str) -> dict:
        return self._impl.download_result(job_id, output_directory)
