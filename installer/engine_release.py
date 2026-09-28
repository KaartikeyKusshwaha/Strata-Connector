"""Download and verify a signed public Strata Engine distribution.

The Engine source remains in its separate private repository.  A release
workflow publishes only a signed, platform-specific runtime archive to the
public Connector releases.  The installer verifies the signed release
metadata and archive checksum before extracting anything into the install
directory.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .config import InstallerConfig


class EngineReleaseError(RuntimeError):
    """Raised when a public Engine release cannot be trusted or staged."""


@dataclass(frozen=True)
class EngineRelease:
    """Verified Engine release metadata and extracted temporary root."""

    root: str
    manifest: dict[str, Any]
    archive_sha256: str


def canonical_release_bytes(manifest: dict[str, Any]) -> bytes:
    """Return canonical bytes for the release signature."""
    payload = {key: value for key, value in manifest.items() if key != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _ensure_ed25519() -> Any:
    """Load cryptography, bootstrapping it into a temporary directory if needed.

    The release installer already installs Python dependencies.  Bootstrapping
    only this verifier keeps a clean source/archive install safe even when the
    host Python does not yet have ``cryptography`` available.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        return Ed25519PublicKey
    except ImportError:
        bootstrap = Path(tempfile.mkdtemp(prefix="strata_release_crypto_"))
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                    "--target",
                    str(bootstrap),
                    "cryptography>=41,<47",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            sys.path.insert(0, str(bootstrap))
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            return Ed25519PublicKey
        except Exception as exc:
            shutil.rmtree(bootstrap, ignore_errors=True)
            raise EngineReleaseError(
                "The signed Engine release requires cryptography; bootstrap failed. "
                "Install the Connector dependencies and retry."
            ) from exc


def verify_release_signature(manifest: dict[str, Any], public_key_b64: str) -> None:
    """Verify the Ed25519 signature in a release manifest."""
    signature = str(manifest.get("signature", ""))
    if not signature.startswith("ed25519:"):
        raise EngineReleaseError("Engine release manifest has no Ed25519 signature.")
    try:
        signature_bytes = base64.b64decode(signature.split(":", 1)[1], validate=True)
        key_bytes = base64.b64decode(public_key_b64, validate=True)
        if len(signature_bytes) != 64 or len(key_bytes) != 32:
            raise EngineReleaseError("Engine release signature/key has an invalid length.")
        Ed25519PublicKey = _ensure_ed25519()
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(
            signature_bytes, canonical_release_bytes(manifest)
        )
    except Exception as exc:
        raise EngineReleaseError("Engine release signature verification failed.") from exc


def _download(url: str, destination: Path, max_bytes: int) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Strata-Toolkit-Installer/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                raise EngineReleaseError("Engine release archive exceeds the configured size limit.")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise EngineReleaseError("Engine release archive exceeds the configured size limit.")
                output.write(chunk)
    except EngineReleaseError:
        raise
    except Exception as exc:
        raise EngineReleaseError(f"Could not download Engine release from {url}: {exc}") from exc


def _safe_extract(zip_path: Path, destination: Path, max_members: int = 100_000) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise EngineReleaseError("Engine release contains too many archive members.")
        root = destination.resolve()
        for member in members:
            name = member.filename.replace("\\", "/")
            path = Path(name)
            if not name or path.is_absolute() or ".." in path.parts:
                raise EngineReleaseError(f"Unsafe Engine archive path: {member.filename!r}")
            # Refuse Unix symlink entries even when extracted on Windows.
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise EngineReleaseError(f"Symlink entries are not allowed: {member.filename!r}")
            target = (destination / path).resolve()
            if root not in target.parents and target != root:
                raise EngineReleaseError(f"Engine archive escapes extraction root: {member.filename!r}")
        archive.extractall(destination)


def _validate_engine_root(root: Path) -> None:
    required = ("api", "blender_worker", "engine", "contracts")
    missing = [name for name in required if not (root / name).is_dir()]
    if missing:
        raise EngineReleaseError(
            "Downloaded Engine release is missing required packages: " + ", ".join(missing)
        )


