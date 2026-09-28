"""Opt-in real-world smoke test for the bundled local Engine mode."""
from __future__ import annotations

import os
import time

import pytest

from connector_mcp.api_client import StrataAPIClient


@pytest.mark.integration
def test_local_engine_real_world_flow(tmp_path):
    if os.environ.get("STRATA_TEST_LOCAL_ENGINE") != "1":
        pytest.skip("Set STRATA_TEST_LOCAL_ENGINE=1 for the local Engine integration test")
    engine_root = os.environ.get("STRATA_ENGINE_ROOT")
    world_path = os.environ.get("STRATA_TEST_WORLD_PATH")
    if not engine_root or not world_path:
        pytest.skip("Set STRATA_ENGINE_ROOT and STRATA_TEST_WORLD_PATH")
    if not os.path.isdir(world_path):
        pytest.skip("STRATA_TEST_WORLD_PATH is not a directory")

    os.environ.setdefault("STRATA_API_MODE", "local")
    os.environ.setdefault("STRATA_LOCAL_ENGINE_DATA", str(tmp_path / "engine-data"))
    client = StrataAPIClient()
    try:
        auth = client.authenticate("local-integration")
        assert auth["authenticated"] is True
        submission = client.submit_build(
            world_path=world_path,
            output_directory=str(tmp_path / "output"),
            missing_asset_policy="generate",
        )
        assert submission["status"] == "queued"
        job_id = submission["job_id"]
        deadline = time.monotonic() + float(os.environ.get("STRATA_LOCAL_TEST_TIMEOUT", "300"))
        status = client.get_job_status(job_id)
        while status["status"] in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(1)
            status = client.get_job_status(job_id)
        assert status["status"] == "completed", status
        result = client.download_result(job_id, str(tmp_path / "download"))
        assert result["status"] == "download_complete"
        assert os.path.isfile(tmp_path / "download" / "World.blend")
        assert os.path.isfile(tmp_path / "download" / "strata-world-manifest.json")
    finally:
        client.impl.close()
