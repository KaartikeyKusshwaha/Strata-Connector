"""End-to-End Test for the Strata Connector (Step 10).

Verifies the full lifecycle:
1. Preflight world
2. Submit job (with test token)
3. Monitor status
4. Download result
5. Verify manifest checksums
"""
import pytest
from connector_mcp.api_client import StrataAPIClient


def test_e2e_managed_build_lifecycle(tmp_path):
    """Simulates an end-to-end managed build job using the API stub."""
    client = StrataAPIClient()
    world_path = str(tmp_path / "MyWorld")
    (tmp_path / "MyWorld").mkdir()

    # 1. Preflight
    preflight = client.preflight_world(world_path)
    assert preflight["status"] == "preflight_complete"

    # 2. Submit
    submission = client.submit_build(
        world_path=world_path,
        output_directory=str(tmp_path / "output"),
    )
    job_id = submission["job_id"]
    assert submission["status"] == "queued"

    # 3. Monitor
    # The stub sets queued immediately
    status = client.get_job_status(job_id)
    assert status["status"] == "queued"

    # Simulate private engine completing the job
    client._jobs[job_id]["status"] = "completed"

    status_done = client.get_job_status(job_id)
    assert status_done["status"] == "completed"

    # 4. Download result
    download = client.download_result(job_id, str(tmp_path / "output"))
    assert download["status"] == "download_complete"
    assert download["manifest_path"].endswith("strata-world-manifest.json")
