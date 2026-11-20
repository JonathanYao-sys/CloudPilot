# ADR 0001: Local-Only Reference Architecture and Frozen A/B/C/P Model Selection

- **Date:** 2026-11-20
- **Status:** Accepted (Phase 1 / Gate 1)
- **Context:** `agent.md` v4.0 requires a 100% locally planned, locally executed macOS AI agent trained, evaluated, and packaged on the user's Apple M4 MacBook Air (24 GB RAM, 36.64 GB free disk).

## 1. Decision: Model Baselines (A, B, C, P)

Based on empirical Phase 0 measurements (`docs/environment_report.json`), we freeze the following four model roles:

| Role | Identifier | Checkpoint / Origin | License | Rationale |
| --- | --- | --- | --- | --- |
| **A (Base Executor)** | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` | Local `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit` (`SHA256: ddffab9c...`) | Apache-2.0 | Fast Metal inference (`124.9 tok/s`, `357 MB` peak RAM). Untrained base model exhibits formatting/schema drift on strict CloudPilot tool calls, making it an ideal candidate for on-Mac LoRA specialization. |
| **B (Fine-Tuned Executor)** | `CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1` | Derived from **A** via on-Mac `mlx_lm.lora` training (`model/adapters/` & fused `model/deployment/`) | Apache-2.0 | Trained strictly on this Mac to map bounded plan steps and workspace observations to valid, permission-aware CloudPilot JSON tool calls and abstentions. |
| **C (Independent Small Model)** | `mlx-community/SmolLM2-135M-Instruct` | Local `.hf_cache/models/SmolLM2-135M-Instruct` (`SHA256: 989e3ef7...`) | Apache-2.0 | Distinct architecture/family (`LlamaForCausalLM`, 135M params, `253.7 tok/s`, `298 MB` peak RAM) serving as the external local small-model baseline in Phase 7 A/B/C benchmarks. |
| **P (Local Planner)** | `CloudPilot Hybrid Local Planner (Qwen2.5-0.5B-Instruct-4bit + Deterministic Schema-Constrained Task Compiler)` | Shares Base A weights sequentially + rule-based schema compiler (`app/local_planner/planner.py`) | Apache-2.0 | Disclosed per `agent.md` Section 3 & Section 6: combines local LLM intent parsing with deterministic schema-constrained plan compilation so plans are 100% schema-valid without requiring two large models resident in RAM simultaneously. |

## 2. Decision: Separation of Concerns in the Planning–Execution Loop

1. **Local Planner (`P`):** Accepts a user's natural-language file organization request and workspace file listing, producing a bounded `TaskPlanV1` (`protocol/schemas/task_plan_v1.json`) where every mutating operation defaults to non-destructive `copy_file` with `on_conflict: "skip"` and requires explicit user plan approval.
2. **Local Executor (`B`):** Given an approved plan step and live workspace observation, predicts the exact JSON tool call (`{"tool": ..., "args": ...}`) or structured abstention/error (`{"tool": "abstain", "reason": ...}`).
3. **Policy Validator (`app/security/policy_validator.py`):** Deterministically enforces workspace root confinement, blocks path traversal (`..`), blocks external symlinks, enforces tool allowlist (`list_files`, `get_file_info`, `create_folder`, `copy_file`, `verify_file`, `generate_manifest`), enforces file-size/operation limits, and checks plan approval & idempotency keys before any filesystem access occurs.
4. **Deterministic Tool Runtime (`app/local_executor/tool_runtime.py`):** Executes validated operations using `pathlib` / `shutil` / `hashlib` with zero `eval` or shell execution, recording every state transition (`PENDING`, `AWAITING_APPROVAL`, `RUNNING`, `BLOCKED`, `FAILED`, `CANCELLED`, `COMPLETED`) in SQLite (`app/local_executor/state_store.py`).

## 3. Decision: Native macOS Application Packaging

We select **SwiftUI (`swiftc` 6.4.2)** for the native macOS desktop frontend (`app/frontend/CloudPilotApp.swift`), bundled as a genuine macOS `.app` (`release/artifacts/CloudPilot.app`) and packaged into an installable `.dmg` (`release/artifacts/CloudPilot-v1.0-macOS.dmg`) via `hdiutil`. The SwiftUI app communicates with the local Python/MLX runtime over local subprocess IPC / loopback without any cloud dependencies or API keys.
