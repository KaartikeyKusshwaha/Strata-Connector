"""Strata Reference Engine — deterministic mock server.

A protocol test fixture that implements only the published contract.
Generates synthetic manifests and artifacts. Not a production engine.

This is NOT the private engine with names changed. It produces only
legal synthetic output from legal synthetic input.
"""
from __future__ import annotations

import uuid
from typing import Optional

from contracts.schemas import (
    CONTRACT_VERSION,
    ArtifactManifest,
    BuildConsent,
    BuildRequest,
    BuildStatus,
    ChunkDescriptor,
    StrataError,
    WorldDiagnostics,
)
from contracts.enums import ErrorCode, JobStatus, RetentionPolicy

from .synthetic import (
    synthetic_chunk_descriptors,
    synthetic_diagnostics,
    synthetic_manifest,
    synthetic_request_id,
    synthetic_world_hash,
    write_synthetic_output,
)


class ReferenceEngine:
    """Deterministic reference engine for protocol development and testing.

    Supports these scenarios:
    - Success: returns a completed build with synthetic manifest
    - Invalid contract version: rejects with StrataError
    - Bad checksum: returns manifest with intentionally wrong checksums
    - Failed job: returns a failed BuildStatus
    - Cancelled job: returns a cancelled BuildStatus
    - Malformed diagnostics: returns diagnostics with unexpected structure
    """

    def __init__(self):
        self._jobs: dict = {}

    def preflight(self, world_path: str) -> dict:
        """Returns a synthetic preflight result."""
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": str(uuid.uuid4()),
            "world_path": world_path,
            "estimated_blocks": 2560,
            "estimated_chunks": 4,
            "missing_assets": ["minecraft:custom_block_999"],
            "status": "preflight_complete",
        }

    def generate_consent(
        self,
        request: BuildRequest,
        world_path: str = "synthetic/world.zip",
    ) -> BuildConsent:
        """Generates a consent summary for the user to approve."""
        return BuildConsent(
            request_id=request.request_id,
            files=[
                {
                    "path": world_path,
                    "sha256": request.world_input.sha256,
                    "purpose": "World data for chunk generation",
                    "size_mb": "12.5",
                },
            ],
            retention=request.retention,
            estimated_upload_size_mb=12.5,
            user_approved=False,
        )

    def submit(
        self,
        request: BuildRequest,
        scenario: str = "success",
    ) -> BuildStatus:
        """Submits a synthetic build and returns the result immediately."""
        job_id = f"ref-{uuid.uuid4().hex[:8]}"

        if scenario == "invalid_contract_version":
            raise ValueError(
                f"Unsupported contract version '{request.contract_version}'"
            )

        if scenario == "failed":
            return BuildStatus(
                job_id=job_id,
                request_id=request.request_id,
                status=JobStatus.FAILED,
                diagnostics=WorldDiagnostics(
                    failure_reasons=["Synthetic failure: world data corrupt"]
                ),
            )

        if scenario == "cancelled":
            return BuildStatus(
                job_id=job_id,
                request_id=request.request_id,
                status=JobStatus.CANCELLED,
            )

        # Success scenario
        manifest_data = synthetic_manifest(
            request_id=request.request_id,
        )
        manifest = ArtifactManifest(**manifest_data)
        diagnostics_data = synthetic_diagnostics()
        diagnostics = WorldDiagnostics(**diagnostics_data)

        if scenario == "bad_checksum":
            manifest.output_checksums = {
                k: "0" * 64 for k in manifest.output_checksums
            }

        if scenario == "malformed_diagnostics":
            diagnostics = WorldDiagnostics(
                chunk_count=-1,
                total_blocks=-999,
                failure_reasons=[""],
            )

        return BuildStatus(
            job_id=job_id,
            request_id=request.request_id,
            status=JobStatus.COMPLETED,
            progress_percent=100,
            manifest=manifest,
            diagnostics=diagnostics,
            retention_status="delete_after_download",
        )

    def write_output(self, output_dir: str, request_id: str = "") -> str:
        """Writes synthetic build output to disk. Returns manifest path."""
        return write_synthetic_output(output_dir, request_id)

    def make_error(
        self,
        code: ErrorCode,
        message: str,
        operation_id: str = "",
    ) -> StrataError:
        """Creates a structured error response."""
        return StrataError(
            operation_id=operation_id or str(uuid.uuid4()),
            error_code=code,
            message=message,
        )
