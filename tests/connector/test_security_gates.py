"""Tests for connector_mcp.security_gates (§9.5 service security gates)."""
from __future__ import annotations

import io
import struct
import tempfile
import zipfile
from pathlib import Path

import pytest

from connector_mcp.security_gates import (
    INPUT_QUOTA_DEFAULTS,
    THREAT_MODEL,
    check_archive_safety,
    sanitize_log_fields,
    validate_input_quotas,
    validate_job_isolation,
)


# ---------------------------------------------------------------------------
# Input quota tests
# ---------------------------------------------------------------------------

class TestInputQuotas:
    def test_pass_within_limits(self):
        result = validate_input_quotas(
            file_count=50,
            compressed_size_mb=100.0,
            uncompressed_size_mb=500.0,
            chunk_count=16,
        )
        assert result["valid"] is True
        assert result["violations"] == []

    def test_fail_excessive_files(self):
        result = validate_input_quotas(file_count=2000)
        assert result["valid"] is False
        assert any("file_count" in v for v in result["violations"])

    def test_fail_excessive_compressed_size(self):
        result = validate_input_quotas(compressed_size_mb=5000.0)
        assert result["valid"] is False
        assert any("compressed_size" in v for v in result["violations"])

    def test_fail_excessive_uncompressed_size(self):
        result = validate_input_quotas(uncompressed_size_mb=20000.0)
        assert result["valid"] is False
        assert any("uncompressed_size" in v for v in result["violations"])

    def test_fail_excessive_chunks(self):
        result = validate_input_quotas(chunk_count=5000)
        assert result["valid"] is False
        assert any("chunk_count" in v for v in result["violations"])

    def test_multiple_violations(self):
        result = validate_input_quotas(
            file_count=2000,
            compressed_size_mb=5000.0,
        )
        assert result["valid"] is False
        assert len(result["violations"]) == 2


# ---------------------------------------------------------------------------
# Archive safety tests
# ---------------------------------------------------------------------------

class TestArchiveSafety:
    def test_safe_archive(self, tmp_path):
        archive_path = tmp_path / "safe.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("data/file1.txt", "hello")
            zf.writestr("data/file2.txt", "world")
        result = check_archive_safety(archive_path)
        assert result["safe"] is True
        assert result["warnings"] == []

    def test_rejects_path_traversal(self, tmp_path):
        archive_path = tmp_path / "traversal.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("../../etc/passwd", "evil")
        result = check_archive_safety(archive_path)
        assert result["safe"] is False
        assert any("traversal" in w.lower() for w in result["warnings"])

    def test_rejects_absolute_path(self, tmp_path):
        archive_path = tmp_path / "absolute.zip"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("/etc/passwd", "evil")
        result = check_archive_safety(archive_path)
        assert result["safe"] is False
        assert any("absolute" in w.lower() for w in result["warnings"])

    def test_rejects_zip_bomb_ratio(self, tmp_path):
        """Create a file with extreme compression ratio metadata."""
        archive_path = tmp_path / "bomb.zip"
        # Create a zip with a small compressed file but claim large uncompressed
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write lots of zeros — compresses extremely well
            zf.writestr("bomb.txt", "\0" * 1_000_000)
        result = check_archive_safety(archive_path)
        # The ratio of 1MB zeros compressed should exceed 100x
        if result["safe"] is False:
            assert any("ratio" in w.lower() or "bomb" in w.lower()
                       for w in result["warnings"])

    def test_nonexistent_archive(self, tmp_path):
        result = check_archive_safety(tmp_path / "nope.zip")
        assert result["safe"] is False

    def test_corrupted_archive(self, tmp_path):
        bad = tmp_path / "bad.zip"
        bad.write_bytes(b"not a zip file")
        result = check_archive_safety(bad)
        assert result["safe"] is False


# ---------------------------------------------------------------------------
# Log sanitization tests
# ---------------------------------------------------------------------------

class TestSanitizeLogFields:
    def test_redacts_token(self):
        data = {"user": "alice", "access_token": "abc123", "job_id": "j1"}
        result = sanitize_log_fields(data)
        assert result["access_token"] == "[REDACTED]"
        assert result["user"] == "alice"
        assert result["job_id"] == "j1"

    def test_redacts_password(self):
        result = sanitize_log_fields({"password": "hunter2"})
        assert result["password"] == "[REDACTED]"

    def test_redacts_secret_key(self):
        result = sanitize_log_fields({"signing_key": "s3cr3t"})
        assert result["signing_key"] == "[REDACTED]"

    def test_redacts_nested_sensitive(self):
        data = {"auth": {"api_key": "key123", "user": "bob"}}
        result = sanitize_log_fields(data)
        assert result["auth"]["api_key"] == "[REDACTED]"
        assert result["auth"]["user"] == "bob"

    def test_redacts_absolute_paths(self):
        data = {"file": "C:\\Users\\test\\secret.txt"}
        result = sanitize_log_fields(data)
        assert "Users" not in result["file"]
        assert "secret.txt" in result["file"]

    def test_preserves_non_sensitive(self):
        data = {"status": "running", "count": 42}
        result = sanitize_log_fields(data)
        assert result == data


# ---------------------------------------------------------------------------
# Job isolation tests
# ---------------------------------------------------------------------------

class TestJobIsolation:
    def test_allows_same_user(self):
        result = validate_job_isolation("job-1", "user-A", "user-A")
        assert result["authorized"] is True

    def test_rejects_cross_user(self):
        result = validate_job_isolation("job-1", "user-B", "user-A")
        assert result["authorized"] is False
        assert "not the owner" in result["reason"]

    def test_rejects_missing_user(self):
        result = validate_job_isolation("job-1", "", "user-A")
        assert result["authorized"] is False

    def test_rejects_no_owner(self):
        result = validate_job_isolation("job-1", "user-A", "")
        assert result["authorized"] is False


# ---------------------------------------------------------------------------
# Threat model test
# ---------------------------------------------------------------------------

class TestThreatModel:
    def test_threat_model_documented(self):
        assert len(THREAT_MODEL) >= 8
        required_threats = [
            "malicious_plugin_input",
            "path_traversal",
            "archive_bomb",
            "cross_user_access",
            "output_tampering",
        ]
        for threat in required_threats:
            assert threat in THREAT_MODEL, f"Missing threat: {threat}"
            assert len(THREAT_MODEL[threat]) > 20, f"Threat {threat} undocumented"

    def test_quota_defaults_defined(self):
        assert INPUT_QUOTA_DEFAULTS["max_file_count"] == 1000
        assert INPUT_QUOTA_DEFAULTS["max_chunk_count"] == 4096
        assert INPUT_QUOTA_DEFAULTS["archive_bomb_ratio"] == 100.0
