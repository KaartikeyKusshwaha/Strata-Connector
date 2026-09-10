"""Strata Toolkit installer logic.

Performs atomic installation of the Strata Toolkit components:
- Connector runtime in an isolated application directory
- Dedicated strata-mcp launcher
- Codex plugin package referencing the launcher
- Blender add-on compatible with the runtime
- Windows Add/Remove Programs uninstall metadata

This module is a stub. Implementation depends on having a finalized
launcher executable and signing infrastructure (Plan Phase 4).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

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


def install(
    config: Optional[InstallerConfig] = None,
    install_dir: str = "",
    blender_addons_dir: str = "",
) -> InstallResult:
    """Installs the Strata Toolkit atomically.

    Steps (stub):
    1. Validate target directories and permissions
    2. Check for existing installation (upgrade/downgrade)
    3. Validate component version compatibility
    4. Install Connector runtime to isolated directory
    5. Install strata-mcp launcher
    6. Install Codex plugin package
    7. Install Blender add-on
    8. Register Windows uninstall metadata
    9. Verify installation integrity

    Returns:
        InstallResult with success status and details.
    """
    # Stub — full implementation in Phase 4
    return InstallResult(
        success=False,
        message="Installer not yet implemented. See CODEX_PLUGIN_PLAN.md Phase 4.",
    )


def uninstall(
    config: Optional[InstallerConfig] = None,
    install_dir: str = "",
) -> InstallResult:
    """Uninstalls the Strata Toolkit.

    Steps (stub):
    1. Stop any running bridge servers
    2. Remove Codex plugin
    3. Remove Blender add-on
    4. Remove Connector runtime and launcher
    5. Clean up Windows registry entries
    6. Remove install directory if empty

    Returns:
        InstallResult with success status and details.
    """
    # Stub — full implementation in Phase 4
    return InstallResult(
        success=False,
        message="Uninstaller not yet implemented. See CODEX_PLUGIN_PLAN.md Phase 4.",
    )


def check_upgrade(
    current_version: str = "",
    target_version: str = "",
) -> dict:
    """Checks whether an upgrade/downgrade is safe.

    Returns a dict with compatibility information and
    any required repair steps.
    """
    # Stub — full implementation in Phase 4
    return {
        "current_version": current_version,
        "target_version": target_version,
        "compatible": False,
        "message": "Upgrade check not yet implemented.",
        "repair_steps": [],
    }
