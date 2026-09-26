"""Blender bridge pairing flow for the Strata Connector.

Implements the single-source pairing protocol described in
docs/IMPLEMENTATION_AND_DEPLOYMENT_PLAN.md Section 5.

Blender is the sole source of pairing nonces and user approvals.
The Connector queries bridge status, forwards the user-provided
nonce to the live Blender socket, and stores the resulting session token.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from addon.bridge_auth import SessionToken
from .bridge_client import BridgeClient


class PairingState(str, Enum):
    STOPPED = "stopped"
    AWAITING_PAIRING = "awaiting_pairing"
    PAIRED = "paired"
    EXPIRED = "expired"
    ERROR = "error"


class PairingManager:
    """Manages the pairing lifecycle between the Connector and Blender bridge.

    Adopts the live state from the Blender bridge server rather than
    generating independent credentials or nonces.
    """

    def __init__(self, bridge_client: Optional[BridgeClient] = None):
        self._bridge = bridge_client or BridgeClient()

    @property
    def bridge(self) -> BridgeClient:
        return self._bridge

    @property
    def state(self) -> PairingState:
        status = self._bridge.get_pairing_status()
        raw_state = status.get("pairing_state", "stopped")
        try:
            return PairingState(raw_state)
        except ValueError:
            return PairingState.ERROR

    @property
    def session_token(self) -> Optional[SessionToken]:
        if not self._bridge.session_token:
            return None
        return SessionToken(
            token=self._bridge.session_token,
            created_at=0.0,
            expires_at=time.time() + 3600,
            session_id=getattr(self._bridge, "session_id", ""),
        )

    def complete_pairing(self, nonce: str) -> dict:
        """Forwards the nonce to the live Blender bridge to complete pairing."""
        if not nonce or not nonce.strip():
            return {
                "status": "bridge_not_paired",
                "error_code": "missing_nonce",
                "message": "A pairing nonce is required. Obtain the nonce from the Strata panel in Blender.",
            }

        response = self._bridge.pair(nonce.strip())
        if response.get("status") == "paired":
            return {
                "status": "paired",
                "message": "Successfully paired with Blender bridge.",
                "session_token": response.get("session_token", ""),
                "session_id": response.get("session_id", ""),
                "protocol_version": response.get("protocol_version", "1.0"),
                "expires_in": response.get("expires_in", 28800),
            }

        # Structured error handling
        error_code = response.get("error_code", "bridge_not_paired")
        return {
            "status": "bridge_not_paired",
            "error_code": error_code,
            "message": response.get("message", "Failed to complete pairing with Blender bridge."),
            "recovery": (
                "Open Blender, open the Strata tab in the 3D Viewport sidebar, "
                "click 'Start Strata Bridge', click 'Pair with Codex', then 'Approve Pairing'."
            ),
        }

    def get_status(self) -> dict:
        """Returns the current pairing state as reported by the Blender bridge."""
        bridge_status = self._bridge.get_pairing_status()
        raw_state = bridge_status.get("pairing_state", "stopped")
        result = {
            "pairing_state": raw_state,
            "protocol_version": bridge_status.get("protocol_version", "1.0"),
        }
        if raw_state == "paired":
            result["session_id"] = getattr(self._bridge, "session_id", "")
            result["expires_in"] = bridge_status.get("expires_in", 28800)
        elif raw_state == "awaiting_pairing":
            result["approval_required"] = bridge_status.get("approval_required", True)
            result["recovery"] = (
                "A pairing request is pending in Blender. Click 'Approve Pairing' in "
                "the Strata panel in Blender, then submit the displayed nonce to Codex."
            )
        else:
            result["recovery"] = (
                "Open Blender, go to the Strata panel in the 3D Viewport sidebar, "
                "click 'Start Strata Bridge', click 'Pair with Codex', then 'Approve Pairing'."
            )
        return result

    def invalidate(self) -> None:
        """Invalidates the local session token."""
        self._bridge.session_token = None
        self._bridge.session_id = ""
