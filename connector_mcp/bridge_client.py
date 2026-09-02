"""Local Blender bridge client for the Strata connector.

Communicates with the Blender add-on's localhost bridge using
per-session token-authenticated JSON commands.
"""
from __future__ import annotations

import json
import socket
from typing import Any, Dict, Optional


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9877


class BridgeClient:
    """Sends token-authenticated commands to the Blender bridge."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        session_token: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.session_token = session_token

    def call(self, command: str, **kwargs: Any) -> dict:
        """Sends a named command to the Blender bridge and returns the response."""
        payload = {
            "command": command,
            "session_token": self.session_token or "",
            **kwargs,
        }
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as sock:
                sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
                data = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                return json.loads(data.decode("utf-8").strip())
        except (ConnectionRefusedError, TimeoutError, OSError):
            return {
                "status": "bridge_unavailable",
                "message": f"Cannot connect to Blender bridge at {self.host}:{self.port}. "
                           "Ensure Blender is running and the Strata bridge is started.",
            }

    def open_result(self, manifest_path: str) -> dict:
        """Opens a verified build result in Blender via the bridge."""
        return self.call("open_result", manifest_path=manifest_path)
