"""Service security, operations, and recovery gates (§9.5).

Provides input validation, rate limiting, archive safety checking,
and structured security logging for the Strata Connector.
"""
from __future__ import annotations

import hashlib
import os
import re
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


# ---------------------------------------------------------------------------
# Threat model (§9.5.1)
# ---------------------------------------------------------------------------

THREAT_MODEL: dict[str, str] = {
    "malicious_plugin_input": (
        "Untrusted MCP input could inject path traversal, oversized payloads, "
        "or trigger unintended Blender operations. Mitigated by quota checks "
        "and strict input validation."
    ),
    "path_traversal": (
        "Archive entries or user-supplied paths may escape sandbox. "
        "Mitigated by check_archive_safety and normalized path validation."
    ),
    "archive_bomb": (
        "Zip bombs with extreme compression ratios exhaust disk/memory. "
        "Mitigated by ratio limit (100x) and uncompressed size cap."
    ),
    "cross_user_access": (
        "One user accessing another user's jobs or desktop session. "
        "Mitigated by validate_job_isolation with strict owner matching."
    ),
    "stolen_token": (
        "Browser or device token reused from a different session. "
        "Mitigated by per-session nonce binding and token expiry."
    ),
    "compromised_worker": (
        "Worker process accessing unrelated jobs or network. "
        "Mitigated by sandboxed output directories and no inbound port."
    ),
    "replayed_command": (
        "Previously consumed command replayed to a paired desktop. "
        "Mitigated by one-time nonce and expiry timestamps."
    ),
    "dependency_compromise": (
        "Tampered dependency injected via supply chain. "
        "Mitigated by pinned dependencies, SBOM, and hash verification."
    ),
    "output_tampering": (
        "Build output modified in transit or at rest. "
        "Mitigated by HMAC-SHA256 manifest signing and per-file checksums."
    ),
}


# ---------------------------------------------------------------------------
# Input quotas (§9.5.3)
# ---------------------------------------------------------------------------

INPUT_QUOTA_DEFAULTS: dict[str, int | float] = {
    "max_file_count": 1000,
    "max_compressed_size_mb": 2048,       # 2 GB
    "max_uncompressed_size_mb": 10240,    # 10 GB
    "max_chunk_count": 4096,
    "max_upload_duration_seconds": 3600,  # 1 hour
    "max_job_cpu_seconds": 7200,          # 2 hours
    "max_job_ram_mb": 8192,               # 8 GB
    "max_queue_depth": 100,
    "archive_bomb_ratio": 100.0,          # reject if ratio > 100x
}


def validate_input_quotas(
    file_count: int = 0,
    compressed_size_mb: float = 0.0,
    uncompressed_size_mb: float = 0.0,
    chunk_count: int = 0,
) -> dict[str, Any]:
    """Validate job input against quota limits.

    Returns ``{"valid": True/False, "violations": [...]}``.
    """
    violations: list[str] = []
    q = INPUT_QUOTA_DEFAULTS

    if file_count > q["max_file_count"]:
        violations.append(
            f"file_count {file_count} exceeds limit {q['max_file_count']}"
        )
    if compressed_size_mb > q["max_compressed_size_mb"]:
        violations.append(
            f"compressed_size {compressed_size_mb} MB exceeds limit "
            f"{q['max_compressed_size_mb']} MB"
        )
    if uncompressed_size_mb > q["max_uncompressed_size_mb"]:
        violations.append(
            f"uncompressed_size {uncompressed_size_mb} MB exceeds limit "
            f"{q['max_uncompressed_size_mb']} MB"
        )
    if chunk_count > q["max_chunk_count"]:
        violations.append(
            f"chunk_count {chunk_count} exceeds limit {q['max_chunk_count']}"
        )

    return {"valid": len(violations) == 0, "violations": violations}


# ---------------------------------------------------------------------------
# Archive safety (§9.5.4)
# ---------------------------------------------------------------------------

