# CloudPilot — Local-Only System Architecture (`docs/architecture.md`)

## 1. Architectural Overview

CloudPilot strictly separates **intent planning**, **tool grounding**, **security policy validation**, and **deterministic filesystem execution** across four local layers on the user's Mac:

```text
+-------------------------------------------------------------------+
| 1. Native macOS SwiftUI Desktop App (app/frontend/CloudPilotApp)  |
|    Home/Chat · Plan Preview · Execution Monitor · Models · Audit  |
+---------------------------------+---------------------------------+
                                  | Local Subprocess JSON IPC
                                  v
+-------------------------------------------------------------------+
| 2. Local Planner (P) — app/local_planner/planner.py               |
|    Qwen2.5-0.5B-Instruct-4bit + Deterministic Schema Compiler     |
|    Natural Language + Workspace Listing -> TaskPlanV1 (DAG)       |
+---------------------------------+---------------------------------+
                                  | Approved TaskPlanV1 Step
                                  v
+-------------------------------------------------------------------+
| 3. Local Fine-Tuned Executor (B) — app/local_executor/            |
|    CloudPilot-Qwen2.5-0.5B-Executor-LoRA-v1 on Apple M4 Metal 4   |
|    Grounds PlanStep + Live Workspace Files -> ToolCallV1 JSON     |
+---------------------------------+---------------------------------+
                                  | Untrusted Model Output
                                  v
+-------------------------------------------------------------------+
| 4. Deterministic Policy Validator — app/security/policy_validator |
|    Workspace root confinement · Symlink/traversal guard · Limits  |
+---------------------------------+---------------------------------+
                                  | Validated ToolCallV1
                                  v
+-------------------------------------------------------------------+
| 5. Deterministic Tool Runtime & SQLite State Store                |
|    pathlib/shutil/hashlib (6 tools) · SQLite task/step/audit DB   |
+-------------------------------------------------------------------+
```

## 2. Key Component Responsibilities

1. **Local Planner (`P`, `app/local_planner/planner.py`):**
   - Generates a bounded DAG (`TaskPlanV1`) validated against `protocol/schemas/task_plan_v1.json`.
   - Enforces non-destructive defaults (`copy_file` with `on_conflict: "skip"`, followed by `verify_file` SHA-256 verification and `generate_manifest`).
   - Performs local error recovery (`replan_on_error`) by incrementing `plan_version` when a transient error such as `FILE_NOT_FOUND` occurs.

2. **Fine-Tuned Local Executor (`B`, `app/local_executor/executor_agent.py`):**
   - Trained via on-Mac MLX LoRA (`mlx_lm.lora`) on 1,000 synthetic examples across 8 task families and fused into `model/deployment/model.safetensors`.
   - Maps each plan step and live workspace observation into a structured `ToolCallV1` (`list_files`, `get_file_info`, `create_folder`, `copy_file`, `verify_file`, `generate_manifest`, `abstain`, or `report_error`).

3. **Policy Validator (`app/security/policy_validator.py`):**
   - Ensures schema validity never grants permission by itself.
   - Canonicalizes every path relative to the authorized `workspace_root`, rejecting `..`, leading `/` or `~`, NUL bytes, and symlinks pointing outside the workspace.
   - Blocks write tools unless `plan.approvals.approved == True` and blocks `on_conflict == "overwrite"` unless `allow_overwrite == True`.

4. **Deterministic Tool Runtime & SQLite State Store (`app/local_executor/tool_runtime.py`, `state_store.py`):**
   - Executes the 6 allowlisted tools using Python's `pathlib`, `shutil`, and `hashlib` with zero `eval` or shell execution.
   - Persists every task state (`PENDING`, `AWAITING_APPROVAL`, `RUNNING`, `BLOCKED`, `FAILED`, `CANCELLED`, `COMPLETED`), idempotency key, retry count, and audit event in SQLite (`.cloudpilot_state.db`).
