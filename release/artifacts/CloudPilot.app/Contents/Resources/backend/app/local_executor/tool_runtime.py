"""
CloudPilot Deterministic Local Tool Runtime (Phase 2 & Phase 3)
Executes only the 6 allowlisted tools inside the user-authorized workspace root:
  - list_files
  - get_file_info
  - create_folder
  - copy_file
  - verify_file
  - generate_manifest
Zero eval, zero shell execution, deterministic pathlib/shutil/hashlib operations.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.local_executor.state_store import StateStore
from app.security.policy_validator import PolicyValidator, PolicyViolationError
from protocol.versions.v1 import ErrorCode, TaskPlanV1, TaskState, ToolCallV1


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ToolExecutionResult:
    ok: bool
    tool: str
    output: Dict[str, Any]
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "output": self.output,
            "error_code": self.error_code.value if self.error_code else None,
            "error_message": self.error_message,
        }


class DeterministicToolRuntime:
    def __init__(self, validator: PolicyValidator, state_store: Optional[StateStore] = None):
        self.validator = validator
        self.state_store = state_store
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "list_files": self._handle_list_files,
            "get_file_info": self._handle_get_file_info,
            "create_folder": self._handle_create_folder,
            "copy_file": self._handle_copy_file,
            "verify_file": self._handle_verify_file,
            "generate_manifest": self._handle_generate_manifest,
        }

    def preview_plan(self, plan: TaskPlanV1) -> List[Dict[str, Any]]:
        """Dry-run preview of plan steps without modifying user files."""
        self.validator.validate_plan(
            plan,
            expected_min_version=1,
        )
        previews = []
        for step in plan.steps:
            previews.append({
                "step_id": step.step_id,
                "action": step.action,
                "args": step.args,
                "mutates_filesystem": step.action in {"create_folder", "copy_file", "generate_manifest"},
                "dry_run_status": "READY",
            })
        return previews

    def execute_tool_call(
        self,
        raw_call: Dict[str, Any],
        plan: Optional[TaskPlanV1] = None,
        dry_run: bool = False,
    ) -> ToolExecutionResult:
        try:
            call: ToolCallV1 = self.validator.validate_tool_call(raw_call, plan=plan)
        except Exception as exc:
            code = getattr(exc, "error_code", ErrorCode.SCHEMA_INVALID)
            return ToolExecutionResult(
                ok=False,
                tool=str(raw_call.get("tool", "unknown")),
                output={},
                error_code=code,
                error_message=str(exc),
            )

        if call.tool == "abstain":
            return ToolExecutionResult(
                ok=True,
                tool="abstain",
                output={"abstained": True, "reason": call.args.get("reason", "Ambiguous or unauthorized request")},
            )

        if call.tool == "report_error":
            code_str = call.args.get("error_code", ErrorCode.PRECONDITION_FAILED.value)
            code = ErrorCode(code_str) if code_str in ErrorCode.__members__ else ErrorCode.PRECONDITION_FAILED
            return ToolExecutionResult(
                ok=False,
                tool="report_error",
                output=call.args,
                error_code=code,
                error_message=call.args.get("message", "Executor reported structured error"),
            )

        if dry_run:
            return ToolExecutionResult(
                ok=True,
                tool=call.tool,
                output={"dry_run": True, "validated_args": call.args},
            )

        handler = self._handlers[call.tool]
        try:
            out = handler(call.args)
            return ToolExecutionResult(ok=True, tool=call.tool, output=out)
        except PolicyViolationError as exc:
            return ToolExecutionResult(
                ok=False,
                tool=call.tool,
                output={},
                error_code=exc.error_code,
                error_message=exc.message,
            )
        except Exception as exc:
            return ToolExecutionResult(
                ok=False,
                tool=call.tool,
                output={},
                error_code=ErrorCode.PRECONDITION_FAILED,
                error_message=str(exc),
            )

    def _handle_list_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = args.get("path", ".")
        target = self.validator.resolve_safe_path(rel, must_exist=True)
        if not target.is_dir():
            raise PolicyViolationError(f"Path is not a directory: {rel}", ErrorCode.PRECONDITION_FAILED)

        max_items = min(int(args.get("max_items", 100)), self.validator.policy.max_files_per_list)
        entries = []
        for entry in sorted(target.iterdir(), key=lambda p: p.name):
            if entry.name.startswith(".cloudpilot"):
                continue
            if entry.is_symlink():
                resolved = entry.resolve()
                if not self.validator._is_within_root(resolved):
                    continue
            rel_entry = str(entry.relative_to(self.validator.root))
            entries.append({
                "path": rel_entry,
                "name": entry.name,
                "kind": "directory" if entry.is_dir() else "file",
                "size_bytes": entry.stat().st_size if entry.is_file() else 0,
            })
            if len(entries) >= max_items:
                break
        return {"directory": rel, "count": len(entries), "entries": entries}

    def _handle_get_file_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = args["path"]
        target = self.validator.resolve_safe_path(rel, must_exist=True)
        st = target.stat()
        info: Dict[str, Any] = {
            "path": str(target.relative_to(self.validator.root)),
            "name": target.name,
            "kind": "directory" if target.is_dir() else "file",
            "size_bytes": st.st_size if target.is_file() else 0,
        }
        if target.is_file():
            info["sha256"] = sha256_file(target)
        return info

    def _handle_create_folder(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = args["path"]
        target = self.validator.resolve_safe_path(rel, must_exist=False)
        if target.exists() and target.is_file():
            raise PolicyViolationError(
                f"Cannot create folder at {rel}: a file already exists at that path",
                ErrorCode.TARGET_EXISTS,
            )
        already_existed = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        return {
            "path": str(target.relative_to(self.validator.root)),
            "created": not already_existed,
            "idempotent": True,
        }

    def _handle_copy_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        src_rel = args["source"]
        dst_rel = args["destination"]
        on_conflict = args.get("on_conflict", "skip")

        src = self.validator.resolve_safe_path(src_rel, must_exist=True)
        if not src.is_file():
            raise PolicyViolationError(f"Source is not a regular file: {src_rel}", ErrorCode.FILE_NOT_FOUND)

        dst = self.validator.resolve_safe_path(dst_rel, must_exist=False)
        if dst.exists():
            if dst.is_dir():
                raise PolicyViolationError(f"Destination is a directory: {dst_rel}", ErrorCode.TARGET_EXISTS)
            if on_conflict == "skip":
                src_hash = sha256_file(src)
                dst_hash = sha256_file(dst)
                return {
                    "source": src_rel,
                    "destination": dst_rel,
                    "action_taken": "skipped_existing",
                    "identical_sha256": src_hash == dst_hash,
                    "sha256": dst_hash,
                }
            if on_conflict == "error":
                raise PolicyViolationError(f"Target file already exists: {dst_rel}", ErrorCode.TARGET_EXISTS)

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {
            "source": src_rel,
            "destination": dst_rel,
            "action_taken": "copied",
            "size_bytes": dst.stat().st_size,
            "sha256": sha256_file(dst),
        }

    def _handle_verify_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = args["path"]
        target = self.validator.resolve_safe_path(rel, must_exist=True)
        if not target.is_file():
            raise PolicyViolationError(f"Cannot verify non-file path: {rel}", ErrorCode.FILE_NOT_FOUND)

        actual_sha = sha256_file(target)
        actual_size = target.stat().st_size

        against_rel = args.get("against")
        expected_sha = args.get("expected_sha256")

        if against_rel:
            against_path = self.validator.resolve_safe_path(against_rel, must_exist=True)
            if not against_path.is_file():
                raise PolicyViolationError(
                    f"Comparison source does not exist: {against_rel}",
                    ErrorCode.FILE_NOT_FOUND,
                )
            ref_sha = sha256_file(against_path)
            if actual_sha != ref_sha:
                raise PolicyViolationError(
                    f"Checksum mismatch for {rel} vs {against_rel}",
                    ErrorCode.PRECONDITION_FAILED,
                )

        if expected_sha and actual_sha != expected_sha:
            raise PolicyViolationError(
                f"Checksum mismatch for {rel}: expected {expected_sha}, got {actual_sha}",
                ErrorCode.PRECONDITION_FAILED,
            )

        return {
            "path": rel,
            "verified": True,
            "size_bytes": actual_size,
            "sha256": actual_sha,
        }

    def _handle_generate_manifest(self, args: Dict[str, Any]) -> Dict[str, Any]:
        dst_rel = args["destination"]
        dst = self.validator.resolve_safe_path(dst_rel, must_exist=False)
        include_hashes = bool(args.get("include_hashes", True))

        files_summary = []
        for item in sorted(self.validator.root.rglob("*")):
            if item == dst or item.name.startswith(".cloudpilot"):
                continue
            if item.is_file() and not item.is_symlink():
                entry: Dict[str, Any] = {
                    "path": str(item.relative_to(self.validator.root)),
                    "size_bytes": item.stat().st_size,
                }
                if include_hashes:
                    entry["sha256"] = sha256_file(item)
                files_summary.append(entry)

        manifest_data = {
            "schema": "cloudpilot.workspace_manifest.v1",
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file_count": len(files_summary),
            "files": files_summary,
        }
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        return {
            "destination": dst_rel,
            "file_count": len(files_summary),
            "manifest_sha256": sha256_file(dst),
        }
