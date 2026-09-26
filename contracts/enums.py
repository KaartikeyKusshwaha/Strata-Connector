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
    COMMAND_EXPIRED = "command_expired"
    COMMAND_UNKNOWN = "command_unknown"
    COMMAND_REPLAYED = "command_replayed"


class CommandName(str, Enum):
    """Allow-listed named bridge command verbs for cloud-to-desktop dispatch."""
    OPEN_RESULT = "open_result"
    GET_CHUNK_STREAMING_STATUS = "get_chunk_streaming_status"
    LOAD_CHUNK_RADIUS = "load_chunk_radius"
    SET_INTERACTIVE_BLOCK_STATE = "set_interactive_block_state"
    KEYFRAME_INTERACTIVE_BLOCK_STATE = "keyframe_interactive_block_state"


class CommandStatus(str, Enum):
    """Execution lifecycle status for dispatched command envelopes."""
    PENDING = "pending"
    DELIVERED = "delivered"
    EXECUTED = "executed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
