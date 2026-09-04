"""Tests for Strata data contracts.

Verifies schema validation, contract version enforcement, semver major
rejection, and validation of all 8 named schema models.
"""
import json
import os
import pytest

from contracts.schemas import (
    CONTRACT_VERSION,
    ArtifactManifest,
    BuildConsent,
    BuildRequest,
    BuildStatus,
    ChunkDescriptor,
    SourceDescriptor,
    StrataError,
    StreamingStatus,
    WorldDiagnostics,
    BuildInputManifest,
)
from contracts.enums import (
    AssetKind,
    ErrorCode,
    JobStatus,
    MissingAssetPolicy,
    OutputMode,
    RetentionPolicy,
)


VALID_SHA256 = "a" * 64
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts", "fixtures")


# ---------------------------------------------------------------------------
# SourceDescriptor
# ---------------------------------------------------------------------------

def test_source_descriptor_valid():
    sd = SourceDescriptor(kind=AssetKind.BLEND, sha256=VALID_SHA256)
    assert sd.kind == AssetKind.BLEND
    assert len(sd.sha256) == 64


def test_source_descriptor_rejects_short_hash():
    with pytest.raises(Exception):
        SourceDescriptor(kind=AssetKind.BLEND, sha256="tooshort")


# ---------------------------------------------------------------------------
# BuildRequest
# ---------------------------------------------------------------------------

def test_build_request_valid():
    req = BuildRequest(
        request_id="test-001",
        engine_version="2026.09.0",
        world_input=SourceDescriptor(kind=AssetKind.ARCHIVE, sha256=VALID_SHA256),
    )
    assert req.contract_version == CONTRACT_VERSION
    assert req.request_id == "test-001"


def test_build_request_rejects_unknown_major_version():
    with pytest.raises(Exception):
        BuildRequest(
            contract_version="99.0",
            request_id="test-bad",
            world_input=SourceDescriptor(kind=AssetKind.ARCHIVE, sha256=VALID_SHA256),
        )


def test_build_request_accepts_compatible_minor():
    req = BuildRequest(
        contract_version="1.1",
        request_id="test-minor",
        world_input=SourceDescriptor(kind=AssetKind.ARCHIVE, sha256=VALID_SHA256),
    )
    assert req.contract_version == "1.1"


def test_build_request_from_fixture():
    fixture_path = os.path.join(FIXTURES_DIR, "valid_build_request.json")
    if os.path.exists(fixture_path):
        with open(fixture_path) as f:
            data = json.load(f)
        req = BuildRequest(**data)
        assert req.contract_version == "1.0"


# ---------------------------------------------------------------------------
# BuildConsent
# ---------------------------------------------------------------------------

def test_build_consent():
    consent = BuildConsent(
        request_id="test-consent",
        files=[{"path": "world.zip", "sha256": VALID_SHA256, "purpose": "World data", "size_mb": "12.5"}],
        estimated_upload_size_mb=12.5,
    )
    assert len(consent.files) == 1
    assert consent.user_approved is False


# ---------------------------------------------------------------------------
# ArtifactManifest
# ---------------------------------------------------------------------------

def test_artifact_manifest_valid():
    manifest = ArtifactManifest(
        engine_version="2026.09.0",
        chunks={
            "0:0:0": ChunkDescriptor(
                name="Chunk_xp000_yp000_zp000",
                file="chunks/Chunk_xp000_yp000_zp000.blend",
                block_count=256,
                bounds_minecraft=[0, 0, 0, 15, 15, 15],
            )
        },
    )
    assert manifest.schema_version == 1
    assert "0:0:0" in manifest.chunks


# ---------------------------------------------------------------------------
# BuildStatus
# ---------------------------------------------------------------------------

def test_build_status_completed():
    result = BuildStatus(
        job_id="job-001",
        status=JobStatus.COMPLETED,
        diagnostics=WorldDiagnostics(chunk_count=4, total_blocks=100),
    )
    assert result.status == JobStatus.COMPLETED
    assert result.diagnostics.chunk_count == 4


def test_build_status_failed():
    result = BuildStatus(
        job_id="job-002",
        status=JobStatus.FAILED,
        diagnostics=WorldDiagnostics(failure_reasons=["Missing world data"]),
    )
    assert result.status == JobStatus.FAILED
    assert len(result.diagnostics.failure_reasons) == 1


# ---------------------------------------------------------------------------
# WorldDiagnostics
# ---------------------------------------------------------------------------

def test_world_diagnostics_with_warnings():
    diag = WorldDiagnostics(
        chunk_count=4,
        total_blocks=2560,
        visible_blocks=1536,
        warnings=["1 block ID not in known registry"],
    )
    assert len(diag.warnings) == 1


# ---------------------------------------------------------------------------
# StreamingStatus
# ---------------------------------------------------------------------------

def test_streaming_status():
    ss = StreamingStatus(
        loaded_chunks=["Chunk_xp000_yp000_zp000", "Chunk_xp001_yp000_zp000"],
        working_set_center=[0, 0, 0],
        total_object_count=100,
        visible_object_count=50,
    )
    assert len(ss.loaded_chunks) == 2


# ---------------------------------------------------------------------------
# StrataError
# ---------------------------------------------------------------------------

def test_strata_error():
    err = StrataError(
        operation_id="op-001",
        error_code=ErrorCode.PATH_TRAVERSAL,
        message="Path contains directory traversal",
    )
    assert err.error_code == ErrorCode.PATH_TRAVERSAL
    assert err.contract_version == CONTRACT_VERSION


# ---------------------------------------------------------------------------
# BuildInputManifest
# ---------------------------------------------------------------------------

def test_build_input_manifest():
    bim = BuildInputManifest(
        request_id="test-bim",
        world_sha256=VALID_SHA256,
        library_sha256=VALID_SHA256,
        texture_sha256s=[VALID_SHA256],
    )
    assert bim.world_sha256 == VALID_SHA256


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------

def test_all_enums_have_values():
    assert len(AssetKind) == 6
    assert len(MissingAssetPolicy) == 2
    assert len(OutputMode) == 1
    assert len(RetentionPolicy) == 2
    assert len(JobStatus) == 8
    assert len(ErrorCode) >= 10
