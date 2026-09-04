"""Strata data contracts — Pydantic v2 schemas for builds, status,
diagnostics, manifests, streaming, consent, and errors.

This module contains ONLY data definitions and validation rules.
No algorithm code, no engine logic, no private module imports.

Schema inventory (§4.1):
  BuildRequest, BuildInputManifest, BuildConsent,
  BuildStatus, WorldDiagnostics, ArtifactManifest,
  ChunkDescriptor, StreamingStatus, StrataError
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .enums import (
    AssetKind,
    ErrorCode,
    JobStatus,
    MissingAssetPolicy,
    OutputMode,
    RetentionPolicy,
)

CONTRACT_VERSION = "1.0"

_SEMVER_MAJOR_RE = re.compile(r"^(\d+)\.")


def _major(version: str) -> int:
    m = _SEMVER_MAJOR_RE.match(version)
    return int(m.group(1)) if m else -1


# ---------------------------------------------------------------------------
# Source / input descriptors
# ---------------------------------------------------------------------------

class SourceDescriptor(BaseModel):
    """Describes an input data source with its kind and content hash."""
    kind: AssetKind
    sha256: str = Field(..., min_length=64, max_length=64)


# ---------------------------------------------------------------------------
# BuildRequest  (connector → engine)
# ---------------------------------------------------------------------------

class BuildRequest(BaseModel):
    """Versioned build request submitted by the Connector to the Engine.

    The Engine must reject unknown contract major versions, missing hashes,
    unsupported input kinds, and archive paths that escape staging.
    """
    contract_version: str = Field(default=CONTRACT_VERSION)
    request_id: str = Field(..., description="Unique request UUID")
    engine_version: str = Field(
        default="", description="Requested engine version, e.g. '2026.09.0'"
    )
    world_input: SourceDescriptor
    library_input: SourceDescriptor = Field(
        default_factory=lambda: SourceDescriptor(kind=AssetKind.NONE, sha256="0" * 64)
    )
    texture_inputs: List[SourceDescriptor] = Field(default_factory=list)
    output: dict = Field(
        default_factory=lambda: {"mode": "streamed_a1_3d", "chunk_size": 16}
    )
    retention: RetentionPolicy = RetentionPolicy.DELETE_AFTER_DOWNLOAD

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, v: str) -> str:
        if _major(v) != _major(CONTRACT_VERSION):
            raise ValueError(
                f"Unsupported contract major version '{v}'. "
                f"Expected major {_major(CONTRACT_VERSION)}."
            )
        return v


# ---------------------------------------------------------------------------
# BuildInputManifest
# ---------------------------------------------------------------------------

class BuildInputManifest(BaseModel):
    """Declares the exact inputs for a build — hashes only, no source paths."""
    contract_version: str = CONTRACT_VERSION
    request_id: str
    world_sha256: str
    library_sha256: Optional[str] = None
    texture_sha256s: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# BuildConsent  (shown to user before upload)
# ---------------------------------------------------------------------------

class BuildConsent(BaseModel):
    """Consent summary presented to the user before submitting a managed build.
    Lists every file that will be uploaded, its hash, intended use, and
    retention policy."""
    contract_version: str = CONTRACT_VERSION
    request_id: str
    files: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of {path, sha256, purpose, size_mb} dicts"
    )
    retention: RetentionPolicy = RetentionPolicy.DELETE_AFTER_DOWNLOAD
    estimated_upload_size_mb: float = 0.0
    user_approved: bool = False


# ---------------------------------------------------------------------------
# ChunkDescriptor
# ---------------------------------------------------------------------------

class ChunkDescriptor(BaseModel):
    """One chunk's metadata inside a signed manifest."""
    name: str
    file: str
    block_count: int = 0
    static_object_count: int = 0
    rig_root_count: int = 0
    bounds_minecraft: List[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ArtifactManifest  (engine → connector, signed)
# ---------------------------------------------------------------------------

class ArtifactManifest(BaseModel):
    """Signed manifest produced by the Engine and validated by the Connector.

    The Connector must reject mismatched contract major versions, invalid
    signatures, checksum mismatches, and output paths that escape the
    result directory.
    """
    schema_version: int = 1
    contract_version: str = CONTRACT_VERSION
    engine_version: str
    request_id: str = ""
    input_hashes: Dict[str, str] = Field(default_factory=dict)
    chunk_size: int = 16
    coordinate_mapping: str = "minecraft_xyz_to_blender_xzy"
    prototype_library: str = "Strata_PrototypeLibrary.blend"
    missing_asset_policy: str = "generate"
    chunks: Dict[str, ChunkDescriptor] = Field(default_factory=dict)
    output_checksums: Dict[str, str] = Field(default_factory=dict)
    signature: Optional[str] = None


# ---------------------------------------------------------------------------
# WorldDiagnostics
# ---------------------------------------------------------------------------

class WorldDiagnostics(BaseModel):
    """Structured diagnostics returned with every build result."""
    unmapped_ids: List[str] = Field(default_factory=list)
    ignored_non_block_assets: List[str] = Field(default_factory=list)
    generated_fallback_assets: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    total_blocks: int = 0
    visible_blocks: int = 0
    warnings: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# BuildStatus  (engine → connector)
# ---------------------------------------------------------------------------

class BuildStatus(BaseModel):
    """Versioned build status returned by the Engine to the Connector."""
    contract_version: str = CONTRACT_VERSION
    job_id: str
    request_id: str = ""
    status: JobStatus
    progress_percent: int = 0
    manifest: Optional[ArtifactManifest] = None
    diagnostics: Optional[WorldDiagnostics] = None
    output_archive_url: Optional[str] = None
    output_archive_sha256: Optional[str] = None
    retention_status: Optional[str] = None


# ---------------------------------------------------------------------------
# StreamingStatus  (blender bridge → connector)
# ---------------------------------------------------------------------------

class StreamingStatus(BaseModel):
    """Current chunk streaming state from the Blender session."""
    contract_version: str = CONTRACT_VERSION
    operation_id: str = ""
    loaded_chunks: List[str] = Field(default_factory=list)
    pinned_chunks: List[str] = Field(default_factory=list)
    working_set_center: List[int] = Field(default_factory=lambda: [0, 0, 0])
    total_object_count: int = 0
    visible_object_count: int = 0


# ---------------------------------------------------------------------------
# StrataError
# ---------------------------------------------------------------------------

class StrataError(BaseModel):
    """Structured error response. Safe for agent consumption — never
    contains tokens, server paths, stack traces, or user data."""
    contract_version: str = CONTRACT_VERSION
    operation_id: str = ""
    error_code: ErrorCode = ErrorCode.UNKNOWN
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Legacy aliases for backward compatibility
# ---------------------------------------------------------------------------
JobRequest = BuildRequest
JobResult = BuildStatus
JobDiagnostics = WorldDiagnostics
SignedManifest = ArtifactManifest
ManifestChunkEntry = ChunkDescriptor
UploadConsentSummary = BuildConsent
