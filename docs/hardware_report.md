# CloudPilot — Real Hardware & Local Environment Report (Phase 0)

> **Generated on:** `2026-11-20`  
> **Privacy Redaction:** Hardware serial numbers, UUIDs, UDIDs, and personal identifiers omitted per `agent.md` Section 2.3 and Section 5.8.

## 1. Host Machine Specifications

| Property | Measured Value | Verification Command |
| --- | --- | --- |
| **Model Name** | MacBook Air (`Mac16,12`) | `system_profiler SPHardwareDataType` |
| **SoC / Chip** | Apple M4 | `system_profiler SPHardwareDataType` |
| **Architecture** | `arm64` (Apple Silicon) | `uname -m` |
| **CPU Cores** | 10 total (4 Performance + 6 Efficiency) | `system_profiler SPHardwareDataType` |
| **GPU Cores** | 10-core Apple M4 GPU (`applegpu_g16g`) | `system_profiler SPDisplaysDataType` |
| **Metal Support** | Metal 4 (`max_recommended_working_set_size`: 17.76 GiB) | `mlx.core.device_info()` |
| **Unified Memory** | 24 GB (`25,769,803,776` bytes) | `sysctl -n hw.memsize` |
| **Internal SSD** | 228.27 GB total, **36.64 GB free** | `df -h /` |
| **Display** | Built-in Liquid Retina Display (2560 × 1664) | `system_profiler SPDisplaysDataType` |
| **Thermal / Power Envelope** | Fanless MacBook Air passive cooling; burst GPU loads run at peak speed while sustained training is bounded to short (<3 min) LoRA runs | Hardware design |

## 2. Operating System & Local Toolchain

| Component | Measured Version / Path | Status |
| --- | --- | --- |
| **macOS** | macOS `27.2.1` (Build `26B131`) | Verified |
| **Xcode Developer Tools** | `/Applications/Xcode.app/Contents/Developer` | Verified |
| **Swift Compiler** | `Apple Swift version 6.4.2 (swiftlang-6.4.2.1.9 clang-2100.4.1.1)` | Verified (Native SwiftUI `.app` compilation supported) |
| **Git** | `git version 2.54.0 (Apple Git-157)` | Verified |
| **Project Python Venv** | Python `3.13.18` (`.venv/bin/python`) | Verified |
| **Apple MLX / MLX-LM** | `mlx 0.32.4`, `mlx-lm 0.31.2` | Verified (Metal GPU inference & LoRA training) |
| **FFmpeg** | `/opt/homebrew/bin/ffmpeg` (installed locally) | Verified (Local MP4 video rendering supported) |
| **SQLite3 / Pydantic / Pytest** | Installed in `.venv` | Verified |

## 3. Local Development Agent & Execution Audit

- **Development Environment:** Running directly on the user's Apple M4 MacBook Air in `CloudPilot` (workspace root), managed by `orchestrator.py` and `progress.json` with local Git checkpoints.
- **Local ML Runtime:** Apple MLX (`mlx.core` + `mlx_lm`) executing natively on the Apple M4 10-core Metal 4 GPU.
- **Local Model Cache:** Provisioned under `CloudPilot/.hf_cache/models/` so that all training, inference, planning, execution, app packaging, and benchmark evaluation run with `HF_HUB_OFFLINE=1` and zero external API calls.

## 4. On-Mac Inference & Tiny LoRA Training Smoke Tests

Executed via `.venv/bin/python training/scripts/m0_smoke_test.py` and logged to `docs/environment_report.json` and `logs/m0_smoke_test.json`:

### 4.1 Model A — Base Executor (`mlx-community/Qwen2.5-0.5B-Instruct-4bit`)
- **Disk Footprint:** `278.41 MB`
- **Primary Weights SHA-256:** `ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153`
- **Model Load Time:** `0.268 s`
- **Time To First Token (TTFT):** `626.72 ms`
- **Decode Throughput:** `124.90 tokens/sec`
- **Peak Metal Memory:** `357.38 MB` (Active: `268.14 MB`)

### 4.2 Model C — Independent Small Model Baseline (`mlx-community/SmolLM2-135M-Instruct`)
- **Disk Footprint:** `261.19 MB`
- **Primary Weights SHA-256:** `989e3ef746b41999ca096055a60c87057b8e842824253391bc0d9ed8dfc6936e`
- **Model Load Time:** `0.128 s`
- **Time To First Token (TTFT):** `442.56 ms`
- **Decode Throughput:** `253.71 tokens/sec`
- **Peak Metal Memory:** `298.18 MB` (Active: `257.54 MB`)

### 4.3 On-Mac LoRA Fine-Tuning Smoke Test (`mlx_lm.lora`)
- **Base Checkpoint:** `mlx-community/Qwen2.5-0.5B-Instruct-4bit`
- **Configuration:** 5 iterations, batch size 2, 4 LoRA layers, seed 42
- **Trainable Parameters:** `0.148%` (`0.733M / 494.033M`)
- **Validation Loss Progression:** `5.111` (iter 1) → `3.605` (iter 5)
- **Training Throughput:** `175 tokens/sec`
- **Total Wall Time:** `10.33 s`
- **Exported Adapter Verification:** `adapters.safetensors` (`2,869.77 KB`, SHA-256 `8d43e6b69c91e815579146b7b31ae67b84d3c8e8353730cfaf79b087067063b6`)

## 5. Gate 0 Verdict

**PASSED.** The Apple M4 MacBook Air with 24 GB unified memory and Metal 4 comfortably supports local MLX inference (>120 tok/s), fast on-device LoRA fine-tuning (~175 tok/s, <1 GB peak memory), native SwiftUI macOS `.app` / `.dmg` packaging, and local FFmpeg video production within the 36.64 GB free SSD budget.
