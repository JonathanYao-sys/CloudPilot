#!/usr/bin/env python3
"""
CloudPilot Local Promotional Video Renderer (Phase 10 / M7)
Combines the real 36-frame live interactive app recording (`marketing/footage/live_frames/frame_*.png`,
captured directly from `CloudPilot.app --record-live-demo` while typing, drafting a 10-step DAG plan,
approving, streaming real Model B Metal GPU step traces S1..S10 with network sockets blocked,
and recording SQLite audit rows) with the real A/B/C benchmark chart cards into:
  1. `marketing/footage/live_app_recording.mp4` (raw continuous app workflow recording)
  2. `marketing/exports/CloudPilot_Promo.mp4` (final 1080p H.264 + AAC promotional video)
Zero cloud video, image, or TTS services are used.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["PingFang HK", "Heiti TC", "Hiragino Sans GB", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

ROOT_DIR = Path(__file__).resolve().parents[1]
SHOTS_DIR = ROOT_DIR / "marketing" / "assets" / "screenshots"
CHARTS_DIR = ROOT_DIR / "evaluation" / "charts"
LIVE_FRAMES_DIR = ROOT_DIR / "marketing" / "footage" / "live_frames"
SLIDES_DIR = ROOT_DIR / "marketing" / "footage" / "slides"
LIVE_RECORDING_MP4 = ROOT_DIR / "marketing" / "footage" / "live_app_recording.mp4"
EXPORTS_DIR = ROOT_DIR / "marketing" / "exports"
OUTPUT_MP4 = EXPORTS_DIR / "CloudPilot_Promo.mp4"


def render_slide(
    out_path: Path,
    badge: str,
    title: str,
    subtitle_en: str,
    subtitle_cn: str,
    image_paths: List[Path],
    footer_caption: str,
) -> None:
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor="#0b0f17")
    fig.text(0.05, 0.92, badge, color="#34d399", fontsize=15, fontweight="bold")
    fig.text(0.05, 0.855, title, color="#f3f4f6", fontsize=28, fontweight="bold")
    fig.text(0.05, 0.805, subtitle_en, color="#9ca3af", fontsize=16)
    fig.text(0.05, 0.765, subtitle_cn, color="#38bdf8", fontsize=15)

    if len(image_paths) == 1:
        ax = fig.add_axes([0.08, 0.14, 0.84, 0.58])
        ax.imshow(mpimg.imread(str(image_paths[0])))
        ax.axis("off")
    elif len(image_paths) >= 2:
        ax1 = fig.add_axes([0.05, 0.15, 0.43, 0.56])
        ax2 = fig.add_axes([0.52, 0.15, 0.43, 0.56])
        ax1.imshow(mpimg.imread(str(image_paths[0])))
        ax1.axis("off")
        ax2.imshow(mpimg.imread(str(image_paths[1])))
        ax2.axis("off")

    fig.text(
        0.5,
        0.055,
        footer_caption,
        color="#ffffff",
        fontsize=16,
        fontweight="bold",
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#161f30", edgecolor="#38bdf8", alpha=0.95),
    )
    fig.savefig(out_path, dpi=100, facecolor="#0b0f17")
    plt.close(fig)


def main() -> int:
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    live_frames = sorted(LIVE_FRAMES_DIR.glob("frame_*.png"))
    if len(live_frames) < 20:
        raise RuntimeError(f"Expected >= 20 live recorded app frames in {LIVE_FRAMES_DIR}, found {len(live_frames)}")

    # 1. Encode standalone continuous live app recording (marketing/footage/live_app_recording.mp4)
    live_concat = SLIDES_DIR / "live_ffconcat.txt"
    live_lines: List[str] = []
    for lf in live_frames:
        live_lines.append(f"file '../live_frames/{lf.name}'")
        live_lines.append("duration 0.65")
    live_lines.append(f"file '../live_frames/{live_frames[-1].name}'")
    live_concat.write_text("\n".join(live_lines) + "\n", encoding="utf-8")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(live_concat),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0b0f17,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-movflags", "+faststart",
            str(LIVE_RECORDING_MP4),
        ],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )

    # 2. Render benchmark & closing cards and combine with all 36 live app frames into CloudPilot_Promo.mp4
    bench_slide = SLIDES_DIR / "slide_04.png"
    render_slide(
        bench_slide,
        "SCENE 4 · THREE-MODEL (A/B/C) ON-MAC BENCHMARK & TWO-LAYER SECURITY",
        "Fine-Tuned Model B: 95.31% Grounding & 92.86% Model-Only Safety Refusal",
        "Self-run offline benchmark (not an official public leaderboard rank). Post-hoc unmodified A/C baseline disclosed.",
        "本机 MLX LoRA 微调使精确接地率从 56.25% 升至 95.31%，纯模型安全拒答率从 0.0% 升至 92.86% (26/28)",
        [CHARTS_DIR / "accuracy_comparison.png", CHARTS_DIR / "family_breakdown.png"],
        "[00:23] Model B reaches 95.31% grounding & 92.86% model-only refusal at 167.96 tok/s on Apple M4.",
    )

    closing_slide = SLIDES_DIR / "slide_05.png"
    render_slide(
        closing_slide,
        "SCENE 5 · SELF-CONTAINED DMG WITH BUNDLED PYTHON 3.13 & .SAFETENSORS WEIGHTS",
        "CloudPilot v1.0 for macOS — Standalone Offline Execution Verified",
        "Bundles Python 3.13 + MLX + Fused Model B (.safetensors) inside CloudPilot.app · Apache-2.0 License",
        "安装包自带 Python 3.13 解释器、MLX 运行时与微调权重 (.safetensors)，干净 Mac 断网可直接运行",
        [SHOTS_DIR / "04_local_models.png", SHOTS_DIR / "05_settings_privacy.png"],
        "[00:28] Download CloudPilot-v1.0-macOS.dmg from GitHub Release v1.0.0 — 100% On-Mac AI.",
    )

    full_concat = SLIDES_DIR / "ffconcat.txt"
    full_lines: List[str] = []
    for lf in live_frames:
        full_lines.append(f"file '../live_frames/{lf.name}'")
        full_lines.append("duration 0.65")
    full_lines.append("file 'slide_04.png'")
    full_lines.append("duration 4.5")
    full_lines.append("file 'slide_05.png'")
    full_lines.append("duration 3.5")
    full_lines.append("file 'slide_05.png'")
    full_concat.write_text("\n".join(full_lines) + "\n", encoding="utf-8")

    audio_aiff = SLIDES_DIR / "narration.aiff"
    narration_text = (
        "CloudPilot. Local Intelligence, Local Execution. "
        "Watch the real native macOS app organize study P D Fs, markdown notes, and C S V sheets while completely offline with network sockets blocked. "
        "Local Planner P compiles a ten-step non-destructive plan, and bundled Fine-Tuned Model B executes each step on Apple M4 Metal at one hundred sixty-eight tokens per second. "
        "On-Mac LoRA fine-tuning improved exact tool grounding from fifty-six point two percent to ninety-five point three percent, and raised model-only safety refusal from zero percent to ninety-two point九 percent."
    )
    use_say_audio = False
    if shutil.which("say"):
        proc_say = subprocess.run(["say", "-o", str(audio_aiff), narration_text], capture_output=True, text=True)
        if proc_say.returncode == 0 and audio_aiff.exists() and audio_aiff.stat().st_size > 1000:
            use_say_audio = True

    vf_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0b0f17,format=yuv420p"
    if use_say_audio:
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(full_concat),
            "-i", str(audio_aiff),
            "-vf", vf_filter,
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(OUTPUT_MP4),
        ]
    else:
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(full_concat),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", vf_filter,
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-t", "31.4",
            "-movflags", "+faststart",
            str(OUTPUT_MP4),
        ]

    subprocess.run(cmd_ffmpeg, cwd=ROOT_DIR, check=True, capture_output=True, text=True)
    print(
        f"Rendered live app recording ({LIVE_RECORDING_MP4.stat().st_size / 1024:.1f} KB) and "
        f"final promo video ({OUTPUT_MP4.stat().st_size / 1024:.1f} KB) from {len(live_frames)} live app frames + 2 benchmark cards."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
