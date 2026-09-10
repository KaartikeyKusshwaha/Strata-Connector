"""Blender bridge pairing flow for the Strata Connector.

Implements the explicit pairing protocol described in CODEX_PLUGIN_PLAN.md
Section 7. The connector creates a short-lived pairing request; the Blender
add-on approves it; the connector completes pairing and stores the ephemeral
session capability token.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from addon.bridge_auth import generate_session_token, SessionToken


class PairingState(str, Enum):
    STOPPED = "stopped"
    AWAITING_PAIRING = "awaiting_pairing"
    PAIRED = "paired"
    EXPIRED = "expired"
    ERROR = "error"


# Default pairing request lifetime: 5 minutes
DEFAULT_PAIRING_TTL_SECONDS = 300


@dataclass
class PairingRequest:
    """A short-lived, one-time local pairing request."""
    nonce: str
    created_at: float
    expires_at: float
    consumed: bool = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def is_valid(self) -> bool:
        return not self.consumed and not self.is_expired()


class PairingManager:
    """Manages the pairing lifecycle between the Connector and Blender bridge."""

    def __init__(self):
        self._state: PairingState = PairingState.STOPPED
        self._current_request: Optional[PairingRequest] = None
        self._session_token: Optional[SessionToken] = None
        self._error_message: str = ""

    @property
    def state(self) -> PairingState:
        # Auto-detect expiry
        if self._state == PairingState.PAIRED and self._session_token:
            if self._session_token.is_expired():
                self._state = PairingState.EXPIRED
        if self._state == PairingState.AWAITING_PAIRING and self._current_request:
            if self._current_request.is_expired():
                self._state = PairingState.EXPIRED
        return self._state

    @property
    def session_token(self) -> Optional[SessionToken]:
        return self._session_token

    def create_pairing_request(
        self, ttl_seconds: int = DEFAULT_PAIRING_TTL_SECONDS
    ) -> PairingRequest:
        """Creates a new short-lived pairing request with a random nonce."""
        nonce = uuid.uuid4().hex[:16]
        now = time.time()
        self._current_request = PairingRequest(
            nonce=nonce,
            created_at=now,
            expires_at=now + ttl_seconds,
        )
        self._state = PairingState.AWAITING_PAIRING
        self._error_message = ""
        return self._current_request

    def complete_pairing(self, nonce: str) -> dict:
        """Completes pairing if the nonce matches an active request.

        Returns a structured result dict.
        """
        if self._current_request is None:
            return {
                "status": "bridge_not_paired",
                "message": "No pairing request is active. Start pairing from the Blender add-on first.",
            }

        if self._current_request.consumed:
            return {
                "status": "bridge_not_paired",
                "message": "Pairing request has already been used. Create a new pairing request.",
            }

        if self._current_request.is_expired():
            self._state = PairingState.EXPIRED
            return {
                "status": "bridge_not_paired",
                "message": "Pairing request has expired. Create a new pairing request from Blender.",
            }

        if nonce != self._current_request.nonce:
            return {
                "status": "bridge_not_paired",
                "message": "Pairing nonce does not match. Verify and retry.",
            }

        # Success: consume the request and generate a session token
        self._current_request.consumed = True
        self._session_token = generate_session_token()
        self._state = PairingState.PAIRED
        return {
            "status": "paired",
            "message": "Successfully paired with Blender bridge.",
            "session_token": self._session_token.token,
            "expires_in": int(self._session_token.expires_at - time.time()),
        }

    def get_status(self) -> dict:
        """Returns the current pairing state as a structured dict."""
        state = self.state  # triggers auto-expiry check
        result = {
            "pairing_state": state.value,
        }
        if state == PairingState.PAIRED and self._session_token:
            result["expires_in"] = max(0, int(self._session_token.expires_at - time.time()))
        if state == PairingState.ERROR:
            result["error"] = self._error_message
        if state in (PairingState.EXPIRED, PairingState.STOPPED, PairingState.ERROR):
            result["recovery"] = (
                "Open Blender, go to the Strata panel in the N-panel sidebar, "
                "click 'Start Strata Bridge', then 'Pair with Codex'."
            )
        return result

    def invalidate(self) -> None:
        """Invalidates the current session (bridge restart, disconnect, etc.)."""
        self._session_token = None
        self._current_request = None
        self._state = PairingState.STOPPED
