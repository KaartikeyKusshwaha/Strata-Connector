"""Tests for the signed public Engine release lane."""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import threading
import zipfile
from pathlib import Path

import pytest

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from installer.config import InstallerConfig
from installer.engine_release import canonical_release_bytes, download_engine_release
from installer.install import install


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib hook name
        pass


@pytest.fixture
def signed_release(tmp_path: Path):
    """Create a signed release served by a local HTTP server."""
    archive = tmp_path / "strata-engine-test.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for package in ("api", "blender_worker", "engine", "contracts"):
            output.writestr(f"strata-engine/{package}/__init__.py", "# test package\n")
        output.writestr("strata-engine/engine-version.txt", "2026.09.0-test\n")

    manifest = {
        "schema_version": 1,
        "product": "strata-engine",
        "engine_version": "2026.09.0",
        "platform": "windows-x64",
        "archive_file": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_size_bytes": archive.stat().st_size,
    }
    private_key = Ed25519PrivateKey.generate()
    signature = private_key.sign(canonical_release_bytes(manifest))
    manifest["signature"] = "ed25519:" + base64.b64encode(signature).decode("ascii")
    manifest_path = tmp_path / "strata-engine-release.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    handler = lambda *args, **kwargs: _QuietHandler(  # noqa: E731
        *args, directory=str(tmp_path), **kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode("ascii")
    yield {
        "url": f"http://127.0.0.1:{server.server_port}/{manifest_path.name}",
        "public_key": public_key,
    }
    server.shutdown()
    thread.join(timeout=5)


def test_signed_engine_release_download_and_extract(signed_release):
    cfg = InstallerConfig(engine_release_public_key=signed_release["public_key"])
    release = download_engine_release(
        manifest_url=signed_release["url"],
        config=cfg,
    )
    try:
        root = Path(release.root)
        assert all((root / package).is_dir() for package in ("api", "blender_worker", "engine", "contracts"))
        assert release.archive_sha256 == release.manifest["archive_sha256"]
    finally:
        from installer.engine_release import cleanup_engine_release

        cleanup_engine_release(release)


def test_installer_stages_verified_public_engine(tmp_path: Path, signed_release):
    cfg = InstallerConfig(engine_release_public_key=signed_release["public_key"])
    result = install(
        config=cfg,
        install_dir=str(tmp_path / "install"),
        install_dependencies=False,
        engine_release_manifest_url=signed_release["url"],
        auto_download_engine=True,
    )
    assert result.success is True
    manifest = json.loads((tmp_path / "install" / "install_manifest.json").read_text(encoding="utf-8"))
    assert manifest["engine_source"] == "public-release"
    assert manifest["engine_version"] == "2026.09.0"
    assert (tmp_path / "install" / "engine" / "engine-version.txt").is_file()
