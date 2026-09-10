"""Interactive block state operators for the Strata Blender add-on.

Handles setting and keyframing the `strata_open` custom property
on interactive block rig objects.
"""
from __future__ import annotations

from typing import Any


def handle_set_interactive_block_state(
    object_name: str = "",
    open_state: float = 1.0,
    **kwargs: Any,
) -> dict:
    """Sets the strata_open custom property on a block rig object.

    Args:
        object_name: Name of the Blender object.
        open_state: State value (0.0=closed, 1.0=open).
    """
    if not object_name:
        return {"status": "error", "message": "object_name is required."}

    try:
        import bpy
    except ImportError:
        return {
            "status": "ok",
            "message": f"Set {object_name} strata_open={open_state} (simulated).",
        }

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {
            "status": "error",
            "message": f"Object '{object_name}' not found in scene.",
        }

    # Clamp to valid range
    open_state = max(0.0, min(1.0, open_state))
    obj["strata_open"] = open_state

    return {
        "status": "ok",
        "object_name": object_name,
        "strata_open": open_state,
    }


def handle_keyframe_interactive_block_state(
    object_name: str = "",
    frame: int = 1,
    **kwargs: Any,
) -> dict:
    """Keyframes the strata_open custom property at the specified frame.

    Args:
        object_name: Name of the Blender object.
        frame: Frame number to insert the keyframe.
    """
    if not object_name:
        return {"status": "error", "message": "object_name is required."}

    try:
        import bpy
    except ImportError:
        return {
            "status": "ok",
            "message": f"Keyframed {object_name} at frame {frame} (simulated).",
        }

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        return {
            "status": "error",
            "message": f"Object '{object_name}' not found in scene.",
        }

    if "strata_open" not in obj:
        return {
            "status": "error",
            "message": f"Object '{object_name}' has no 'strata_open' property. "
                       "Set the state before keyframing.",
        }

    obj.keyframe_insert(data_path='["strata_open"]', frame=frame)

    return {
        "status": "ok",
        "object_name": object_name,
        "frame": frame,
        "strata_open": obj["strata_open"],
    }
