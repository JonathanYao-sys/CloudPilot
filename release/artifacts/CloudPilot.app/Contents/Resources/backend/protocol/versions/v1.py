"""
CloudPilot Task Protocol v1.0 — Pydantic & JSON Schema Validation
Enforces strict schema typing, DAG dependency checks, and structured error codes.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT_DIR = Path(__file__).resolve().parents[2]
TASK_PLAN_SCHEMA_PATH = ROOT_DIR / "protocol" / "schemas" / "task_plan_v1.json"
TOOL_CALL_SCHEMA_PATH = ROOT_DIR / "protocol" / "schemas" / "tool_call_v1.json"

ALLOWED_PLAN_TOOLS = (
    "list_files",
    "get_file_info",
    "create_folder",
    "copy_file",
    "verify_file",
    "generate_manifest",
)

ALLOWED_EXECUTOR_TOOLS = ALLOWED_PLAN_TOOLS + (
    "abstain",
    "report_error",
)


class TaskState(str, Enum):
    PENDING = "PENDING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    TARGET_EXISTS = "TARGET_EXISTS"
    UNSAFE_PATH = "UNSAFE_PATH"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


class ProtocolValidationError(Exception):
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.SCHEMA_INVALID):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class RetryBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_retries: int = Field(default=2, ge=0, le=5)
    timeout_seconds: float = Field(default=30.0, ge=0.5, le=300.0)


class ApprovalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requires_user_approval: bool = True
    approved: bool = False
    allow_overwrite: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class VerificationRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verify_checksums: bool = True
    require_manifest: bool = False


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str = Field(..., pattern=r"^s[0-9]+$")
    action: Literal[
        "list_files",
        "get_file_info",
        "create_folder",
        "copy_file",
        "verify_file",
        "generate_manifest",
    ]
    args: Dict[str, Any]
    depends_on: List[str] = Field(default_factory=list)
    preconditions: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    @field_validator("args")
    @classmethod
    def check_required_args_per_action(cls, v: Dict[str, Any], info) -> Dict[str, Any]:
        action = info.data.get("action")
        if action == "list_files":
            if "path" not in v:
                v = {"path": ".", **v}
        elif action == "get_file_info":
            if not isinstance(v.get("path"), str) or not v["path"].strip():
                raise ValueError("get_file_info requires non-empty string 'path'")
        elif action == "create_folder":
            if not isinstance(v.get("path"), str) or not v["path"].strip():
                raise ValueError("create_folder requires non-empty string 'path'")
        elif action == "copy_file":
            for req in ("source", "destination"):
                if not isinstance(v.get(req), str) or not v[req].strip():
                    raise ValueError(f"copy_file requires non-empty string '{req}'")
            on_conflict = v.get("on_conflict", "skip")
            if on_conflict not in ("skip", "error", "overwrite"):
                raise ValueError(f"Invalid on_conflict value: {on_conflict}")
            v["on_conflict"] = on_conflict
        elif action == "verify_file":
            if not isinstance(v.get("path"), str) or not v["path"].strip():
                raise ValueError("verify_file requires non-empty string 'path'")
        elif action == "generate_manifest":
            if not isinstance(v.get("destination"), str) or not v["destination"].strip():
                raise ValueError("generate_manifest requires non-empty string 'destination'")
        return v


class TaskPlanV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: Literal["1.0"] = "1.0"
    task_id: str = Field(..., min_length=3, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    plan_version: int = Field(..., ge=1)
    workspace_id: str = Field(..., min_length=1, max_length=128)
    goal: str = Field(..., min_length=3, max_length=1000)
    success_conditions: List[str] = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=6, max_length=256)
    retry_bounds: RetryBounds = Field(default_factory=RetryBounds)
    approvals: ApprovalSpec = Field(default_factory=ApprovalSpec)
    verification_requirements: VerificationRequirements = Field(default_factory=VerificationRequirements)
    steps: List[PlanStep] = Field(..., min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_step_dag(self) -> "TaskPlanV1":
        seen_ids: List[str] = []
        all_ids = {s.step_id for s in self.steps}
        if len(all_ids) != len(self.steps):
            raise ValueError("Duplicate step_id detected in plan steps")
        for step in self.steps:
            for dep in step.depends_on:
                if dep == step.step_id:
                    raise ValueError(f"Step {step.step_id} cannot depend on itself")
                if dep not in all_ids:
                    raise ValueError(f"Step {step.step_id} depends on unknown step {dep}")
                if dep not in seen_ids:
                    raise ValueError(
                        f"Step {step.step_id} depends on future step {dep}; steps must be topologically ordered"
                    )
            seen_ids.append(step.step_id)
        return self


class ToolCallV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal[
        "list_files",
        "get_file_info",
        "create_folder",
        "copy_file",
        "verify_file",
        "generate_manifest",
        "abstain",
        "report_error",
    ]
    args: Dict[str, Any]
    step_id: Optional[str] = None


def validate_task_plan_dict(raw: Dict[str, Any]) -> TaskPlanV1:
    """Validate against both JSON Schema and Pydantic DAG model."""
    schema = json.loads(TASK_PLAN_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=raw, schema=schema)
        return TaskPlanV1.model_validate(raw)
    except Exception as exc:
        raise ProtocolValidationError(
            f"Task plan schema validation failed: {exc}",
            error_code=ErrorCode.SCHEMA_INVALID,
        ) from exc


def validate_tool_call_dict(raw: Dict[str, Any]) -> ToolCallV1:
    schema = json.loads(TOOL_CALL_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=raw, schema=schema)
        return ToolCallV1.model_validate(raw)
    except Exception as exc:
        raise ProtocolValidationError(
            f"Tool call schema validation failed: {exc}",
            error_code=ErrorCode.SCHEMA_INVALID,
        ) from exc
