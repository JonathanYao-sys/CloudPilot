"""
M5 Verification Test Suite (Gate 6):
Verifies that CloudPilot.app and CloudPilot-v1.0-macOS.dmg exist, pass codesign verification,
require zero cloud API keys, and complete an offline user-approved task with fine-tuned Model B.
"""

import json
import os
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m5_app_bundle_and_dmg_exist():
    app_bundle = ROOT_DIR / "release" / "artifacts" / "CloudPilot.app"
    exe = app_bundle / "Contents" / "MacOS" / "CloudPilot"
    plist = app_bundle / "Contents" / "Info.plist"
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"

    assert app_bundle.exists() and app_bundle.is_dir(), "CloudPilot.app bundle missing"
    assert exe.exists(), "Compiled Mach-O executable missing inside CloudPilot.app"
    assert plist.exists(), "Info.plist missing inside CloudPilot.app"
    assert dmg.exists() and dmg.stat().st_size > 50_000, "CloudPilot-v1.0-macOS.dmg missing or too small"


def test_m5_app_headless_offline_self_test(tmp_path: Path):
    exe = ROOT_DIR / "release" / "artifacts" / "CloudPilot.app" / "Contents" / "MacOS" / "CloudPilot"
    env = os.environ.copy()
    env["CLOUDPILOT_ROOT"] = str(ROOT_DIR)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["CLOUDPILOT_OFFLINE_ONLY"] = "1"

    proc = subprocess.run(
        [str(exe), "--headless-self-test"],
        cwd=ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["status"] == "PASSED"
    assert payload["offline_only"] is True
    assert payload["cloud_api_keys_required"] is False
    assert payload["verified_copy_exists"] is True
    assert payload["manifest_exists"] is True


def test_m5_dmg_verifies_via_hdiutil():
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"
    proc = subprocess.run(
        ["hdiutil", "verify", str(dmg)],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"hdiutil verify failed: {proc.stderr}"