def download_engine_release(
    manifest_url: str = "",
    config: Optional[InstallerConfig] = None,
    public_key_b64: str = "",
    platform: str = "windows-x64",
) -> EngineRelease:
    """Download, verify, and extract the configured Engine release.

    The returned root is a temporary directory owned by the caller.  The
    installer copies it into its atomic staging directory and removes it in a
    ``finally`` block.
    """
    cfg = config or InstallerConfig()
    manifest_url = (manifest_url or os.environ.get("STRATA_ENGINE_RELEASE_MANIFEST_URL", "")).strip()
    manifest_url = manifest_url or cfg.engine_release_manifest_url
    public_key_b64 = (public_key_b64 or os.environ.get("STRATA_ENGINE_RELEASE_PUBLIC_KEY", "")).strip()
    public_key_b64 = public_key_b64 or cfg.engine_release_public_key
    if not manifest_url or not public_key_b64:
        raise EngineReleaseError(
            "No Engine release manifest URL/public key is configured. "
            "Use --engine-root or configure the signed public release lane."
        )

    max_bytes = int(os.environ.get("STRATA_ENGINE_RELEASE_MAX_BYTES", str(2 * 1024**3)))
    work_root = Path(tempfile.mkdtemp(prefix="strata_engine_release_"))
    try:
        manifest_path = work_root / "strata-engine-release.json"
        _download(manifest_url, manifest_path, max_bytes=2 * 1024 * 1024)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EngineReleaseError("Engine release manifest is not valid JSON.") from exc
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise EngineReleaseError("Unsupported Engine release manifest schema.")
        if manifest.get("platform") != platform:
            raise EngineReleaseError(
                f"Engine release platform {manifest.get('platform')!r} is not {platform!r}."
            )
        def version_tuple(value: str) -> tuple[int, ...]:
            parts = []
            for item in value.split("."):
                digits = "".join(ch for ch in item if ch.isdigit())
                parts.append(int(digits or "0"))
            return tuple(parts)

        if version_tuple(str(manifest.get("engine_version", ""))) < version_tuple(cfg.min_engine_version):
            raise EngineReleaseError("Engine release is older than the Connector compatibility floor.")
        verify_release_signature(manifest, public_key_b64)

        asset_name = str(manifest.get("archive_file", ""))
        expected_hash = str(manifest.get("archive_sha256", "")).lower()
        if not asset_name or Path(asset_name).name != asset_name or not expected_hash:
            raise EngineReleaseError("Engine release manifest has invalid archive metadata.")
        archive_url = urllib.parse.urljoin(manifest_url, asset_name)
        archive_path = work_root / asset_name
        _download(archive_url, archive_path, max_bytes=max_bytes)
        declared_size = manifest.get("archive_size_bytes")
        if declared_size is not None and int(declared_size) != archive_path.stat().st_size:
            raise EngineReleaseError("Engine release archive size does not match its manifest.")
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if digest != expected_hash:
            raise EngineReleaseError("Engine release archive SHA-256 verification failed.")
        extracted = work_root / "engine"
        _safe_extract(archive_path, extracted)
        # Archives may contain a single top-level directory for clean release
        # packaging; normalize that layout before validation/copying.
        candidate = extracted
        if not (candidate / "api").is_dir():
            children = [path for path in extracted.iterdir() if path.is_dir()]
            if len(children) == 1:
                candidate = children[0]
        _validate_engine_root(candidate)
        return EngineRelease(root=str(candidate), manifest=manifest, archive_sha256=digest)
    except Exception:
        shutil.rmtree(work_root, ignore_errors=True)
        raise


def cleanup_engine_release(release: Optional[EngineRelease]) -> None:
    """Remove the temporary parent directory created for a release."""
    if not release:
        return
    path = Path(release.root).resolve()
    for parent in (path, *path.parents):
        if parent.name.startswith("strata_engine_release_"):
            shutil.rmtree(parent, ignore_errors=True)
            return
