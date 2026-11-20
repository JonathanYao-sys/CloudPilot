# CloudPilot — Privacy Policy & Data Handling (`docs/privacy.md`)

## 1. Zero Telemetry & Zero Cloud AI

- **100% On-Device Processing:** User prompts, workspace directory listings, file metadata, file contents, task plans, model inferences, SQLite state databases, and audit logs never leave this Mac.
- **No Cloud API Keys:** CloudPilot contains no code paths, SDKs, or settings for OpenAI, Anthropic, Google Gemini, or any hosted LLM endpoint.
- **Offline Runtime Enforcement:** The runtime sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `CLOUDPILOT_OFFLINE_ONLY=1` on startup.

## 2. Redaction & Public Artifact Hygiene

Per `agent.md` Section 2.3 and Section 5.8:
- Hardware serial numbers, Hardware UUIDs, Provisioning UDIDs, and personal credentials are stripped from `docs/hardware_report.md` and `docs/environment_report.json`.
- All 1,320 training, validation, and test examples in `training/datasets/*.jsonl` are 100% synthetic and verified by `training/data_pipeline/validate_dataset.py` to contain zero personal file paths, usernames, or secrets (`pii_and_secret_scan: CLEAN`).

## 3. Clear Separation Between Offline Execution and Optional Publication Transport

- **Normal Product Operation:** 100% offline.
- **External Network Transport (Provisioning / Optional Release Publication Only):** Network access was used solely during Phase 0 to cache open-weight base models (`mlx-community/Qwen2.5-0.5B-Instruct-4bit` and `mlx-community/SmolLM2-135M-Instruct`) and open-source Python packages into `.hf_cache/` and `.venv/`. Any future upload of the repository, release DMG, website, or video to GitHub requires explicit user authorization (`agent.md` Section 2.2).
