"""Blender-side bridge socket server for the Strata Connector.

Runs as a daemon thread inside Blender, listening on localhost:9877.
Dispatches incoming JSON commands to Blender operators via the
token-authenticated bridge protocol.

This module is only imported inside Blender's Python environment.
"""
from __future__ import annotations

import hmac
import json
import socket
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from .bridge_auth import (
    SessionToken,
    TokenExpiredError,
    TokenInvalidError,
    generate_session_token,
    validate_token,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9877
PROTOCOL_VERSION = "1.0"

# Commands that do not require a session token
_PAIRING_COMMANDS = {"pair", "get_pairing_status"}


class BridgeServer:
    """Token-authenticated JSON bridge server running inside Blender."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ):
        self.host = host
        self.port = port
        self._session_token: Optional[SessionToken] = None
        self._pairing_nonce: Optional[str] = None
        self._pairing_approved: bool = False
        self._pairing_expires_at: float = 0.0
        self._session_id: str = ""
        self._server_socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._handlers: Dict[str, Callable] = {}
        try:
            from .result_loader import validate_and_open_result
            self._handlers["open_result"] = validate_and_open_result
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paired(self) -> bool:
        return (
            self._session_token is not None
            and not self._session_token.is_expired()
        )

    @property
    def pairing_state(self) -> str:
        if not self._running:
            return "stopped"
        if self._session_token and self._session_token.is_expired():
            return "expired"
        if self.is_paired:
            return "paired"
        if self._pairing_nonce:
            if time.time() > self._pairing_expires_at:
                return "expired"
            return "awaiting_pairing"
        return "awaiting_pairing"

    def register_handler(self, command: str, handler: Callable) -> None:
        """Registers a command handler function."""
        self._handlers[command] = handler

    def create_pairing_request(self, ttl_seconds: int = 300) -> str:
        """Creates a pairing request and returns the nonce."""
        self._pairing_nonce = uuid.uuid4().hex[:16]
        self._pairing_approved = False
        self._pairing_expires_at = time.time() + ttl_seconds
        self._session_id = uuid.uuid4().hex[:12]
        return self._pairing_nonce

    def approve_pairing(self) -> None:
        """Approves the current pairing request (called from Blender UI)."""
        self._pairing_approved = True

    def start(self) -> None:
        """Starts the bridge server in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._serve, daemon=True, name="StrataBridge"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stops the bridge server and invalidates tokens."""
        self._running = False
        self._session_token = None
        self._pairing_nonce = None
        self._pairing_approved = False
        self._pairing_expires_at = 0.0
        self._session_id = ""
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass

    def _serve(self) -> None:
        """Main server loop."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        try:
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(1)
        except OSError:
            self._running = False
            return

        while self._running:
            try:
                conn, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                self._handle_connection(conn)
            except Exception:
                pass
            finally:
                conn.close()

        try:
            self._server_socket.close()
        except OSError:
            pass

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handles a single client connection."""
        conn.settimeout(10)
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        if not data:
            return

        try:
            request = json.loads(data.decode("utf-8").strip())
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {"status": "error", "message": "Malformed JSON request."}
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
            return

        command = request.get("command", "")

        # Pairing commands don't require a token
        if command in _PAIRING_COMMANDS:
            response = self._handle_pairing(request)
        else:
            # Validate session token
            token_str = request.get("session_token", "")
            if not self._session_token:
                response = {
                    "status": "bridge_not_paired",
                    "error_code": "bridge_not_paired",
                    "message": "Bridge is not paired. Click 'Pair with Codex' in Blender and approve pairing.",
                }
            else:
                try:
                    validate_token(token_str, self._session_token)
                    response = self._dispatch(command, request)
                except TokenInvalidError as e:
                    response = {
                        "status": "bridge_not_paired",
                        "error_code": "token_invalid",
                        "message": str(e),
                    }
                except TokenExpiredError as e:
                    response = {
                        "status": "bridge_not_paired",
                        "error_code": "token_expired",
                        "message": str(e),
                        "recovery": "Restart the bridge and pair again.",
                    }

        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))

    def _handle_pairing(self, request: dict) -> dict:
        """Handles pairing-related commands."""
        command = request.get("command", "")

        if command == "get_pairing_status":
            return {
                "status": "ok",
                "pairing_state": self.pairing_state,
                "approval_required": bool(self._pairing_nonce and not self._pairing_approved),
                "protocol_version": PROTOCOL_VERSION,
                "session_id": self._session_id,
                "has_active_request": bool(self._pairing_nonce and time.time() <= self._pairing_expires_at),
            }

        if command == "pair":
            nonce = request.get("nonce", "")
            if not nonce:
                return self._handle_pairing({"command": "get_pairing_status"})

            if not self._pairing_nonce:
                return {
                    "status": "error",
                    "error_code": "no_pairing_request",
                    "message": "No active pairing request in Blender. Click 'Pair with Codex' in Blender first.",
                }

            if time.time() > self._pairing_expires_at:
                self._pairing_nonce = None
                self._pairing_approved = False
                return {
                    "status": "error",
                    "error_code": "pairing_expired",
                    "message": "Pairing request has expired in Blender. Click 'Pair with Codex' in Blender again.",
                }

            if not self._pairing_approved:
                return {
                    "status": "error",
                    "error_code": "approval_required",
                    "message": "Pairing request has not been approved in Blender. Click 'Approve Pairing' in Blender.",
                }

            if not hmac.compare_digest(str(nonce), str(self._pairing_nonce)):
                return {
                    "status": "error",
                    "error_code": "nonce_mismatch",
                    "message": "Pairing nonce does not match the active Blender request.",
                }

            # Generate session token and consume nonce once
            self._session_token = generate_session_token(session_id=self._session_id)
            self._pairing_nonce = None
            self._pairing_approved = False
            return {
                "status": "paired",
                "session_token": self._session_token.token,
                "session_id": self._session_id,
                "protocol_version": PROTOCOL_VERSION,
                "expires_in": max(0, int(self._session_token.expires_at - time.time())),
            }

        return {"status": "error", "message": f"Unknown pairing command: {command}"}

    def _dispatch(self, command: str, request: dict) -> dict:
        """Dispatches an authenticated command to its handler."""
        handler = self._handlers.get(command)
        if not handler:
            return {"status": "error", "message": f"Unknown command: {command}"}

        # Remove protocol fields, pass remaining as kwargs
        kwargs = {k: v for k, v in request.items()
                  if k not in ("command", "session_token")}
        try:
            return handler(**kwargs)
        except Exception as e:
            return {"status": "error", "message": str(e)}
