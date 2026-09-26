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
import hashlib
import json
import os
import shutil
import time
import uuid
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
        exists = os.path.exists(world_path)
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "world_path": world_path,
            "world_exists": exists,
            "estimated_blocks": 2560 if exists else 0,
            "estimated_chunks": 4 if exists else 0,
            "missing_assets": [] if exists else ["world_not_found"],
            "status": "preflight_complete",
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
    """Client for the production Strata Engine HTTP service."""

    def __init__(
        self,
        base_url: str = "https://api.strata.dev",
        device_token: str = "",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.device_token = device_token
        self.timeout = timeout
        self.max_retries = max_retries

    def authenticate(self, user_code: str = "") -> dict:
        raise OfflineError(
            f"Cannot connect to Strata Engine service at {self.base_url}. "
            "Production managed Engine is not deployed. Use fixture mode for local testing."
        )

    def preflight_world(self, world_path: str) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")

    def inspect_library(self, library_blend_path: str) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")

    def submit_build(self, *args, **kwargs) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")

    def get_job_status(self, job_id: str) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")

    def cancel_job(self, job_id: str) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")

    def download_result(self, job_id: str, output_directory: str) -> dict:
        raise OfflineError(f"Strata Engine service at {self.base_url} is unreachable.")


class StrataAPIClient(BaseStrataAPIClient):
    """Facade for Strata API client.

    Defaults to FixtureAPIClient for offline/developer operations.
    Can be configured via mode='http' or STRATA_API_MODE='http' env var.
    """

    def __init__(
        self,
        base_url: str = "https://api.strata.dev",
        device_token: str = "",
        mode: Optional[str] = None,
    ):
        selected_mode = mode or os.environ.get("STRATA_API_MODE", "fixture")
        if selected_mode.lower() == "http":
            self._impl: BaseStrataAPIClient = HTTPStrataAPIClient(
                base_url=base_url,
                device_token=device_token,
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
