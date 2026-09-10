"""Tests for the Blender bridge pairing flow.

Covers missing, invalid, expired, restarted, and successful pairing scenarios.
"""
import time
import pytest
from connector_mcp.pairing import PairingManager, PairingState


def test_initial_state_is_stopped():
    pm = PairingManager()
    assert pm.state == PairingState.STOPPED


def test_create_pairing_request():
    pm = PairingManager()
    req = pm.create_pairing_request()
    assert req.nonce
    assert req.is_valid()
    assert pm.state == PairingState.AWAITING_PAIRING


def test_complete_pairing_success():
    pm = PairingManager()
    req = pm.create_pairing_request()
    result = pm.complete_pairing(req.nonce)
    assert result["status"] == "paired"
    assert "session_token" in result
    assert pm.state == PairingState.PAIRED


def test_complete_pairing_wrong_nonce():
    pm = PairingManager()
    pm.create_pairing_request()
    result = pm.complete_pairing("wrong-nonce")
    assert result["status"] == "bridge_not_paired"
    assert "nonce" in result["message"].lower() or "match" in result["message"].lower()


def test_complete_pairing_no_request():
    pm = PairingManager()
    result = pm.complete_pairing("any-nonce")
    assert result["status"] == "bridge_not_paired"
    assert "no pairing" in result["message"].lower()


def test_complete_pairing_already_consumed():
    pm = PairingManager()
    req = pm.create_pairing_request()
    pm.complete_pairing(req.nonce)
    result = pm.complete_pairing(req.nonce)
    assert result["status"] == "bridge_not_paired"
    assert "already" in result["message"].lower()


def test_complete_pairing_expired_request():
    pm = PairingManager()
    req = pm.create_pairing_request(ttl_seconds=0)
    time.sleep(0.01)
    result = pm.complete_pairing(req.nonce)
    assert result["status"] == "bridge_not_paired"
    assert "expired" in result["message"].lower()


def test_get_status_stopped():
    pm = PairingManager()
    status = pm.get_status()
    assert status["pairing_state"] == "stopped"
    assert "recovery" in status


def test_get_status_paired():
    pm = PairingManager()
    req = pm.create_pairing_request()
    pm.complete_pairing(req.nonce)
    status = pm.get_status()
    assert status["pairing_state"] == "paired"
    assert "expires_in" in status


def test_invalidate_resets_state():
    pm = PairingManager()
    req = pm.create_pairing_request()
    pm.complete_pairing(req.nonce)
    assert pm.state == PairingState.PAIRED
    pm.invalidate()
    assert pm.state == PairingState.STOPPED


def test_session_token_available_after_pairing():
    pm = PairingManager()
    req = pm.create_pairing_request()
    pm.complete_pairing(req.nonce)
    assert pm.session_token is not None
    assert not pm.session_token.is_expired()


def test_pairing_nonces_are_unique():
    pm = PairingManager()
    nonces = set()
    for _ in range(50):
        req = pm.create_pairing_request()
        nonces.add(req.nonce)
    assert len(nonces) == 50
