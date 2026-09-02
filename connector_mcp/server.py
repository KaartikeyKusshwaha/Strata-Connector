"""Strata MCP Connector — thin stdio client.

This is the local MCP server exposed to Codex and other MCP clients.
It communicates with the Private Strata API for engine work and the local
Blender bridge for scene operations.

CRITICAL: This module must NEVER import the strata engine modules.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .api_client import StrataAPIClient
from .bridge_client import BridgeClient

mcp = FastMCP("strata-connector")

_api = StrataAPIClient()
_bridge = BridgeClient()


# ---------------------------------------------------------------------------
# World inspection & build submission
# ---------------------------------------------------------------------------

@mcp.tool()
def strata_preflight_world(world_path: str) -> dict:
    """Inspects a Minecraft world save and returns build estimates without
    submitting a job. Returns block counts, chunk estimates, and missing
    asset diagnostics."""
    return _api.preflight_world(world_path)


@mcp.tool()
def strata_inspect_library(library_blend_path: str) -> dict:
    """Lists top-level object names in a block-library .blend file for
    reconciliation against Minecraft block IDs."""
    return _api.inspect_library(library_blend_path)


@mcp.tool()
def strata_submit_build(
    world_path: str,
    output_directory: str,
    library_blend_path: str = "",
    missing_asset_policy: str = "generate",
    chunk_size: int = 16,
    retention: str = "delete_after_download",
) -> dict:
    """Submits a managed build job to the private Strata engine.

    MUTATING: This uploads world data and declared assets to the private
    worker. A data-upload summary is presented before submission.
    """
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
    """Returns the current status, progress percentage, and diagnostics
    for a submitted build job."""
    return _api.get_job_status(job_id)


@mcp.tool()
def strata_download_result(job_id: str, output_directory: str) -> dict:
    """Downloads the completed build result (manifest + chunk files) to
    the specified output directory. Validates signed manifest checksums
    before making files available."""
    return _api.download_result(job_id, output_directory)


@mcp.tool()
def strata_open_result_in_blender(manifest_path: str) -> dict:
    """Opens a verified build result in the user's Blender session via
    the local bridge. Validates manifest signature before hand-off.

    MUTATING: Opens files in Blender.
    """
    return _bridge.open_result(manifest_path)


# ---------------------------------------------------------------------------
# Chunk streaming & interactive blocks (via local Blender bridge)
# ---------------------------------------------------------------------------

@mcp.tool()
def strata_get_chunk_streaming_status() -> dict:
    """Returns streaming status of loaded chunks, active working set
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
    """Loads a 3D chunk working set around center coordinate in Blender."""
    return _bridge.call(
        "load_chunk_radius",
        center_x=center_x, center_y=center_y, center_z=center_z,
        radius_x=radius_x, radius_y=radius_y, radius_z=radius_z,
    )


@mcp.tool()
def strata_set_interactive_block_state(
    object_name: str, open_state: float = 1.0
) -> dict:
    """Sets the strata_open driver property (0.0=closed, 1.0=open) on an
    interactive block rig object in Blender."""
    return _bridge.call(
        "set_interactive_block_state",
        object_name=object_name, open_state=open_state,
    )


@mcp.tool()
def strata_keyframe_interactive_block_state(
    object_name: str, frame: int = 1
) -> dict:
    """Keyframes the strata_open driver property on an interactive block
    rig object at the specified frame in Blender."""
    return _bridge.call(
        "keyframe_interactive_block_state",
        object_name=object_name, frame=frame,
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()
