"""Live integration tests for HTTPStrataAPIClient against running Engine API."""
import os
import pytest
from connector_mcp.api_client import HTTPStrataAPIClient, OfflineError, StrataAPIClient


def test_strata_api_client_honors_endpoint_environment(monkeypatch):
    monkeypatch.setenv("STRATA_API_MODE", "http")
    monkeypatch.setenv("STRATA_API_URL", "http://127.0.0.1:8080")
    client = StrataAPIClient()
    assert isinstance(client.impl, HTTPStrataAPIClient)
    assert client.impl.base_url == "http://127.0.0.1:8080"


def test_http_client_unreachable_endpoint():
    client = HTTPStrataAPIClient(base_url="http://127.0.0.1:59999", timeout=1)
    with pytest.raises(OfflineError) as exc_info:
        client.authenticate("dummy-device")
    assert "unreachable" in str(exc_info.value).lower() or "cannot connect" in str(exc_info.value).lower()


def test_http_client_live_engine_flow():
    base_url = "http://127.0.0.1:8080"
    client = HTTPStrataAPIClient(base_url=base_url, timeout=5)

    # Check if server is running
    try:
        health = client.health()
    except OfflineError:
        pytest.skip("Local Engine API server is not running on port 8080")

    assert health["status"] == "healthy"

    # Authenticate / pair
    auth = client.authenticate(user_code="live-tester-dev")
    assert auth["authenticated"] is True
    assert len(auth["access_token"]) > 0

    # Submit build
    submit_res = client.submit_build(
        world_path="C:/Worlds/SurvivalTest",
        output_directory="C:/Builds/Output",
        missing_asset_policy="generate",
    )
    assert submit_res["status"] == "queued"
    job_id = submit_res["job_id"]

    # Status check
    status = client.get_job_status(job_id)
    assert status["status"] in ("queued", "running", "completed")

    # Cancel
    cancelled = client.cancel_job(job_id)
    assert cancelled["status"] == "cancelled"
