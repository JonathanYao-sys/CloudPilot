# CloudPilot — Offline Compliance Report (`docs/offline_compliance.md`)

> **Required by:** `agent.md` Section 16 (`OFFLINE COMPLIANCE REPORT`)  
> **Verification Date:** `2026-11-20`  
> **Compliance Verdict:** **100% LOCAL AI & COMPUTE COMPLIANT**

## 1. All Model Names, Origins, and Local Training / Inference Processes

| Model Role | Model Name / Checkpoint | Origin / Local Cache Path | SHA-256 Checksum | Local Process on This Mac |
| --- | --- | --- | --- | --- |
| **A (Original Base Executor)** | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` | `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit/model.safetensors` | `ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153` | Local Metal 4 GPU inference via `mlx_lm` (`176.85 tok/s`) |
| **B (Fine-Tuned Executor — Adapter)** | `CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1` | `model/adapters/adapters.safetensors` (`5.61 MB`) | `49b6f62a9838ff4e69b62249a7eb10ce6430d8f7a4f0ce8a3eaa43d6512b66e9` | Trained locally on this Mac via `mlx_lm.lora` (160 iters, `210.05s`) |
| **B (Fine-Tuned Executor — Fused)** | `CloudPilot-Qwen2.5-0.5B-Executor-Fused-v1` | `model/deployment/model.safetensors` (`265.18 MB`) | `97cd74ed52a094ff05068216e67c48be9415cc58c4bde29cb95a3cc0983e7706` | Fused locally via `mlx_lm.fuse` (`1.57s`) and loaded in `CloudPilot.app` (`167.87 tok/s`) |
| **C (Independent Small Baseline)** | `mlx-community/SmolLM2-135M-Instruct` | `.hf_cache/models/SmolLM2-135M-Instruct/model.safetensors` | `989e3ef746b41999ca096055a60c87057b8e842824253391bc0d9ed8dfc6936e` | Local Metal 4 GPU inference via `mlx_lm` (`216.29 tok/s`) |
| **P (Local Planner)** | `Qwen2.5-0.5B-Instruct-4bit` + Deterministic Schema Compiler | `app/local_planner/planner.py` | Shares Base A weights | Sequential on-Mac planning + schema compilation (`TaskPlanV1`) |

## 2. Development Agent & Workflow Orchestrator Audit

- **Workflow Orchestrator:** `orchestrator.py` + `progress.json` + local Git tags (`checkpoint-M0` through `checkpoint-M7`).
- **Execution Proof:** Every build, dataset synthesis, LoRA fine-tuning run, model fusion, benchmark evaluation, SwiftUI compilation (`swiftc`), DMG creation (`hdiutil`), screenshot export, and FFmpeg MP4 video render executed directly on this Apple M4 MacBook Air (`Mac16,12`, 24 GB RAM).

## 3. Commands & Logs Confirming Training Occurred on This Mac

- **Training Command:** `.venv/bin/python training/scripts/train_local_lora.py` (invoking `mlx_lm lora --config training/configs/lora_config.yaml` and `mlx_lm fuse`)
- **Saved Log File:** `logs/m4_lora_train.log`
- **Saved Metrics File:** `training/reports/training_metrics.json`
- **Evidence Summary:**
  - Trainable parameters: `0.297% (1.466M/494.033M)` across 8 LoRA layers (`rank=8`)
  - Validation loss improved from `3.728` (iter 1) to `0.348` (iter 120) / `0.366` (iter 160)
  - Training loss improved from `0.962` (iter 10) to `0.070` (iter 160)
  - Held-out test exact argument grounding improved from `56.25%` (Base A) to **`95.31%`** (Fine-Tuned B).

## 4. List of Allowed Network Transfers (Provisioning Only, Zero Personal Data)

| Transfer Type | Source | Local Destination | Personal Data Sent? |
| --- | --- | --- | --- |
| Open-weight checkpoint download (A) | HuggingFace Hub (`mlx-community/Qwen2.5-0.5B-Instruct-4bit`) | `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit` | **No** |
| Open-weight checkpoint download (C) | HuggingFace Hub (`mlx-community/SmolLM2-135M-Instruct`) | `.hf_cache/models/SmolLM2-135M-Instruct` | **No** |
| Open-source Python wheels | PyPI (`mlx`, `mlx-lm`, `pydantic`, `jsonschema`, `pytest`, `matplotlib`) | `.venv/` | **No** |

## 5. Network-Disconnected App & Runtime Test Evidence

- **Socket-Blocked Pytest Proof (`tests/test_m2_offline_loop.py`):** Monkeypatches `socket.socket.connect` and `socket.create_connection` to raise `RuntimeError("NETWORK_DISABLED_BY_OFFLINE_PROOF")` on any connection attempt. Both `test_offline_end_to_end_natural_language_vertical_slice` and `test_offline_error_replan_and_cancellation` **PASSED** while sockets were blocked.
- **Native macOS App Offline Self-Test (`tests/test_m5_macos_app_and_dmg.py`):** Runs `release/artifacts/CloudPilot.app/Contents/MacOS/CloudPilot --headless-self-test` with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, verifying end-to-end file organization, SHA-256 verification, and manifest generation (`status: PASSED`).

## 6. Online Storage / Distribution Services Confirmation

- **Authorized Publication Host:** Following explicit user authorization (`M8`), GitHub (`https://github.com/JonathanYao-sys/CloudPilot`), GitHub Releases (`https://github.com/JonathanYao-sys/CloudPilot/releases/tag/v1.0.0`), and GitHub Pages (`https://jonathanyao-sys.github.io/CloudPilot/website/`) were used **solely for static file storage and distribution transport**.
- **Zero Remote Compute Confirmation:** No GitHub Actions build runners, remote CI/CD workflows, cloud GPUs, or hosted AI APIs were invoked at any stage. All code compilation, synthetic dataset generation, MLX LoRA fine-tuning, weight fusion, A/B/C benchmarking, DMG packaging, static website authoring, and FFmpeg video rendering occurred 100% locally on the user's Apple M4 MacBook Air.
