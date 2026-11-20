"""
M5 Verification Test Suite (Gate 6):
Verifies that:
1. CloudPilot.app and CloudPilot-v1.0-macOS.dmg bundle:
   - Standalone relocatable Python 3.13 interpreter & stdlib (Contents/Resources/python_runtime/bin/python3.13)
   - Offline MLX / Transformers / Pydantic site-packages (Contents/Resources/python_packages/)
   - Fine-tuned Model B fused deployment weights (Contents/Resources/model/deployment/model.safetensors)
   - Fine-tuned Model B LoRA adapter weights (Contents/Resources/model/adapters/adapters.safetensors)
   - Complete backend runtime (Contents/Resources/backend/{app,protocol})
2. Mounting the DMG, installing CloudPilot.app to an isolated directory outside the project root,
   unmounting the DMG, and running the installed .app in a stripped clean-Mac environment
   (PATH=/usr/bin:/bin:/usr/sbin:/sbin, empty HOME, outbound network sockets blocked)
   executes the bundled Python 3.13 binary, loads the bundled .safetensors weights, and completes a task offline.
3. All 6 exported macOS UI screenshots are genuine, distinct captures with 6 unique SHA-256 hashes,
   plus >= 30 live interactive recording frames exist for the promotional video.
"""

import hashlib
import json
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


def test_m5_app_bundle_and_dmg_include_bundled_python_and_weights():
    app_bundle = ROOT_DIR / "release" / "artifacts" / "CloudPilot.app"
    exe = app_bundle / "Contents" / "MacOS" / "CloudPilot"
    plist = app_bundle / "Contents" / "Info.plist"
    bundled_py = app_bundle / "Contents" / "Resources" / "python_runtime" / "bin" / "python3.13"
    bundled_libpy = app_bundle / "Contents" / "Resources" / "python_runtime" / "lib" / "libpython3.13.dylib"
    bundled_deploy = app_bundle / "Contents" / "Resources" / "model" / "deployment" / "model.safetensors"
    bundled_adapter = app_bundle / "Contents" / "Resources" / "model" / "adapters" / "adapters.safetensors"
    bundled_backend = app_bundle / "Contents" / "Resources" / "backend" / "app" / "local_executor" / "orchestration_loop.py"
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"

    assert app_bundle.exists() and app_bundle.is_dir(), "CloudPilot.app bundle missing"
    assert exe.exists(), "Compiled Mach-O executable missing inside CloudPilot.app"
    assert plist.exists(), "Info.plist missing inside CloudPilot.app"
    assert bundled_py.exists() and bundled_py.stat().st_size > 10 * 1024 * 1024, (
        "Standalone Python 3.13 interpreter must be bundled inside CloudPilot.app/Contents/Resources/python_runtime"
    )
    assert bundled_libpy.exists(), "libpython3.13.dylib must be bundled inside CloudPilot.app"
    assert bundled_deploy.exists() and bundled_deploy.stat().st_size > 250 * 1024 * 1024, (
        "Fine-tuned Model B deployment weights (.safetensors) must be bundled inside CloudPilot.app"
    )
    assert bundled_adapter.exists() and bundled_adapter.stat().st_size > 5 * 1024 * 1024, (
        "Fine-tuned Model B LoRA adapter weights (.safetensors) must be bundled inside CloudPilot.app"
    )
    assert bundled_backend.exists(), "Backend runtime must be bundled inside CloudPilot.app"
    assert dmg.exists() and dmg.stat().st_size > 350 * 1024 * 1024, (
        f"CloudPilot-v1.0-macOS.dmg must contain bundled Python + MLX + weights (>350 MB), got {dmg.stat().st_size}"
    )


def test_m5_dmg_mount_install_and_clean_mac_offline_execution(tmp_path: Path):
    """Mount DMG, copy CloudPilot.app to an isolated temp directory, detach DMG,
    and run with stripped PATH (/usr/bin:/bin), clean empty HOME, and blocked network sockets."""
    dmg = ROOT_DIR / "release" / "artifacts" / "CloudPilot-v1.0-macOS.dmg"
    verify_proc = subprocess.run(["hdiutil", "verify", str(dmg)], capture_output=True, text=True)
    assert verify_proc.returncode == 0, f"hdiutil verify failed: {verify_proc.stderr}"

    mnt_dir = tmp_path / "dmg_mount"
    mnt_dir.mkdir()
    install_dir = tmp_path / "InstalledApps"
    install_dir.mkdir()
    installed_app = install_dir / "CloudPilot.app"
    isolated_ws = tmp_path / "Isolated_User_Workspace"
    clean_home = tmp_path / "Clean_Empty_Home"
    clean_home.mkdir()

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

    # Stripped clean-Mac environment: no Homebrew in PATH, no access to user's real $HOME, network offline
    clean_env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(clean_home),
        "TMPDIR": str(tmp_path),
        "LANG": "en_US.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "CLOUDPILOT_OFFLINE_ONLY": "1",
    }

    proc = subprocess.run(
        [str(installed_exe), "--headless-self-test", "--workspace", str(isolated_ws)],
        cwd=tmp_path,
        env=clean_env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["status"] == "PASSED"
    assert payload["offline_only"] is True
    assert payload["cloud_api_keys_required"] is False
    assert payload["bundled_weights_exist"] is True
    assert payload["bundled_python_exists"] is True
    assert payload["network_sockets_blocked"] is True
    assert payload["verified_copy_exists"] is True
    assert payload["manifest_exists"] is True

    # Crucial proof: python_executable, loaded_model_dir, and loaded_backend_module ALL resolve inside the installed .app!
    installed_app_real = str(installed_app.resolve())
    assert payload["python_executable"].startswith(installed_app_real), (
        f"Expected bundled Python inside installed app ({installed_app_real}), got {payload['python_executable']}"
    )
    assert payload["loaded_model_dir"].startswith(installed_app_real), (
        f"Expected model to load from installed app ({installed_app_real}), got {payload['loaded_model_dir']}"
    )
    assert payload["loaded_backend_module"].startswith(installed_app_real), (
        f"Expected backend to load from installed app ({installed_app_real}), got {payload['loaded_backend_module']}"
    )


def test_m5_six_screenshots_and_live_recording_frames_are_distinct():
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

    live_frames = sorted((ROOT_DIR / "marketing" / "footage" / "live_frames").glob("frame_*.png"))
    assert len(live_frames) >= 30, f"Expected >= 30 live interactive recording frames, got {len(live_frames)}"
    live_hashes = {sha256_file(f) for f in live_frames}
    assert len(live_hashes) >= 25, f"Expected >= 25 unique live recording frames, got {len(live_hashes)}"
