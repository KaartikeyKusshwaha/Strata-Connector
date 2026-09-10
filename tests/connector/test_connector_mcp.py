"""Tests for Connector MCP server.

Verifies tool registration, the renamed tool, and the critical
no-engine-import audit.
"""
import ast
import os
import pytest
from connector_mcp.server import mcp


def test_connector_mcp_registers_all_10_tools():
    tools = mcp._tool_manager.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "strata_preflight_world",
        "strata_inspect_library",
        "strata_submit_managed_build",
        "strata_get_job_status",
        "strata_download_result",
        "strata_open_result_in_blender",
        "strata_get_chunk_streaming_status",
        "strata_load_chunk_radius",
        "strata_set_interactive_block_state",
        "strata_keyframe_interactive_block_state",
        "strata_pair_blender",
    }

    for name in expected:
        assert name in tool_names, f"Missing MCP tool: {name}"

    assert len(expected) == 11


def test_old_submit_build_name_removed():
    """The old strata_submit_build should NOT exist anymore."""
    tools = mcp._tool_manager.list_tools()
    tool_names = {t.name for t in tools}
    assert "strata_submit_build" not in tool_names


def test_no_strata_engine_imports_in_connector_mcp():
    """CRITICAL AUDIT: The connector_mcp package must NEVER import strata
    engine modules. This test walks all .py files in connector_mcp/ and
    verifies no prohibited imports exist."""

    connector_dir = os.path.join(os.path.dirname(__file__), "..", "..", "connector_mcp")
    connector_dir = os.path.abspath(connector_dir)

    violations = []

    for root, _dirs, files in os.walk(connector_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source, filename=fpath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("strata"):
                            violations.append(f"{fpath}:{node.lineno} imports '{alias.name}'")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("strata"):
                        violations.append(f"{fpath}:{node.lineno} imports from '{node.module}'")

    assert not violations, (
        "PROHIBITED ENGINE IMPORTS FOUND IN CONNECTOR:\n" + "\n".join(violations)
    )
