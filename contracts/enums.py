"""Strata data contracts — shared enumerations for requests, status, and errors.

This module contains ONLY data definitions. No algorithm code, no engine logic.
"""
from enum import Enum


class AssetKind(str, Enum):
    NONE = "none"
    ARCHIVE = "archive"
    BLEND = "blend"
    USER_PACK = "user_pack"
    PROJECT_PACK = "project_pack"
    MINECRAFT_JAR = "minecraft_jar"


class MissingAssetPolicy(str, Enum):
    GENERATE = "generate"
    ERROR = "error"


class OutputMode(str, Enum):
    STREAMED_A1_3D = "streamed_a1_3d"


class RetentionPolicy(str, Enum):
    DELETE_AFTER_DOWNLOAD = "delete_after_download"
    RETAIN_7_DAYS = "retain_7_days"


class JobStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ErrorCode(str, Enum):
    """Structured error codes for StrataError responses."""
    UNKNOWN = "unknown"
    INVALID_CONTRACT_VERSION = "invalid_contract_version"
    INVALID_INPUT = "invalid_input"
    PATH_TRAVERSAL = "path_traversal"
    INPUT_TOO_LARGE = "input_too_large"
    MISSING_CONSENT = "missing_consent"
    AUTH_FAILED = "auth_failed"
    AUTH_EXPIRED = "auth_expired"
    JOB_NOT_FOUND = "job_not_found"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"
    MANIFEST_INVALID = "manifest_invalid"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    SIGNATURE_INVALID = "signature_invalid"
    BRIDGE_UNAVAILABLE = "bridge_unavailable"
    ENGINE_UNAVAILABLE = "engine_unavailable"
