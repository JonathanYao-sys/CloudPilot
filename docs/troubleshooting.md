# CloudPilot — Troubleshooting & Error Recovery Guide (`docs/troubleshooting.md`)

## 1. Structured Error Codes & Resolution

CloudPilot's `PolicyValidator` and `DeterministicToolRuntime` emit typed `ErrorCode` values (`protocol/versions/v1.py`):

| Error Code | Meaning | How CloudPilot / User Resolves It |
| --- | --- | --- |
| `FILE_NOT_FOUND` | Source or verification target file is missing inside workspace | Local Planner automatically invokes `replan_on_error()` to create `plan_version + 1` with live workspace files |
| `PERMISSION_DENIED` | Plan has not been approved, or `on_conflict='overwrite'` was requested when `allow_overwrite=False` | Approve the plan in **Plan Preview**, or use non-destructive `on_conflict='skip'` |
| `SCHEMA_INVALID` | Plan or tool call JSON violated `task_plan_v1.json` or `tool_call_v1.json` | Check `protocol/schemas/` or re-run Local Planner / Fine-Tuned Model B |
| `TARGET_EXISTS` | Destination path already exists as a conflicting file/folder | Use `on_conflict='skip'` (default idempotent behavior) |
| `UNSAFE_PATH` | Path contained `..`, leading `/`, `~`, NUL bytes, or an external symlink | Blocked deterministically; use relative paths strictly inside the authorized workspace root |
| `PRECONDITION_FAILED` | Step dependency unmet, stale `plan_version`, or SHA-256 checksum mismatch | Inspect `.cloudpilot_state.db` audit log and re-run verification |
| `MODEL_UNAVAILABLE` | Local checkpoint missing from `.hf_cache/models/` or `model/deployment/` | Run `.venv/bin/python -m app.local_executor.orchestration_loop models` to verify local weights |

## 2. macOS Gatekeeper Prompt on First Launch

- **Symptom:** macOS displays *"CloudPilot.app cannot be opened because the developer cannot be verified"* when launching on a different user account.
- **Cause:** `CloudPilot.app` is ad-hoc signed locally (`codesign --force --deep --sign -`) without a paid Apple Developer ID notarization certificate (`agent.md` Section 11.6).
- **Solution:** Control-click (or right-click) `CloudPilot.app` in Finder and click **Open**, or run:
  ```bash
  xattr -dr com.apple.quarantine release/artifacts/CloudPilot.app
  ```

## 3. Resetting Workspace SQLite State

If a sandbox test workspace needs a clean state database:
```bash
rm -f /path/to/sandbox_workspace/.cloudpilot_state.db
```
