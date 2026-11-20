"""
CloudPilot Local Executor Agent (Phase 3, Phase 5, Phase 7)
Wraps the fine-tuned on-device Executor Model (Model B) or baseline models (A / C)
to ground a bounded plan step and workspace observation into a validated JSON tool call.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.model_runtime.mlx_loader import GenerationTrace, LocalMLXRuntime
from protocol.versions.v1 import ALLOWED_EXECUTOR_TOOLS, PlanStep

EXECUTOR_SYSTEM_PROMPT = (
    "You are CloudPilot Local Executor running offline on macOS. "
    "Given the workspace observation and the current plan step, respond with a single valid JSON object only: "
    '{"tool": "<tool_name>", "args": {...}}. '
    "Allowed tools: list_files, get_file_info, create_folder, copy_file, verify_file, generate_manifest, abstain, report_error. "
    "Never use shell commands, never traverse outside workspace ('..'), and abstain or report_error on unsafe or ambiguous steps."
)


def build_executor_user_prompt(
    step: PlanStep,
    workspace_files: List[str],
    allow_overwrite: bool = False,
) -> str:
    payload = {
        "step_id": step.step_id,
        "requested_action": step.action,
        "requested_args": step.args,
        "workspace_files": sorted(workspace_files),
        "policy": {
            "workspace_confined": True,
            "allow_overwrite": allow_overwrite,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


class LocalExecutorAgent:
    def __init__(
        self,
        runtime: LocalMLXRuntime,
        role: str = "B",
        allow_deterministic_fallback: bool = True,
    ):
        self.runtime = runtime
        self.role = role.upper()
        self.allow_deterministic_fallback = allow_deterministic_fallback

    def resolve_step(
        self,
        step: PlanStep,
        workspace_files: List[str],
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Invoke the local MLX Executor model on Metal GPU to ground the plan step into a JSON tool call.
        Returns both the resolved tool call and transparent provenance metadata
        (whether raw model output was directly valid or required deterministic fallback).
        """
        user_prompt = build_executor_user_prompt(step, workspace_files, allow_overwrite=allow_overwrite)
        trace: GenerationTrace = self.runtime.generate_structured(
            role=self.role,
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=96,
        )

        parsed = trace.parsed_json
        raw_model_valid = False
        tool_call: Optional[Dict[str, Any]] = None

        if isinstance(parsed, dict):
            tool_name = parsed.get("tool") or parsed.get("action")
            tool_args = parsed.get("args")
            if tool_name in ALLOWED_EXECUTOR_TOOLS and isinstance(tool_args, dict):
                # Check if model grounded the right tool and essential args
                if tool_name == step.action and self._args_match_step(step.action, tool_args, step.args):
                    raw_model_valid = True
                    tool_call = {"tool": tool_name, "args": tool_args, "step_id": step.step_id}
                elif tool_name in ("abstain", "report_error"):
                    raw_model_valid = True
                    tool_call = {"tool": tool_name, "args": tool_args, "step_id": step.step_id}

        fallback_used = False
        if tool_call is None:
            if not self.allow_deterministic_fallback:
                tool_call = {
                    "tool": "report_error",
                    "args": {
                        "error_code": "SCHEMA_INVALID",
                        "message": f"Model {trace.model_id} produced unparseable tool call: {trace.raw_output[:120]}",
                    },
                    "step_id": step.step_id,
                }
            else:
                fallback_used = True
                tool_call = {
                    "tool": step.action,
                    "args": dict(step.args),
                    "step_id": step.step_id,
                }

        return {
            "tool_call": tool_call,
            "raw_model_valid": raw_model_valid,
            "fallback_used": fallback_used,
            "trace": {
                "role": trace.role,
                "model_id": trace.model_id,
                "adapter_used": trace.adapter_used,
                "raw_output": trace.raw_output,
                "tokens_per_sec": trace.tokens_per_sec,
                "ttft_ms": trace.ttft_ms,
                "peak_metal_memory_mb": trace.peak_metal_memory_mb,
            },
        }

    @staticmethod
    def _args_match_step(action: str, candidate: Dict[str, Any], expected: Dict[str, Any]) -> bool:
        if action in ("create_folder", "get_file_info"):
            return candidate.get("path") == expected.get("path")
        if action == "copy_file":
            return (
                candidate.get("source") == expected.get("source")
                and candidate.get("destination") == expected.get("destination")
            )
        if action == "verify_file":
            return candidate.get("path") == expected.get("path")
        if action == "generate_manifest":
            return candidate.get("destination") == expected.get("destination")
        if action == "list_files":
            return True
        return False
