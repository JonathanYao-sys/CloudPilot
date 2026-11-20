# CloudPilot — Local Intelligence. Local Execution.
### 云领航 (CloudPilot) — 100% 本地规划与本地执行的 macOS AI 智能体

> **Specification:** `agent.md` v4.0 — **LOCAL-ONLY**  
> **Workflow Architecture:** `agent.md -> Orchestrator (orchestrator.py) -> Coding Agent -> progress.json + Git Checkpoints`  
> **Hardware Verified:** Apple M4 MacBook Air (`Mac16,12`, 10-core CPU, 10-core Metal 4 GPU, 24 GB Unified Memory, macOS `27.2.1`)  
> **Cloud Compute / Cloud API Keys:** **ZERO (0 Remote Calls, `HF_HUB_OFFLINE=1`)**

---

## 中文快速开始 (Chinese Quick Start)

### 1. 产品简介
**CloudPilot（云领航）** 是一款完全运行在您自己 Mac 上的离线桌面文件整理 AI 智能体。它不依赖任何云端大模型 API（无需 OpenAI / Anthropic / Google 密钥），所有任务规划（Local Planner `P`）、微调工具调用推理（Local Fine-Tuned Executor `B`）、确定性安全校验（Policy Validator）以及文件操作与 SHA-256 完整性验证全部在您的 Apple Silicon Mac 本地 Metal GPU 上完成。

### 2. 三步离线安装与使用
1. **安装应用：** 双击打开 `release/artifacts/CloudPilot-v1.0-macOS.dmg`，将 `CloudPilot.app` 拖入 `Applications`（应用程序）文件夹。首次打开如遇 macOS Gatekeeper 提示（本地 Ad-hoc 签名，未经过付费 Apple Developer ID 公证），请右键点击 `CloudPilot.app` 选择 **“打开 (Open)”**。
2. **授权沙盒工作区：** 在应用首页（**Home / Chat**）选择您需要整理的本地文件夹（默认仅允许访问显式授权的工作区根目录，自动拦截 `..` 路径穿越与外部软链接）。
3. **预览计划并离线执行：** 输入自然语言整理需求（例如：*“按类别整理学习 PDF、笔记和表格并校验 SHA-256”*），点击 **Generate Local Plan Preview** 预览非破坏性复制计划（默认 `copy_file` + `on_conflict="skip"`），确认无误后点击 **Approve & Execute with Model B** 即可在断网状态下完成整理与哈希校验。

---

## English Technical Overview

### 1. Autonomous Workflow Architecture (`orchestrator.py` + `progress.json`)

This repository implements the closed-loop autonomous development workflow:

```text
  agent.md (All Product Requirements & Final Acceptance Criteria)
                              ↓
  Orchestrator (`orchestrator.py`: Read Plan · Assign Next Stage · Record State)
                              ↓
  Coding Agent (Write Code → Run → Test → Auto-Repair within retry bounds)
                              ↓
  progress.json + Git Checkpoints (`checkpoint-M0` .. `checkpoint-M7`)
       ↺ Unfinished → Resume Execution / All Passed → Finish
```

### 2. Seven Mandatory Deliverables Summary

| # | Deliverable | Local Verified Path & Public URL | Status | Verification Evidence |
| --- | --- | --- | --- | --- |
| **1** | **Fine-Tuned Model Weights (Model B)** | `model/adapters/adapters.safetensors` (`5.61 MiB`) & `model/deployment/model.safetensors` (`265.18 MiB`) · [Release Asset](https://github.com/JonathanYao-sys/CloudPilot/releases/tag/v1.0.0) | `DONE` | Trained on Apple M4 via `mlx_lm.lora` (160 iters, val loss `3.728` [iter 1] → `0.348` [best, iter 120] / `0.366` [final, iter 160]); `model/MODEL_CARD.md` |
| **2** | **macOS Application (`.app` & `.dmg`)** | `release/artifacts/CloudPilot.app` & `release/artifacts/CloudPilot-v1.0-macOS.dmg` (`487.01 MiB` / `510,661,870 B` self-contained with Python 3.13 + MLX + Model B) · [Release Download](https://github.com/JonathanYao-sys/CloudPilot/releases/download/v1.0.0/CloudPilot-v1.0-macOS.dmg) | `DONE` | Native SwiftUI (`arm64`), bundles Python 3.13 interpreter, MLX packages, `model.safetensors` & backend; clean-Mac stripped-env DMG mount+install verified offline |
| **3** | **User & Technical Documentation** | `README.md`, `docs/*.md`, `docs/ADR/0001-*.md` | `DONE` | CN Quick Start + EN Technical Docs, Security, Privacy, Offline Compliance |
| **4** | **GitHub Repository / Release** | [`https://github.com/JonathanYao-sys/CloudPilot`](https://github.com/JonathanYao-sys/CloudPilot) · [Release `v1.0.0`](https://github.com/JonathanYao-sys/CloudPilot/releases/tag/v1.0.0) | `DONE` | Audited repo, `checkpoint-M0..M8` tags, verified release assets & SHA-256 checksums |
| **5** | **Three-Model Benchmark Report (A/B/C)** | `evaluation/EVALUATION_REPORT.md`, `evaluation/results.csv`, `evaluation/charts/*.png`, `evaluation/baselines/PRETRAIN_BASELINE_REPORT.md` (post-hoc unmodified A/C baseline) | `DONE` | Model B (`95.31%` grounding, `92.86%` model-only safety refusal) vs. Base A (`56.25%` / `0.0%`) vs. Small C (`0.0%` / `0.0%`) |
| **6** | **Product Launch Website** | `website/index.html`, `website/styles.css`, `website/app.js` · [`https://jonathanyao-sys.github.io/CloudPilot/website/`](https://jonathanyao-sys.github.io/CloudPilot/website/) | `DONE` | 100% local static HTML/CSS/JS with 6 distinct real screenshots & benchmark charts, 0 CDN links |
| **7** | **Promotional Video (`.mp4`)** | `marketing/exports/CloudPilot_Promo.mp4` (`5.59 MiB` / `5,860,554 B`, `155.06s` Mandarin voice narration + `CloudPilot_Promo.srt`) & `marketing/footage/live_app_recording.mp4` (`1.50 MiB`) · [Release Video Asset](https://github.com/JonathanYao-sys/CloudPilot/releases/download/v1.0.0/CloudPilot_Promo.mp4) | `DONE` | 6-chapter Mandarin-voiced 1080p H.264+AAC MP4 combining 36-frame continuous live app recording, benchmark charts, and synchronized subtitles via FFmpeg |

### 3. Reproducing the Entire Project Offline on macOS

```bash
# 1. Inspect orchestrator status & milestone checkpoints
.venv/bin/python orchestrator.py status

# 2. Run the full offline pytest verification suite (M0 through M7)
HF_HUB_OFFLINE=1 .venv/bin/pytest -v

# 3. Run the CLI planning & execution loop with network disabled
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop models
```
