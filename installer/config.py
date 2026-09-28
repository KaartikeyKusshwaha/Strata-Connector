"""Strata Toolkit installer configuration.

Defines the version compatibility matrix, component paths, and
Windows registry metadata for atomic installation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# Version compatibility matrix
COMPATIBILITY_MATRIX = {
    "connector": "1.1.x",
    "contract": "1.0",
    "engine": "2026.09.0+ (signed local runtime or managed service)",
    "blender": "4.5+",
    "python": "3.10-3.13",
    "os": "Windows 10/11 x64",
}


@dataclass
class InstallerConfig:
    """Configuration for the Strata Toolkit installer."""

    product_name: str = "Strata Toolkit"
    publisher: str = "Strata"
    version: str = "1.1.2"

    # Component paths (relative to install root)
    connector_runtime_dir: str = "runtime"
    launcher_path: str = "bin/strata-mcp.cmd"
    plugin_dir: str = "codex-plugin"
    addon_dir: str = "blender-addon"

    # Windows registry metadata
    registry_key: str = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StrataToolkit"
    install_location: str = ""

    # Compatible version ranges
    min_connector_version: str = "1.1.0"
    max_connector_version: str = "1.1.99"
    min_blender_version: str = "4.5.0"
    min_engine_version: str = "2026.09.0"
    # Public release metadata only. The private Engine source is never placed
    # in this repository; its signed Windows bundle is published as a release
    # asset by the owner-controlled Engine workflow.
    engine_release_manifest_url: str = (
        "https://github.com/KaartikeyKusshwaha/Strata-Connector/releases/download/"
        "engine-v2026.09.0/strata-engine-release.json"
    )
    engine_release_public_key: str = "WgGP7tntAnhqaugcDCZuLGIHh8Gmc+0a5uNkGXYC9dQ="

    def _parse_version(self, v_str: str) -> List[int]:
        parts = []
        for p in v_str.split("."):
            num = ""
            for ch in p:
                if ch.isdigit():
                    num += ch
                else:
                    break
            parts.append(int(num) if num else 0)
        return parts

    def validate_compatibility(
        self,
        connector_version: str = "",
        blender_version: str = "",
    ) -> Dict[str, str]:
        """Validates component version compatibility.

        Returns a dict of {component: status} where status is
        'compatible', 'incompatible', or 'unknown'.
        """
        results: Dict[str, str] = {
            "connector": "unknown",
            "blender": "unknown",
            "plugin": "compatible",
            "addon": "compatible",
        }

        if connector_version:
            conn_parts = self._parse_version(connector_version)
            min_parts = self._parse_version(self.min_connector_version)
            max_parts = self._parse_version(self.max_connector_version)
            if conn_parts >= min_parts and conn_parts <= max_parts:
                results["connector"] = "compatible"
            else:
                results["connector"] = "incompatible"

        if blender_version:
            blend_parts = self._parse_version(blender_version)
            min_blend = self._parse_version(self.min_blender_version)
            if blend_parts >= min_blend:
                results["blender"] = "compatible"
            else:
                results["blender"] = "incompatible"

        return results
