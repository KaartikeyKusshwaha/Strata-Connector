"""Tests for plugin packaging integrity.

Verifies the codex_plugin/ directory structure, manifest validity,
and absence of private/sensitive files.
"""
import json
import os
import pytest

PLUGIN_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "codex_plugin"
)
PLUGIN_ROOT = os.path.abspath(PLUGIN_ROOT)


def test_plugin_directory_exists():
    assert os.path.isdir(PLUGIN_ROOT), "codex_plugin/ directory must exist"


def test_plugin_json_exists_and_valid():
    path = os.path.join(PLUGIN_ROOT, ".codex-plugin", "plugin.json")
    assert os.path.isfile(path), "plugin.json must exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "name" in data
    assert data["name"] == "strata-toolkit"
    assert "version" in data
    assert "description" in data
    assert "developer" in data
    assert "skills" in data
    assert isinstance(data["skills"], list)
    assert len(data["skills"]) > 0
    assert "hooks" in data
    assert data["hooks"] == []
    assert "permissions" in data
    assert data["permissions"] == []


def test_mcp_json_exists_and_valid():
    path = os.path.join(PLUGIN_ROOT, ".mcp.json")
    assert os.path.isfile(path), ".mcp.json must exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "mcpServers" in data
    servers = data["mcpServers"]
    assert "strata-connector" in servers
    server_config = servers["strata-connector"]
    assert server_config["command"] == "strata-mcp"
    assert server_config["transport"] == "stdio"


def test_skill_md_exists():
    path = os.path.join(PLUGIN_ROOT, "skills", "strata-toolkit", "SKILL.md")
    assert os.path.isfile(path), "SKILL.md must exist"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Verify key sections exist
    assert "strata-toolkit" in content
    assert "Workflow" in content
    assert "Preflight" in content or "preflight" in content
    assert "Consent" in content or "consent" in content
    assert "strata_pair_blender" in content
    assert "Tool Approval" in content or "tool approval" in content.lower()


def test_readme_exists():
    path = os.path.join(PLUGIN_ROOT, "README.md")
    assert os.path.isfile(path), "Plugin README.md must exist"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Strata Toolkit" in content
    assert "Installation" in content or "installation" in content.lower()


def test_assets_directory_exists():
    path = os.path.join(PLUGIN_ROOT, "assets")
    assert os.path.isdir(path), "assets/ directory must exist"


def test_no_python_source_in_plugin():
    """Plugin directory must not contain Python source files.
    The plugin is a distribution wrapper, not a code package."""
    for root, _dirs, files in os.walk(PLUGIN_ROOT):
        for fname in files:
            assert not fname.endswith(".py"), (
                f"Python source file found in plugin directory: "
                f"{os.path.join(root, fname)}"
            )


def test_no_private_files_in_plugin():
    """Plugin directory must not contain private engine files, credentials,
    or test fixture data."""
    forbidden_patterns = [
        ".env", ".key", ".pem", ".p12",
        "credentials", "secret", "token",
        ".jar", ".mcmeta", ".nbt", ".dat", ".schematic",
    ]
    for root, _dirs, files in os.walk(PLUGIN_ROOT):
        for fname in files:
            lower = fname.lower()
            for pattern in forbidden_patterns:
                assert pattern not in lower, (
                    f"Potentially sensitive file in plugin directory: "
                    f"{os.path.join(root, fname)}"
                )
