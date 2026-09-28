"""Release artifact packager, signer, and installation verifier.

Packages the Strata Connector release archive, calculates SHA-256 hashes,
signs the release manifest, and verifies clean install/upgrade/uninstall.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from connector_mcp.manifest_validator import sign_manifest

VERSION = "1.1.1"
DIST_DIR = REPO_ROOT / "dist"
ARCHIVE_NAME = f"strata-connector-windows-x64-v{VERSION}.zip"
SIGNING_SECRET_ENV = "STRATA_RELEASE_SIGNING_SECRET"


def build_package() -> Path:
    signing_secret = os.environ.get(SIGNING_SECRET_ENV, "").strip()
    if not signing_secret:
        raise RuntimeError(
            f"{SIGNING_SECRET_ENV} must be set to an owner-managed signing secret; "
            "refusing to create a release signed with a public/default key."
        )
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DIST_DIR / ARCHIVE_NAME

    if archive_path.exists():
        archive_path.unlink()

    included_dirs = [
        "addon",
        "codex_plugin",
        "connector_mcp",
        "contracts",
        "reference_engine",
        "installer",
    ]
    included_files = [
        "README.md",
        "LICENSE",
        "TERMS.md",
        "PRIVACY.md",
        "pyproject.toml",
        "docs/LIVE_DEVICE_TEST_SETUP.md",
    ]

    print(f"Building release archive: {archive_path.name}")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for d in included_dirs:
            src_dir = REPO_ROOT / d
            if not src_dir.exists():
                continue
            for root, _, files in os.walk(src_dir):
                for f in files:
                    if f.endswith((".pyc", ".pyo")) or "__pycache__" in root:
                        continue
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(REPO_ROOT)
                    zf.write(full_p, rel_p.as_posix())

        for f in included_files:
            file_p = REPO_ROOT / f
            if file_p.exists():
                zf.write(file_p, f)

    # Compute SHA-256
    sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (DIST_DIR / f"{ARCHIVE_NAME}.sha256").write_text(f"{sha256}  {ARCHIVE_NAME}\n", encoding="utf-8")
    print(f"Archive SHA-256: {sha256}")

    # Build signed release manifest
    manifest_data = {
        "release_name": "strata-connector",
        "version": VERSION,
        "platform": "windows-x64",
        "archive_file": ARCHIVE_NAME,
        "archive_sha256": sha256,
        "archive_size_bytes": archive_path.stat().st_size,
        "blender_compatibility": ">=4.5.0,<5.0.0",
        "contract_version": "1.0",
    }
    signature = sign_manifest(manifest_data, signing_secret)
    manifest_data["signature"] = signature

    manifest_path = DIST_DIR / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"Signed release manifest written: {manifest_path}")

    return archive_path


def _rmtree_retry(path: Path, retries: int = 3, delay: float = 0.5):
    """Remove directory tree with retries for Windows permission issues."""
    for attempt in range(retries):
        try:
            shutil.rmtree(str(path))
            return
        except PermissionError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def verify_clean_machine_lifecycle(archive_path: Path):
    """Simulates a fresh-machine installation, upgrade check, and clean uninstallation."""
    print("Testing clean-machine installation lifecycle...")

    # Use separate directories so we don't have cwd or handle issues
    # inside the TemporaryDirectory context
    base_tmp = Path(tempfile.mkdtemp(prefix="strata_clean_test_"))
    try:
        extract_dir = base_tmp / "stage"
        target_install_dir = base_tmp / "installed_strata"
        addon_dest = base_tmp / "blender_addons"
        addon_dest.mkdir(parents=True, exist_ok=True)

        # 1. Extract release package
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)

        # 2. Run installer — import from extracted copy
        stage_str = str(extract_dir)
        if stage_str not in sys.path:
            sys.path.insert(0, stage_str)

        # Force reimport to get the extracted copy, not the repo copy
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("installer"):
                del sys.modules[mod_name]

        from installer.install import install, check_upgrade, uninstall

        result = install(
            install_dir=str(target_install_dir),
            blender_addons_dir=str(addon_dest),
            source_root=str(extract_dir),
        )
        assert result.success is True, f"Install failed: {result.message}"
        assert (target_install_dir / "bin" / "strata-mcp.cmd").exists(), \
            "Missing launcher script"
        assert (target_install_dir / "install_manifest.json").exists(), \
            "Missing install manifest"
        assert (addon_dest / "strata_toolkit" / "__init__.py").exists(), \
            "Missing Blender add-on"
        print("  -> Clean installation: PASS")

        # 3. Check upgrade compatibility
        upgrade_check = check_upgrade("1.1.1", "1.1.2")
        assert upgrade_check["compatible"] is True
        print("  -> Upgrade verification: PASS")

        # 4. Uninstall — pass both install_dir AND blender_addons_dir
        uninst_res = uninstall(
            install_dir=str(target_install_dir),
            blender_addons_dir=str(addon_dest),
        )
        assert uninst_res.success is True, f"Uninstall failed: {uninst_res.message}"

        # The install directory should be gone; allow a brief retry for Windows
        if target_install_dir.exists():
            time.sleep(0.5)
        assert not target_install_dir.exists(), \
            f"Install directory still exists after uninstall: {target_install_dir}"

        # Blender addon should be removed
        assert not (addon_dest / "strata_toolkit").exists(), \
            "Blender add-on still present after uninstall"
        print("  -> Clean uninstall: PASS")

    finally:
        # Clean up the base tmp dir
        try:
            _rmtree_retry(base_tmp)
        except Exception:
            print(f"  [WARN] Could not clean up temp dir: {base_tmp}")

    print("All clean-machine lifecycle gates PASSED.")


if __name__ == "__main__":
    archive = build_package()
    verify_clean_machine_lifecycle(archive)
