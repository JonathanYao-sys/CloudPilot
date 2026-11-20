# CloudPilot — Project Status & Gate Tracker

> **Source Specification:** `agent.md` (4.0 — LOCAL-ONLY)  
> **Workflow Pattern:** `agent.md -> Orchestrator -> Coding Agent -> progress.json + Git Checkpoints`  
> **Overall Workflow Status:** `IN_PROGRESS`  
> **Current Active Milestone:** `M0`  
> **Last Updated (UTC):** `2026-11-20T00:00:00Z`

## 1. Milestone & Gate Summary

| Milestone | Phase / Gate | Title | Status | Attempts | Git Checkpoint |
| --- | --- | --- | --- | --- | --- |
| **M0** | Phase 0 & Phase 1 (Gate 0 & Gate 1) | Local hardware/agent audit, MLX environment setup, inference & tiny train smoke test, A/B/C/P baseline freeze | `NOT_STARTED` | 0/3 | — |
| **M1** | Phase 2 (Gate 2) | Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime | `NOT_STARTED` | 0/3 | — |
| **M2** | Phase 3 (Gate 3) | Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice | `NOT_STARTED` | 0/3 | — |
| **M3** | Phase 4 (Gate 4) | Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline | `NOT_STARTED` | 0/3 | — |
| **M4** | Phase 5 (Gate 5) | On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card | `NOT_STARTED` | 0/3 | — |
| **M5** | Phase 6 (Gate 6) | Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B | `NOT_STARTED` | 0/3 | — |
| **M6** | Phase 7 (Gate 7) | Three-model (A/B/C) local benchmark: BFCL-style offline suite, CloudPilot Executor Suite, speed/memory, security, charts | `NOT_STARTED` | 0/3 | — |
| **M7** | Phase 8, Phase 9 & Phase 10 (Local Build) (Gate 8 (Local), Gate 9 (Local), Gate 10) | Complete CN/EN docs, local static website, locally captured & rendered promotional MP4 video, checksums & delivery manifest | `NOT_STARTED` | 0/3 | — |
| **M8** | Phase 8 & Phase 9 (Public Internet Publication) (Gate 8 (Public) & Gate 9 (Public)) | Authorized GitHub Repository/Release Upload, Static Website Hosting & Video Publication | `NOT_STARTED` | 0/3 | — |

## 2. Detailed Milestone Evidence, Failure Reasons & Next Steps

### M0: Local hardware/agent audit, MLX environment setup, inference & tiny train smoke test, A/B/C/P baseline freeze
- **Status:** `NOT_STARTED`
- **Dependencies:** None
- **Verification Command:** `.venv/bin/pytest tests/test_m0_hardware_and_models.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Run M0 hardware inspection, provision local Python 3.13 + MLX venv, cache A/C models, and run inference/training smoke test.

### M1: Versioned local task protocol, JSON schemas, Policy Validator, and deterministic safe Tool Runtime
- **Status:** `NOT_STARTED`
- **Dependencies:** M0
- **Verification Command:** `.venv/bin/pytest tests/test_m1_protocol_and_security.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Implement task protocol v1.0, Pydantic/JSON schemas, Policy Validator, SQLite state store, and deterministic 6-tool runtime.

### M2: Entirely local planning-execution loop & network-disabled end-to-end sandbox vertical slice
- **Status:** `NOT_STARTED`
- **Dependencies:** M1
- **Verification Command:** `.venv/bin/pytest tests/test_m2_offline_loop.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Build local Planner + local Executor Model orchestration loop with socket/network-blocked offline proof test.

### M3: Local synthetic dataset generation (train/val/test), validation checks, and pre-training A/C baseline
- **Status:** `NOT_STARTED`
- **Dependencies:** M1, M2
- **Verification Command:** `.venv/bin/pytest tests/test_m3_dataset_quality.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Generate and validate >=1,200 synthetic cases across 8 families with zero train/test leakage.

### M4: On-Mac MLX LoRA fine-tuning, exported .safetensors adapter & fused deployment model, Model Card
- **Status:** `NOT_STARTED`
- **Dependencies:** M3
- **Verification Command:** `.venv/bin/pytest tests/test_m4_finetuned_model.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Fine-tune Model A on this Apple M4 Mac using MLX LoRA to produce Model B (.safetensors), fuse deployment weights, and verify in app loader.

### M5: Native offline macOS App (.app) and installable disk image (.dmg) integrating fine-tuned Model B
- **Status:** `NOT_STARTED`
- **Dependencies:** M2, M4
- **Verification Command:** `.venv/bin/pytest tests/test_m5_macos_app_and_dmg.py -v`
- **Attempts:** 0 / 3
- **Next Step:** Compile native SwiftUI macOS app bundling/connecting to local runtime & Model B, package into installable DMG, and test offline execution.

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

- `2026-11-20T00:00:00Z` **[WORKFLOW_INITIALIZED]** (`M0`): Initialized CloudPilot orchestrator state from agent.md with semua gates NOT_STARTED.
