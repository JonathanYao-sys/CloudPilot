"""
M2 Verification Test Suite (Gate 3):
Verifies the entirely local planning-execution loop with network access disabled
(socket monkeypatch proof), including natural-language plan generation, local MLX model traces,
user approval gate, file organization, SHA-256 verification, failure replan recovery, and cancellation.
"""

import json
import socket
from pathlib import Path

import pytest

from app.local_executor.orchestration_loop import LocalOrchestrationLoop
from protocol.versions.v1 import TaskState


@pytest.fixture
def block_all_network(monkeypatch):
    """No-cloud proof: block all outbound socket connections during normal task execution."""

    def _blocked_connect(*args, **kwargs):
        raise RuntimeError("NETWORK_DISABLED_BY_OFFLINE_PROOF: outbound socket connection attempted!")

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket, "create_connection", _blocked_connect)


def test_offline_end_to_end_natural_language_vertical_slice(tmp_path: Path, block_all_network):
    workspace = tmp_path / "offline_demo_ws"
    workspace.mkdir()
    (workspace / "Chapter3.pdf").write_bytes(b"%PDF-1.4 AP European History Study Notes")
    (workspace / "Lecture_Notes.md").write_text("# Renaissance Summary\nKey dates and figures.", encoding="utf-8")
    (workspace / "Budget_2026.csv").write_text("item,cost\nbooks,45\n", encoding="utf-8")

    loop = LocalOrchestrationLoop(
        workspace_root=workspace,
        executor_role="B",
        use_llm_planner_trace=True,
    )

    # 1. Draft plan from natural-language request while network is disabled
    draft = loop.draft_plan(
        "Organize my workspace study files by category and verify every copied file.",
        workspace_id="gate3_sandbox",
        auto_approve=False,
    )
    assert draft["state"] == TaskState.AWAITING_APPROVAL.value
    assert draft["planner_trace"] is not None
    assert draft["planner_trace"]["tokens_per_sec"] > 10.0
    assert len(draft["dry_run_preview"]) >= 6

    # Ensure no files were modified before user approval
    assert not (workspace / "PDF_Docs").exists()

    # 2. Approve and execute with local MLX Executor running on Metal GPU
    result = loop.approve_and_execute(draft["task_id"], approved_by="offline_reviewer")
    assert result["state"] == TaskState.COMPLETED.value
    assert len(result["step_traces"]) >= 6
    assert all(t["executor_trace"]["tokens_per_sec"] > 10.0 for t in result["step_traces"])

    # 3. Verify organized files and manifest exist and match original content
    assert (workspace / "PDF_Docs" / "Chapter3.pdf").exists()
    assert (workspace / "Notes" / "Lecture_Notes.md").exists()
    assert (workspace / "Data_Sheets" / "Budget_2026.csv").exists()
    manifest_file = workspace / "organization_manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_data["file_count"] >= 6


def test_offline_error_replan_and_cancellation(tmp_path: Path, block_all_network):
    workspace = tmp_path / "recovery_ws"
    workspace.mkdir()
    f1 = workspace / "KeepMe.pdf"
    f2 = workspace / "Vanishing.pdf"
    f1.write_bytes(b"%PDF-1.4 stable file")
    f2.write_bytes(b"%PDF-1.4 transient file")

    loop = LocalOrchestrationLoop(
        workspace_root=workspace,
        executor_role="B",
        use_llm_planner_trace=False,
    )

    # Draft plan when both files exist
    draft = loop.draft_plan("Organize all PDF files into folder Archive_PDFs", auto_approve=False)

    # Simulate external removal of Vanishing.pdf before execution so copy_file fails with FILE_NOT_FOUND
    f2.unlink()

    # Execution should catch FILE_NOT_FOUND, trigger local Planner replan_on_error, and complete for KeepMe.pdf
    res = loop.approve_and_execute(draft["task_id"], approved_by="offline_reviewer", allow_replan_on_error=True)
    assert res["state"] == TaskState.COMPLETED.value
    assert res.get("replanned_from_task_id") == draft["task_id"]
    assert (workspace / "Archive_PDFs" / "KeepMe.pdf").exists()

    # Test explicit cancellation checkpoint
    draft_cancel = loop.draft_plan("Organize all PDF files into folder Cancelled_Dir", auto_approve=False)
    cancel_res = loop.approve_and_execute(
        draft_cancel["task_id"],
        approved_by="offline_reviewer",
        cancel_check=lambda step_id: step_id == "s2",
    )
    assert cancel_res["state"] == TaskState.CANCELLED.value
