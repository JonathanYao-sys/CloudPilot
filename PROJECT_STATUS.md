# CloudPilot — Project Status & Gate Tracker

> **Source Specification:** `agent.md` (4.0 — LOCAL-ONLY)  
> **Workflow Pattern:** `agent.md -> Orchestrator -> Coding Agent -> progress.json + Git Checkpoints`  
> **Overall Workflow Status:** `IN_PROGRESS`  
> **Current Active Milestone:** `M6`  
> **Last Updated (UTC):** `2026-11-20T06:11:02Z`

## 1. Milestone & Gate Summary

| Milestone | Phase / Gate | Title | Status | Attempts | Git Checkpoint |
| --- | --- | --- | --- | --- | --- |
| **M0** | Phase 0 & Phase 1 (Gate 0 & Gate 1) | Local hardware/agent audit, MLX environment setup, inference & tiny train smoke test, A/B/C/P baseline freeze | `PASSED` | 1/3 | `checkpoint-M0` (`4e43417`) |
| **M1** | Phase 2 (Gate 2) | Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime | `PASSED` | 2/3 | `checkpoint-M1` (`d6132d2`) |
| **M2** | Phase 3 (Gate 3) | Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice | `PASSED` | 2/3 | `checkpoint-M2` (`1b0b81e`) |
| **M3** | Phase 4 (Gate 4) | Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline | `PASSED` | 1/3 | `checkpoint-M3` (`42ac98e`) |
| **M4** | Phase 5 (Gate 5) | On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card | `PASSED` | 1/3 | `checkpoint-M4` (`5e9aa8a`) |
| **M5** | Phase 6 (Gate 6) | Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B | `PASSED` | 2/3 | `checkpoint-M5` (`1feaf82`) |
| **M6** | Phase 7 (Gate 7) | Three-model (A/B/C) local benchmark: BFCL-style offline suite, CloudPilot Executor Suite, speed/memory, security, charts | `NOT_STARTED` | 0/3 | — |
| **M7** | Phase 8, Phase 9 & Phase 10 (Local Build) (Gate 8 (Local), Gate 9 (Local), Gate 10) | Complete CN/EN docs, local static website, locally captured & rendered promotional MP4 video, checksums & delivery manifest | `NOT_STARTED` | 0/3 | — |
| **M8** | Phase 8 & Phase 9 (Public Internet Publication) (Gate 8 (Public) & Gate 9 (Public)) | Authorized GitHub Repository/Release Upload, Static Website Hosting & Video Publication | `NOT_STARTED` | 0/3 | — |

## 2. Detailed Milestone Evidence, Failure Reasons & Next Steps

### M0: Local hardware/agent audit, MLX environment setup, inference & tiny train smoke test, A/B/C/P baseline freeze
- **Status:** `PASSED`
- **Dependencies:** None
- **Verification Command:** `.venv/bin/pytest tests/test_m0_hardware_and_models.py -v`
- **Attempts:** 1 / 3
- **Gate Verification Evidence:** Apple M4 24GB RAM verified; Model A (124.9 tok/s) & Model C (253.71 tok/s) cached locally; 5-step MLX LoRA smoke test passed in 10.33s.
- **Git Checkpoint:** commit `4e43417ea3a77d0e1e7cb9b03336e11f4c26aabb`, tag `checkpoint-M0` at `2026-11-20T05:54:43Z`
- **Next Step:** Proceed to M1: Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime

### M1: Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime
- **Status:** `PASSED`
- **Dependencies:** M0
- **Verification Command:** `.venv/bin/pytest tests/test_m1_protocol_and_security.py -v`
- **Attempts:** 2 / 3
- **Recorded Failure Reasons (Auto-Repair Loop):**
  1. `Command `.venv/bin/pytest tests/test_m1_protocol_and_security.py -v` exited 2: .py:88: in import_module |     return _bootstrap._gcd_import(name[level:], package, level) |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | tests/test_m1_protocol_and_security.py:13: in <module> |     from app.local_executor.state_store import StateStore | E   ModuleNotFoundError: No module named 'app' | =========================== short test summary info ============================ | ERROR tests/test_m1_protocol_and_security.py | !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!! | =============================== 1 error in 0.05s ===============================`
