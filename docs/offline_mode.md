# CloudPilot — Offline Mode & Zero-Cloud Architecture Specification

> **Status:** Active Enforcement (`agent.md` Section 0, Section 3, Section 5.8)

## 1. Offline-First Guarantee

Once the initial open-weight model checkpoints (`Qwen2.5-0.5B-Instruct-4bit` and `SmolLM2-135M-Instruct`) and Python/MLX dependencies are provisioned in `CloudPilot/.hf_cache` and `CloudPilot/.venv`, **every component of CloudPilot operates with zero network connectivity**:

1. **Environment Flags Enforced at Runtime:**
   - `HF_HUB_OFFLINE=1`
   - `TRANSFORMERS_OFFLINE=1`
   - `CLOUDPILOT_OFFLINE_ONLY=1`
   - Local model paths resolved strictly from local disk (`CloudPilot/.hf_cache/models/` and `CloudPilot/model/`).

2. **No Remote Endpoints or Cloud Fallbacks:**
   - No OpenAI, Anthropic, Google, or hosted inference SDKs are imported or configured.
   - No API key fields exist in the configuration, CLI, or macOS SwiftUI application.
   - All Planner → Executor → Policy Validator → Tool Runtime communication happens in-process or via local IPC.

3. **Network-Disabled Verification Harness (`tests/test_m2_offline_loop.py`):**
   - Monkeypatches Python's `socket.socket.connect` and `socket.create_connection` to raise `RuntimeError("NETWORK_DISABLED_BY_OFFLINE_PROOF")` for any non-local address.
   - Executes the complete natural-language request → Local Planner → User Plan Approval → Local Fine-Tuned Executor (Model B) → Policy Validator → Deterministic Tool Runtime → Verification → SQLite Audit History flow while network sockets are blocked.

## 2. Limited Network Exception Log (Provisioning Only)

Per `agent.md` Section 0 ("Limited network exception — transport/publication only"):

| Step | Action | Source | Local Destination | Purpose |
| --- | --- | --- | --- | --- |
| 1 | Download Base Model A | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` | `.hf_cache/models/Qwen2.5-0.5B-Instruct-4bit` | Local base Executor & Planner checkpoint |
| 2 | Download Baseline Model C | `mlx-community/SmolLM2-135M-Instruct` | `.hf_cache/models/SmolLM2-135M-Instruct` | Independent local small model baseline |
| 3 | Python Wheel Provisioning | PyPI (`mlx`, `mlx-lm`, `pydantic`, `jsonschema`, `pytest`, `matplotlib`) | `.venv/` | Local MLX runtime, schema validation, test suite, chart rendering |

No personal data, workspace files, prompts, or telemetry were transmitted during provisioning.
