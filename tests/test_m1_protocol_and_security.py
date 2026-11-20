"""
M1 Verification Test Suite (Gate 2):
Tests versioned task protocol schemas, DAG dependency checks, Policy Validator security boundaries,
SQLite state persistence, and all 6 deterministic tools in Tool Runtime.
"""

import json
import os
from pathlib import Path

import pytest

from app.local_executor.state_store import StateStore
from app.local_executor.tool_runtime import DeterministicToolRuntime
from app.security.policy_validator import PolicyValidator, PolicyViolationError, WorkspacePolicy
from protocol.versions.v1 import (
    ErrorCode,
    ProtocolValidationError,
    TaskState,
    validate_task_plan_dict,
    validate_tool_call_dict,
)

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_demo_plan_schema_valid():
    demo_path = ROOT_DIR / "protocol" / "examples" / "demo_plan.json"
    raw = json.loads(demo_path.read_text(encoding="utf-8"))
    plan = validate_task_plan_dict(raw)
    assert plan.protocol_version == "1.0"
    assert plan.task_id == "demo-001"
    assert len(plan.steps) == 4


def test_reject_invalid_schema_and_disallowed_tools():
    demo_path = ROOT_DIR / "protocol" / "examples" / "demo_plan.json"
    raw = json.loads(demo_path.read_text(encoding="utf-8"))

    # Disallowed shell execution tool
    bad_tool = json.loads(json.dumps(raw))
    bad_tool["steps"][0]["action"] = "execute_shell"
    with pytest.raises(ProtocolValidationError) as exc_info:
        validate_task_plan_dict(bad_tool)
    assert exc_info.value.error_code == ErrorCode.SCHEMA_INVALID

    # Future/circular step dependency
    bad_dag = json.loads(json.dumps(raw))
    bad_dag["steps"][0]["depends_on"] = ["s2"]
    with pytest.raises(ProtocolValidationError) as exc_info2:
        validate_task_plan_dict(bad_dag)
    assert exc_info2.value.error_code == ErrorCode.SCHEMA_INVALID


def test_policy_validator_blocks_traversal_symlinks_and_unapproved_writes(tmp_path: Path):
    workspace = tmp_path / "sandbox"
    workspace.mkdir()
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("SECRET_DO_NOT_READ", encoding="utf-8")

    validator = PolicyValidator(WorkspacePolicy(workspace_root=workspace))

    # 1. Path traversal '..'
    with pytest.raises(PolicyViolationError) as e1:
        validator.resolve_safe_path("../outside_secret.txt")
    assert e1.value.error_code == ErrorCode.UNSAFE_PATH

    # 2. Absolute path
    with pytest.raises(PolicyViolationError) as e2:
        validator.resolve_safe_path("/etc/passwd")
    assert e2.value.error_code == ErrorCode.UNSAFE_PATH

    # 3. Home relative path
    with pytest.raises(PolicyViolationError) as e3:
        validator.resolve_safe_path("~/.ssh/id_rsa")
    assert e3.value.error_code == ErrorCode.UNSAFE_PATH

    # 4. External symlink inside workspace
    symlink_path = workspace / "evil_link.txt"
    os.symlink(outside, symlink_path)
    with pytest.raises(PolicyViolationError) as e4:
        validator.resolve_safe_path("evil_link.txt")
    assert e4.value.error_code == ErrorCode.UNSAFE_PATH

    # 5. Unapproved plan with write steps
    demo_raw = json.loads((ROOT_DIR / "protocol" / "examples" / "demo_plan.json").read_text(encoding="utf-8"))
    demo_raw["approvals"]["approved"] = False
    unapproved_plan = validate_task_plan_dict(demo_raw)
    with pytest.raises(PolicyViolationError) as e5:
        validator.validate_plan(unapproved_plan)
    assert e5.value.error_code == ErrorCode.PERMISSION_DENIED

    # 6. Overwrite without permission
    with pytest.raises(PolicyViolationError) as e6:
        validator.validate_tool_call(
            {"tool": "copy_file", "args": {"source": "a.txt", "destination": "b.txt", "on_conflict": "overwrite"}}
        )
    assert e6.value.error_code == ErrorCode.PERMISSION_DENIED


def test_deterministic_tool_runtime_and_sqlite_state_store(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "Chapter3.pdf").write_bytes(b"%PDF-1.4 synthetic AP Euro study guide content")

    db_path = tmp_path / "state.db"
    store = StateStore(db_path)
    validator = PolicyValidator(WorkspacePolicy(workspace_root=workspace))
    runtime = DeterministicToolRuntime(validator=validator, state_store=store)

    demo_raw = json.loads((ROOT_DIR / "protocol" / "examples" / "demo_plan.json").read_text(encoding="utf-8"))
    demo_raw["approvals"]["approved"] = False
    plan = validate_task_plan_dict(demo_raw)

    # Register unapproved plan -> AWAITING_APPROVAL
    task_row = store.register_plan(plan)
    assert task_row["state"] == TaskState.AWAITING_APPROVAL.value

    # Approve task -> PENDING
    store.approve_task(plan.task_id, approved_by="local_tester")
    task_row = store.get_task(plan.task_id)
    assert task_row["state"] == TaskState.PENDING.value
    assert task_row["approved"] == 1

    approved_plan = validate_task_plan_dict(json.loads(task_row["plan_json"]))

    # Execute all 4 steps in demo_plan
    store.update_task_state(plan.task_id, TaskState.RUNNING)
    for step in approved_plan.steps:
        store.update_step_state(plan.task_id, step.step_id, TaskState.RUNNING, increment_attempt=True)
        res = runtime.execute_tool_call({"tool": step.action, "args": step.args}, plan=approved_plan)
        assert res.ok, f"Step {step.step_id} failed: {res.error_message}"
        store.update_step_state(plan.task_id, step.step_id, TaskState.COMPLETED, result=res.output)

    store.update_task_state(plan.task_id, TaskState.COMPLETED)

    # Also test list_files and get_file_info
    list_res = runtime.execute_tool_call({"tool": "list_files", "args": {"path": "AP_Euro"}})
    assert list_res.ok
    assert list_res.output["count"] == 2

    info_res = runtime.execute_tool_call({"tool": "get_file_info", "args": {"path": "AP_Euro/Chapter3.pdf"}})
    assert info_res.ok
    assert info_res.output["size_bytes"] > 10
    assert len(info_res.output["sha256"]) == 64

    # Idempotent replay of copy_file with on_conflict="skip"
    replay_copy = runtime.execute_tool_call(
        {
            "tool": "copy_file",
            "args": {"source": "Chapter3.pdf", "destination": "AP_Euro/Chapter3.pdf", "on_conflict": "skip"},
        },
        plan=approved_plan,
    )
    assert replay_copy.ok
    assert replay_copy.output["action_taken"] == "skipped_existing"
    assert replay_copy.output["identical_sha256"] is True

    final_task = store.get_task(plan.task_id)
    assert final_task["state"] == TaskState.COMPLETED.value
    logs = store.get_audit_logs(plan.task_id)
    assert len(logs) >= 6
