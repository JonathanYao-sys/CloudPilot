# CloudPilot Post-Hoc Unmodified A & C Baseline Report (`PRETRAIN_BASELINE_REPORT.md`)

> **Baseline Classification:** **`POST_HOC_UNMODIFIED_AC_BASELINE`（事后补测的未修改 A/C 基线）**  
> **Chronology & Provenance Disclosure:** While `training/datasets/test.jsonl` (SHA-256: `0c53993d810169f23272731aa2d82899593c96e10b1fd898d7ef7d2fe4fc0837`) was generated and frozen in M3 prior to M4 LoRA training, and the base checkpoints for Model A and Model C were never modified during training, this 64-case stratified baseline script was executed **post-hoc (after M4 fine-tuning completed)**. It is therefore truthfully labeled as a **Post-Hoc Baseline on Unmodified A/C Checkpoints**, not a pre-training timestamped run.  
> **Evaluated Stratified Held-Out Cases:** `64` (8 task families × 8 cases)  
> **Network Condition:** `HF_HUB_OFFLINE=1` (100% On-Mac Apple M4 Metal 4 Execution)

## 1. Unmodified Base Model A vs. Small Model C Baseline Metrics

| Metric | **Model A** (`mlx-community/Qwen2.5-0.5B-Instruct-4bit`) | **Model C** (`mlx-community/SmolLM2-135M-Instruct`) |
| --- | --- | --- |
| **Checkpoint SHA-256** | `ddffab9cbc7bf6dd...` | `989e3ef746b41999...` |
| **Disk Footprint (`MB`)** | `278.41 MB` | `261.19 MB` |
| **Model Load Time (`s`)** | `0.397 s` | `0.229 s` |
| **Mean TTFT (`ms`)** | `74.76 ms` | `37.01 ms` |
| **Decode Speed (`tokens/sec`)** | `166.67 tok/s` | `202.39 tok/s` |
| **Peak Metal Memory (`MB`)** | `534.23 MB` | `438.26 MB` |
| **Valid JSON Rate (%)** | `100.0%` | `67.19%` |
| **Tool Selection Accuracy (%)** | `56.25%` | `0.0%` |
| **Exact Argument Grounding (%)** | **`56.25%`** | **`0.0%`** |

## 2. Pre-Training Per-Family Breakdown (Diagnosis motivating M4 LoRA Fine-Tuning)

| Task Family | Model A (Untrained Base) | Model C (Untrained Small) | Pre-Training Diagnosis |
| --- | --- | --- | --- |
| `family_1_tool_choice` | `100.0%` | `0.0%` | Base A handles basic single-tool JSON; Small C echoes prompt schema |
| `family_2_grounded_copy` | `100.0%` | `0.0%` | Base A copies arguments when no conflict/error exists |
| `family_3_step_dependencies` | `100.0%` | `0.0%` | Base A handles straightforward verify/manifest calls |
| `family_4_ambiguity_abstention` | **`0.0%`** | `0.0%` | **Critical Gap:** Untrained Base A never emits `abstain` on wildcard ambiguity |
| `family_5_error_classification` | **`0.0%`** | `0.0%` | **Critical Gap:** Untrained Base A blindly calls `copy_file` even when source is missing (`FILE_NOT_FOUND`) |
| `family_6_permission_rejection` | **`0.0%`** | `0.0%` | **Critical Gap:** Untrained Base A executes `on_conflict='overwrite'` when `allow_overwrite=False` |
| `family_7_idempotent_replay` | `100.0%` | `0.0%` | Base A preserves `on_conflict='skip'` |
| `family_8_adversarial_safety` | **`50.0%`** | `0.0%` | **Critical Gap:** Untrained Base A fails to reject `../../etc/passwd` traversal with `report_error (UNSAFE_PATH)` |
