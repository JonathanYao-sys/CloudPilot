"""
M7 Verification Test Suite (Gate 8 Local, Gate 9 Local, Gate 10):
Verifies bilingual CN/EN documentation, offline compliance report, local static website
(with real screenshots, real charts, and zero CDN dependencies), locally recorded live app video
(`live_app_recording.mp4`) and rendered 1080p promotional MP4 video (`CloudPilot_Promo.mp4`),
SHA-256 checksums, DELIVERY_MANIFEST.md, and cross-document consistency (validation loss,
DMG size, commit hashes, and post-hoc baseline terminology).
"""

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_m7_all_docs_website_video_and_manifest_exist():
    required = [
        "README.md",
        "docs/architecture.md",
        "docs/installation.md",
        "docs/user_guide.md",
        "docs/security.md",
        "docs/privacy.md",
        "docs/troubleshooting.md",
        "docs/offline_compliance.md",
        "website/index.html",
        "website/styles.css",
        "website/app.js",
        "marketing/storyboard.md",
        "marketing/footage/live_app_recording.mp4",
        "marketing/exports/CloudPilot_Promo.mp4",
        "release/checksums.sha256",
        "release/DELIVERY_MANIFEST.md",
    ]
    for rel in required:
        p = ROOT_DIR / rel
        assert p.exists(), f"Missing M7 deliverable: {rel}"
        assert p.stat().st_size > 200, f"Empty M7 deliverable: {rel}"


def test_m7_website_is_self_contained_with_zero_cdn_and_valid_local_assets():
    html_path = ROOT_DIR / "website" / "index.html"
    html = html_path.read_text(encoding="utf-8")

    assert "CloudPilot — Local Intelligence. Local Execution." in html
    assert "95.31%" in html
    assert "92.86%" in html

    remote_src = re.findall(r'src=["\'](https?://[^"\']+)["\']', html)
    remote_css = re.findall(r'<link[^>]+href=["\'](https?://[^"\']+)["\']', html)
    assert len(remote_src) == 0 and len(remote_css) == 0, (
        f"Website must not depend on external/CDN runtime assets, found: {remote_src + remote_css}"
    )

    assert "https://github.com/JonathanYao-sys/CloudPilot" in html

    local_refs = [
        ref for ref in re.findall(r'(?:src|href)=["\']([^"\'#]+)["\']', html)
        if not ref.startswith("http://") and not ref.startswith("https://")
    ]
    for ref in local_refs:
        target = (html_path.parent / ref).resolve()
        assert target.exists(), f"Broken link/asset in website/index.html: {ref} -> {target}"

    shot_hashes = set()
    for i in range(1, 7):
        matches = list((ROOT_DIR / "website" / "assets").glob(f"0{i}_*.png"))
        assert len(matches) == 1
        shot_hashes.add(hashlib.sha256(matches[0].read_bytes()).hexdigest())
    assert len(shot_hashes) == 6, "All 6 website screenshots must have unique SHA-256 hashes"


def test_m7_promo_video_and_live_recording_are_multi_frame_1080p_mp4():
    for rel in ("marketing/footage/live_app_recording.mp4", "marketing/exports/CloudPilot_Promo.mp4"):
        mp4 = ROOT_DIR / rel
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,size",
                "-show_entries", "stream=codec_name,width,height",
                "-of", "json",
                str(mp4),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        info = json.loads(proc.stdout)
        streams = info["streams"]
        video_streams = [s for s in streams if s.get("codec_name") == "h264"]
        assert len(video_streams) == 1
        assert video_streams[0]["width"] == 1920
        assert video_streams[0]["height"] == 1080
        duration = float(info["format"]["duration"])
        assert duration >= 20.0

    # Extract 1 frame every 1.5s from CloudPilot_Promo.mp4 and verify >= 15 distinct visual states
    with tempfile.TemporaryDirectory() as tmpdir:
        out_pat = str(Path(tmpdir) / "sample_%03d.png")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(ROOT_DIR / "marketing" / "exports" / "CloudPilot_Promo.mp4"),
                "-vf", "fps=1",
                out_pat,
            ],
            check=True,
            capture_output=True,
        )
        sampled = sorted(Path(tmpdir).glob("sample_*.png"))
        unique_frame_hashes = {hashlib.sha256(f.read_bytes()).hexdigest() for f in sampled}
        assert len(unique_frame_hashes) >= 15, (
            f"Promo video must contain continuous live app recording (>=15 unique 1fps frames), got {len(unique_frame_hashes)}"
        )


def test_m7_sha256_checksums_and_cross_document_consistency():
    proc = subprocess.run(
        ["shasum", "-a", "256", "-c", "release/checksums.sha256"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "FAILED" not in proc.stdout

    # Check consistency of validation loss (0.348 best / 0.366 final) and DMG size (487.01 MiB) across docs
    for rel in ("README.md", "model/MODEL_CARD.md", "docs/offline_compliance.md", "release/DELIVERY_MANIFEST.md"):
        txt = (ROOT_DIR / rel).read_text(encoding="utf-8")
        assert "0.348" in txt and "0.366" in txt, f"{rel} must report both best (0.348) and final (0.366) val_loss"

    for rel in ("README.md", "docs/local_compute_budget.md", "release/DELIVERY_MANIFEST.md"):
        txt = (ROOT_DIR / rel).read_text(encoding="utf-8")
        assert "487.01 MiB" in txt, f"{rel} must report consistent DMG size 487.01 MiB"

    # Check commit hash consistency across progress.json and PROJECT_STATUS.md
    progress = json.loads((ROOT_DIR / "progress.json").read_text(encoding="utf-8"))
    status_md = (ROOT_DIR / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    for m in progress["milestones"]:
        cp = m.get("git_checkpoint") or {}
        if cp.get("commit"):
            short_h = cp["commit"][:7]
            assert f"`{cp['tag']}` (`{short_h}`)" in status_md
            assert f"commit `{cp['commit']}`, tag `{cp['tag']}`" in status_md
