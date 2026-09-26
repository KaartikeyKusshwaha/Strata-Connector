"""Tests for the single-source Blender bridge pairing protocol.

Covers:
- Stopped bridge behavior
- Nonce generation solely in Blender BridgeServer
- Approval required before pairing completion
- Constant-time nonce validation and one-time consumption
- Session token handoff to BridgeClient
- Authenticated command dispatch over live socket
- Wrong nonce, repeated/consumed nonce, and expired nonce rejections
- Bridge restart invalidating session tokens
"""
import time
import pytest

from addon.bridge_server import BridgeServer
from connector_mcp.bridge_client import BridgeClient
from connector_mcp.pairing import PairingManager, PairingState

TEST_HOST = "127.0.0.1"
TEST_PORT = 9988  # Dedicated test port to avoid conflict with default 9877


@pytest.fixture
def running_bridge_server():
    """Starts a live BridgeServer on a test port and tears it down after the test."""
    server = BridgeServer(host=TEST_HOST, port=TEST_PORT)
    # Register dummy command handler for authenticated dispatch test
    server.register_handler("test_cmd", lambda **kwargs: {"status": "ok", "echo": kwargs})
    server.start()
    time.sleep(0.05)  # Allow socket to bind and listen
    yield server
    server.stop()
    time.sleep(0.05)


def test_stopped_bridge_behavior():
    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)
    assert pm.state == PairingState.STOPPED

    status = pm.get_status()
    assert status["pairing_state"] == "stopped"
    assert "recovery" in status

    result = pm.complete_pairing("any-nonce")
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "bridge_unavailable"


def test_missing_nonce_rejected():
    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)
    result = pm.complete_pairing("")
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "missing_nonce"


def test_pairing_requires_active_request(running_bridge_server):
    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    result = pm.complete_pairing("unrequested-nonce")
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "no_pairing_request"


def test_pairing_requires_explicit_user_approval(running_bridge_server):
    server = running_bridge_server
    nonce = server.create_pairing_request()
    assert not server._pairing_approved

    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    # Attempt pairing before Blender user clicks "Approve Pairing"
    result = pm.complete_pairing(nonce)
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "approval_required"


def test_pairing_rejects_wrong_nonce(running_bridge_server):
    server = running_bridge_server
    server.create_pairing_request()
    server.approve_pairing()

    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    result = pm.complete_pairing("wrong-nonce-1234")
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "nonce_mismatch"


def test_pairing_rejects_expired_request(running_bridge_server):
    server = running_bridge_server
    nonce = server.create_pairing_request(ttl_seconds=0)
    server.approve_pairing()
    time.sleep(0.02)

    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    result = pm.complete_pairing(nonce)
    assert result["status"] == "bridge_not_paired"
    assert result["error_code"] == "pairing_expired"


def test_successful_pairing_and_authenticated_command(running_bridge_server):
    server = running_bridge_server
    nonce = server.create_pairing_request(ttl_seconds=300)
    server.approve_pairing()

    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    # Complete pairing
    result = pm.complete_pairing(nonce)
    assert result["status"] == "paired"
    assert "session_token" in result
    token = result["session_token"]
    assert client.session_token == token

    # Verification: authenticated command through client succeeds
    resp = client.call("test_cmd", param="hello")
    assert resp["status"] == "ok"
    assert resp["echo"] == {"param": "hello"}

    # Verification: nonce is consumed once and cannot be replayed
    replay_result = pm.complete_pairing(nonce)
    assert replay_result["status"] == "bridge_not_paired"
    assert replay_result["error_code"] == "no_pairing_request"


def test_bridge_restart_invalidates_session(running_bridge_server):
    server = running_bridge_server
    nonce = server.create_pairing_request()
    server.approve_pairing()

    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    pm = PairingManager(client)

    result = pm.complete_pairing(nonce)
    assert result["status"] == "paired"

    # Stop bridge and restart with fresh session
    server.stop()
    time.sleep(0.05)
    server.start()
    time.sleep(0.05)

    # Previous token is no longer recognized by the restarted bridge
    resp = client.call("test_cmd")
    assert resp["status"] == "bridge_not_paired"


def test_invalidate_clears_token():
    client = BridgeClient(host=TEST_HOST, port=TEST_PORT)
    client.session_token = "some-token"
    client.session_id = "sess-123"
    pm = PairingManager(client)

    assert pm.session_token is not None
    pm.invalidate()
    assert client.session_token is None
    assert client.session_id == ""
    assert pm.session_token is None
