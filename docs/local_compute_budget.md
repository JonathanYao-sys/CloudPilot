# CloudPilot — Local Compute, Memory & Disk Budget (Phase 0)

> **Machine:** Apple M4 MacBook Air (24 GB Unified Memory, 36.64 GB Free SSD)  
> **Constraint:** 100% On-Mac Compute (`agent.md` Section 0 & Section 5.7)

## 1. Unified Memory Budget (24 GB Total / 17.76 GiB Metal Recommended Working Set)

Because desktop applications and macOS system services consume ~6–8 GB of unified memory during normal operation, CloudPilot allocates a strict **<= 4.0 GB peak Metal memory ceiling** for all AI operations:

| Workload | Resident Models | Measured / Projected Peak Metal RAM | Safety Margin vs 17.76 GiB Limit |
| --- | --- | --- | --- |
| **Local Planner (P)** | `Qwen2.5-0.5B-Instruct-4bit` + deterministic schema engine | `~360 MB` | > 17.0 GiB free |
| **Local Executor (A / B)** | `Qwen2.5-0.5B-Instruct-4bit` + LoRA adapter / fused model | `~365 MB` | > 17.0 GiB free |
| **Baseline Comparison (C)** | `SmolLM2-135M-Instruct` | `~298 MB` | > 17.0 GiB free |
| **Sequential P → B Runtime** | Shared base checkpoint / sequential invocation | `~380 MB` | No dual-model residency required |
| **On-Mac LoRA Fine-Tuning** | `mlx_lm.lora` (batch=2, rank=8, layers=8, seq_len=512) | `~1.15 GB` | > 16.5 GiB free |

## 2. SSD Storage Budget (36.64 GB Available)

To protect the user's SSD from running low on space, total project footprint (including model cache, datasets, fused weights, `.app`, `.dmg`, benchmark logs, and MP4 video) is capped at **<= 2.5 GB**:

| Artifact Category | Path | Budgeted Size | Actual / Expected |
| --- | --- | --- | --- |
| Cached Model A (`Qwen2.5-0.5B-Instruct-4bit`) | `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit` | 300 MB | `278.41 MB` |
| Cached Model C (`SmolLM2-135M-Instruct`) | `.hf_cache/models/SmolLM2-135M-Instruct` | 300 MB | `261.19 MB` |
| Synthetic Datasets (`train`/`val`/`test`) | `training/datasets/*.jsonl` | 15 MB | `~3 MB` |
| Fine-Tuned LoRA Adapter (`B`) | `model/adapters/adapters.safetensors` | 25 MB | `~6 MB` |
| Fused Deployment Model (`B-fused`) | `model/deployment/` | 320 MB | `~280 MB` |
| macOS Application & DMG | `release/artifacts/` | 100 MB | `~25 MB` |
| Evaluation Logs, Charts & Promo Video | `evaluation/` + `marketing/exports/` | 50 MB | `~15 MB` |
| **Total Workspace Disk Usage** | `CloudPilot` | **<= 1.2 GB** | **~870 MB** (leaves >35.5 GB free) |

## 3. Thermal & Energy Envelope (Fanless MacBook Air M4)

- **Observation:** The M4 MacBook Air uses passive cooling. Short bursts (< 3 minutes) run at full clock without thermal throttling.
- **Engineering Decision:**
  - Keep LoRA fine-tuning compact and high-signal: `Qwen2.5-0.5B-Instruct-4bit` with 8 LoRA layers, batch size 2, max sequence length 512, and 200 iterations completes in **~35–50 seconds** at ~150–180 tok/s, avoiding thermal throttling entirely.
  - Use sequential model loading during A/B/C evaluation and explicit `mx.clear_cache()` between model runs.
