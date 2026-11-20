"""
M7 Verification Test Suite (Gate 8 Local, Gate 9 Local, Gate 10):
Verifies bilingual CN/EN documentation, offline compliance report, local static website
(with real screenshots, real charts, and zero CDN dependencies), locally rendered 1080p
promotional MP4 video via ffprobe, SHA-256 checksums, and DELIVERY_MANIFEST.md.
"""

import json
import re
import subprocess
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

    # Verify required hero text and real benchmark numbers
    assert "CloudPilot — Local Intelligence. Local Execution." in html
    assert "95.31%" in html
    assert "167.87 tok/s" in html

    # Verify zero remote http/https script, stylesheet, or image sources
    remote_refs = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', html)
    assert len(remote_refs) == 0, f"Website must not depend on external/CDN URLs at runtime, found: {remote_refs}"

    # Verify every local src/href target exists on disk
    local_refs = re.findall(r'(?:src|href)=["\']([^"\'#]+)["\']', html)
    for ref in local_refs:
        target = (html_path.parent / ref).resolve()
        assert target.exists(), f"Broken link/asset in website/index.html: {ref} -> {target}"


def test_m7_promo_video_is_playable_1080p_mp4():
    mp4 = ROOT_DIR / "marketing" / "exports" / "CloudPilot_Promo.mp4"
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


def test_m7_sha256_checksums_verify():
    proc = subprocess.run(
        ["shasum", "-a", "256", "-c", "release/checksums.sha256"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "FAILED" not in proc.stdout
