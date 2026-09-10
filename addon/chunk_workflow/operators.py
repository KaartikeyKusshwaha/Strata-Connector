"""Chunk streaming operators for the Strata Blender add-on.

Handles chunk visibility toggling and working set management
using the 3D A1 chunk naming convention.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _chunk_name(cx: int, cy: int, cz: int) -> str:
    """Generates a chunk collection name from coordinates.

    Uses the 3D A1 naming convention:
    Chunk_x<p|m><cx>_y<p|m><cy>_z<p|m><cz>
    """
    def _coord(val: int, axis: str) -> str:
        sign = "p" if val >= 0 else "m"
        return f"{axis}{sign}{abs(val):03d}"

    return f"Chunk_{_coord(cx, 'x')}_{_coord(cy, 'y')}_{_coord(cz, 'z')}"


def handle_get_chunk_streaming_status(**kwargs: Any) -> dict:
    """Returns the current chunk streaming state.

    When running outside Blender, returns a stub response.
    """
    try:
        import bpy
        # Scan scene collections for Strata chunk collections
        loaded_chunks: List[str] = []
        pinned_chunks: List[str] = []

        for collection in bpy.data.collections:
            if collection.name.startswith("Chunk_"):
                loaded_chunks.append(collection.name)
                if not collection.hide_viewport:
                    pinned_chunks.append(collection.name)

        return {
            "status": "ok",
            "loaded_chunks": loaded_chunks,
            "pinned_chunks": pinned_chunks,
            "working_set_center": [0, 0, 0],
            "total_object_count": len(bpy.data.objects),
            "visible_object_count": sum(
                1 for obj in bpy.data.objects if obj.visible_get()
            ),
        }
    except ImportError:
        return {
            "status": "ok",
            "loaded_chunks": [],
            "pinned_chunks": [],
            "working_set_center": [0, 0, 0],
            "total_object_count": 0,
            "visible_object_count": 0,
        }


def handle_load_chunk_radius(
    center_x: int = 0,
    center_y: int = 0,
    center_z: int = 0,
    radius_x: int = 1,
    radius_y: int = 1,
    radius_z: int = 1,
    **kwargs: Any,
) -> dict:
    """Loads/shows chunks within the specified radius around a center point.

    Hides chunks outside the radius and shows chunks within it.
    """
    try:
        import bpy
    except ImportError:
        return {
            "status": "ok",
            "message": "Chunk loading simulated (not in Blender).",
            "center": [center_x, center_y, center_z],
            "radius": [radius_x, radius_y, radius_z],
        }

    # Compute which chunk names should be visible
    visible_names = set()
    for cx in range(center_x - radius_x, center_x + radius_x + 1):
        for cy in range(center_y - radius_y, center_y + radius_y + 1):
            for cz in range(center_z - radius_z, center_z + radius_z + 1):
                visible_names.add(_chunk_name(cx, cy, cz))

    shown = []
    hidden = []
    for collection in bpy.data.collections:
        if not collection.name.startswith("Chunk_"):
            continue
        if collection.name in visible_names:
            collection.hide_viewport = False
            collection.hide_render = False
            shown.append(collection.name)
        else:
            collection.hide_viewport = True
            collection.hide_render = True
            hidden.append(collection.name)

    return {
        "status": "ok",
        "center": [center_x, center_y, center_z],
        "radius": [radius_x, radius_y, radius_z],
        "shown_chunks": shown,
        "hidden_chunks": hidden,
    }
