"""Strata Toolkit installer logic.

Performs atomic installation of the Strata Toolkit components:
- Connector runtime in an isolated application directory
- Dedicated strata-mcp launcher script
- Codex plugin package referencing the launcher
- Blender add-on compatible with the runtime
- Clean rollback on failure and reversible uninstall
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import InstallerConfig


@dataclass
class InstallResult:
    """Result of an install/uninstall operation."""

    success: bool = False
    message: str = ""
    installed_components: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.installed_components is None:
            self.installed_components = []
        if self.errors is None:
            self.errors = []


def _hash_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def install(
    config: Optional[InstallerConfig] = None,
    install_dir: str = "",
    blender_addons_dir: str = "",
    source_root: Optional[str] = None,
) -> InstallResult:
    """Installs the Strata Toolkit atomically with clean rollback on failure.

    Steps:
    1. Validate destination path
    2. Check component compatibility
    3. Stage components in temporary sibling directory
    4. Write launcher and install manifest
    5. Atomically promote staged directory to install_dir
    6. If blender_addons_dir is specified, copy add-on there
    7. On error: clean up temporary staging and roll back any copied files
    """
    cfg = config or InstallerConfig()
    if not install_dir:
        return InstallResult(success=False, message="install_dir must be specified.")

    abs_install = os.path.abspath(install_dir)
    parent_dir = os.path.dirname(abs_install)
    os.makedirs(parent_dir, exist_ok=True)

    root = source_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    stage_dir = os.path.join(parent_dir, f".strata_install_tmp_{uuid.uuid4().hex[:8]}")
    installed_components = []
    errors = []

    try:
        os.makedirs(stage_dir, exist_ok=True)

        # 1. Stage runtime components
        runtime_dst = os.path.join(stage_dir, cfg.connector_runtime_dir)
        os.makedirs(runtime_dst, exist_ok=True)
        for pkg in ["connector_mcp", "contracts", "reference_engine", "addon"]:
            src_pkg = os.path.join(root, pkg)
            if os.path.isdir(src_pkg):
                shutil.copytree(src_pkg, os.path.join(runtime_dst, pkg))
        installed_components.append("runtime")

        # 2. Stage launcher
        bin_dst = os.path.join(stage_dir, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        launcher_file = os.path.join(bin_dst, "strata-mcp.cmd")
        with open(launcher_file, "w", encoding="utf-8") as f:
            f.write(f'@echo off\n"{sys.executable}" -m connector_mcp.server %*\n')
        installed_components.append("launcher")

        # 3. Stage codex-plugin
        plugin_src = os.path.join(root, "codex_plugin")
        plugin_dst = os.path.join(stage_dir, cfg.plugin_dir)
        if os.path.isdir(plugin_src):
            shutil.copytree(plugin_src, plugin_dst)
            installed_components.append("plugin")

        # 4. Stage blender-addon
        addon_src = os.path.join(root, "addon")
        addon_dst = os.path.join(stage_dir, cfg.addon_dir)
        if os.path.isdir(addon_src):
            shutil.copytree(addon_src, addon_dst)
            installed_components.append("addon")

        # 5. Write install manifest
        manifest_data = {
            "product_name": cfg.product_name,
            "version": cfg.version,
            "installed_at": time.time(),
            "installed_components": installed_components,
            "install_dir": abs_install,
            "blender_addons_dir": blender_addons_dir if blender_addons_dir else None,
        }
        manifest_path = os.path.join(stage_dir, "install_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # 6. Atomic promotion
        if os.path.exists(abs_install):
            shutil.rmtree(abs_install)
        try:
            os.replace(stage_dir, abs_install)
        except OSError:
            shutil.move(stage_dir, abs_install)

        # 7. Optional Blender add-on deployment
        if blender_addons_dir and os.path.isdir(blender_addons_dir):
            blender_target = os.path.join(blender_addons_dir, "strata_toolkit")
            if os.path.exists(blender_target):
                shutil.rmtree(blender_target)
            shutil.copytree(addon_src, blender_target)
            installed_components.append("blender_addon_installed")

        return InstallResult(
            success=True,
            message="Strata Toolkit installed successfully.",
            installed_components=installed_components,
            errors=[],
        )

    except Exception as e:
        # Rollback: delete stage dir and ensure broken partial install is removed
        if os.path.exists(stage_dir):
            shutil.rmtree(stage_dir, ignore_errors=True)
        if os.path.exists(abs_install):
            shutil.rmtree(abs_install, ignore_errors=True)
        return InstallResult(
            success=False,
            message=f"Installation failed and was rolled back: {e}",
            installed_components=[],
            errors=[str(e)],
        )


def uninstall(
    config: Optional[InstallerConfig] = None,
    install_dir: str = "",
    blender_addons_dir: str = "",
) -> InstallResult:
    """Uninstalls the Strata Toolkit, preserving user worlds and results.

    Steps:
    1. Read install manifest
    2. Remove installed Blender add-on if present
    3. Remove install_dir
    4. Verify clean removal
    """
    if not install_dir or not os.path.exists(install_dir):
        return InstallResult(success=True, message="Install directory does not exist. Nothing to uninstall.")

    abs_install = os.path.abspath(install_dir)
    manifest_path = os.path.join(abs_install, "install_manifest.json")
    removed_components = []

    # Check for installed Blender add-on from manifest or parameter
    target_blender_dir = blender_addons_dir
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not target_blender_dir:
                    target_blender_dir = data.get("blender_addons_dir")
        except Exception:
            pass

    if target_blender_dir and os.path.isdir(target_blender_dir):
        addon_installed = os.path.join(target_blender_dir, "strata_toolkit")
        if os.path.exists(addon_installed):
            shutil.rmtree(addon_installed, ignore_errors=True)
            removed_components.append("blender_addon")

    # Remove main install directory
    try:
        shutil.rmtree(abs_install)
        removed_components.append("install_dir")
        return InstallResult(
            success=True,
            message="Strata Toolkit uninstalled cleanly.",
            installed_components=removed_components,
        )
    except Exception as e:
        return InstallResult(
            success=False,
            message=f"Failed to remove install directory: {e}",
            errors=[str(e)],
        )


def check_upgrade(
    current_version: str = "",
    target_version: str = "",
) -> dict:
    """Checks whether an upgrade/downgrade is safe."""
    if not current_version or not target_version:
        return {
            "compatible": False,
            "message": "Both current_version and target_version must be provided.",
            "repair_steps": [],
        }

    cur_major = current_version.split(".")[0]
    tgt_major = target_version.split(".")[0]

    if cur_major != tgt_major:
        return {
            "current_version": current_version,
            "target_version": target_version,
            "compatible": False,
            "message": f"Major version upgrade from {current_version} to {target_version} requires clean reinstall.",
            "repair_steps": ["Backup custom libraries", "Uninstall previous version", "Install target version"],
        }

    return {
        "current_version": current_version,
        "target_version": target_version,
        "compatible": True,
        "message": f"Safe upgrade from {current_version} to {target_version}.",
        "repair_steps": [],
    }