- **Gate Verification Evidence:** TaskPlanV1/ToolCallV1 JSON schemas, DAG validation, PolicyValidator path/symlink/approval guards, SQLite StateStore, and 6-tool DeterministicToolRuntime verified (4/4 pytest passed).
- **Git Checkpoint:** commit `d6132d2959b6ce9804300712d95368cefc8149b4`, tag `checkpoint-M1` at `2026-11-20T05:57:44Z`
- **Next Step:** Proceed to M2: Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice

### M2: Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice
- **Status:** `PASSED`
- **Dependencies:** M1
- **Verification Command:** `.venv/bin/pytest tests/test_m2_offline_loop.py -v`
- **Attempts:** 2 / 3
- **Recorded Failure Reasons (Auto-Repair Loop):**
  1. `Command `.venv/bin/pytest tests/test_m2_offline_loop.py -v` exited 1: " / "KeepMe.pdf").exists() | E       AssertionError: assert False | E        +  where False = exists() | E        +    where exists = ((PosixPath('/private/var/folders/l7/2_dj5q8x14j9h07fp07hfg000000gn/T/pytest-of-yao/pytest-1/test_offline_error_replan_and_0/recovery_ws') / 'Archive_PDFs') / 'KeepMe.pdf').exists |  | tests/test_m2_offline_loop.py:96: AssertionError | =========================== short test summary info ============================ | FAILED tests/test_m2_offline_loop.py::test_offline_error_replan_and_cancellation | ========================= 1 failed, 1 passed in 5.34s ==========================`
- **Gate Verification Evidence:** Network-disabled socket-blocked end-to-end planning-execution loop, local MLX model traces, SHA-256 verification, FILE_NOT_FOUND replan recovery, and cancellation verified (2/2 pytest passed).
- **Git Checkpoint:** commit `1b0b81e80304b6fbd3219eb41c05777128ce30c0`, tag `checkpoint-M2` at `2026-11-20T06:00:18Z`
- **Next Step:** Proceed to M3: Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline

### M3: Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline
- **Status:** `PASSED`
- **Dependencies:** M1, M2
- **Verification Command:** `.venv/bin/pytest tests/test_m3_dataset_quality.py -v`
- **Attempts:** 1 / 3
- **Gate Verification Evidence:** Generated and rule-validated 1,320 synthetic cases (1000 train, 160 val, 160 frozen test) across 8 families with 0 cross-split leakage and 0 PII (2/2 pytest passed).
- **Git Checkpoint:** commit `42ac98ec106930a41c542279771424ee09caf66e`, tag `checkpoint-M3` at `2026-11-20T06:02:07Z`
- **Next Step:** Proceed to M4: On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card

### M4: On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card
- **Status:** `PASSED`
- **Dependencies:** M3
- **Verification Command:** `.venv/bin/pytest tests/test_m4_finetuned_model.py -v`
- **Attempts:** 1 / 3
- **Gate Verification Evidence:** On-Mac MLX LoRA fine-tuning (160 iters, val_loss 3.728 -> 0.348) produced adapters.safetensors (5.61 MB) and fused model.safetensors (265.18 MB); verified in App loader (3/3 pytest passed).
- **Git Checkpoint:** commit `5e9aa8abe4664dd72b9687689b7263c330b039d1`, tag `checkpoint-M4` at `2026-11-20T06:09:12Z`
- **Next Step:** Proceed to M5: Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B

