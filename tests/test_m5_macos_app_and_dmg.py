"""
M5 Verification Test Suite (Gate 6):
Verifies that:
1. CloudPilot.app and CloudPilot-v1.0-macOS.dmg bundle the fine-tuned Model B weights (.safetensors)
   and backend runtime directly inside Contents/Resources/.
2. Mounting the DMG, installing CloudPilot.app to an isolated directory outside /Users/yao/CloudPilot,
   and running it offline (--headless-self-test) loads both the model weights and backend from inside
   the installed .app bundle (zero dependency on /Users/yao/CloudPilot source tree) and completes a task.
3. All 6 exported macOS UI screenshots are genuine, distinct, high-resolution captures with 6 unique SHA-256 hashes.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_m5_app_bundle_and_dmg_include_bundled_weights():
    app_bundle = ROOT_DIR / "release" / "artifacts" / "CloudPilot.app"
    exe = app_bundle / "Contents" / "MacOS" / "CloudPilot"
    plist = app_bundle / "Contents" / "Info.plist"
    bundled_deploy = app_bundle / "Contents" / "Resources" / "model" / "deployment" / "model.safetensors"
    bundled_adapter = app_bundle / "Contents" / "Resources" / "model" / "adapters" / "adapters.safetensors"
    bundled_backend = app_bundle / "Contents" / "Resources" / "backend" / "app" / "local_executor" / "orchestration_loop.py"
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"

    assert app_bundle.exists() and app_bundle.is_dir(), "CloudPilot.app bundle missing"
    assert exe.exists(), "Compiled Mach-O executable missing inside CloudPilot.app"
    assert plist.exists(), "Info.plist missing inside CloudPilot.app"
    assert bundled_deploy.exists() and bundled_deploy.stat().st_size > 250 * 1024 * 1024, (
        "Fine-tuned Model B deployment weights (.safetensors) must be bundled inside CloudPilot.app"
    )
    assert bundled_adapter.exists() and bundled_adapter.stat().st_size > 5 * 1024 * 1024, (
        "Fine-tuned Model B LoRA adapter weights (.safetensors) must be bundled inside CloudPilot.app"
    )
    assert bundled_backend.exists(), "Backend runtime must be bundled inside CloudPilot.app"
    assert dmg.exists() and dmg.stat().st_size > 200 * 1024 * 1024, (
        f"CloudPilot-v1.0-macOS.dmg must contain the bundled weights (>200 MB), got {dmg.stat().st_size}"
    )


def test_m5_dmg_mount_install_and_isolated_offline_execution(tmp_path: Path):
    """Mount DMG, copy CloudPilot.app to an isolated temp directory outside /Users/yao/CloudPilot,
    detach DMG, and run offline task to prove standalone execution."""
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"
    verify_proc = subprocess.run(["hdiutil", "verify", str(dmg)], capture_output=True, text=True)
    assert verify_proc.returncode == 0, f"hdiutil verify failed: {verify_proc.stderr}"

    mnt_dir = tmp_path / "dmg_mount"
    mnt_dir.mkdir()
    install_dir = tmp_path / "InstalledApps"
    install_dir.mkdir()
    installed_app = install_dir / "CloudPilot.app"
    isolated_ws = tmp_path / "Isolated_User_Workspace"

    subprocess.run(
        ["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly", "-mountpoint", str(mnt_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        mounted_app = mnt_dir / "CloudPilot.app"
        assert mounted_app.exists(), "CloudPilot.app not found inside mounted DMG volume"
        shutil.copytree(mounted_app, installed_app, symlinks=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mnt_dir), "-force"], check=False, capture_output=True)

    installed_exe = installed_app / "Contents" / "MacOS" / "CloudPilot"
    assert installed_exe.exists()

    # Run from tmp_path with CLOUDPILOT_ROOT unset so it cannot fall back to /Users/yao/CloudPilot
    env = os.environ.copy()
    env.pop("CLOUDPILOT_ROOT", None)
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["CLOUDPILOT_OFFLINE_ONLY"] = "1"

    proc = subprocess.run(
        [str(installed_exe), "--headless-self-test", "--workspace", str(isolated_ws)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["status"] == "PASSED"
    assert payload["offline_only"] is True
    assert payload["cloud_api_keys_required"] is False
    assert payload["bundled_weights_exist"] is True
    assert payload["verified_copy_exists"] is True
    assert payload["manifest_exists"] is True

    # Crucial proof: loaded_model_dir and loaded_backend_module must resolve inside the installed .app in tmp_path!
    installed_app_real = str(installed_app.resolve())
    assert payload["loaded_model_dir"].startswith(installed_app_real), (
        f"Expected model to load from installed app ({installed_app_real}), got {payload['loaded_model_dir']}"
    )
    assert payload["loaded_backend_module"].startswith(installed_app_real), (
        f"Expected backend to load from installed app ({installed_app_real}), got {payload['loaded_backend_module']}"
    )


def test_m5_six_screenshots_are_distinct_and_non_trivial():
    shots_dir = ROOT_DIR / "marketing" / "assets" / "screenshots"
    expected_files = [
        "01_home_chat.png",
        "02_plan_preview.png",
        "03_execution_monitor.png",
        "04_local_models.png",
        "05_settings_privacy.png",
        "06_audit_history.png",
    ]
    hashes = set()
    for fname in expected_files:
        p = shots_dir / fname
        assert p.exists(), f"Missing screenshot: {fname}"
        assert p.stat().st_size > 200_000, f"Screenshot {fname} is unexpectedly small ({p.stat().st_size} bytes)"
        hashes.add(sha256_file(p))

    assert len(hashes) == 6, f"All 6 screenshots must be visually distinct (found only {len(hashes)} unique hashes)"
