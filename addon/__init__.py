"""Strata Toolkit — Blender add-on for AI-native Minecraft world production.

Provides the Blender-side bridge server, pairing UI, chunk streaming
operators, and interactive block state controls.

This add-on is installed in Blender and communicates with the Strata
Connector MCP server via a token-authenticated localhost bridge.
"""
from __future__ import annotations

bl_info = {
    "name": "Strata Toolkit",
    "author": "Strata",
    "version": (1, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > Strata",
    "description": "AI-native Minecraft world bridge for Codex and Strata",
    "category": "Import-Export",
}

# Guard all bpy imports — this module is also imported during non-Blender
# testing to verify it doesn't pull in engine code.
try:
    import bpy
    _IN_BLENDER = True
except ImportError:
    _IN_BLENDER = False

from .bridge_auth import generate_session_token, validate_token

# Bridge server singleton — only created when running inside Blender
_bridge_server = None


def _get_bridge_server():
    """Lazily initializes and returns the bridge server singleton."""
    global _bridge_server
    if _bridge_server is None:
        from .bridge_server import BridgeServer
        _bridge_server = BridgeServer()
    return _bridge_server


if _IN_BLENDER:
    class STRATA_OT_start_bridge(bpy.types.Operator):
        """Start the Strata bridge server."""
        bl_idname = "strata.start_bridge"
        bl_label = "Start Strata Bridge"
        bl_description = "Start the localhost bridge server for Codex communication"

        def execute(self, context):
            server = _get_bridge_server()
            if server.is_running:
                self.report({"WARNING"}, "Strata bridge is already running.")
                return {"CANCELLED"}

            # Register command handlers
            from .chunk_workflow.operators import (
                handle_get_chunk_streaming_status,
                handle_load_chunk_radius,
            )
            from .interactive_blocks.operators import (
                handle_set_interactive_block_state,
                handle_keyframe_interactive_block_state,
            )
            from .library_generator import generate_barebones_library

            server.register_handler("open_result", self._handle_open_result)
            server.register_handler(
                "get_chunk_streaming_status", handle_get_chunk_streaming_status
            )
            server.register_handler("load_chunk_radius", handle_load_chunk_radius)
            server.register_handler(
                "set_interactive_block_state", handle_set_interactive_block_state
            )
            server.register_handler(
                "keyframe_interactive_block_state",
                handle_keyframe_interactive_block_state,
            )
            server.register_handler(
                "generate_barebones_library", generate_barebones_library
            )

            server.start()
            self.report({"INFO"}, "Strata bridge started.")
            return {"FINISHED"}

        @staticmethod
        def _handle_open_result(manifest_path: str = "", **kwargs) -> dict:
            """Opens a verified result manifest in Blender."""
            from .result_loader import validate_and_open_result
            return validate_and_open_result(manifest_path)

    class STRATA_OT_stop_bridge(bpy.types.Operator):
        """Stop the Strata bridge server."""
        bl_idname = "strata.stop_bridge"
        bl_label = "Stop Strata Bridge"
        bl_description = "Stop the localhost bridge server and invalidate tokens"

        def execute(self, context):
            server = _get_bridge_server()
            server.stop()
            self.report({"INFO"}, "Strata bridge stopped.")
            return {"FINISHED"}

    class STRATA_OT_pair_codex(bpy.types.Operator):
        """Create a pairing request for Codex."""
        bl_idname = "strata.pair_codex"
        bl_label = "Pair with Codex"
        bl_description = "Create a pairing request and show the nonce for Codex"

        def execute(self, context):
            server = _get_bridge_server()
            if not server.is_running:
                self.report({"ERROR"}, "Start the bridge first.")
                return {"CANCELLED"}

            nonce = server.create_pairing_request()
            self.report({"INFO"}, f"Pairing nonce generated: {nonce}. Please approve pairing.")
            context.scene.strata_pairing_nonce = nonce
            return {"FINISHED"}

    class STRATA_OT_approve_pairing(bpy.types.Operator):
        """Approve a pending pairing request."""
        bl_idname = "strata.approve_pairing"
        bl_label = "Approve Pairing"
        bl_description = "Approve the pending pairing request from Codex"

        def execute(self, context):
            server = _get_bridge_server()
            server.approve_pairing()
            self.report({"INFO"}, "Pairing request approved. Ready for Codex connection.")
            return {"FINISHED"}

    class STRATA_PT_bridge_panel(bpy.types.Panel):
        """Strata Bridge panel in the 3D Viewport sidebar."""
        bl_label = "Strata Bridge"
        bl_idname = "STRATA_PT_bridge_panel"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Strata"

        def draw(self, context):
            layout = self.layout
            server = _get_bridge_server()

            # Status indicator
            state = server.pairing_state
            state_icons = {
                "stopped": "CANCEL",
                "awaiting_pairing": "TIME",
                "paired": "CHECKMARK",
                "expired": "ERROR",
                "error": "ERROR",
            }
            icon = state_icons.get(state, "QUESTION")
            layout.label(text=f"Bridge: {state.replace('_', ' ').title()}", icon=icon)

            # Bridge controls
            col = layout.column(align=True)
            if not server.is_running:
                col.operator("strata.start_bridge", icon="PLAY")
            else:
                col.operator("strata.stop_bridge", icon="PAUSE")

                # Pairing controls
                layout.separator()
                if state == "paired":
                    layout.label(text="Connected to Codex", icon="LINKED")
                else:
                    layout.operator("strata.pair_codex", icon="LINK_BLEND")
                    nonce = getattr(context.scene, "strata_pairing_nonce", "")
                    if nonce and server._pairing_nonce:
                        box = layout.box()
                        box.label(text=f"Nonce: {nonce}")
                        if not server._pairing_approved:
                            box.operator("strata.approve_pairing", icon="CHECKMARK")
                        else:
                            box.label(text="Approved - ready for Codex", icon="TIME")

    _classes = (
        STRATA_OT_start_bridge,
        STRATA_OT_stop_bridge,
        STRATA_OT_pair_codex,
        STRATA_OT_approve_pairing,
        STRATA_PT_bridge_panel,
    )

    def register():
        for cls in _classes:
            bpy.utils.register_class(cls)
        bpy.types.Scene.strata_pairing_nonce = bpy.props.StringProperty(
            name="Strata Pairing Nonce",
            default="",
        )

    def unregister():
        global _bridge_server
        if _bridge_server and _bridge_server.is_running:
            _bridge_server.stop()
        for cls in reversed(_classes):
            bpy.utils.unregister_class(cls)
        if hasattr(bpy.types.Scene, "strata_pairing_nonce"):
            del bpy.types.Scene.strata_pairing_nonce
        _bridge_server = None

else:
    # Outside Blender — provide no-op register/unregister
    def register():
        pass

    def unregister():
        pass