def check_archive_safety(archive_path: str | Path) -> dict[str, Any]:
    """Check a ZIP archive for path traversal, symlinks, and zip bombs.

    Returns ``{"safe": True/False, "warnings": [...]}``.
    """
    archive_path = Path(archive_path)
    warnings: list[str] = []

    if not archive_path.exists():
        return {"safe": False, "warnings": ["Archive does not exist"]}

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            total_compressed = 0
            total_uncompressed = 0

            for info in zf.infolist():
                name = info.filename

                # Path traversal check
                try:
                    resolved = PurePosixPath(name)
                    if ".." in resolved.parts:
                        warnings.append(
                            f"Path traversal detected: {name}"
                        )
                except Exception:
                    pass

                # Also check Windows-style paths
                if "..\\" in name or "../" in name:
                    warnings.append(f"Path traversal detected: {name}")

                # Absolute path check
                if name.startswith("/") or name.startswith("\\"):
                    warnings.append(f"Absolute path in archive: {name}")

                # Check for Windows drive letters
                if len(name) > 1 and name[1] == ":":
                    warnings.append(f"Absolute Windows path: {name}")

                # Symlink check (external_attr bit 29 = symlink on Unix)
                if info.external_attr >> 28 == 0xA:
                    warnings.append(f"Symlink entry detected: {name}")

                # Also check create_system for Unix symlinks
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    warnings.append(f"Symlink entry detected: {name}")

                total_compressed += info.compress_size
                total_uncompressed += info.file_size

            # Zip bomb ratio check
            if total_compressed > 0:
                ratio = total_uncompressed / total_compressed
                max_ratio = INPUT_QUOTA_DEFAULTS["archive_bomb_ratio"]
                if ratio > max_ratio:
                    warnings.append(
                        f"Compression ratio {ratio:.1f}x exceeds "
                        f"limit {max_ratio}x (possible zip bomb)"
                    )

    except zipfile.BadZipFile:
        warnings.append("Invalid or corrupted ZIP file")

    # Deduplicate warnings
    warnings = list(dict.fromkeys(warnings))
    return {"safe": len(warnings) == 0, "warnings": warnings}


# ---------------------------------------------------------------------------
# Log field sanitization (§9.5.5)
# ---------------------------------------------------------------------------

_SENSITIVE_PATTERNS = re.compile(
    r"(token|nonce|password|secret|key|authorization|cookie|session_id|"
    r"api_key|access_token|refresh_token|signing_key)",
    re.IGNORECASE,
)


def sanitize_log_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields from log entries.

    Redacts: tokens, nonces, passwords, secret keys, absolute paths.
    Returns a new dict with redacted values.
    """
    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        if _SENSITIVE_PATTERNS.search(key):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and _is_absolute_path(value):
            sanitized[key] = _redact_path(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_fields(value)
        else:
            sanitized[key] = value

    return sanitized


def _is_absolute_path(value: str) -> bool:
    """Check if a string looks like an absolute file path."""
    if not value:
        return False
    # Unix absolute
    if value.startswith("/") and "/" in value[1:]:
        return True
    # Windows absolute (C:\... or C:/...)
    if len(value) > 2 and value[1] == ":" and value[2] in ("/", "\\"):
        return True
    return False


def _redact_path(path: str) -> str:
    """Keep only the basename of an absolute path."""
    return f"[PATH]/{Path(path).name}"


# ---------------------------------------------------------------------------
# Job isolation (§9.5.2)
# ---------------------------------------------------------------------------

def validate_job_isolation(
    job_id: str,
    requesting_user_id: str,
    job_owner_id: str,
) -> dict[str, Any]:
    """Validate that a requesting user owns the job they're accessing.

    Returns ``{"authorized": True/False, "reason": "..."}``.
    """
    if not requesting_user_id:
        return {
            "authorized": False,
            "reason": "Missing requesting user ID",
        }
    if not job_owner_id:
        return {
            "authorized": False,
            "reason": "Job has no owner record",
        }
    if requesting_user_id != job_owner_id:
        return {
            "authorized": False,
            "reason": (
                f"User '{requesting_user_id}' is not the owner of job "
                f"'{job_id}' (owner: '{job_owner_id}')"
            ),
        }
    return {
        "authorized": True,
        "reason": "User is the job owner",
    }
