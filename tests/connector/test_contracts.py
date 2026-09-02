"""Unit tests for Strata data contracts (Step 2).

Verifies schema validation, contract version enforcement, and rejection of
invalid payloads.
"""
import pytest
from contracts.schemas import (
    CONTRACT_VERSION,
    JobDiagnostics,
    JobRequest,
    JobResult,
    ManifestChunkEntry,
    SignedManifest,
    SourceDescriptor,
    UploadConsentSummary,
)
from contracts.enums import (
    AssetKind,
    JobStatus,
    MissingAssetPolicy,
    OutputMode,
    RetentionPolicy,
)


VALID_SHA256 = "a" * 64


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
# JobRequest
# ---------------------------------------------------------------------------

def test_job_request_valid():
    req = JobRequest(
        engine_version="2026.09.0",
        world_source=SourceDescriptor(kind=AssetKind.NONE, sha256=VALID_SHA256),
    )
    assert req.contract_version == CONTRACT_VERSION
    assert req.chunk_size == 16
    assert req.missing_asset_policy == MissingAssetPolicy.GENERATE
    assert req.output_mode == OutputMode.STREAMED_A1_3D
    assert req.retention == RetentionPolicy.DELETE_AFTER_DOWNLOAD


def test_job_request_rejects_unknown_contract_version():
    with pytest.raises(Exception):
        JobRequest(
            contract_version="999",
            engine_version="2026.09.0",
            world_source=SourceDescriptor(kind=AssetKind.NONE, sha256=VALID_SHA256),
        )


def test_job_request_rejects_missing_engine_version():
    with pytest.raises(Exception):
        JobRequest(
            world_source=SourceDescriptor(kind=AssetKind.NONE, sha256=VALID_SHA256),
        )


def test_job_request_with_texture_sources():
    req = JobRequest(
        engine_version="2026.09.0",
        world_source=SourceDescriptor(kind=AssetKind.NONE, sha256=VALID_SHA256),
        texture_sources=[
            SourceDescriptor(kind=AssetKind.USER_PACK, sha256=VALID_SHA256),
            SourceDescriptor(kind=AssetKind.MINECRAFT_JAR, sha256=VALID_SHA256),
        ],
    )
    assert len(req.texture_sources) == 2


# ---------------------------------------------------------------------------
# SignedManifest
# ---------------------------------------------------------------------------

def test_signed_manifest_valid():
    manifest = SignedManifest(
        engine_version="2026.09.0",
        chunks={
            "0:0:0": ManifestChunkEntry(
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
# JobResult
# ---------------------------------------------------------------------------

def test_job_result_valid():
    result = JobResult(
        job_id="job-001",
        status=JobStatus.COMPLETED,
        diagnostics=JobDiagnostics(chunk_count=4, total_blocks=100),
    )
    assert result.status == JobStatus.COMPLETED
    assert result.diagnostics.chunk_count == 4


def test_job_result_failed():
    result = JobResult(
        job_id="job-002",
        status=JobStatus.FAILED,
        diagnostics=JobDiagnostics(failure_reasons=["Missing world data"]),
    )
    assert result.status == JobStatus.FAILED
    assert len(result.diagnostics.failure_reasons) == 1


# ---------------------------------------------------------------------------
# UploadConsentSummary
# ---------------------------------------------------------------------------

def test_upload_consent_summary():
    summary = UploadConsentSummary(
        world_path="C:/saves/MyWorld",
        world_sha256=VALID_SHA256,
        retention_policy=RetentionPolicy.DELETE_AFTER_DOWNLOAD,
        estimated_upload_size_mb=45.2,
    )
    assert summary.retention_policy == RetentionPolicy.DELETE_AFTER_DOWNLOAD


# ---------------------------------------------------------------------------
# Enum coverage
# ---------------------------------------------------------------------------

def test_all_enums_have_values():
    assert len(AssetKind) == 5
    assert len(MissingAssetPolicy) == 2
    assert len(OutputMode) == 1
    assert len(RetentionPolicy) == 2
    assert len(JobStatus) == 8
