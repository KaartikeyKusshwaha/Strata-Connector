"""Signed manifest validation for the Strata Connector.

The Connector validates result signatures, checksums, contract versions,
and output paths before Blender opens any result.

Security checks:
- Reject unknown contract major versions
- Verify signing public key (placeholder for real implementation)
- Validate all output checksums
- Reject output paths that escape the result directory
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Dict

from contracts.schemas import CONTRACT_VERSION, ArtifactManifest
from .path_security import validate_output_path, PathSecurityError


class ManifestValidationError(Exception):
    """Raised when manifest validation fails."""
    pass


# Known signing public keys (placeholder — in production these would be
# loaded from a secure configuration or key store)
KNOWN_SIGNING_KEYS = {
    "ref-engine-synthetic-signature",  # Reference engine test signature
}


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
) -> ArtifactManifest:
    """Loads and validates a signed manifest from disk.

    Raises ManifestValidationError if:
    - The manifest file does not exist.
    - The JSON is malformed.
    - The contract major version does not match.
    - The signature is not recognized.
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

    # Verify signature (placeholder — in production this would use
    # cryptographic verification with the signing public key)
    if manifest.signature and manifest.signature not in KNOWN_SIGNING_KEYS:
        raise ManifestValidationError(
            f"Unrecognized manifest signature."
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
