"""Pytest integration test for Blender 4.5 headless verification."""
import json
import os
import subprocess
import shutil
import pytest

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
VERIFY_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "blender_headless_verify.py"))


@pytest.mark.skipif(not os.path.exists(BLENDER_EXE), reason="Blender 4.5 not found on system")
def test_blender_headless_render_matrix():
    """Runs scripts/blender_headless_verify.py inside Blender 4.5 LTS."""
    assert os.path.isfile(VERIFY_SCRIPT), f"Script not found: {VERIFY_SCRIPT}"

    cmd = [BLENDER_EXE, "-b", "--python", VERIFY_SCRIPT]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"Blender headless execution failed:\n{proc.stdout}\n{proc.stderr}"

    audit_path = os.path.abspath("test-tmp/renders/render_audit.json")
    assert os.path.isfile(audit_path), "render_audit.json was not produced"

    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "PASS"
    gates = data["gates"]
    assert gates["RENDER-TERRAIN"] == "PASS"
    assert gates["RENDER-WATER"] == "PASS"
    assert gates["RENDER-LIGHT-DAY"] == "PASS"
    assert gates["RENDER-LIGHT-NIGHT"] == "PASS"
    assert gates["RENDER-TOGGLE"] == "PASS"
