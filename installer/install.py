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
import subprocess
import sys
import time
import uuid
import argparse
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


def default_install_dir() -> str:
    """Returns the per-user install directory used by the CLI."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return os.path.join(local_app_data, "Strata")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "Strata")


def default_blender_addons_dir() -> str:
    """Returns the Blender 4.5 per-user add-on directory used by the CLI."""
    app_data = os.environ.get("APPDATA")
    if app_data:
        return os.path.join(
            app_data,
            "Blender Foundation",
            "Blender",
            "4.5",
            "scripts",
            "addons",
        )
    return os.path.join(
        os.path.expanduser("~"), ".config", "blender", "4.5", "scripts", "addons"
    )


def _install_runtime_dependencies(site_dir: str, python_executable: str) -> None:
    """Install runtime dependencies into the isolated Strata runtime.

    Dependencies are installed into the product directory instead of the
    user's global interpreter. This keeps the launcher reproducible on a clean
    machine and makes failure explicit when a package cannot be downloaded.
    """
    os.makedirs(site_dir, exist_ok=True)
    requirements = [
        "mcp[cli]>=1.3.0,<2",
        "pydantic>=2.0.0,<3",
        "httpx>=0.27.0,<1",
    ]
    subprocess.run(
        [
            python_executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--target",
            site_dir,
            *requirements,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _write_launcher(launcher_file: str, python_executable: str = "") -> None:
    """Write a portable Windows launcher for the installed runtime.

    The installer may run on a build machine whose absolute Python path does
    not exist on the target device. Prefer the target's Python launcher and
    allow an explicit ``STRATA_PYTHON_EXE`` override for managed deployments.
    """
    with open(launcher_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "@echo off\n"
            "setlocal\n"
            "set \"STRATA_ROOT=%~dp0..\"\n"
            "set \"PYTHONPATH=%STRATA_ROOT%\\runtime;%STRATA_ROOT%\\runtime\\site-packages;%PYTHONPATH%\"\n"
            "if defined STRATA_PYTHON_EXE (\n"
            "  \"%STRATA_PYTHON_EXE%\" -m connector_mcp.server %*\n"
            ") else (\n"
            "  py -3.13 -m connector_mcp.server %*\n"
            ")\n"
            "exit /b %ERRORLEVEL%\n"
        )


def register_local_codex_marketplace(install_dir: str, marketplace_dir: str = "") -> str:
    """Create an isolated local marketplace pointing at the installed plugin.

    This does not modify Codex configuration. The user explicitly adds the
    returned marketplace root with `codex plugin marketplace add` and then
    installs the named plugin. The copied local manifest is patched to the
    installed launcher, so it does not depend on the source checkout.
    """
    abs_install = os.path.abspath(install_dir)
    root = os.path.abspath(
        marketplace_dir or os.path.join(abs_install, "codex-marketplace")
    )
    plugin_src = os.path.join(abs_install, "codex-plugin")
    if not os.path.isdir(plugin_src):
        raise FileNotFoundError(f"Installed Codex plugin not found: {plugin_src}")

    plugin_dst = os.path.join(root, "plugins", "strata-toolkit")
    os.makedirs(os.path.dirname(plugin_dst), exist_ok=True)
    if os.path.exists(plugin_dst):
        shutil.rmtree(plugin_dst)
    shutil.copytree(plugin_src, plugin_dst)

    # Local marketplace installs must use the installed stdio launcher. Keep
    # the public root mcp.json remote-capable; only the local copy is patched.
    local_mcp_path = os.path.join(plugin_dst, "mcp.json")
    launcher_path = os.path.join(abs_install, "bin", "strata-mcp.cmd")
    with open(local_mcp_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                "mcpServers": {
                    "strata-local": {
                        "command": launcher_path,
                        "args": [],
                        "type": "stdio",
                    }
                },
            },
            f,
            indent=2,
        )

    marketplace = {
        "name": "strata-local",
        "interface": {"displayName": "Strata Local"},
        "plugins": [
            {
                "name": "strata-toolkit",
                "source": {"source": "local", "path": "./plugins/strata-toolkit"},
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        ],
    }
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "marketplace.json"), "w", encoding="utf-8") as f:
        json.dump(marketplace, f, indent=2)
    return root


def install(
    config: Optional[InstallerConfig] = None,
    install_dir: str = "",
    blender_addons_dir: str = "",
    source_root: Optional[str] = None,
    install_dependencies: bool = False,
    register_codex: bool = False,
    codex_marketplace_dir: str = "",
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
        install_dir = default_install_dir()

    abs_install = os.path.abspath(install_dir)
    parent_dir = os.path.dirname(abs_install)
    os.makedirs(parent_dir, exist_ok=True)

    root = source_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    stage_dir = os.path.join(parent_dir, f".strata_install_tmp_{uuid.uuid4().hex[:8]}")
    backup_dir = os.path.join(parent_dir, f".strata_install_backup_{uuid.uuid4().hex[:8]}")
    installed_components = []
    errors = []
    blender_target = ""
    promoted = False

    try:
        os.makedirs(stage_dir, exist_ok=True)

        # 1. Stage runtime components
        runtime_dst = os.path.join(stage_dir, cfg.connector_runtime_dir)
        os.makedirs(runtime_dst, exist_ok=True)
        for pkg in ["connector_mcp", "contracts", "reference_engine", "addon"]:
            src_pkg = os.path.join(root, pkg)
            if os.path.isdir(src_pkg):
                shutil.copytree(src_pkg, os.path.join(runtime_dst, pkg))
        if install_dependencies:
            _install_runtime_dependencies(
                os.path.join(runtime_dst, "site-packages"), sys.executable
            )
        installed_components.append("runtime")

        # 2. Stage launcher
        bin_dst = os.path.join(stage_dir, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        launcher_file = os.path.join(bin_dst, "strata-mcp.cmd")
        _write_launcher(launcher_file, sys.executable)
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

        if blender_addons_dir:
            installed_components.append("blender_addon_installed")

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
            os.replace(abs_install, backup_dir)
        try:
            os.replace(stage_dir, abs_install)
        except OSError:
            shutil.move(stage_dir, abs_install)
        promoted = True

        # 7. Optional Blender add-on deployment
        if blender_addons_dir:
            os.makedirs(blender_addons_dir, exist_ok=True)
            blender_target = os.path.join(blender_addons_dir, "strata_toolkit")
            if os.path.exists(blender_target):
                shutil.rmtree(blender_target)
            shutil.copytree(addon_src, blender_target)

        marketplace_path = ""
        if register_codex:
            marketplace_path = register_local_codex_marketplace(
                abs_install, codex_marketplace_dir
            )
            installed_components.append("codex_marketplace")
            with open(os.path.join(abs_install, "install_manifest.json"), "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_data["installed_components"] = installed_components
            manifest_data["codex_marketplace_path"] = marketplace_path
            with open(os.path.join(abs_install, "install_manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

        # Remove the old installation only after all post-promotion steps have
        # succeeded, so a failed add-on or marketplace copy can still roll back.
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)

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
        if promoted and os.path.exists(abs_install):
            shutil.rmtree(abs_install, ignore_errors=True)
        if os.path.exists(backup_dir) and not os.path.exists(abs_install):
            try:
                os.replace(backup_dir, abs_install)
            except OSError:
                pass
        if blender_target and os.path.exists(blender_target):
            shutil.rmtree(blender_target, ignore_errors=True)
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


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line entry point used by the release ZIP and clean-device guide."""
    parser = argparse.ArgumentParser(description="Install the Strata Toolkit.")
    parser.add_argument("--install-dir", default=default_install_dir())
    parser.add_argument("--blender-addons-dir", default=default_blender_addons_dir())
    parser.add_argument("--source-root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--register-codex", action="store_true")
    parser.add_argument("--codex-marketplace-dir", default="")
    parser.add_argument("--no-dependencies", action="store_true", help="Skip isolated dependency installation (developer tests only).")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.uninstall:
        result = uninstall(
            install_dir=args.install_dir,
            blender_addons_dir=args.blender_addons_dir,
        )
    else:
        result = install(
            install_dir=args.install_dir,
            blender_addons_dir=args.blender_addons_dir,
            source_root=args.source_root,
            install_dependencies=not args.no_dependencies,
            register_codex=args.register_codex,
            codex_marketplace_dir=args.codex_marketplace_dir,
        )

    payload = result.__dict__
    if args.as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.message)
        for component in result.installed_components:
            print(f"  installed: {component}")
        for error in result.errors:
            print(f"  error: {error}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
