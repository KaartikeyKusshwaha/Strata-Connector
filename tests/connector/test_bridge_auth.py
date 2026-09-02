"""Tests for per-session token authentication (Step 4).

Verifies absent, invalid, expired, and valid session token scenarios.
"""
import time
import pytest
from addon.bridge_auth import (
    SessionToken,
    TokenExpiredError,
    TokenInvalidError,
    generate_session_token,
    validate_token,
)


def test_generate_session_token():
    token = generate_session_token(lifetime_seconds=3600)
    assert len(token.token) == 64  # SHA-256 hex digest
    assert token.created_at <= time.time()
    assert token.expires_at > time.time()
    assert not token.is_expired()


def test_validate_token_valid():
    token = generate_session_token(lifetime_seconds=3600)
    assert validate_token(token.token, token) is True


def test_validate_token_absent():
    token = generate_session_token(lifetime_seconds=3600)
    with pytest.raises(TokenInvalidError, match="required"):
        validate_token(None, token)

    with pytest.raises(TokenInvalidError, match="required"):
        validate_token("", token)


def test_validate_token_invalid():
    token = generate_session_token(lifetime_seconds=3600)
    with pytest.raises(TokenInvalidError, match="does not match"):
        validate_token("wrong_token_value", token)


def test_validate_token_expired():
    token = generate_session_token(lifetime_seconds=0)
    # Force expiry by setting expires_at in the past
    token.expires_at = time.time() - 1
    with pytest.raises(TokenExpiredError, match="expired"):
        validate_token(token.token, token)


def test_two_tokens_are_unique():
    t1 = generate_session_token()
    t2 = generate_session_token()
    assert t1.token != t2.token
