"""Strata MCP Connector — thin stdio client.

This is the local MCP server exposed to Codex and other MCP clients.
It communicates with the Private Strata API for engine work and the local
Blender bridge for scene operations.

This module must NEVER import private engine modules.
"""
from __future__ import annotations

import os
import uuid

from mcp.server.fastmcp import FastMCP

from .api_client import StrataAPIClient
from .bridge_client import BridgeClient
from .pairing import PairingManager
from .path_security import validate_path, PathSecurityError
from .manifest_validator import (
    ManifestValidationError,
    load_and_validate_manifest,
    verify_output_checksums,
)
from contracts.schemas import StrataError
from contracts.enums import ErrorCode

mcp = FastMCP("strata-connector")

_api = StrataAPIClient()
_bridge = BridgeClient()
_pairing = PairingManager(_bridge)

# Maximum input file size: 2 GB
MAX_INPUT_SIZE_BYTES = 2 * 1024 * 1024 * 1024


def _error_response(code: ErrorCode, message: str) -> dict:
    """Creates a structured error response safe for agent consumption."""
    return StrataError(
        operation_id=str(uuid.uuid4()),
        error_code=code,
        message=message,
    ).model_dump()


# ---------------------------------------------------------------------------
# World inspection & build submission
# ---------------------------------------------------------------------------

@mcp.tool()
def strata_preflight_world(world_path: str) -> dict:
    """Validates selected inputs and shows a capability/privacy report.
    Returns block counts, chunk estimates, and missing asset diagnostics."""
    try:
        validate_path(world_path)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))
    return _api.preflight_world(world_path)


@mcp.tool()
def strata_inspect_library(library_blend_path: str) -> dict:
    """Inspects a user-selected library through supported metadata.
    Lists top-level object names for reconciliation against Minecraft block IDs."""
    try:
        validate_path(library_blend_path)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))
    return _api.inspect_library(library_blend_path)


@mcp.tool()
def strata_generate_barebones_library(output_path: str) -> dict:
    """Generates a procedural fallback block library in the paired Blender.

    MUTATING: Creates a .blend library and provenance sidecar. This is a legal
    placeholder library, not a Minecraft texture extractor; use a custom
    library or the private Engine for production assets.
    """
    try:
        norm_path = validate_path(output_path)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))
    if not norm_path.lower().endswith(".blend"):
        return _error_response(
            ErrorCode.INVALID_INPUT,
            "Barebones library output must use a .blend extension.",
        )
    return _bridge.call("generate_barebones_library", output_path=norm_path)


@mcp.tool()
def strata_submit_managed_build(
    world_path: str,
    output_directory: str,
    library_blend_path: str = "",
    missing_asset_policy: str = "generate",
    chunk_size: int = 16,
    retention: str = "delete_after_download",
) -> dict:
    """Submits explicitly consented inputs to the Engine for a managed build.

    MUTATING: This uploads world data and declared assets to the private
    worker. A consent summary with files, hashes, intended use, and
    retention is presented before submission.
    """
    try:
        validate_path(world_path)
        validate_path(output_directory)
        if library_blend_path:
            validate_path(library_blend_path)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))

    # Check input size limits
    if os.path.exists(world_path) and not os.path.isdir(world_path):
        size = os.path.getsize(world_path)
        if size > MAX_INPUT_SIZE_BYTES:
            return _error_response(
                ErrorCode.INPUT_TOO_LARGE,
                f"Input file exceeds {MAX_INPUT_SIZE_BYTES // (1024**3)} GB limit.",
            )

    return _api.submit_build(
        world_path=world_path,
        output_directory=output_directory,
        library_blend_path=library_blend_path,
        missing_asset_policy=missing_asset_policy,
        chunk_size=chunk_size,
        retention=retention,
    )


@mcp.tool()
def strata_get_job_status(job_id: str) -> dict:
    """Retrieves structured job progress, percentage, and diagnostics
    for a submitted build job."""
    return _api.get_job_status(job_id)


