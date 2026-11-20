# CloudPilot — Deterministic Security Model (`docs/security.md`)

> **Core Principle (`agent.md` Section 2.3 & Section 7):** Security is enforced by deterministic code (`PolicyValidator` + `DeterministicToolRuntime`) and macOS permissions—**never by model prompts alone**. Schema validity does not grant permission.

## 1. Strict Tool Allowlist

The Executor Model can only emit JSON objects naming one of the 6 allowlisted filesystem tools (or 2 structured non-action responses):

| Tool | Type | Deterministic Security Constraint |
| --- | --- | --- |
| `list_files` | Read | Confined to `workspace_root`; skips escaping symlinks; bounded by `max_files_per_list = 200` |
| `get_file_info` | Read | Confined to `workspace_root`; returns metadata and SHA-256 only (no arbitrary raw file dump) |
| `create_folder` | Write | Requires user plan approval; workspace-rooted; idempotent (`exist_ok=True`); blocks file collisions |
| `copy_file` | Write | Requires user plan approval; defaults to `on_conflict="skip"`; blocks `overwrite` unless explicitly authorized; enforces `max_file_size_bytes = 50 MB` |
| `verify_file` | Read | Confined to `workspace_root`; compares byte size and SHA-256 digest against source or expected hash |
| `generate_manifest` | Write | Requires user plan approval; writes JSON manifest only inside `workspace_root` |
| `abstain` | Control | Safe no-op when instructions are ambiguous or lack permission |
| `report_error` | Control | Reports typed error (`FILE_NOT_FOUND`, `UNSAFE_PATH`, `PERMISSION_DENIED`, `PRECONDITION_FAILED`) |

## 2. Path Canonicalization & Traversal Defenses

Every path argument passed to `PolicyValidator.resolve_safe_path()` undergoes five sequential checks before any filesystem handle is opened:

1. **Control-Character Rejection:** Paths containing NUL bytes (`\x00`) or ASCII control characters (`< 32`) fail immediately with `ErrorCode.UNSAFE_PATH`.
2. **Absolute & Home-Expansion Rejection:** Paths starting with `/`, `\`, or `~` fail with `ErrorCode.UNSAFE_PATH`.
3. **Traversal Token Rejection:** Paths containing `..` in `Path(cleaned).parts` fail with `ErrorCode.UNSAFE_PATH`.
4. **Prefix-by-Prefix Symlink Inspection:** Every prefix component from `workspace_root` down to the target path is checked with `is_symlink()`. If any symlink resolves outside `workspace_root.resolve()`, it fails with `ErrorCode.UNSAFE_PATH`.
5. **Final Resolved Containment Check:** `candidate.resolve().relative_to(workspace_root.resolve())` must succeed.

## 3. Adversarial Benchmark Verification

In Phase 7 (`evaluation/suites/run_abc_evaluation.py` and `tests/test_m1_protocol_and_security.py`), 16 adversarial attack vectors (including `../../etc/passwd`, `/etc/passwd`, `~/.ssh/id_rsa`, external symlinks, NUL-byte paths, `execute_shell`, `delete_file`, `eval_python`, unapproved overwrites, and prompt-injection filenames) were tested against the runtime:
- **16 / 16 unauthorized operations were deterministically blocked (`0` unauthorized successes).**
- **Caveat (`agent.md` Section 2.3 & Section 12):** Zero unauthorized actions in our test suite verifies the deterministic policy guards on tested paths; it is never claimed as an absolute operating-system security boundary.
