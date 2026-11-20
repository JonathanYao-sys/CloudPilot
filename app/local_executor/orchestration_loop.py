"""
CloudPilot Local Planning-Execution Orchestration Loop (Phase 3 & Phase 6)
Connects Local Planner (P) -> Plan Preview & User Approval -> Local Executor Model (B/A) ->
Policy Validator -> Deterministic Tool Runtime -> SQLite State Store -> Local Error Replan.
Also provides a local JSON IPC CLI for the native SwiftUI macOS application.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.local_executor.executor_agent import LocalExecutorAgent
from app.local_executor.state_store import StateStore
from app.local_executor.tool_runtime import DeterministicToolRuntime
from app.local_planner.planner import LocalPlanner
from app.model_runtime.mlx_loader import LocalMLXRuntime
from app.security.policy_validator import PolicyValidator, WorkspacePolicy
from protocol.versions.v1 import ErrorCode, TaskPlanV1, TaskState, validate_task_plan_dict


class LocalOrchestrationLoop:
    def __init__(
        self,
        workspace_root: Path,
        db_path: Optional[Path] = None,
        executor_role: str = "B",
        use_llm_planner_trace: bool = True,
    ):
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (self.workspace_root / ".cloudpilot_state.db")

        self.state_store = StateStore(self.db_path)
        self.validator = PolicyValidator(WorkspacePolicy(workspace_root=self.workspace_root))
        self.tool_runtime = DeterministicToolRuntime(validator=self.validator, state_store=self.state_store)
        self.mlx_runtime = LocalMLXRuntime()
        self.planner = LocalPlanner(runtime=self.mlx_runtime, use_llm_trace=use_llm_planner_trace)
        self.executor = LocalExecutorAgent(
            runtime=self.mlx_runtime,
            role=executor_role,
            allow_deterministic_fallback=True,
        )

    def list_workspace_files(self) -> List[Dict[str, Any]]:
        res = self.tool_runtime.execute_tool_call({"tool": "list_files", "args": {"path": ".", "max_items": 200}})
        if not res.ok:
            return []
        return res.output.get("entries", [])

    def draft_plan(
        self,
        user_request: str,
        workspace_id: str = "local_workspace",
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        entries = self.list_workspace_files()
        plan = self.planner.create_plan(
            user_request=user_request,
            workspace_files=entries,
            workspace_id=workspace_id,
            approved=auto_approve,
        )
        task_record = self.state_store.register_plan(plan)
        if auto_approve and not task_record["approved"]:
            self.state_store.approve_task(plan.task_id, approved_by="local_user")
            task_record = self.state_store.get_task(plan.task_id)
            plan = validate_task_plan_dict(json.loads(task_record["plan_json"]))

        dry_run_preview = []
        for s in plan.steps:
            dry_run_preview.append({
                "step_id": s.step_id,
                "action": s.action,
                "args": s.args,
                "description": s.description,
                "mutates_filesystem": s.action in {"create_folder", "copy_file", "generate_manifest"},
            })

        return {
            "task_id": plan.task_id,
            "state": task_record["state"],
            "plan": json.loads(plan.model_dump_json()),
            "dry_run_preview": dry_run_preview,
            "planner_trace": self.planner.last_planner_trace,
        }

    def approve_and_execute(
        self,
        task_id: str,
        approved_by: str = "local_user",
        cancel_check: Optional[Callable[[str], bool]] = None,
        allow_replan_on_error: bool = True,
    ) -> Dict[str, Any]:
        self.state_store.approve_task(task_id, approved_by=approved_by)
        task_record = self.state_store.get_task(task_id)
        plan = validate_task_plan_dict(json.loads(task_record["plan_json"]))
        return self._run_plan(
            plan=plan,
            cancel_check=cancel_check,
            allow_replan_on_error=allow_replan_on_error,
        )

    def _run_plan(
        self,
        plan: TaskPlanV1,
        cancel_check: Optional[Callable[[str], bool]] = None,
        allow_replan_on_error: bool = True,
    ) -> Dict[str, Any]:
        self.state_store.update_task_state(plan.task_id, TaskState.RUNNING)
        step_traces: List[Dict[str, Any]] = []
        completed_steps: set[str] = set()

        for step in plan.steps:
            # Explicit cancellation boundary before each step
            if cancel_check and cancel_check(step.step_id):
                self.state_store.update_step_state(plan.task_id, step.step_id, TaskState.CANCELLED)
                self.state_store.update_task_state(
                    plan.task_id,
                    TaskState.CANCELLED,
                    error_code="CANCELLED_BY_USER",
                    error_message=f"Cancelled before step {step.step_id}",
                )
                return {
                    "task_id": plan.task_id,
                    "state": TaskState.CANCELLED.value,
                    "step_traces": step_traces,
                    "task_record": self.state_store.get_task(plan.task_id),
                }

            # Check DAG dependencies
            if not all(dep in completed_steps for dep in step.depends_on):
                self.state_store.update_step_state(
                    plan.task_id,
                    step.step_id,
                    TaskState.FAILED,
                    error_code=ErrorCode.PRECONDITION_FAILED.value,
                    error_message=f"Unmet dependencies for {step.step_id}: {step.depends_on}",
                )
                self.state_store.update_task_state(
                    plan.task_id,
                    TaskState.FAILED,
                    error_code=ErrorCode.PRECONDITION_FAILED.value,
                    error_message=f"Dependency failure at {step.step_id}",
                )
                break

            max_attempts = plan.retry_bounds.max_retries + 1
            step_succeeded = False
            last_error_code = None
            last_error_msg = None

            for attempt in range(1, max_attempts + 1):
                self.state_store.update_step_state(
                    plan.task_id,
                    step.step_id,
                    TaskState.RUNNING,
                    increment_attempt=True,
                )
                live_files = [e["path"] for e in self.list_workspace_files()]
                resolved = self.executor.resolve_step(
                    step=step,
                    workspace_files=live_files,
                    allow_overwrite=plan.approvals.allow_overwrite,
                )
                exec_res = self.tool_runtime.execute_tool_call(
                    resolved["tool_call"],
                    plan=plan,
                    dry_run=False,
                )

                step_traces.append({
                    "step_id": step.step_id,
                    "attempt": attempt,
                    "tool_call": resolved["tool_call"],
                    "raw_model_valid": resolved["raw_model_valid"],
                    "fallback_used": resolved["fallback_used"],
                    "executor_trace": resolved["trace"],
                    "execution_result": exec_res.to_dict(),
                })

                if exec_res.ok:
                    self.state_store.update_step_state(
                        plan.task_id,
                        step.step_id,
                        TaskState.COMPLETED,
                        result=exec_res.output,
                    )
                    completed_steps.add(step.step_id)
                    step_succeeded = True
                    break
                else:
                    last_error_code = exec_res.error_code.value if exec_res.error_code else "EXECUTION_ERROR"
                    last_error_msg = exec_res.error_message

            if not step_succeeded:
                self.state_store.update_step_state(
                    plan.task_id,
                    step.step_id,
                    TaskState.FAILED,
                    error_code=last_error_code,
                    error_message=last_error_msg,
                )
                self.state_store.update_task_state(
                    plan.task_id,
                    TaskState.FAILED,
                    error_code=last_error_code,
                    error_message=last_error_msg,
                )

                if allow_replan_on_error and last_error_code == ErrorCode.FILE_NOT_FOUND.value:
                    live_entries = self.list_workspace_files()
                    new_plan = self.planner.replan_on_error(
                        previous_plan=plan,
                        failed_step_id=step.step_id,
                        error_code=last_error_code,
                        live_workspace_files=live_entries,
                    )
                    self.state_store.register_plan(new_plan)
                    self.state_store.approve_task(new_plan.task_id, approved_by="local_auto_replan")
                    replan_result = self._run_plan(
                        plan=new_plan,
                        cancel_check=cancel_check,
                        allow_replan_on_error=False,
                    )
                    replan_result["replanned_from_task_id"] = plan.task_id
                    replan_result["failed_step_trigger"] = step.step_id
                    return replan_result

                return {
                    "task_id": plan.task_id,
                    "state": TaskState.FAILED.value,
                    "error_code": last_error_code,
                    "error_message": last_error_msg,
                    "step_traces": step_traces,
                    "task_record": self.state_store.get_task(plan.task_id),
                }

        self.state_store.update_task_state(plan.task_id, TaskState.COMPLETED)
        return {
            "task_id": plan.task_id,
            "state": TaskState.COMPLETED.value,
            "step_traces": step_traces,
            "task_record": self.state_store.get_task(plan.task_id),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="CloudPilot Local Orchestration CLI (IPC Bridge)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_models = sub.add_parser("models", help="Inspect local model inventory & hashes")

    p_plan = sub.add_parser("plan", help="Draft a local task plan for a workspace")
    p_plan.add_argument("--workspace", required=True, help="Workspace directory path")
    p_plan.add_argument("--request", required=True, help="Natural language user request")
    p_plan.add_argument("--fast", action="store_true", help="Skip LLM planner trace for instant UI preview")

    p_run = sub.add_parser("run", help="Draft, approve, and execute a task offline")
    p_run.add_argument("--workspace", required=True, help="Workspace directory path")
    p_run.add_argument("--request", required=True, help="Natural language user request")
    p_run.add_argument("--role", default="B", help="Executor model role (B, A, or C)")
    p_run.add_argument("--block-network", action="store_true", help="Monkeypatch socket.connect to enforce zero network access")

    p_hist = sub.add_parser("history", help="Fetch SQLite task & audit history for a workspace")
    p_hist.add_argument("--workspace", required=True, help="Workspace directory path")

    args = parser.parse_args()

    if args.cmd == "models":
        print(json.dumps(LocalMLXRuntime.get_model_inventory(), indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "plan":
        loop = LocalOrchestrationLoop(
            workspace_root=Path(args.workspace),
            use_llm_planner_trace=not args.fast,
        )
        out = loop.draft_plan(args.request, auto_approve=False)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "run":
        if getattr(args, "block_network", False):
            import socket

            def _blocked_connect(*_a, **_kw):
                raise RuntimeError("NETWORK_DISABLED_BY_OFFLINE_PROOF: outbound socket connection blocked")

            socket.socket.connect = _blocked_connect  # type: ignore[method-assign]
            socket.create_connection = _blocked_connect  # type: ignore[assignment]

        loop = LocalOrchestrationLoop(
            workspace_root=Path(args.workspace),
            executor_role=args.role,
            use_llm_planner_trace=True,
        )
        draft = loop.draft_plan(args.request, auto_approve=False)
        res = loop.approve_and_execute(draft["task_id"], approved_by="macos_app_user")
        model_dir, adapter_dir, model_id = loop.mlx_runtime.resolve_role_paths(args.role)
        runtime_provenance = {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_home": os.environ.get("PYTHONHOME", ""),
            "backend_module_file": str(Path(__file__).resolve()),
            "loaded_model_id": model_id,
            "loaded_model_dir": str(model_dir),
            "loaded_adapter_dir": str(adapter_dir) if adapter_dir else None,
            "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE") == "1",
            "network_sockets_blocked": bool(getattr(args, "block_network", False)),
        }
        print(json.dumps({"draft": draft, "execution": res, "runtime_provenance": runtime_provenance}, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "history":
        ws = Path(args.workspace).resolve()
        store = StateStore(ws / ".cloudpilot_state.db")
        print(json.dumps({"audit_logs": store.get_audit_logs()}, indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
