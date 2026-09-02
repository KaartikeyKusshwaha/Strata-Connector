"""HTTP client stub for the Private Strata API.

Currently returns fixture responses for local development and testing.
Will be replaced with real HTTP calls when the private API is deployed.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from typing import Optional


class StrataAPIClient:
    """Stub client for the private Strata API."""

    def __init__(self, base_url: str = "https://api.strata.dev", auth_token: str = ""):
        self.base_url = base_url
        self.auth_token = auth_token
        self._jobs: dict = {}

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

    def preflight_world(self, world_path: str) -> dict:
        """Returns preflight build estimates (fixture response)."""
        return {
            "contract_version": "1",
            "operation_id": str(uuid.uuid4()),
            "world_path": world_path,
            "world_exists": os.path.exists(world_path),
            "estimated_blocks": 0,
            "estimated_chunks": 0,
            "missing_assets": [],
            "status": "preflight_complete",
        }

    def inspect_library(self, library_blend_path: str) -> dict:
        """Returns library inspection results (fixture response)."""
        return {
            "contract_version": "1",
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
        """Submits a managed build job (fixture response)."""
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = {
            "status": "queued",
            "world_path": world_path,
            "output_directory": output_directory,
        }
        return {
            "contract_version": "1",
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "status": "queued",
            "upload_summary": {
                "world_path": world_path,
                "world_sha256": self._hash_file(world_path),
                "library_path": library_blend_path or None,
                "retention": retention,
            },
            "message": "Build job submitted. Use strata_get_job_status to track progress.",
        }

    def get_job_status(self, job_id: str) -> dict:
        """Returns job status (fixture response)."""
        job = self._jobs.get(job_id)
        if not job:
            return {
                "contract_version": "1",
                "operation_id": str(uuid.uuid4()),
                "job_id": job_id,
                "status": "not_found",
                "message": f"Job '{job_id}' not found.",
            }
        return {
            "contract_version": "1",
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "status": job["status"],
            "progress_percent": 100 if job["status"] == "completed" else 0,
        }

    def download_result(self, job_id: str, output_directory: str) -> dict:
        """Downloads build result (fixture response)."""
        return {
            "contract_version": "1",
            "operation_id": str(uuid.uuid4()),
            "job_id": job_id,
            "output_directory": output_directory,
            "status": "download_complete",
            "manifest_path": os.path.join(output_directory, "strata-world-manifest.json"),
        }
