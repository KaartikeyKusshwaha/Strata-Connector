"""Strata data contracts — shared enumerations for job requests and results.

This module contains ONLY data definitions. No algorithm code, no engine logic.
"""
from enum import Enum


class AssetKind(str, Enum):
    NONE = "none"
    BLEND = "blend"
    USER_PACK = "user_pack"
    SELECTED_PACK = "selected_pack"
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
