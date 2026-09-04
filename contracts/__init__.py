# Strata Contracts — versioned data schemas for the Connector/Engine protocol
from .schemas import (
    CONTRACT_VERSION,
    ArtifactManifest,
    BuildConsent,
    BuildInputManifest,
    BuildRequest,
    BuildStatus,
    ChunkDescriptor,
    SourceDescriptor,
    StrataError,
    StreamingStatus,
    WorldDiagnostics,
    # Legacy aliases
    JobRequest,
    JobResult,
    JobDiagnostics,
    SignedManifest,
    ManifestChunkEntry,
    UploadConsentSummary,
)
from .enums import (
    AssetKind,
    ErrorCode,
    JobStatus,
    MissingAssetPolicy,
    OutputMode,
    RetentionPolicy,
)
