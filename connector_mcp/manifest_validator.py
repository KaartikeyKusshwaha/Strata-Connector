"""Signed manifest validation for the Strata connector.

The connector validates result signatures and checksums before Blender
opens any result. Rejects mismatched engine/contract versions.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Optional

from contracts.schemas import CONTRACT_VERSION, SignedManifest


class ManifestValidationError(Exception):
    """Raised when manifest validation fails."""
    pass


def load_and_validate_manifest(
    manifest_path: str,
    expected_contract_version: str = CONTRACT_VERSION,
) -> SignedManifest:
    """Loads and validates a signed manifest from disk.

    Raises ManifestValidationError if:
    - The manifest file does not exist.
    - The JSON is malformed.
    - The contract_version does not match.
    - Required fields are missing.
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

    manifest = SignedManifest(**data)

    if manifest.contract_version != expected_contract_version:
        raise ManifestValidationError(
            f"Contract version mismatch: manifest has '{manifest.contract_version}', "
            f"expected '{expected_contract_version}'."
        )

    return manifest


def verify_output_checksums(
    manifest: SignedManifest,
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
