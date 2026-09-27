"""Tests for cryptographic manifest signature verification and key rotation."""
import json
import os
import tempfile
import pytest

from contracts.schemas import CONTRACT_VERSION
from connector_mcp.manifest_validator import (
    ManifestValidationError,
    canonical_manifest_bytes,
    load_and_validate_manifest,
    sign_manifest,
    verify_manifest_signature,
)
from reference_engine.synthetic import synthetic_manifest


@pytest.fixture
def sample_manifest_dict():
    return synthetic_manifest(request_id="test-job-sig")


def test_canonical_manifest_bytes_deterministic(sample_manifest_dict):
    b1 = canonical_manifest_bytes(sample_manifest_dict)
    sample_manifest_dict["signature"] = "some-sig"
    b2 = canonical_manifest_bytes(sample_manifest_dict)
    assert b1 == b2, "Signature field must be excluded from canonical bytes"


def test_sign_and_verify_hmac(sample_manifest_dict):
    secret = "my-test-secret-key-12345"
    sig = sign_manifest(sample_manifest_dict, secret)
    assert sig.startswith("hmac-sha256:")

    # Verification with matching key succeeds
    assert verify_manifest_signature(sample_manifest_dict, sig, trusted_keys=[secret]) is True

    # Verification with wrong key fails
    assert verify_manifest_signature(sample_manifest_dict, sig, trusted_keys=["wrong-key"]) is False


def test_load_and_validate_signed_manifest_file(sample_manifest_dict, tmp_path):
    secret = "strata-release-key-2026-v1"
    sig = sign_manifest(sample_manifest_dict, secret)
    sample_manifest_dict["signature"] = sig

    manifest_file = tmp_path / "strata-world-manifest.json"
    manifest_file.write_text(json.dumps(sample_manifest_dict, indent=2), encoding="utf-8")

    # Loads and validates with trusted key
    validated = load_and_validate_manifest(str(manifest_file), trusted_keys=[secret])
    assert validated.signature == sig


def test_tampered_signature_fails_validation(sample_manifest_dict, tmp_path):
    secret = "strata-release-key-2026-v1"
    sample_manifest_dict["signature"] = "hmac-sha256:0000000000000000000000000000000000000000000000000000000000000000"

    manifest_file = tmp_path / "strata-world-manifest.json"
    manifest_file.write_text(json.dumps(sample_manifest_dict, indent=2), encoding="utf-8")

    with pytest.raises(ManifestValidationError) as exc:
        load_and_validate_manifest(str(manifest_file), trusted_keys=[secret])
    assert "signature verification failed" in str(exc.value).lower()


def test_key_rotation_via_env(sample_manifest_dict, monkeypatch):
    rotated_key = "rotated-strata-key-2027"
    monkeypatch.setenv("STRATA_SIGNING_KEYS", f"old-key,{rotated_key}")

    sig = sign_manifest(sample_manifest_dict, rotated_key)
    assert verify_manifest_signature(sample_manifest_dict, sig) is True
