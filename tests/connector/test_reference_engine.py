"""Tests for Connector-to-Reference-Engine compatibility.

Tests all scenarios: success, invalid contract version, bad checksum,
failed job, cancelled job, malformed diagnostics.
"""
import pytest
from contracts.schemas import BuildRequest, SourceDescriptor, CONTRACT_VERSION
from contracts.enums import AssetKind, JobStatus
from reference_engine.server import ReferenceEngine


VALID_SHA256 = "a" * 64


@pytest.fixture
def engine():
    return ReferenceEngine()


@pytest.fixture
def valid_request():
    return BuildRequest(
        request_id="test-ref-001",
        engine_version="2026.09.0",
        world_input=SourceDescriptor(kind=AssetKind.ARCHIVE, sha256=VALID_SHA256),
    )


def test_success_scenario(engine, valid_request):
    result = engine.submit(valid_request, scenario="success")
    assert result.status == JobStatus.COMPLETED
    assert result.progress_percent == 100
    assert result.manifest is not None
    assert result.diagnostics is not None
    assert result.manifest.contract_version == CONTRACT_VERSION
    assert len(result.manifest.chunks) > 0
    assert result.diagnostics.chunk_count > 0


def test_preflight(engine):
    result = engine.preflight("synthetic/world")
    assert result["status"] == "preflight_complete"
    assert result["contract_version"] == CONTRACT_VERSION
    assert result["estimated_chunks"] == 4


def test_consent_generation(engine, valid_request):
    consent = engine.generate_consent(valid_request)
    assert consent.request_id == valid_request.request_id
    assert consent.user_approved is False
    assert len(consent.files) > 0


def test_invalid_contract_version(engine, valid_request):
    with pytest.raises(ValueError, match="Unsupported"):
        engine.submit(valid_request, scenario="invalid_contract_version")


def test_failed_job(engine, valid_request):
    result = engine.submit(valid_request, scenario="failed")
    assert result.status == JobStatus.FAILED
    assert result.diagnostics is not None
    assert len(result.diagnostics.failure_reasons) > 0


def test_cancelled_job(engine, valid_request):
    result = engine.submit(valid_request, scenario="cancelled")
    assert result.status == JobStatus.CANCELLED


def test_bad_checksum(engine, valid_request):
    result = engine.submit(valid_request, scenario="bad_checksum")
    assert result.status == JobStatus.COMPLETED
    assert result.manifest is not None
    # All checksums should be zeros (intentionally wrong)
    for checksum in result.manifest.output_checksums.values():
        assert checksum == "0" * 64


def test_malformed_diagnostics(engine, valid_request):
    result = engine.submit(valid_request, scenario="malformed_diagnostics")
    assert result.status == JobStatus.COMPLETED
    assert result.diagnostics is not None
    assert result.diagnostics.chunk_count == -1
    assert result.diagnostics.total_blocks == -999


def test_write_synthetic_output(engine, tmp_path):
    output_dir = str(tmp_path / "output")
    manifest_path = engine.write_output(output_dir, request_id="write-test")
    assert manifest_path.endswith("strata-world-manifest.json")
    assert (tmp_path / "output" / "strata-world-manifest.json").exists()
    assert (tmp_path / "output" / "chunks").is_dir()


def test_error_generation(engine):
    from contracts.enums import ErrorCode
    err = engine.make_error(ErrorCode.AUTH_FAILED, "Token expired")
    assert err.error_code == ErrorCode.AUTH_FAILED
    assert "expired" in err.message
