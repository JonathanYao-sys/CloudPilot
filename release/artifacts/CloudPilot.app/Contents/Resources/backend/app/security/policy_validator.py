"""
CloudPilot Deterministic Policy Validator (Phase 2 & Phase 3)
Enforces workspace root confinement, blocks path traversal ('..'), absolute paths,
external symlinks, disallowed tools, unapproved destructive writes, and excessive resource limits.
Schema validity alone never grants permission.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from protocol.versions.v1 import (
    ALLOWED_EXECUTOR_TOOLS,
    ALLOWED_PLAN_TOOLS,
    ErrorCode,
    TaskPlanV1,
    ToolCallV1,
    validate_tool_call_dict,
)

WRITE_TOOLS = {"create_folder", "copy_file", "generate_manifest"}
READ_TOOLS = {"list_files", "get_file_info", "verify_file"}


@dataclass
class WorkspacePolicy:
    workspace_root: Path
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50 MB default
    max_files_per_list: int = 200
    max_steps_per_plan: int = 32
    allow_overwrite: bool = False


class PolicyViolationError(Exception):
    def __init__(self, message: str, error_code: ErrorCode):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class PolicyValidator:
    def __init__(self, policy: WorkspacePolicy):
        self.policy = policy
        self.root = policy.workspace_root.resolve()

    def resolve_safe_path(self, rel_path: str, must_exist: bool = False) -> Path:
        """
        Canonicalize path and verify it stays strictly inside workspace_root.
        Rejects:
        - empty or non-string paths
        - absolute paths or '~' expansion
        - '..' traversal components
        - symlinks pointing outside workspace_root
        - NUL bytes or control characters
        """
        if not isinstance(rel_path, str) or not rel_path.strip():
            raise PolicyViolationError("Empty or non-string path rejected", ErrorCode.UNSAFE_PATH)

        if "\x00" in rel_path or any(ord(c) < 32 for c in rel_path):
            raise PolicyViolationError(f"Control characters in path rejected: {rel_path!r}", ErrorCode.UNSAFE_PATH)

        cleaned = rel_path.strip()
        if cleaned.startswith("/") or cleaned.startswith("~") or cleaned.startswith("\\"):
            raise PolicyViolationError(f"Absolute or home-relative path rejected: {rel_path}", ErrorCode.UNSAFE_PATH)

        raw_parts = Path(cleaned).parts
        if ".." in raw_parts:
            raise PolicyViolationError(f"Path traversal ('..') rejected: {rel_path}", ErrorCode.UNSAFE_PATH)

        candidate = self.root / cleaned

        # Check every existing prefix for symlinks escaping workspace_root
        curr = self.root
        for part in raw_parts:
            curr = curr / part
            if curr.is_symlink():
                target = curr.resolve()
                if not self._is_within_root(target):
                    raise PolicyViolationError(
                        f"Symlink {rel_path} escapes authorized workspace root",
                        ErrorCode.UNSAFE_PATH,
                    )

        resolved = candidate.resolve()
        if not self._is_within_root(resolved):
            raise PolicyViolationError(
                f"Resolved path {resolved} escapes workspace root {self.root}",
                ErrorCode.UNSAFE_PATH,
            )

        if must_exist and not resolved.exists():
            raise PolicyViolationError(
                f"Required path does not exist in workspace: {rel_path}",
                ErrorCode.FILE_NOT_FOUND,
            )

        return resolved

    def _is_within_root(self, target: Path) -> bool:
        try:
            target.relative_to(self.root)
            return True
        except ValueError:
            return False

    def validate_plan(self, plan: TaskPlanV1, expected_min_version: int = 1) -> None:
        if plan.plan_version < expected_min_version:
            raise PolicyViolationError(
                f"Stale plan_version {plan.plan_version} < {expected_min_version}",
                ErrorCode.PRECONDITION_FAILED,
            )

        if len(plan.steps) > self.policy.max_steps_per_plan:
            raise PolicyViolationError(
                f"Plan has {len(plan.steps)} steps, exceeding limit {self.policy.max_steps_per_plan}",
                ErrorCode.PERMISSION_DENIED,
            )

        has_writes = any(s.action in WRITE_TOOLS for s in plan.steps)
        if has_writes and plan.approvals.requires_user_approval and not plan.approvals.approved:
            raise PolicyViolationError(
                "Plan modifies workspace files but has not been approved by the user",
                ErrorCode.PERMISSION_DENIED,
            )

        for step in plan.steps:
            if step.action not in ALLOWED_PLAN_TOOLS:
                raise PolicyViolationError(
                    f"Disallowed action {step.action} in step {step.step_id}",
                    ErrorCode.PERMISSION_DENIED,
                )
            self._validate_tool_args(step.action, step.args, plan_allow_overwrite=plan.approvals.allow_overwrite)

    def validate_tool_call(
        self,
        raw_call: Dict[str, Any],
        plan: Optional[TaskPlanV1] = None,
    ) -> ToolCallV1:
        call = validate_tool_call_dict(raw_call)
        if call.tool not in ALLOWED_EXECUTOR_TOOLS:
            raise PolicyViolationError(
                f"Tool {call.tool!r} is not in allowlist",
                ErrorCode.PERMISSION_DENIED,
            )

        if call.tool in ("abstain", "report_error"):
            return call

        if call.tool in WRITE_TOOLS and plan is not None:
            if plan.approvals.requires_user_approval and not plan.approvals.approved:
                raise PolicyViolationError(
                    f"Write tool {call.tool} blocked: plan is not user-approved",
                    ErrorCode.PERMISSION_DENIED,
                )

        allow_overwrite = self.policy.allow_overwrite or (
            plan.approvals.allow_overwrite if plan is not None else False
        )
        self._validate_tool_args(call.tool, call.args, plan_allow_overwrite=allow_overwrite)
        return call

    def _validate_tool_args(
        self,
        tool: str,
        args: Dict[str, Any],
        plan_allow_overwrite: bool = False,
    ) -> None:
        if tool == "list_files":
            rel = args.get("path", ".")
            self.resolve_safe_path(rel, must_exist=False)
            max_items = args.get("max_items", self.policy.max_files_per_list)
            if not isinstance(max_items, int) or max_items < 1 or max_items > self.policy.max_files_per_list:
                raise PolicyViolationError(
                    f"list_files max_items {max_items} exceeds policy limit {self.policy.max_files_per_list}",
                    ErrorCode.PERMISSION_DENIED,
                )

        elif tool == "get_file_info":
            self.resolve_safe_path(args.get("path", ""), must_exist=False)

        elif tool == "create_folder":
            self.resolve_safe_path(args.get("path", ""), must_exist=False)

        elif tool == "copy_file":
            src = self.resolve_safe_path(args.get("source", ""), must_exist=False)
            dst = self.resolve_safe_path(args.get("destination", ""), must_exist=False)
            if src == dst:
                raise PolicyViolationError(
                    "copy_file source and destination cannot be identical",
                    ErrorCode.PRECONDITION_FAILED,
                )
            on_conflict = args.get("on_conflict", "skip")
            if on_conflict == "overwrite" and not plan_allow_overwrite:
                raise PolicyViolationError(
                    "copy_file with on_conflict='overwrite' denied without explicit overwrite permission",
                    ErrorCode.PERMISSION_DENIED,
                )
            if src.exists() and src.is_file():
                if src.stat().st_size > self.policy.max_file_size_bytes:
                    raise PolicyViolationError(
                        f"Source file exceeds max_file_size_bytes ({self.policy.max_file_size_bytes})",
                        ErrorCode.PERMISSION_DENIED,
                    )

        elif tool == "verify_file":
            self.resolve_safe_path(args.get("path", ""), must_exist=False)
            if "against" in args and args["against"] is not None:
                self.resolve_safe_path(args["against"], must_exist=False)

        elif tool == "generate_manifest":
            dst = self.resolve_safe_path(args.get("destination", ""), must_exist=False)
            if dst.exists() and not plan_allow_overwrite and not args.get("idempotent_ok", True):
                raise PolicyViolationError(
                    f"Manifest destination {args.get('destination')} already exists",
                    ErrorCode.TARGET_EXISTS,
                )
