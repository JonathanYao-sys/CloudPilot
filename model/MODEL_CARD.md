# Model Card — CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1 (Model B)

## 1. Model Identity & Provenance

- **Model Name:** `CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1` (Model B)
- **Parent Base Model (A):** `mlx-community/Qwen2.5-0.5B-Instruct-4bit` (`Qwen2.5-0.5B-Instruct`, 4-bit quantized MLX checkpoint)
- **Base Model SHA-256:** `ddffab9cbc7bf6dde941c6724841eeca8981fcfa81ca20ff8efff1396326d153`
- **License:** Apache-2.0
- **Training Machine:** User's Apple M4 MacBook Air (`Mac16,12`, 10-core CPU, 10-core Metal 4 GPU, 24 GB Unified Memory)
- **Training Framework:** Apple MLX (`mlx_lm.lora`) — **100% On-Mac Local Metal Compute (0 Cloud GPUs / 0 Remote APIs)**

## 2. Artifact Distinction: LoRA Adapter vs. Fused Deployment Checkpoint

Per `agent.md` Section 10.7, CloudPilot exports and clearly distinguishes both artifact forms:

| Artifact Type | Relative Path | Size | SHA-256 Checksum | Usage |
| --- | --- | --- | --- | --- |
| **LoRA Adapter Weights** | `model/adapters/adapters.safetensors` | `5.61 MB` | `49b6f62a9838ff4e69b62249a7eb10ce6430d8f7a4f0ce8a3eaa43d6512b66e9` | Lightweight rank-8 LoRA delta loaded on top of Base A |
| **LoRA Adapter Config** | `model/adapters/adapter_config.json` | `~1 KB` | `c14454f9ed3e857965144a85c0b5539f6fc0bacf21d417364cc89f790496d30c` | Hyperparameters & target layer specification |
| **Fused Deployment Model** | `model/deployment/model.safetensors` | `265.18 MB` | `97cd74ed52a094ff05068216e67c48be9415cc58c4bde29cb95a3cc0983e7706` | Self-contained fused checkpoint loaded by `CloudPilot.app` |

## 3. Local Training Dataset & Hyperparameters

- **Training Split:** `training/datasets/train.jsonl` (`1,000` rule-validated synthetic examples across 8 task families)
- **Validation Split:** `training/datasets/validation.jsonl` (`160` examples; used exclusively for checkpoint selection)
- **Held-Out Test Split:** `training/datasets/test.jsonl` (`160` frozen examples; never seen during training)
- **Hyperparameters (`training/configs/lora_config.yaml`):**
  - `num_layers`: `8`
  - `lora_parameters`: `rank=8, scale=20.0, dropout=0.0`
  - `batch_size`: `4`
  - `iters`: `160`
  - `learning_rate`: `1e-4` (Adam)
  - `max_seq_length`: `512`
  - `seed`: `42`

## 4. Measured On-Mac Training Progression

- **Trainable Parameters:** `Trainable parameters: 0.297% (1.466M/494.033M)`
- **Wall-Clock Training Duration:** `210.05 seconds`
- **Fuse & Export Duration:** `1.57 seconds`
- **Validation Loss:** `3.728` (iter 1) → `0.348` (best, iter 120) / `0.366` (final, iter 160)
- **Training Loss:** `0.962` (iter 10) → **`0.07`** (iter 160)

## 5. Intended Use, Boundaries & Limitations

- **Intended Role:** Local Executor Model (`B`) inside CloudPilot's offline macOS architecture. Maps bounded plan steps and workspace file listings to allowlisted JSON tool calls (`list_files`, `get_file_info`, `create_folder`, `copy_file`, `verify_file`, `generate_manifest`) or structured abstentions/errors (`abstain`, `report_error`).
- **Safety Boundary:** Model output is always treated as untrusted until verified by `PolicyValidator` (`app/security/policy_validator.py`). The model has no shell, terminal, network, or arbitrary file-deletion capability.
- **Limitations:** Trained specifically for bounded workspace file organization within the CloudPilot v1.0 protocol schema (`max_seq_length=512`); not intended for open-ended chat or general code generation.

## 6. Local Loading & Reproduction Instructions

```bash
# 1. Reproduce on-Mac LoRA fine-tuning and fusion completely offline:
HF_HUB_OFFLINE=1 .venv/bin/python training/scripts/train_local_lora.py

# 2. Load via CloudPilot's LocalMLXRuntime:
HF_HUB_OFFLINE=1 .venv/bin/python -m app.local_executor.orchestration_loop models
```
