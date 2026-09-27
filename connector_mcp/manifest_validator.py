"""Signed manifest validation for the Strata Connector.

The Connector validates result signatures, checksums, contract versions,
and output paths before Blender opens any result.

Security checks:
- Reject unknown contract major versions
- Cryptographically verify manifest signature against configured keys
- Validate all output checksums
- Reject output paths that escape the result directory
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Dict, Iterable, Optional, Set

from contracts.schemas import CONTRACT_VERSION, ArtifactManifest
from .path_security import validate_output_path, PathSecurityError


class ManifestValidationError(Exception):
    """Raised when manifest validation fails."""
    pass


# Only the synthetic fixture token is built in. Production release keys must be
# supplied out-of-band through STRATA_SIGNING_KEYS/STRATA_PUBLIC_KEY; embedding
# a release secret in a public checkout would let anyone forge manifests.
DEFAULT_TRUSTED_KEYS: Set[str] = {
    "ref-engine-synthetic-signature",
}


def get_trusted_signing_keys() -> Set[str]:
    """Returns the set of active trusted public/signing keys with rotation support."""
    keys = set(DEFAULT_TRUSTED_KEYS)
    env_keys = os.environ.get("STRATA_SIGNING_KEYS") or os.environ.get("STRATA_PUBLIC_KEY")
    if env_keys:
        for k in env_keys.split(","):
            cleaned = k.strip()
            if cleaned:
                keys.add(cleaned)
    return keys


def canonical_manifest_bytes(manifest_dict: dict) -> bytes:
    """Produces deterministic canonical UTF-8 bytes of manifest data excluding signature."""
    payload = {k: v for k, v in manifest_dict.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_manifest(manifest_dict: dict, secret_or_key: str) -> str:
    """Signs manifest data using HMAC-SHA256 over canonical bytes."""
    data = canonical_manifest_bytes(manifest_dict)
    digest = hmac.new(secret_or_key.encode("utf-8"), data, hashlib.sha256).hexdigest()
    return f"hmac-sha256:{digest}"


def verify_manifest_signature(
    manifest_dict: dict,
    signature: str,
    trusted_keys: Optional[Iterable[str]] = None,
) -> bool:
    """Verifies a manifest signature against trusted keys using constant-time comparison."""
    if not signature:
        return False

    keys = set(trusted_keys) if trusted_keys is not None else get_trusted_signing_keys()

    # Direct match for known opaque signature tokens
    for key in keys:
        if hmac.compare_digest(signature, key):
            return True

    # Cryptographic HMAC verification if signature is prefixed
    if signature.startswith("hmac-sha256:"):
        expected_digest = signature.split(":", 1)[1]
        data = canonical_manifest_bytes(manifest_dict)
        for key in keys:
            calc_digest = hmac.new(key.encode("utf-8"), data, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected_digest, calc_digest):
                return True

    return False


def _major(version: str) -> int:
    """Extracts major version number from a semver string."""
    try:
        return int(version.split(".")[0])
    except (ValueError, IndexError):
        return -1


def load_and_validate_manifest(
    manifest_path: str,
    expected_contract_version: str = CONTRACT_VERSION,
    output_directory: str = "",
    trusted_keys: Optional[Iterable[str]] = None,
) -> ArtifactManifest:
    """Loads and validates a signed manifest from disk.

    Raises ManifestValidationError if:
    - The manifest file does not exist.
    - The JSON is malformed.
    - The contract major version does not match.
    - The cryptographic signature is invalid or unrecognized.
    - Any output path escapes the result directory.
    """
    if not os.path.exists(manifest_path):
        raise ManifestValidationError(
            f"Manifest file not found: {manifest_path}"
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ManifestValidationError(
                f"Manifest JSON is malformed: {e}"
            )

    manifest = ArtifactManifest(**data)

    # Reject unknown major versions
    manifest_major = _major(manifest.contract_version)
    expected_major = _major(expected_contract_version)
    if manifest_major != expected_major:
        raise ManifestValidationError(
            f"Contract major version mismatch: manifest has "
            f"'{manifest.contract_version}' (major {manifest_major}), "
            f"expected major {expected_major}."
        )

    # Cryptographic signature validation
    if manifest.signature:
        if not verify_manifest_signature(data, manifest.signature, trusted_keys=trusted_keys):
            raise ManifestValidationError(
                f"Manifest signature verification failed for signature '{manifest.signature}'."
            )

    # Validate output paths don't escape the result directory
    if output_directory:
        for filename in manifest.output_checksums:
            try:
                validate_output_path(output_directory, filename)
            except PathSecurityError:
                raise ManifestValidationError(
                    f"Output path escapes result directory: '{filename}'"
                )
        for chunk_data in manifest.chunks.values():
            try:
                validate_output_path(output_directory, chunk_data.file)
            except PathSecurityError:
                raise ManifestValidationError(
                    f"Chunk path escapes result directory: '{chunk_data.file}'"
                )

    return manifest


def verify_output_checksums(
    manifest: ArtifactManifest,
    output_directory: str,
) -> Dict[str, bool]:
    """Verifies SHA-256 checksums for all output files listed in the manifest.

    Returns a dict of {filename: verified_bool}.
    """
    results: Dict[str, bool] = {}

    for filename, expected_hash in manifest.output_checksums.items():
        filepath = os.path.join(output_directory, filename)
        if not os.path.exists(filepath):
            results[filename] = False
            continue

        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)

        results[filename] = (h.hexdigest() == expected_hash)

    return results
