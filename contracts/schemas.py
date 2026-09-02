"""Strata data contracts — Pydantic v2 schemas for job requests, results,
diagnostics, and signed manifests.

This module contains ONLY data definitions and validation rules.
No algorithm code, no engine logic, no import of strata engine modules.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from .enums import (
    AssetKind,
    JobStatus,
    MissingAssetPolicy,
    OutputMode,
    RetentionPolicy,
)

CONTRACT_VERSION = "1"


# ---------------------------------------------------------------------------
# Source descriptors
# ---------------------------------------------------------------------------

class SourceDescriptor(BaseModel):
    """Describes an input data source with its kind and content hash."""
    kind: AssetKind
    sha256: str = Field(..., min_length=64, max_length=64)


# ---------------------------------------------------------------------------
# Job Request (connector → private API)
# ---------------------------------------------------------------------------

class JobRequest(BaseModel):
    """Versioned job request submitted by the connector to the private API.

    The API must reject unknown contract versions, missing hashes,
    unsupported Minecraft versions, unsupported asset kinds, and archive
    paths that escape the staging directory.
    """
    contract_version: str = Field(default=CONTRACT_VERSION)
    engine_version: str = Field(..., description="Requested engine version, e.g. '2026.09.0'")
    world_source: SourceDescriptor
    library_source: SourceDescriptor = Field(
        default_factory=lambda: SourceDescriptor(kind=AssetKind.NONE, sha256="0" * 64)
    )
    texture_sources: List[SourceDescriptor] = Field(default_factory=list)
    chunk_size: int = Field(default=16, ge=1, le=64)
    missing_asset_policy: MissingAssetPolicy = MissingAssetPolicy.GENERATE
    output_mode: OutputMode = OutputMode.STREAMED_A1_3D
    retention: RetentionPolicy = RetentionPolicy.DELETE_AFTER_DOWNLOAD

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, v: str) -> str:
        if v != CONTRACT_VERSION:
            raise ValueError(
                f"Unknown contract version '{v}'. Expected '{CONTRACT_VERSION}'."
            )
        return v


# ---------------------------------------------------------------------------
# Chunk entry in manifest
# ---------------------------------------------------------------------------

class ManifestChunkEntry(BaseModel):
    """One chunk's metadata inside a signed manifest."""
    name: str
    file: str
    block_count: int = 0
    static_object_count: int = 0
    rig_root_count: int = 0
    bounds_minecraft: List[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Signed Manifest (private engine → connector)
# ---------------------------------------------------------------------------

class SignedManifest(BaseModel):
    """Manifest signed by the private engine and validated by the connector.

    The connector must reject mismatched engine/contract versions and
    verify output checksums before opening results in Blender.
    """
    schema_version: int = 1
    contract_version: str = CONTRACT_VERSION
    engine_version: str
    input_hashes: Dict[str, str] = Field(default_factory=dict)
    chunk_size: int = 16
    coordinate_mapping: str = "minecraft_xyz_to_blender_xzy"
    prototype_library: str = "Strata_PrototypeLibrary.blend"
    missing_asset_policy: str = "generate"
    chunks: Dict[str, ManifestChunkEntry] = Field(default_factory=dict)
    output_checksums: Dict[str, str] = Field(default_factory=dict)
    signature: Optional[str] = None


# ---------------------------------------------------------------------------
# Job Diagnostics
# ---------------------------------------------------------------------------

class JobDiagnostics(BaseModel):
    """Structured diagnostics returned with every job result."""
    unmapped_ids: List[str] = Field(default_factory=list)
    ignored_non_block_assets: List[str] = Field(default_factory=list)
    generated_fallback_assets: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    total_blocks: int = 0
    visible_blocks: int = 0
    failure_reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Job Result (private API → connector)
# ---------------------------------------------------------------------------

class JobResult(BaseModel):
    """Versioned job result returned by the private API to the connector."""
    contract_version: str = CONTRACT_VERSION
    job_id: str
    status: JobStatus
    manifest: Optional[SignedManifest] = None
    diagnostics: Optional[JobDiagnostics] = None
    output_archive_url: Optional[str] = None
    output_archive_sha256: Optional[str] = None


# ---------------------------------------------------------------------------
# Upload consent summary (shown to user before submission)
# ---------------------------------------------------------------------------

class UploadConsentSummary(BaseModel):
    """Data-upload summary presented to the user before submission."""
    world_path: str
    world_sha256: str
    library_path: Optional[str] = None
    library_sha256: Optional[str] = None
    texture_packs: List[str] = Field(default_factory=list)
    retention_policy: RetentionPolicy = RetentionPolicy.DELETE_AFTER_DOWNLOAD
    estimated_upload_size_mb: float = 0.0
