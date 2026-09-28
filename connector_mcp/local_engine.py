"""Local Strata Engine supervisor.

The public Connector can run the private Engine locally when an authorised
Engine bundle is supplied at install time. The supervisor starts the API and
worker on a loopback-only port, shares a private job root, and tears both
processes down with the MCP process. No public endpoint or cloud service is
required.
"""
from __future__ import annotations

import atexit
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


class LocalEngineError(RuntimeError):
    """Raised when the local Engine cannot be started or becomes unhealthy."""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _blender_executable() -> str:
    configured = os.environ.get("STRATA_BLENDER_EXE", "").strip()
    if configured and os.path.isfile(configured):
        return configured
    discovered = shutil.which("blender") or shutil.which("blender.exe")
    if discovered:
        return discovered
    candidates = (
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    )
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ""


class LocalEngineSupervisor:
    """Own the local Engine API and worker subprocesses for one MCP session."""

    def __init__(self, engine_root: Optional[str] = None):
        raw_root = (
            engine_root
            or os.environ.get("STRATA_ENGINE_ROOT", "")
            or os.environ.get("STRATA_LOCAL_ENGINE_ROOT", "")
        ).strip()
        if not raw_root:
            raise LocalEngineError(
                "Local Engine mode requires STRATA_ENGINE_ROOT or an installed engine bundle."
            )
        self.engine_root = Path(raw_root).expanduser().resolve()
        self.port = int(os.environ.get("STRATA_LOCAL_ENGINE_PORT", "0")) or _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.api_process: Optional[subprocess.Popen] = None
        self.worker_process: Optional[subprocess.Popen] = None
        self.data_root = Path(
            os.environ.get(
                "STRATA_LOCAL_ENGINE_DATA",
                os.path.join(
                    os.environ.get("LOCALAPPDATA", str(Path.home())),
                    "Strata",
                    "local-engine-data",
                ),
            )
        ).expanduser()
        self.log_root = self.data_root / "logs"

    def _validate_root(self) -> None:
        required = ("api", "blender_worker", "engine", "contracts")
        missing = [name for name in required if not (self.engine_root / name).is_dir()]
        if missing:
            raise LocalEngineError(
                f"Invalid local Engine bundle {self.engine_root}; missing: {', '.join(missing)}"
            )

    def _environment(self) -> dict[str, str]:
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.log_root.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["STRATA_JOB_ROOT"] = str(self.data_root)
        env["STRATA_REQUIRE_SIGNING"] = "true"
        env["STRATA_REQUIRE_WORKER"] = "true"
        env.setdefault("STRATA_MANIFEST_SIGNING_SECRET", secrets.token_urlsafe(48))
        env.setdefault("STRATA_ENROLLMENT_KEY", secrets.token_urlsafe(48))
        env.setdefault("STRATA_SIGNING_KEYS", env["STRATA_MANIFEST_SIGNING_SECRET"])
        blender = _blender_executable()
        if blender:
            env.setdefault("STRATA_BLENDER_EXE", blender)
        python_path = str(self.engine_root)
        if env.get("PYTHONPATH"):
            python_path += os.pathsep + env["PYTHONPATH"]
        env["PYTHONPATH"] = python_path
        return env

    @staticmethod
    def _creation_flags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _start_processes(self, env: dict[str, str]) -> None:
        self._validate_root()
        python = os.environ.get("STRATA_ENGINE_PYTHON", "").strip() or sys.executable
        api_log = open(self.log_root / "api.log", "a", encoding="utf-8")
        worker_log = open(self.log_root / "worker.log", "a", encoding="utf-8")
        try:
            self.api_process = subprocess.Popen(
                [
                    python,
                    "-m",
                    "uvicorn",
                    "api.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(self.port),
                ],
                cwd=str(self.engine_root),
                env=env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
                creationflags=self._creation_flags(),
            )
            self.worker_process = subprocess.Popen(
                [python, "-m", "blender_worker.service"],
                cwd=str(self.engine_root),
                env=env,
                stdout=worker_log,
                stderr=subprocess.STDOUT,
                creationflags=self._creation_flags(),
            )
            api_log.close()
            worker_log.close()
        except Exception:
            api_log.close()
            worker_log.close()
            self.stop()
            raise

    def _ready(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/readyz", timeout=2) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False

    def start(self) -> str:
        if self.api_process and self.api_process.poll() is None and self._ready():
            return self.base_url
        env = self._environment()
        self._start_processes(env)
        timeout = float(os.environ.get("STRATA_LOCAL_ENGINE_START_TIMEOUT", "60"))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.api_process and self.api_process.poll() is not None:
                raise LocalEngineError("Local Engine API exited during startup; see api.log.")
            if self.worker_process and self.worker_process.poll() is not None:
                raise LocalEngineError("Local Engine worker exited during startup; see worker.log.")
            if self._ready():
                atexit.register(self.stop)
                os.environ.update(
                    {
                        "STRATA_API_URL": self.base_url,
                        "STRATA_ENROLLMENT_KEY": env["STRATA_ENROLLMENT_KEY"],
                        "STRATA_SIGNING_KEYS": env["STRATA_SIGNING_KEYS"],
                    }
                )
                return self.base_url
            time.sleep(0.25)
        self.stop()
        raise LocalEngineError(
            f"Local Engine did not become ready within {timeout:g}s; inspect {self.log_root}."
        )

    def stop(self) -> None:
        for process in (self.worker_process, self.api_process):
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        self.worker_process = None
        self.api_process = None
