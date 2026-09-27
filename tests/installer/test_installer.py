"""Unit and integration tests for the atomic installer and rollback logic."""
import json
import os
import shutil
import tempfile
import pytest

from installer.config import InstallerConfig
from installer.install import check_upgrade, install, uninstall


@pytest.fixture
def tmp_test_env():
    d = tempfile.mkdtemp(prefix="strata_installer_test_")
    install_dir = os.path.join(d, "StrataToolkit")
    blender_dir = os.path.join(d, "BlenderAddons")
    os.makedirs(blender_dir, exist_ok=True)
    yield {
        "root": d,
        "install_dir": install_dir,
        "blender_dir": blender_dir,
    }
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)


def test_installer_compatibility_validation():
    cfg = InstallerConfig()

    compat = cfg.validate_compatibility(connector_version="1.1.0", blender_version="4.5.0")
    assert compat["connector"] == "compatible"
    assert compat["blender"] == "compatible"

    incompat_conn = cfg.validate_compatibility(connector_version="2.0.0", blender_version="4.5.0")
    assert incompat_conn["connector"] == "incompatible"

    incompat_blend = cfg.validate_compatibility(connector_version="1.1.0", blender_version="3.6.0")
    assert incompat_blend["blender"] == "incompatible"


def test_atomic_install_success(tmp_test_env):
    install_dir = tmp_test_env["install_dir"]
    res = install(install_dir=install_dir)

    assert res.success is True
    assert os.path.isdir(install_dir)

    # Verify components
    manifest_path = os.path.join(install_dir, "install_manifest.json")
    assert os.path.isfile(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["product_name"] == "Strata Toolkit"
    assert "runtime" in data["installed_components"]
    assert "launcher" in data["installed_components"]

    # Verify launcher
    launcher = os.path.join(install_dir, "bin", "strata-mcp.cmd")
    assert os.path.isfile(launcher)
    with open(launcher, "r", encoding="utf-8") as f:
        launcher_text = f.read()
    assert "py -3.13 -m connector_mcp.server" in launcher_text
    assert "STRATA_PYTHON_EXE" in launcher_text
    # A release can be extracted on a different machine, so do not capture the
    # installer's absolute interpreter path in the generated launcher.
    assert os.path.abspath(os.sys.executable) not in launcher_text

    # Verify runtime
    runtime_mcp = os.path.join(install_dir, "runtime", "connector_mcp", "server.py")
    assert os.path.isfile(runtime_mcp)


def test_atomic_install_with_blender_addon(tmp_test_env):
    install_dir = tmp_test_env["install_dir"]
    blender_dir = tmp_test_env["blender_dir"]

    res = install(install_dir=install_dir, blender_addons_dir=blender_dir)
    assert res.success is True

    addon_target = os.path.join(blender_dir, "strata_toolkit", "__init__.py")
    assert os.path.isfile(addon_target)


def test_install_registers_portable_local_codex_marketplace(tmp_test_env):
    install_dir = tmp_test_env["install_dir"]
    res = install(
        install_dir=install_dir,
        blender_addons_dir=tmp_test_env["blender_dir"],
        register_codex=True,
    )
    assert res.success is True
    manifest = json.loads(
        open(os.path.join(install_dir, "install_manifest.json"), encoding="utf-8").read()
    )
    assert "codex_marketplace" in manifest["installed_components"]
    marketplace = manifest["codex_marketplace_path"]
    assert os.path.isfile(os.path.join(marketplace, "marketplace.json"))
    mcp_path = os.path.join(marketplace, "plugins", "strata-toolkit", "mcp.json")
    mcp = json.loads(open(mcp_path, encoding="utf-8").read())
    local_server = mcp["mcpServers"]["strata-local"]
    assert local_server["type"] == "stdio"
    assert local_server["command"].endswith("strata-mcp.cmd")


def test_uninstall_cleans_up(tmp_test_env):
    install_dir = tmp_test_env["install_dir"]
    blender_dir = tmp_test_env["blender_dir"]

    # 1. Install
    res = install(install_dir=install_dir, blender_addons_dir=blender_dir)
    assert res.success is True
    assert os.path.isdir(install_dir)

    # 2. Uninstall
    uninst_res = uninstall(install_dir=install_dir, blender_addons_dir=blender_dir)
    assert uninst_res.success is True
    assert not os.path.exists(install_dir)
    assert not os.path.exists(os.path.join(blender_dir, "strata_toolkit"))


def test_upgrade_check():
    safe = check_upgrade("1.1.0", "1.1.1")
    assert safe["compatible"] is True

    unsafe = check_upgrade("1.1.0", "2.0.0")
    assert unsafe["compatible"] is False
    assert len(unsafe["repair_steps"]) > 0