### M5: Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B
- **Status:** `PASSED`
- **Dependencies:** M2, M4
- **Verification Command:** `.venv/bin/pytest tests/test_m5_macos_app_and_dmg.py -v`
- **Attempts:** 2 / 3
- **Recorded Failure Reasons (Auto-Repair Loop):**
  1. `Command `.venv/bin/pytest tests/test_m5_macos_app_and_dmg.py -v` exited 1:              output=stdout, stderr=stderr) | E               subprocess.CalledProcessError: Command '['/Users/yao/CloudPilot/release/artifacts/CloudPilot.app/Contents/MacOS/CloudPilot', '--headless-self-test']' returned non-zero exit status 1. |  | ../.local/share/uv/python/cpython-3.13.18-macos-aarch64-none/lib/python3.13/subprocess.py:578: CalledProcessError | =========================== short test summary info ============================ | FAILED tests/test_m5_macos_app_and_dmg.py::test_m5_app_headless_offline_self_test | ========================= 1 failed, 2 passed in 3.84s ==========================`
- **Gate Verification Evidence:** Native SwiftUI CloudPilot.app and CloudPilot-v1.0-macOS.dmg built locally, ad-hoc signed, hdiutil-verified, and tested offline with Model B (3/3 pytest passed).
- **Git Checkpoint:** commit `1feaf8203f5d7848e417f90e2e34d8b94c55ea5f`, tag `checkpoint-M5` at `2026-11-20T06:11:02Z`
- **Next Step:** Proceed to M6: Three-model (A/B/C) local benchmark: BFCL-style offline suite, CloudPilot Executor Suite, speed/memory, security, charts

### M6: Three-model (A/B/C) local benchmark: BFCL-style offline suite, CloudPilot Executor Suite, speed/memory, security, charts
- **Status:** `NOT_STARTED`
- **Dependencies:** M4, M5
- **Verification Command:** `.venv/bin/pytest tests/test_m6_benchmarks.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Run full A/B/C evaluation across public tool-calling subset, CloudPilot held-out test set, performance metrics, and security suite.

### M7: Complete CN/EN docs, local static website, locally captured & rendered promotional MP4 video, checksums & delivery manifest
- **Status:** `NOT_STARTED`
- **Dependencies:** M5, M6
- **Verification Command:** `.venv/bin/pytest tests/test_m7_release_and_media.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Author CN/EN docs, build static launch website with real screenshots/charts, render real app promo MP4 via FFmpeg, and audit delivery manifest.

### M8: Authorized GitHub Repository/Release Upload, Static Website Hosting & Video Publication
- **Status:** `NOT_STARTED`
- **Dependencies:** M7
- **Verification Command:** `python3 orchestrator.py check-publication`
- **Attempts:** 0 / 3
- **Next Step:** Await explicit user approval and GitHub target/account configuration per agent.md Section 2.2 before pushing public release/website.

## 3. Orchestrator Execution Log (Recent Events)

