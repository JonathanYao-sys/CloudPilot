#!/usr/bin/env python3
"""
CloudPilot Voiced Promotional Video Renderer (Phase 10 / M7)
Produces a 6-chapter, voice-narrated 1080p promotional video (`marketing/exports/CloudPilot_Promo.mp4`)
and companion SRT subtitle file (`marketing/exports/CloudPilot_Promo.srt`) using macOS offline
Mandarin TTS (`/usr/bin/say -v Tingting`) synchronized chapter-by-chapter with the 36 live
interactive app recording frames (`marketing/footage/live_frames/frame_*.png`) and A/B/C benchmark charts.

Clearly explains through both spoken Mandarin narration and burned-in bilingual subtitles:
  1. What CloudPilot is (100% offline macOS file-organization AI agent, zero cloud API keys)
  2. How the 4-layer local product architecture works (Planner P -> Approval Gate -> Executor B -> Deterministic Runtime)
  3. Real-time offline execution on Apple M4 Metal GPU (168 tok/s, SHA-256 verification)
  4. What engineering work was done on-Mac (1,320 synthetic dataset across 8 families, 160-iter MLX LoRA fine-tuning & weight fusion)
  5. What the A/B/C benchmark & two-layer security tests proved (95.31% grounding, 92.86% model-only safety refusal, 16/16 PolicyValidator blocks)
  6. How it is packaged & delivered (self-contained DMG bundling standalone Python 3.13 + MLX + .safetensors weights + orchestrator Git checkpoints)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

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
OUTPUT_CN_MP4 = EXPORTS_DIR / "CloudPilot_Promo_CN.mp4"
OUTPUT_SRT = EXPORTS_DIR / "CloudPilot_Promo.srt"
OUTPUT_CN_SRT = EXPORTS_DIR / "CloudPilot_Promo_CN.srt"


def get_audio_duration(audio_path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(proc.stdout)
    return float(info["format"]["duration"])


def format_srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    total_s = int(seconds)
    hrs = total_s // 3600
    mins = (total_s % 3600) // 60
    secs = total_s % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def compose_chapter_frame(
    out_path: Path,
    chapter_badge: str,
    chapter_title: str,
    chapter_en: str,
    image_paths: List[Path],
    spoken_cn_line: str,
) -> None:
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor="#0b0f17")

    # Top chapter header bar
    fig.text(0.04, 0.945, chapter_badge, color="#34d399", fontsize=14, fontweight="bold")
    fig.text(0.04, 0.895, chapter_title, color="#f3f4f6", fontsize=24, fontweight="bold")
    fig.text(0.04, 0.858, chapter_en, color="#38bdf8", fontsize=13.5)

    if len(image_paths) == 1:
        ax = fig.add_axes([0.06, 0.14, 0.88, 0.69])
        ax.imshow(mpimg.imread(str(image_paths[0])))
        ax.axis("off")
    elif len(image_paths) >= 2:
        ax1 = fig.add_axes([0.04, 0.15, 0.44, 0.67])
        ax2 = fig.add_axes([0.52, 0.15, 0.44, 0.67])
        ax1.imshow(mpimg.imread(str(image_paths[0])))
        ax1.axis("off")
        ax2.imshow(mpimg.imread(str(image_paths[1])))
        ax2.axis("off")

    # High-contrast bottom subtitle bar synchronized with the spoken voice narration
    fig.text(
        0.5,
        0.058,
        f"[中文语音解说]  {spoken_cn_line}",
        color="#ffffff",
        fontsize=17,
        fontweight="bold",
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.65", facecolor="#111827", edgecolor="#38bdf8", linewidth=1.8, alpha=0.96),
    )

    fig.savefig(out_path, dpi=100, facecolor="#0b0f17")
    plt.close(fig)


def main() -> int:
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    live_frames = sorted(LIVE_FRAMES_DIR.glob("frame_*.png"))
    if len(live_frames) < 30:
        raise RuntimeError(f"Expected >= 30 live recorded app frames in {LIVE_FRAMES_DIR}, found {len(live_frames)}")

    # 1. Encode standalone raw continuous live app recording (marketing/footage/live_app_recording.mp4)
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

    # 2. Define 6 voiced chapters explaining (a) What the product is and (b) What we built/trained/tested
    chapters: List[Dict[str, Any]] = [
        {
            "id": "ch01",
            "badge": "第一章 (1/6) · 产品定位 | WHAT IS CLOUDPILOT?",
            "title": "CloudPilot 云领航：100% 运行在 Mac 本地的离线 AI 文件整理智能体",
            "en": "A 100% On-Mac Offline AI File-Organization Agent · Zero Cloud API Keys · Total Data Privacy",
            "voice_text": (
                "欢迎了解 CloudPilot 云领航。这是一款百分之百运行在苹果 Mac 本地的离线 A I 文件整理智能体。"
                "它不需要任何云端 A P I 密钥，也不上传任何私人文件，所有任务规划、模型推理与安全执行全部在您的 Mac 本地完成。"
            ),
            "subtitles": [
                "欢迎了解 CloudPilot 云领航：一款 100% 运行在苹果 Mac 本地的离线 AI 文件整理智能体。",
                "无需任何云端 API 密钥，绝不上传私人文件，所有规划、推理与安全执行全部在 Mac 本地完成。",
            ],
            "frame_groups": [[lf] for lf in live_frames[0:6]],
        },
        {
            "id": "ch02",
            "badge": "第二章 (2/6) · 产品四层架构 | 4-LAYER LOCAL ARCHITECTURE & APPROVAL GATE",
            "title": "本地规划器 (Planner P) → 用户预览审批 → 微调执行模型 (B) → 确定性沙盒",
            "en": "Local Planner P compiles bounded TaskPlanV1 DAG -> User Approval Gate -> Non-destructive copy_file (on_conflict='skip')",
            "voice_text": (
                "在产品架构上，CloudPilot 采用四层本地安全闭环：第一层，本地规划器将自然语言指令拆解为十步结构化计划；"
                "第二层，所有写入步骤必须经过用户预览和审批；第三层，由本机微调模型生成工具调用；"
                "第四层，由确定性沙盒执行非破坏性复制，并对每个文件进行 S H A 二五六哈希校验。"
            ),
            "subtitles": [
                "四层本地安全闭环：① 本地规划器将自然语言拆解为 10 步结构化 DAG 计划；② 写入操作必须经用户预览审批；",
                "③ 本机微调模型生成 JSON 工具调用；④ 确定性沙盒执行非破坏性复制 (skip) 并逐文件校验 SHA-256 哈希。",
            ],
            "frame_groups": [[lf] for lf in live_frames[6:17]],
        },
        {
            "id": "ch03",
            "badge": "第三章 (3/6) · 实机断网执行演示 | LIVE OFFLINE EXECUTION ON APPLE M4 METAL 4",
            "title": "封锁网络 Socket 实机运行：Model B 以 168 tok/s 流式驱动十步文件整理",
            "en": "Network Sockets Blocked (--block-network) · Real-Time Streaming Execution on Apple M4 GPU at 168 tok/s",
            "voice_text": (
                "现在您看到的是在彻底封锁网络连接的实机环境下，应用调用内置微调模型 Model B 的实时执行过程。"
                "模型在苹果 M4 Metal G P U 上以每秒 168 个 token 的速度流式输出工具调用，"
                "自动创建分类目录、安全复制学习文档、笔记和表格，全部通过哈希校验并生成审计清单。"
            ),
            "subtitles": [
                "实机断网演示（封锁网络 Socket）：应用调用内置微调模型 Model B 在 Apple M4 Metal GPU 上实时推理；",
                "以 168 tok/s 流式输出 JSON 工具调用，自动创建分类目录、安全复制 PDF/笔记/表格并完成 SHA-256 校验。",
            ],
            "frame_groups": [[lf] for lf in live_frames[17:29]],
        },
        {
            "id": "ch04",
            "badge": "第四章 (4/6) · 我们做了什么：本地数据集与本机微调 | ON-MAC DATASET & MLX LORA TRAINING",
            "title": "本机合成 1,320 条八族零泄漏数据集 + Apple M4 本机 MLX LoRA 微调与权重融合",
            "en": "1,320 Validated Synthetic Examples (8 Families, 0 Leakage) + 160-Iter On-Mac MLX LoRA Training (Val Loss 3.728 -> 0.348)",
            "voice_text": (
                "在工程研发中，我们坚持零云端算力。我们在本机合成并规则校验了 1320 条覆盖八大任务族的零泄漏数据集；"
                "直接在这台 24 G B 内存的 M4 Mac 上，使用 Apple M L X 完成 160 步 LoRA 微调训练并融合导出部署权重，"
                "验证集损失从 3.728 降至最低 0.348。"
            ),
            "subtitles": [
                "研发工作 ①：零云端算力，在本机合成并校验 1,320 条覆盖 8 大任务族的零泄漏训练/验证/测试数据集；",
                "研发工作 ②：直接在 24GB M4 Mac 上用 MLX 完成 160 步 LoRA 微调与权重融合，验证损失从 3.728 降至 0.348。",
            ],
            "frame_groups": [
                [live_frames[29]],
                [SHOTS_DIR / "04_local_models.png", SHOTS_DIR / "03_execution_monitor.png"],
            ],
        },
        {
            "id": "ch05",
            "badge": "第五章 (5/6) · 我们做了什么：三模型评测与双层安全验证 | A/B/C BENCHMARK & 2-LAYER SECURITY",
            "title": "Model B 精确接地率提升至 95.31%，纯模型安全拒答率从 0% 跃升至 92.86%",
            "en": "Post-Hoc Unmodified A/C Baseline vs. Fine-Tuned B: 95.31% Grounding, 92.86% Model-Only Refusal + 16/16 PolicyValidator Blocks",
            "voice_text": (
                "我们对基座模型 A、本机微调模型 B 和独立小模型 C 进行了同机离线评测。"
                "微调后，模型 B 的工具精确接地率从 56.25% 提升至 95.31%；"
                "在不依赖规则拦截器的纯模型安全测试中，模型 B 自身对路径穿越和未授权覆盖的拒答率从 0% 提升到 92.86%；"
                "配合第二层确定性策略校验器，16 项越权攻击被百分之百拦截。"
            ),
            "subtitles": [
                "研发工作 ③：A/B/C 三模型同机离线评测，微调使精确工具接地率从 56.25% (Base A) 大幅提升至 95.31% (Model B)；",
                "纯模型安全拒答率从 0% 提升至 92.86% (26/28)，叠加第二层确定性 PolicyValidator 后 16 项越权攻击 100% 拦截。",
            ],
            "frame_groups": [
                [CHARTS_DIR / "accuracy_comparison_cn.png", CHARTS_DIR / "family_breakdown_cn.png"],
                [CHARTS_DIR / "accuracy_comparison_cn.png", CHARTS_DIR / "latency_memory_comparison_cn.png"],
            ],
        },
        {
            "id": "ch06",
            "badge": "第六章 (6/6) · 我们做了什么：自包含 DMG 打包与自动化交付 | SELF-CONTAINED DMG & GIT RELEASE",
            "title": "内置 Python 3.13 + MLX + 微调权重的 487 MiB 独立安装包与全套开源交付",
            "en": "Self-Contained DMG (Bundled Python 3.13 + MLX + Model B) · Orchestrator + Git Checkpoints M0..M8 · 26/26 Offline Pytest Passed",
            "voice_text": (
                "最后，我们将原生 Swift U I 应用、独立 Python 3.13 解释器、M L X 运行时和微调权重全部打包进 487 兆的 D M G 安装包，"
                "验证了在干净 Mac 环境下断网即可独立运行；"
                "并通过任务调度器、26 项自动化测试和 Git 检查点，完成了中英文档、静态网站与 GitHub Release 全套交付。"
            ),
            "subtitles": [
                "研发工作 ④：将原生 SwiftUI 应用、独立 Python 3.13 解释器、MLX 与微调权重封装进 487.01 MiB 自包含 DMG；",
                "通过 Orchestrator 调度器、26/26 离线自动化测试与 Git 检查点，完成中英文档、静态网站与 GitHub Release 全套交付。",
            ],
            "frame_groups": [[lf] for lf in live_frames[30:36]],
        },
    ]

    chapter_mp4s: List[Path] = []
    srt_entries: List[str] = []
    cumulative_time = 0.0
    srt_idx = 1

    for ch in chapters:
        cid = ch["id"]
        audio_aiff = SLIDES_DIR / f"{cid}.aiff"
        # Generate crystal-clear Mandarin voice narration using macOS built-in Tingting voice
        subprocess.run(
            ["say", "-v", "Tingting", "-r", "210", "-o", str(audio_aiff), ch["voice_text"]],
            check=True,
            capture_output=True,
            text=True,
        )
        duration = get_audio_duration(audio_aiff)

        frame_groups = ch["frame_groups"]
        n_frames = len(frame_groups)
        per_frame_dur = duration / n_frames

        # Build SRT entries for this chapter's 2 subtitle halves
        half_dur = duration / len(ch["subtitles"])
        for s_i, sub_line in enumerate(ch["subtitles"]):
            t_start = cumulative_time + s_i * half_dur
            t_end = cumulative_time + (s_i + 1) * half_dur
            srt_entries.append(
                f"{srt_idx}\n{format_srt_time(t_start)} --> {format_srt_time(t_end)}\n{sub_line}\n"
            )
            srt_idx += 1
        cumulative_time += duration

        ch_concat_lines: List[str] = []
        last_png_name = ""
        for f_idx, img_group in enumerate(frame_groups):
            sub_idx = min(int(f_idx * len(ch["subtitles"]) / n_frames), len(ch["subtitles"]) - 1)
            spoken_line = ch["subtitles"][sub_idx]
            out_png = SLIDES_DIR / f"{cid}_frame_{f_idx:02d}.png"
            compose_chapter_frame(
                out_path=out_png,
                chapter_badge=ch["badge"],
                chapter_title=ch["title"],
                chapter_en=ch["en"],
                image_paths=img_group,
                spoken_cn_line=spoken_line,
            )
            last_png_name = out_png.name
            ch_concat_lines.append(f"file '{out_png.name}'")
            ch_concat_lines.append(f"duration {per_frame_dur:.4f}")
        ch_concat_lines.append(f"file '{last_png_name}'")

        ch_concat_file = SLIDES_DIR / f"{cid}_concat.txt"
        ch_concat_file.write_text("\n".join(ch_concat_lines) + "\n", encoding="utf-8")

        ch_mp4 = SLIDES_DIR / f"{cid}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(ch_concat_file),
                "-i", str(audio_aiff),
                "-vf", "scale=1920:1080,format=yuv420p",
                "-r", "30",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-t", f"{duration:.3f}",
                str(ch_mp4),
            ],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        chapter_mp4s.append(ch_mp4)

    # Concatenate all 6 voiced chapter MP4s into final CloudPilot_Promo.mp4
    master_list = SLIDES_DIR / "master_chapters.txt"
    master_list.write_text(
        "\n".join(f"file '{p.name}'" for p in chapter_mp4s) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(master_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(OUTPUT_MP4),
        ],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )

    OUTPUT_SRT.write_text("\n".join(srt_entries), encoding="utf-8")
    OUTPUT_CN_SRT.write_text("\n".join(srt_entries), encoding="utf-8")
    OUTPUT_CN_MP4.write_bytes(OUTPUT_MP4.read_bytes())
    total_dur = get_audio_duration(OUTPUT_MP4)
    print(
        f"Rendered 6-chapter Mandarin-voiced promo video to {OUTPUT_MP4.relative_to(ROOT_DIR)} and "
        f"{OUTPUT_CN_MP4.relative_to(ROOT_DIR)} "
        f"({OUTPUT_MP4.stat().st_size / (1024 * 1024):.2f} MiB, duration={total_dur:.2f}s) "
        f"and subtitles to {OUTPUT_SRT.relative_to(ROOT_DIR)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
