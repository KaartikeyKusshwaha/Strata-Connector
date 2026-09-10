"""Strata Toolkit installer configuration.

Defines the version compatibility matrix, component paths, and
Windows Add/Remove Programs registry metadata for atomic installation.

This module is a stub. Implementation depends on having a finalized
launcher executable and signing infrastructure (Plan Phase 4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# Version compatibility matrix
COMPATIBILITY_MATRIX = {
    "connector": "1.1.x",
    "contract": "1.0",
    "engine": "2026.09.0+",
    "blender": "4.5+",
    "python": "3.10-3.13",
    "os": "Windows 10/11 x64",
}


@dataclass
class InstallerConfig:
    """Configuration for the Strata Toolkit installer."""

    product_name: str = "Strata Toolkit"
    publisher: str = "Strata"
    version: str = "1.1.0"

    # Component paths (relative to install root)
    connector_runtime_dir: str = "runtime"
    launcher_path: str = "bin/strata-mcp.exe"
    plugin_dir: str = "codex-plugin"
    addon_dir: str = "blender-addon"

    # Windows registry metadata
    registry_key: str = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StrataToolkit"
    install_location: str = ""

    # Compatible version ranges
    min_connector_version: str = "1.1.0"
    max_connector_version: str = "1.1.99"
    min_blender_version: str = "4.5.0"

    def validate_compatibility(
        self,
        connector_version: str = "",
        blender_version: str = "",
    ) -> Dict[str, str]:
        """Validates component version compatibility.

        Returns a dict of {component: status} where status is
        'compatible', 'incompatible', or 'unknown'.
        """
        # Stub — full implementation in Phase 4
        return {
            "connector": "unknown",
            "blender": "unknown",
            "plugin": "unknown",
            "addon": "unknown",
        }