- `2026-11-20T05:54:43Z` **[MILESTONE_PASSED]** (`M0`): Attempt 1 passed gate verification. Evidence: Apple M4 24GB RAM verified; Model A (124.9 tok/s) & Model C (253.71 tok/s) cached locally; 5-step MLX LoRA smoke test passed in 10.33s.
- `2026-11-20T05:54:43Z` **[GIT_CHECKPOINT_CREATED]** (`M0`): Created git tag checkpoint-M0 at commit 2d29a55
- `2026-11-20T05:54:51Z` **[MILESTONE_STARTED]** (`M1`): Orchestrator assigned M1 (Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime) to Coding Agent.
- `2026-11-20T05:57:00Z` **[VERIFICATION_FAILED]** (`M1`): Attempt 1/3 failed: Command `.venv/bin/pytest tests/test_m1_protocol_and_security.py -v` exited 2: .py:88: in import_module |     return _bootstrap._gcd_import(name[level:], package, level) |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ | te
- `2026-11-20T05:57:44Z` **[MILESTONE_PASSED]** (`M1`): Attempt 2 passed gate verification. Evidence: TaskPlanV1/ToolCallV1 JSON schemas, DAG validation, PolicyValidator path/symlink/approval guards, SQLite StateStore, and 6-tool DeterministicToolRuntime verified (4/4 pytest passed).
- `2026-11-20T05:57:44Z` **[GIT_CHECKPOINT_CREATED]** (`M1`): Created git tag checkpoint-M1 at commit 5f33cdd
- `2026-11-20T05:57:53Z` **[MILESTONE_STARTED]** (`M2`): Orchestrator assigned M2 (Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice) to Coding Agent.
- `2026-11-20T05:59:52Z` **[VERIFICATION_FAILED]** (`M2`): Attempt 1/3 failed: Command `.venv/bin/pytest tests/test_m2_offline_loop.py -v` exited 1: " / "KeepMe.pdf").exists() | E       AssertionError: assert False | E        +  where False = exists() | E        +    where exists = ((PosixPath('/private/var/folders/l7
- `2026-11-20T06:00:18Z` **[MILESTONE_PASSED]** (`M2`): Attempt 2 passed gate verification. Evidence: Network-disabled socket-blocked end-to-end planning-execution loop, local MLX model traces, SHA-256 verification, FILE_NOT_FOUND replan recovery, and cancellation verified (2/2 pytest passed).
- `2026-11-20T06:00:18Z` **[GIT_CHECKPOINT_CREATED]** (`M2`): Created git tag checkpoint-M2 at commit 0fc71c5
- `2026-11-20T06:00:33Z` **[MILESTONE_STARTED]** (`M3`): Orchestrator assigned M3 (Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline) to Coding Agent.
- `2026-11-20T06:02:07Z` **[MILESTONE_PASSED]** (`M3`): Attempt 1 passed gate verification. Evidence: Generated and rule-validated 1,320 synthetic cases (1000 train, 160 val, 160 frozen test) across 8 families with 0 cross-split leakage and 0 PII (2/2 pytest passed).
- `2026-11-20T06:02:07Z` **[GIT_CHECKPOINT_CREATED]** (`M3`): Created git tag checkpoint-M3 at commit 2915e8e
- `2026-11-20T06:02:15Z` **[MILESTONE_STARTED]** (`M4`): Orchestrator assigned M4 (On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card) to Coding Agent.
- `2026-11-20T06:09:11Z` **[MILESTONE_PASSED]** (`M4`): Attempt 1 passed gate verification. Evidence: On-Mac MLX LoRA fine-tuning (160 iters, val_loss 3.728 -> 0.348) produced adapters.safetensors (5.61 MB) and fused model.safetensors (265.18 MB); verified in App loader (3/3 pytest passed).
- `2026-11-20T06:09:12Z` **[GIT_CHECKPOINT_CREATED]** (`M4`): Created git tag checkpoint-M4 at commit 16f3174
- `2026-11-20T06:09:12Z` **[MILESTONE_STARTED]** (`M5`): Orchestrator assigned M5 (Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B) to Coding Agent.
- `2026-11-20T06:10:07Z` **[VERIFICATION_FAILED]** (`M5`): Attempt 1/3 failed: Command `.venv/bin/pytest tests/test_m5_macos_app_and_dmg.py -v` exited 1:              output=stdout, stderr=stderr) | E               subprocess.CalledProcessError: Command '['/Users/yao/CloudPilot/release/artifacts/CloudPilot.app/Content
- `2026-11-20T06:11:02Z` **[MILESTONE_PASSED]** (`M5`): Attempt 2 passed gate verification. Evidence: Native SwiftUI CloudPilot.app and CloudPilot-v1.0-macOS.dmg built locally, ad-hoc signed, hdiutil-verified, and tested offline with Model B (3/3 pytest passed).
- `2026-11-20T06:11:02Z` **[GIT_CHECKPOINT_CREATED]** (`M5`): Created git tag checkpoint-M5 at commit 1feaf82