@mcp.tool()
def strata_download_result(job_id: str, output_directory: str) -> dict:
    """Downloads and verifies signed artifacts (manifest + chunk files) to
    the specified output directory. Validates signed manifest checksums
    before making files available.

    MUTATING: Creates local files.
    """
    try:
        validate_path(output_directory)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))
    return _api.download_result(job_id, output_directory)


@mcp.tool()
def strata_open_result_in_blender(manifest_path: str) -> dict:
    """Opens a verified result in the active Blender project via
    the local bridge. Validates manifest signature and output checksums before hand-off.

    MUTATING: Opens files in Blender.
    """
    try:
        norm_manifest = validate_path(manifest_path)
    except PathSecurityError as e:
        return _error_response(ErrorCode.PATH_TRAVERSAL, str(e))

    if not os.path.exists(norm_manifest):
        return _error_response(
            ErrorCode.INVALID_INPUT,
            f"Manifest file not found: {norm_manifest}",
        )

    output_dir = os.path.dirname(os.path.abspath(norm_manifest))
    try:
        manifest = load_and_validate_manifest(norm_manifest, output_directory=output_dir)
        if not manifest.output_checksums:
            return _error_response(
                ErrorCode.MANIFEST_INVALID,
                "Artifact manifest contains no output checksums; refusing to open an unverified result.",
            )
        checksum_results = verify_output_checksums(manifest, output_dir)
        failed_files = [fn for fn, ok in checksum_results.items() if not ok]
        if failed_files:
            return _error_response(
                ErrorCode.CHECKSUM_MISMATCH,
                f"Checksum verification failed for: {', '.join(failed_files)}",
            )
    except ManifestValidationError as e:
        return _error_response(ErrorCode.MANIFEST_INVALID, str(e))

    return _bridge.open_result(norm_manifest)


# ---------------------------------------------------------------------------
# Chunk streaming & interactive blocks (via local Blender bridge)
# ---------------------------------------------------------------------------

@mcp.tool()
def strata_get_chunk_streaming_status() -> dict:
    """Reads currently loaded chunk state: loaded/pinned chunks, working set
    center, and object counts from the local Blender session."""
    return _bridge.call("get_chunk_streaming_status")


@mcp.tool()
def strata_load_chunk_radius(
    center_x: int = 0,
    center_y: int = 0,
    center_z: int = 0,
    radius_x: int = 1,
    radius_y: int = 1,
    radius_z: int = 1,
) -> dict:
    """Changes the visible/loaded working set around center coordinate in Blender.

    MUTATING: Changes Blender scene visibility.
    """
    return _bridge.call(
        "load_chunk_radius",
        center_x=center_x, center_y=center_y, center_z=center_z,
        radius_x=radius_x, radius_y=radius_y, radius_z=radius_z,
    )


@mcp.tool()
def strata_set_interactive_block_state(
    object_name: str, open_state: float = 1.0
) -> dict:
    """Changes a supported block-only state (0.0=closed, 1.0=open) on an
    interactive block rig object in Blender.

    MUTATING: Changes Blender object property.
    """
    return _bridge.call(
        "set_interactive_block_state",
        object_name=object_name, open_state=open_state,
    )


@mcp.tool()
def strata_keyframe_interactive_block_state(
    object_name: str, frame: int = 1
) -> dict:
    """Keyframes a supported block-only state on an interactive block
    rig object at the specified frame in Blender.

    MUTATING: Creates Blender keyframe.
    """
    return _bridge.call(
        "keyframe_interactive_block_state",
        object_name=object_name, frame=frame,
    )


# ---------------------------------------------------------------------------
# Blender bridge pairing
# ---------------------------------------------------------------------------

@mcp.tool()
def strata_pair_blender(nonce: str = "") -> dict:
    """Completes an approved local Blender bridge pairing request, or
    returns the current pairing status if no nonce is provided.

    The Blender add-on must first create a pairing request and show the
    nonce to the user. This tool completes that specific approved request.
    It is not a generic bridge command.
    """
    if not nonce:
        return _pairing.get_status()
    result = _pairing.complete_pairing(nonce)
    if result.get("status") == "paired":
        _bridge.session_token = result.get("session_token", "")
    return result


def main():
    mcp.run()


if __name__ == "__main__":
    main()
