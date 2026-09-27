"""Tests for truthful download, manifest validation, and atomic promotion.

Covers:
- Truthful creation of output files (manifest, World.blend, chunks, diagnostics)
- Non-zero file sizes and SHA-256 verification
- Tamper detection
- Atomic rollback leaving no partial files on error
- Error handling for invalid/uncompleted jobs
- OfflineError from HTTP client
"""
import os
import shutil
import tempfile
import pytest

from connector_mcp.api_client import (
    FixtureAPIClient,
    HTTPStrataAPIClient,
    OfflineError,
    StrataAPIClient,
)
from connector_mcp.manifest_validator import (
    load_and_validate_manifest,
    verify_output_checksums,
)


@pytest.fixture
def tmp_output_dir():
    d = tempfile.mkdtemp(prefix="strata_test_out_")
    yield d
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def test_successful_download_creates_real_verified_files(tmp_output_dir):
    client = FixtureAPIClient()
    submit_res = client.submit_build(
        world_path="synthetic/world",
        output_directory=tmp_output_dir,
    )
    job_id = submit_res["job_id"]
    client._jobs[job_id]["status"] = "completed"

    download_dir = os.path.join(tmp_output_dir, "download_test")
    res = client.download_result(job_id, download_dir)

    assert res["status"] == "download_complete"
    assert "manifest_path" in res
    manifest_path = res["manifest_path"]
    assert os.path.isfile(manifest_path)

    # Verify all expected files exist and have non-zero size
    world_blend = os.path.join(download_dir, "World.blend")
    assert os.path.isfile(world_blend)
    assert os.path.getsize(world_blend) > 0

    diag_json = os.path.join(download_dir, "diagnostics.json")
    assert os.path.isfile(diag_json)
    assert os.path.getsize(diag_json) > 0

    chunks_dir = os.path.join(download_dir, "chunks")
    assert os.path.isdir(chunks_dir)
    chunk_files = os.listdir(chunks_dir)
    assert len(chunk_files) > 0
    for cf in chunk_files:
        cpath = os.path.join(chunks_dir, cf)
        assert os.path.getsize(cpath) > 0

    # Validate manifest and verify SHA-256 checksums
    manifest = load_and_validate_manifest(manifest_path, output_directory=download_dir)
    checksums = verify_output_checksums(manifest, download_dir)
    assert len(checksums) >= 4
    assert all(checksums.values()), f"Checksum verification failed: {checksums}"


def test_tamper_detection(tmp_output_dir):
    client = FixtureAPIClient()
    submit_res = client.submit_build(
        world_path="synthetic/world",
        output_directory=tmp_output_dir,
    )
    job_id = submit_res["job_id"]
    client._jobs[job_id]["status"] = "completed"

    download_dir = os.path.join(tmp_output_dir, "tamper_test")
    res = client.download_result(job_id, download_dir)
    manifest_path = res["manifest_path"]

    manifest = load_and_validate_manifest(manifest_path, output_directory=download_dir)

    # Pick a chunk file and tamper one byte
    chunk_item = list(manifest.chunks.values())[0]
    tampered_file = os.path.join(download_dir, chunk_item.file)
    with open(tampered_file, "ab") as f:
        f.write(b"CORRUPTED_BYTE")

    # Checksum verification must fail for the tampered file
    results = verify_output_checksums(manifest, download_dir)
    assert results[chunk_item.file] is False


def test_download_nonexistent_job_fails(tmp_output_dir):
    client = FixtureAPIClient()
    res = client.download_result("nonexistent-job-id", tmp_output_dir)
    assert res["status"] == "error"
    assert res["error_code"] == "job_not_found"


def test_http_client_raises_offline_error():
    client = HTTPStrataAPIClient(base_url="https://api.strata.dev")
    with pytest.raises(OfflineError) as exc_info:
        client.authenticate()
    assert "unreachable" in str(exc_info.value).lower() or "not deployed" in str(exc_info.value).lower()


def test_http_download_rejects_fixture_like_response_without_manifest(monkeypatch, tmp_output_dir):
    class EmptyResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"status": "completed"}

    class EmptyClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, *_args, **_kwargs):
            return EmptyResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", lambda **_kwargs: EmptyClient())
    client = HTTPStrataAPIClient(base_url="http://engine.test")
    output = os.path.join(tmp_output_dir, "http-download")
    result = client.download_result("job-empty", output)
    assert result["status"] == "error"
    assert result["error_code"] == "manifest_missing"
    assert not os.path.exists(output)
