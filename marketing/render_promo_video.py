#!/usr/bin/env python3
"""
CloudPilot Local Promotional Video Renderer (Phase 10 / M7)
Composites 1920x1080 HD storyboard slides integrating real CloudPilot.app screenshots
and real A/B/C benchmark charts, generates offline macOS narration via `/usr/bin/say` (or silent fallback),
and encodes `marketing/exports/CloudPilot_Promo.mp4` locally via `/opt/homebrew/bin/ffmpeg`.
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
FRAMES_DIR = ROOT_DIR / "marketing" / "footage" / "slides"
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

    # Header text
    fig.text(0.05, 0.92, badge, color="#34d399", fontsize=15, fontweight="bold")
    fig.text(0.05, 0.855, title, color="#f3f4f6", fontsize=28, fontweight="bold")
    fig.text(0.05, 0.805, subtitle_en, color="#9ca3af", fontsize=16)
    fig.text(0.05, 0.765, subtitle_cn, color="#38bdf8", fontsize=15)

    if len(image_paths) == 1:
        ax = fig.add_axes([0.08, 0.14, 0.84, 0.58])
        img = mpimg.imread(str(image_paths[0]))
        ax.imshow(img)
        ax.axis("off")
    elif len(image_paths) >= 2:
        ax1 = fig.add_axes([0.05, 0.15, 0.43, 0.56])
        ax2 = fig.add_axes([0.52, 0.15, 0.43, 0.56])
        ax1.imshow(mpimg.imread(str(image_paths[0])))
        ax1.axis("off")
        ax2.imshow(mpimg.imread(str(image_paths[1])))
        ax2.axis("off")

    # Burned-in bottom subtitle bar
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
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    slides_spec: List[Tuple[str, int, str, str, str, str, List[Path], str]] = [
        (
            "slide_01.png",
            4,
            "SCENE 1 · OFFLINE VALUE PROPOSITION",
            "CloudPilot — Local Intelligence. Local Execution.",
            "100% On-Mac AI Agent · Apple M4 Metal 4 GPU · Zero Cloud API Keys Required",
            "CloudPilot 云领航：完全运行在 Mac 本地的离线 AI 智能体，无需任何云端 API 密钥",
            [SHOTS_DIR / "01_home_chat.png"],
            "[00:00] CloudPilot organizes your workspace locally on macOS with zero cloud data transfer.",
        ),
        (
            "slide_02.png",
            4,
            "SCENE 2 · LOCAL PLANNER & APPROVAL GATE",
            "Local Planner (P) -> Plan Preview & User Approval -> Fine-Tuned Executor (B)",
            "Every plan is schema-validated (TaskPlanV1) and previewed before any file operation occurs.",
            "本地规划器生成有界 DAG 计划，所有文件操作默认采用非破坏性复制 (on_conflict='skip') 并需用户审批",
            [SHOTS_DIR / "02_plan_preview.png"],
            "[00:04] Users preview and approve non-destructive copy plans before any file is touched.",
        ),
        (
            "slide_03.png",
            6,
            "SCENE 3 · NETWORK-DISABLED EXECUTION & LOCAL MODELS",
            "Real Offline App Execution (HF_HUB_OFFLINE=1) & On-Mac Model Inventory",
            "Model B grounds tool arguments; PolicyValidator blocks traversal/symlinks; SHA-256 verifies every file.",
            "断网环境下由本地微调模型 Model B 驱动执行，逐文件校验 SHA-256 哈希并记录 SQLite 审计日志",
            [SHOTS_DIR / "03_execution_monitor.png", SHOTS_DIR / "04_local_models.png"],
            "[00:08] Executed with network sockets disabled: 100% SHA-256 verified file copies on Apple M4.",
        ),
        (
            "slide_04.png",
            7,
            "SCENE 4 · THREE-MODEL (A/B/C) ON-MAC BENCHMARK & HONEST LIMITATIONS",
            "Fine-Tuned Model B Reaches 95.31% Grounding (+39.06% over Base A) at 167.87 tok/s",
            "Self-run offline benchmark (not an official public leaderboard rank). Bounded 6-tool MVP scope.",
            "本地 MLX LoRA 微调使精确工具接地准确率从 56.25% (Base A) 提升至 95.31% (Model B)，16项越权攻击全部拦截",
            [CHARTS_DIR / "accuracy_comparison.png", CHARTS_DIR / "family_breakdown.png"],
            "[00:14] On-Mac MLX LoRA fine-tuning improved held-out accuracy from 56.25% to 95.31% at 534 MB Metal RAM.",
        ),
        (
            "slide_05.png",
            5,
            "SCENE 5 · VERIFIED LOCAL RELEASE ARTIFACTS",
            "CloudPilot v1.0 for macOS — DMG, .safetensors Weights, Docs & Audit Trail",
            "Artifacts: CloudPilot-v1.0-macOS.dmg · model/adapters/adapters.safetensors · Apache-2.0 License",
            "完整交付：macOS 安装包 (.dmg)、本地微调权重 (.safetensors)、中英文档、静态网站与 SHA-256 清单",
            [SHOTS_DIR / "05_settings_privacy.png", SHOTS_DIR / "06_audit_history.png"],
            "[00:21] Download CloudPilot-v1.0-macOS.dmg and reproduce training & benchmarks 100% offline.",
        ),
    ]

    concat_lines: List[str] = []
    for fname, duration, badge, title, sub_en, sub_cn, imgs, footer in slides_spec:
        out_png = FRAMES_DIR / fname
        render_slide(out_png, badge, title, sub_en, sub_cn, imgs, footer)
        concat_lines.append(f"file '{out_png}'")
        concat_lines.append(f"duration {duration}")
    # Repeat last file per ffmpeg concat demuxer spec
    concat_lines.append(f"file '{FRAMES_DIR / slides_spec[-1][0]}'")

    concat_file = FRAMES_DIR / "ffconcat.txt"
    concat_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    # Generate optional local offline audio track (macOS /usr/bin/say or sine ambient chime via ffmpeg lavfi)
    audio_aiff = FRAMES_DIR / "narration.aiff"
    narration_text = (
        "CloudPilot. Local Intelligence, Local Execution. "
        "A one hundred percent offline macOS AI agent powered by Apple M L X on Apple M4. "
        "Local Planner P drafts a safe, non-destructive file organization plan. "
        "Our on-Mac fine-tuned Executor Model B reaches ninety-five point three percent accuracy at one hundred sixty-seven tokens per second, "
        "with zero cloud API keys and zero unauthorized file operations."
    )
    use_say_audio = False
    if shutil.which("say"):
        proc_say = subprocess.run(
            ["say", "-o", str(audio_aiff), narration_text],
            capture_output=True,
            text=True,
        )
        if proc_say.returncode == 0 and audio_aiff.exists() and audio_aiff.stat().st_size > 1000:
            use_say_audio = True

    if use_say_audio:
        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_aiff),
            "-vf", "scale=1920:1080,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(OUTPUT_MP4),
        ]
    else:
        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", "scale=1920:1080,format=yuv420p",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-t", "26",
            "-movflags", "+faststart",
            str(OUTPUT_MP4),
        ]

    subprocess.run(cmd_ffmpeg, cwd=ROOT_DIR, check=True, capture_output=True, text=True)
    print(f"Rendered playable promotional video to {OUTPUT_MP4.relative_to(ROOT_DIR)} ({OUTPUT_MP4.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
