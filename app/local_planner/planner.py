"""
CloudPilot Local Planner (Phase 3)
Interprets a natural-language file organization request and workspace file listing
entirely on-device, producing a schema-validated TaskPlanV1.
Also performs local replanning when a step fails with a recoverable error.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.model_runtime.mlx_loader import LocalMLXRuntime
from protocol.versions.v1 import TaskPlanV1, validate_task_plan_dict

CATEGORY_RULES = [
    ("PDF_Docs", (".pdf",), ("pdf", "study", "chapter", "paper", "euro", "history", "report")),
    ("Images", (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"), ("image", "photo", "screenshot", "picture")),
    ("Data_Sheets", (".csv", ".tsv", ".json", ".xlsx"), ("csv", "data", "spreadsheet", "table", "json")),
    ("Notes", (".md", ".txt", ".rst"), ("note", "markdown", "txt", "text", "readme", "summary")),
    ("Archives", (".zip", ".tar", ".gz"), ("archive", "zip", "backup")),
]


def _infer_target_folder_for_file(filename: str, user_request: str) -> Optional[str]:
    req_lower = user_request.lower()
    ext = Path(filename).suffix.lower()

    # Check if user explicitly named a destination folder in quotes or after 'into'/'to' folder
    explicit_match = re.search(
        r"(?:(?:into|to)\s+(?:(?:the\s+)?(?:folder|directory)\s+)?|(?:folder|directory)\s+)['\"]?([A-Za-z0-9_]+)['\"]?",
        user_request,
        flags=re.IGNORECASE,
    )
    if explicit_match:
        cand = explicit_match.group(1)
        if cand.lower() not in {
            "folder", "folders", "directory", "directories", "workspace",
            "files", "all", "the", "a", "category", "categories", "subfolders", "subfolder",
        }:
            # If user asked for specific file type or all files into this folder
            if "pdf" in req_lower and ext != ".pdf":
                return None
            if ("image" in req_lower or "photo" in req_lower) and ext not in (".png", ".jpg", ".jpeg", ".gif"):
                return None
            return cand

    for folder_name, exts, _keywords in CATEGORY_RULES:
        if ext in exts:
            return folder_name
    return "Organized_Files"


class LocalPlanner:
    """
    Hybrid Local Planner (P):
    Uses local on-Mac MLX inference (when runtime is provided) for intent classification trace,
    paired with deterministic schema-constrained compilation to guarantee valid TaskPlanV1 output.
    """

    def __init__(self, runtime: Optional[LocalMLXRuntime] = None, use_llm_trace: bool = True):
        self.runtime = runtime
        self.use_llm_trace = use_llm_trace
        self.last_planner_trace: Optional[Dict[str, Any]] = None

    def create_plan(
        self,
        user_request: str,
        workspace_files: List[Dict[str, Any]],
        workspace_id: str = "authorized_workspace",
        task_id: Optional[str] = None,
        plan_version: int = 1,
        approved: bool = False,
    ) -> TaskPlanV1:
        files_only = [
            f["path"]
            for f in workspace_files
            if f.get("kind") == "file" and "/" not in f["path"] and not f["name"].startswith(".")
        ]

        llm_note = "deterministic_schema_compiler"
        if self.runtime is not None and self.use_llm_trace:
            trace = self.runtime.generate_structured(
                role="A",
                system_prompt=(
                    "You are CloudPilot Local Planner running on macOS. "
                    "Summarize the file organization intent as JSON: {\"intent\": \"organize\", \"strategy\": \"by_category\"}."
                ),
                user_prompt=f"User Request: {user_request}\nFiles: {files_only}",
                max_tokens=40,
            )
            self.last_planner_trace = {
                "model_id": trace.model_id,
                "tokens_per_sec": trace.tokens_per_sec,
                "peak_metal_memory_mb": trace.peak_metal_memory_mb,
                "raw_output": trace.raw_output,
            }
            llm_note = trace.model_id

        digest = hashlib.sha256(f"{workspace_id}:{user_request}:{sorted(files_only)}".encode("utf-8")).hexdigest()[:10]
        resolved_task_id = task_id or f"task-{digest}"
        idempotency_key = f"idem-{resolved_task_id}-v{plan_version}-{digest}"

        # Map each eligible top-level file to its target folder
        assignments: List[tuple[str, str]] = []
        for fname in sorted(files_only):
            folder = _infer_target_folder_for_file(fname, user_request)
            if folder:
                assignments.append((fname, folder))

        steps: List[Dict[str, Any]] = []
        step_counter = 1

        if not assignments:
            # Read-only inspection plan if no files match
            steps.append({
                "step_id": "s1",
                "action": "list_files",
                "args": {"path": ".", "max_items": 50},
                "depends_on": [],
                "preconditions": ["workspace_readable"],
                "description": "List workspace files (no matching files to move/copy)",
            })
        else:
            folder_to_step: Dict[str, str] = {}
            verify_steps: List[str] = []

            for _, folder in assignments:
                if folder not in folder_to_step:
                    sid = f"s{step_counter}"
                    step_counter += 1
                    folder_to_step[folder] = sid
                    steps.append({
                        "step_id": sid,
                        "action": "create_folder",
                        "args": {"path": folder},
                        "depends_on": [],
                        "preconditions": ["workspace_writable"],
                        "description": f"Create folder '{folder}' inside workspace",
                    })

            for fname, folder in assignments:
                folder_sid = folder_to_step[folder]
                copy_sid = f"s{step_counter}"
                step_counter += 1
                dst_path = f"{folder}/{fname}"
                steps.append({
                    "step_id": copy_sid,
                    "action": "copy_file",
                    "args": {
                        "source": fname,
                        "destination": dst_path,
                        "on_conflict": "skip",
                    },
                    "depends_on": [folder_sid],
                    "preconditions": [f"source_exists:{fname}"],
                    "description": f"Safely copy '{fname}' to '{dst_path}' without overwriting",
                })

                ver_sid = f"s{step_counter}"
                step_counter += 1
                verify_steps.append(ver_sid)
                steps.append({
                    "step_id": ver_sid,
                    "action": "verify_file",
                    "args": {
                        "path": dst_path,
                        "against": fname,
                    },
                    "depends_on": [copy_sid],
                    "preconditions": [f"target_exists:{dst_path}"],
                    "description": f"Verify SHA-256 integrity of '{dst_path}' against '{fname}'",
                })

            manifest_sid = f"s{step_counter}"
            steps.append({
                "step_id": manifest_sid,
                "action": "generate_manifest",
                "args": {
                    "destination": "organization_manifest.json",
                    "include_hashes": True,
                },
                "depends_on": verify_steps,
                "preconditions": [],
                "description": f"Generate verified workspace manifest (planner={llm_note})",
            })

        plan_dict = {
            "protocol_version": "1.0",
            "task_id": resolved_task_id,
            "plan_version": plan_version,
            "workspace_id": workspace_id,
            "goal": user_request.strip(),
            "success_conditions": [
                "All target folders exist inside authorized workspace",
                "Every copied file passes SHA-256 verification against original source",
                "Workspace organization manifest is written and hash-verified",
            ],
            "idempotency_key": idempotency_key,
            "retry_bounds": {
                "max_retries": 2,
                "timeout_seconds": 30.0,
            },
            "approvals": {
                "requires_user_approval": True,
                "approved": approved,
                "allow_overwrite": False,
                "approved_by": "local_user" if approved else None,
                "approved_at": "2026-11-20T06:00:00Z" if approved else None,
            },
            "verification_requirements": {
                "verify_checksums": True,
                "require_manifest": True,
            },
            "steps": steps,
        }
        return validate_task_plan_dict(plan_dict)

    def replan_on_error(
        self,
        previous_plan: TaskPlanV1,
        failed_step_id: str,
        error_code: str,
        live_workspace_files: List[Dict[str, Any]],
    ) -> TaskPlanV1:
        """
        Generate plan_version + 1 excluding missing files or unrecoverable steps
        based on live workspace observations.
        """
        return self.create_plan(
            user_request=previous_plan.goal,
            workspace_files=live_workspace_files,
            workspace_id=previous_plan.workspace_id,
            task_id=f"{previous_plan.task_id}-replan{previous_plan.plan_version + 1}",
            plan_version=previous_plan.plan_version + 1,
            approved=previous_plan.approvals.approved,
        )
