"""HTTP client stub for the Private Strata API.

Currently returns fixture responses for local development and testing.
Will be replaced with real HTTP calls when the private API is deployed.

Supports:
- Device/user authentication with short-lived scoped credentials
- Resumable upload/download (stubs)
- Status polling, retry behavior, cancellation
- Retention/deletion state tracking
- Clear offline error handling
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Optional

from contracts.schemas import CONTRACT_VERSION


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class OfflineError(Exception):
    """Raised when the Engine API is unreachable."""
    pass


class StrataAPIClient:
    """Client for the private Strata API.

    Uses short-lived, scoped credentials for authentication.
    Never distributes a reusable API key in the Connector.
    """

    def __init__(
        self,
        base_url: str = "https://api.strata.dev",
        device_token: str = "",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.device_token = device_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._jobs: dict = {}
        self._upload_progress: dict = {}

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
        """Authenticates with short-lived, scoped device credentials.

        In production, this would implement OAuth device flow or similar.
        Currently returns a fixture token.
        """
        self.device_token = f"dev-{uuid.uuid4().hex[:16]}"
        return {
            "contract_version": CONTRACT_VERSION,
            "status": "authenticated",
            "token_expires_in": 3600,
            "scopes": ["build:submit", "build:status", "build:download"],
        }

    def preflight_world(self, world_path: str) -> dict:
        """Returns preflight build estimates."""
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "world_path": world_path,
            "world_exists": os.path.exists(world_path),
            "estimated_blocks": 0,
            "estimated_chunks": 0,
            "missing_assets": [],
            "status": "preflight_complete",
        }

    def inspect_library(self, library_blend_path: str) -> dict:
        """Returns library inspection results."""
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "library_path": library_blend_path,
            "library_exists": os.path.exists(library_blend_path),
            "object_names": [],
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
        """Submits a managed build job with consent summary."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = {
            "status": "queued",
            "world_path": world_path,
            "output_directory": output_directory,
            "retention": retention,
            "retention_status": "pending",
            "created_at": time.time(),
            "progress_percent": 0,
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
        """Returns job status with retention tracking."""
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
            "progress_percent": 100 if job["status"] == "completed" else job.get("progress_percent", 0),
            "retention_status": job.get("retention_status", "pending"),
        }

    def cancel_job(self, job_id: str) -> dict:
        """Cancels a running build job."""
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
        """Downloads build result with retry support."""
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "output_directory": output_directory,
            "status": "download_complete",
            "manifest_path": os.path.join(output_directory, "strata-world-manifest.json"),
        }
