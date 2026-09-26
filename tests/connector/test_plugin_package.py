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
    assert data.get("name") == "strata-toolkit"
    assert "version" in data
    assert "description" in data
    # Must use supported author object rather than obsolete developer string
    assert "author" in data and isinstance(data["author"], dict)
    assert data["author"].get("name") == "Strata"
    # Skills and mcpServers must use relative path references
    assert data.get("skills") == "./skills/"
    assert data.get("mcpServers") == "./.mcp.json"
    assert "interface" in data and isinstance(data["interface"], dict)
    assert data["interface"].get("displayName") == "Strata Toolkit"
    # Obsolete keys must be absent
    assert "developer" not in data
    assert "hooks" not in data
    assert "permissions" not in data


def test_root_plugin_json_exists_and_valid():
    path = os.path.join(PLUGIN_ROOT, "plugin.json")
    assert os.path.isfile(path), "root plugin.json must exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("name") == "strata-toolkit"
    assert "version" in data
    assert "author" in data and isinstance(data["author"], dict)
    assert data.get("skills") == "./skills/"
    assert data.get("mcpServers") == "./mcp.json"
    assert "interface" in data
    assert "termsUrl" in data["interface"]
    assert "privacyPolicyUrl" in data["interface"]


def test_root_mcp_json_exists_and_valid():
    path = os.path.join(PLUGIN_ROOT, "mcp.json")
    assert os.path.isfile(path), "root mcp.json must exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "mcpServers" in data
    servers = data["mcpServers"]
    assert "strata-cloud" in servers
    assert servers["strata-cloud"].get("type") == "streamable-http"
    assert "url" in servers["strata-cloud"]


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
