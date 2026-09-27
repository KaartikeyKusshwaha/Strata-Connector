"""Security tests for the Strata Connector (Phase C).

Tests path traversal defense, input size limits, consent review flow,
manifest rejection (unknown schema major, invalid signature, checksum
mismatch, escaping paths).
"""
import json
import os
import pytest

from connector_mcp.path_security import validate_path, validate_output_path, PathSecurityError
from connector_mcp.manifest_validator import (
    ManifestValidationError,
    load_and_validate_manifest,
    verify_output_checksums,
)


# ---------------------------------------------------------------------------
# Path traversal defense
# ---------------------------------------------------------------------------

class TestPathValidation:

    def test_valid_absolute_path(self):
        result = validate_path("C:\\Users\\test\\world")
        assert os.path.isabs(result)

    def test_rejects_relative_path(self):
        with pytest.raises(PathSecurityError, match="absolute"):
            validate_path("relative/path")

    def test_rejects_empty_path(self):
        with pytest.raises(PathSecurityError, match="empty"):
            validate_path("")

    def test_rejects_traversal(self):
        with pytest.raises(PathSecurityError, match="traversal"):
            validate_path("C:\\Users\\test\\..\\..\\etc\\passwd")

    def test_rejects_null_bytes(self):
        with pytest.raises(PathSecurityError, match="null"):
            validate_path("C:\\Users\\test\x00evil")

    def test_rejects_reserved_device_names(self):
        with pytest.raises(PathSecurityError, match="reserved"):
            validate_path("C:\\CON")


class TestOutputPathValidation:

    def test_valid_output_path(self):
        result = validate_output_path("C:\\output", "chunks\\chunk1.blend")
        assert result.startswith("C:\\output")

    def test_rejects_escaping_path(self):
        with pytest.raises(PathSecurityError, match="escapes"):
            validate_output_path("C:\\output", "..\\..\\etc\\passwd")

    def test_rejects_sibling_prefix_path(self):
        # A naive string-prefix check would incorrectly treat output-sibling
        # paths such as C:\\output-archive as inside C:\\output.
        with pytest.raises(PathSecurityError, match="escapes"):
            validate_output_path("C:\\output", "..\\output-archive\\file.bin")


# ---------------------------------------------------------------------------
# Manifest validation
# ---------------------------------------------------------------------------

class TestManifestValidation:

    def test_rejects_missing_file(self):
        with pytest.raises(ManifestValidationError, match="not found"):
            load_and_validate_manifest("C:\\nonexistent\\manifest.json")

    def test_rejects_malformed_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all {{{")
        with pytest.raises(ManifestValidationError, match="malformed"):
            load_and_validate_manifest(str(bad_file))

    def test_rejects_wrong_major_version(self, tmp_path):
        manifest = {
            "schema_version": 1,
            "contract_version": "99.0",
            "engine_version": "2026.09.0",
            "chunks": {},
            "output_checksums": {},
        }
        f = tmp_path / "manifest.json"
        f.write_text(json.dumps(manifest))
        with pytest.raises(ManifestValidationError, match="major version"):
            load_and_validate_manifest(str(f))

    def test_accepts_compatible_minor_version(self, tmp_path):
        manifest = {
            "schema_version": 1,
            "contract_version": "1.1",
            "engine_version": "2026.09.0",
            "chunks": {},
            "output_checksums": {},
            "signature": "ref-engine-synthetic-signature",
        }
        f = tmp_path / "manifest.json"
        f.write_text(json.dumps(manifest))
        result = load_and_validate_manifest(str(f))
        assert result.contract_version == "1.1"

    def test_rejects_unknown_signature(self, tmp_path):
        manifest = {
            "schema_version": 1,
            "contract_version": "1.0",
            "engine_version": "2026.09.0",
            "chunks": {},
            "output_checksums": {},
            "signature": "unknown-hacker-signature",
        }
        f = tmp_path / "manifest.json"
        f.write_text(json.dumps(manifest))
        with pytest.raises(ManifestValidationError, match="signature"):
            load_and_validate_manifest(str(f))

    def test_rejects_escaping_output_path(self, tmp_path):
        manifest = {
            "schema_version": 1,
            "contract_version": "1.0",
            "engine_version": "2026.09.0",
            "chunks": {},
            "output_checksums": {"../../etc/passwd": "a" * 64},
            "signature": "ref-engine-synthetic-signature",
        }
        f = tmp_path / "manifest.json"
        f.write_text(json.dumps(manifest))
        with pytest.raises(ManifestValidationError, match="escapes"):
            load_and_validate_manifest(str(f), output_directory=str(tmp_path))

    def test_checksum_verification_pass(self, tmp_path):
        import hashlib
        test_file = tmp_path / "test.blend"
        test_file.write_bytes(b"test content")
        expected = hashlib.sha256(b"test content").hexdigest()

        from contracts.schemas import ArtifactManifest
        manifest = ArtifactManifest(
            engine_version="2026.09.0",
            output_checksums={"test.blend": expected},
        )
        results = verify_output_checksums(manifest, str(tmp_path))
        assert results["test.blend"] is True

    def test_checksum_verification_fail(self, tmp_path):
        test_file = tmp_path / "test.blend"
        test_file.write_bytes(b"test content")

        from contracts.schemas import ArtifactManifest
        manifest = ArtifactManifest(
            engine_version="2026.09.0",
            output_checksums={"test.blend": "0" * 64},
        )
        results = verify_output_checksums(manifest, str(tmp_path))
        assert results["test.blend"] is False

    def test_checksum_verification_missing_file(self, tmp_path):
        from contracts.schemas import ArtifactManifest
        manifest = ArtifactManifest(
            engine_version="2026.09.0",
            output_checksums={"missing.blend": "a" * 64},
        )
        results = verify_output_checksums(manifest, str(tmp_path))
        assert results["missing.blend"] is False
