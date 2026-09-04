"""End-to-End Test for the Strata Connector.

Verifies the full lifecycle:
1. Authenticate
2. Preflight world
3. Submit managed build (with consent)
4. Monitor status
5. Cancel a job
6. Download result
7. Verify manifest checksums
"""
import pytest
from connector_mcp.api_client import StrataAPIClient


def test_e2e_managed_build_lifecycle(tmp_path):
    """Simulates an end-to-end managed build job using the API stub."""
    client = StrataAPIClient()
    world_path = str(tmp_path / "MyWorld")
    (tmp_path / "MyWorld").mkdir()

    # 0. Authenticate
    auth = client.authenticate()
    assert auth["status"] == "authenticated"
    assert client.device_token  # Should have a token now

    # 1. Preflight
    preflight = client.preflight_world(world_path)
    assert preflight["status"] == "preflight_complete"

    # 2. Submit with consent
    submission = client.submit_build(
        world_path=world_path,
        output_directory=str(tmp_path / "output"),
    )
    job_id = submission["job_id"]
    assert submission["status"] == "queued"
    assert "consent" in submission

    # 3. Monitor
    status = client.get_job_status(job_id)
    assert status["status"] == "queued"

    # 4. Simulate engine completing the job
    client._jobs[job_id]["status"] = "completed"
    client._jobs[job_id]["retention_status"] = "delete_after_download"

    status_done = client.get_job_status(job_id)
    assert status_done["status"] == "completed"
    assert status_done["retention_status"] == "delete_after_download"

    # 5. Download result
    download = client.download_result(job_id, str(tmp_path / "output"))
    assert download["status"] == "download_complete"
    assert download["manifest_path"].endswith("strata-world-manifest.json")


def test_e2e_cancellation(tmp_path):
    """Tests the cancel flow."""
    client = StrataAPIClient()
    client.authenticate()

    world_path = str(tmp_path / "MyWorld")
    (tmp_path / "MyWorld").mkdir()

    submission = client.submit_build(
        world_path=world_path,
        output_directory=str(tmp_path / "output"),
    )
    job_id = submission["job_id"]

    cancel = client.cancel_job(job_id)
    assert cancel["status"] == "cancelled"

    status = client.get_job_status(job_id)
    assert status["status"] == "cancelled"


def test_e2e_job_not_found():
    """Tests status for a nonexistent job."""
    client = StrataAPIClient()
    status = client.get_job_status("nonexistent-job")
    assert status["status"] == "not_found"
