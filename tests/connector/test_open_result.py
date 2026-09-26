"""Tests for result opening, independent validation, and Blender bridge handoff.

Covers:
- MCP pre-bridge validation (path traversal, missing manifest, checksum mismatch)
- Independent add-on validation (empty manifest, traversal, missing files, major version)
- Live bridge open_result dispatch with authenticated session
"""
import json
import os
import shutil
import tempfile
import time
import pytest

from addon.bridge_server import BridgeServer
from addon.result_loader import validate_and_open_result
from connector_mcp.bridge_client import BridgeClient
from connector_mcp.server import strata_open_result_in_blender
from reference_engine.synthetic import write_synthetic_output


@pytest.fixture
def tmp_result_dir():
    d = tempfile.mkdtemp(prefix="strata_open_res_")
    yield d
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def test_addon_validate_and_open_valid_manifest(tmp_result_dir):
    manifest_path = write_synthetic_output(tmp_result_dir)
    res = validate_and_open_result(manifest_path)

    assert res["status"] == "ok"
    assert res["manifest_path"] == os.path.abspath(manifest_path)
    assert "manifest_sha256" in res
    assert res["linked_chunks"] >= 4
    assert res["total_chunks"] >= 4


def test_addon_validate_nonexistent_manifest():
    res = validate_and_open_result("nonexistent/manifest.json")
    assert res["status"] == "error"
    assert res["error_code"] == "manifest_not_found"


def test_addon_validate_empty_manifest(tmp_result_dir):
    manifest_path = os.path.join(tmp_result_dir, "strata-world-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"contract_version": "1.0", "chunks": {}}, f)

    res = validate_and_open_result(manifest_path)
    assert res["status"] == "error"
    assert res["error_code"] == "empty_manifest"


def test_addon_validate_path_traversal(tmp_result_dir):
    manifest_path = os.path.join(tmp_result_dir, "strata-world-manifest.json")
    bad_manifest = {
        "contract_version": "1.0",
        "chunks": {
            "0:0:0": {
                "name": "BadChunk",
                "file": "../../../escaped.blend",
            }
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    res = validate_and_open_result(manifest_path)
    assert res["status"] == "error"
    assert res["error_code"] == "path_traversal"


def test_addon_validate_missing_chunk_file(tmp_result_dir):
    manifest_path = os.path.join(tmp_result_dir, "strata-world-manifest.json")
    bad_manifest = {
        "contract_version": "1.0",
        "chunks": {
            "0:0:0": {
                "name": "MissingChunk",
                "file": "chunks/missing.blend",
            }
        },
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    res = validate_and_open_result(manifest_path)
    assert res["status"] == "error"
    assert res["error_code"] == "missing_chunk_file"


def test_addon_validate_unsupported_major_version(tmp_result_dir):
    manifest_path = os.path.join(tmp_result_dir, "strata-world-manifest.json")
    bad_manifest = {
        "contract_version": "2.0",
        "chunks": {"0:0:0": {"name": "c", "file": "chunks/c.blend"}},
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    res = validate_and_open_result(manifest_path)
    assert res["status"] == "error"
    assert res["error_code"] == "unsupported_contract_version"


def test_mcp_strata_open_result_rejects_checksum_mismatch(tmp_result_dir):
    manifest_path = write_synthetic_output(tmp_result_dir)

    # Corrupt one chunk file on disk
    manifest_file = os.path.join(tmp_result_dir, "strata-world-manifest.json")
    with open(manifest_file, "r") as f:
        data = json.load(f)
    first_chunk = list(data["chunks"].values())[0]["file"]
    chunk_path = os.path.join(tmp_result_dir, first_chunk)
    with open(chunk_path, "ab") as f:
        f.write(b"TAMPERED_CONTENT")

    # Call MCP tool
    res = strata_open_result_in_blender(manifest_path)
    assert "error" in res.get("status", "") or res.get("error_code") == "checksum_mismatch"


def test_mcp_strata_open_result_rejects_missing_file():
    res = strata_open_result_in_blender(os.path.abspath("nonexistent/manifest.json"))
    assert res.get("error_code") in ("invalid_input", "manifest_invalid")


def test_live_bridge_open_result(tmp_result_dir):
    test_port = 9989
    server = BridgeServer(host="127.0.0.1", port=test_port)
    server.start()
    time.sleep(0.05)

    try:
        # Create and approve pairing
        nonce = server.create_pairing_request()
        server.approve_pairing()

        client = BridgeClient(host="127.0.0.1", port=test_port)
        pair_res = client.pair(nonce)
        assert pair_res["status"] == "paired"

        manifest_path = write_synthetic_output(tmp_result_dir)
        open_res = client.open_result(manifest_path)
        assert open_res["status"] == "ok"
        assert open_res["linked_chunks"] >= 4
    finally:
        server.stop()
        time.sleep(0.05)
