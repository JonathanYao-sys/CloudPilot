#!/usr/bin/env python3
"""
CloudPilot Workflow Orchestrator
Implements the workflow loop:
  agent.md (Requirements & Acceptance Criteria)
     ↓
  Orchestrator (Read plan · Assign next stage · Record state)
     ↓
  Coding Agent (Write code -> Run -> Test -> Auto-repair within retry bounds)
     ↓
  progress.json + Git Checkpoints (Save completed tasks, failure reasons, next step)
     🔄 Unfinished -> Resume execution / All passed -> Finish
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = ROOT_DIR / "progress.json"
STATUS_FILE = ROOT_DIR / "PROJECT_STATUS.md"
SPEC_FILE = ROOT_DIR / "agent.md"


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_progress() -> dict:
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(data: dict) -> None:
    data["updated_at"] = utc_now()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    render_project_status(data)


def render_project_status(data: dict) -> None:
    """Sync PROJECT_STATUS.md deterministically from progress.json."""
    lines = [
        "# CloudPilot — Project Status & Gate Tracker",
        "",
        f"> **Source Specification:** `{data.get('source_spec', 'agent.md')}` ({data.get('spec_version', '4.0')})  ",
        f"> **Workflow Pattern:** `{data.get('workflow_architecture')}`  ",
        f"> **Overall Workflow Status:** `{data.get('workflow_status')}`  ",
        f"> **Current Active Milestone:** `{data.get('current_milestone')}`  ",
        f"> **Last Updated (UTC):** `{data.get('updated_at')}`",
        "",
        "## 1. Milestone & Gate Summary",
        "",
        "| Milestone | Phase / Gate | Title | Status | Attempts | Git Checkpoint |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for m in data["milestones"]:
        cp = m.get("git_checkpoint") or {}
        cp_str = f"`{cp['tag']}` (`{cp['commit'][:7]}`)" if cp.get("commit") else "—"
        lines.append(
            f"| **{m['id']}** | {m['phase']} ({m['gate']}) | {m['title']} | `{m['status']}` | {m['attempts']}/{m['max_attempts']} | {cp_str} |"
        )

    lines.extend([
        "",
        "## 2. Detailed Milestone Evidence, Failure Reasons & Next Steps",
        "",
    ])
    for m in data["milestones"]:
        lines.append(f"### {m['id']}: {m['title']}")
        lines.append(f"- **Status:** `{m['status']}`")
        lines.append(f"- **Dependencies:** {', '.join(m['depends_on']) if m['depends_on'] else 'None'}")
        lines.append(f"- **Verification Command:** `{m['verification_command']}`")
        lines.append(f"- **Attempts:** {m['attempts']} / {m['max_attempts']}")
        if m.get("failure_reasons"):
            lines.append("- **Recorded Failure Reasons (Auto-Repair Loop):**")
            for idx, reason in enumerate(m["failure_reasons"], 1):
                lines.append(f"  {idx}. `{reason}`")
        if m.get("evidence"):
            lines.append(f"- **Gate Verification Evidence:** {m['evidence']}")
        cp = m.get("git_checkpoint") or {}
        if cp.get("commit"):
            lines.append(f"- **Git Checkpoint:** commit `{cp['commit']}`, tag `{cp['tag']}` at `{cp['timestamp']}`")
        lines.append(f"- **Next Step:** {m['next_step']}")
        lines.append("")

    lines.extend([
        "## 3. Orchestrator Execution Log (Recent Events)",
        "",
    ])
    for evt in data.get("history", [])[-20:]:
        lines.append(
            f"- `{evt['timestamp']}` **[{evt['event']}]** (`{evt['milestone']}`): {evt['detail']}"
        )
    lines.append("")

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_milestone(data: dict, milestone_id: str) -> dict:
    for m in data["milestones"]:
        if m["id"] == milestone_id:
            return m
    raise ValueError(f"Unknown milestone: {milestone_id}")


def next_pending_milestone(data: dict):
    completed = {m["id"] for m in data["milestones"] if m["status"] == "PASSED"}
    for m in data["milestones"]:
        if m["status"] in ("NOT_STARTED", "IN_PROGRESS", "FAILED"):
            if all(dep in completed for dep in m["depends_on"]):
                return m
    return None


def create_git_checkpoint(milestone_id: str, title: str) -> dict:
    """Stage changes, create a Git commit and tag for the passed milestone."""
    subprocess.run(["git", "add", "-A"], cwd=ROOT_DIR, check=True)
    status_out = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    commit_msg = f"checkpoint({milestone_id}): {title}"
    if status_out:
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tag_name = f"checkpoint-{milestone_id}"
    subprocess.run(
        ["git", "tag", "-f", tag_name, commit_hash],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "commit": commit_hash,
        "tag": tag_name,
        "timestamp": utc_now(),
    }


def cmd_status(_args) -> int:
    data = load_progress()
    render_project_status(data)
    nxt = next_pending_milestone(data)
    print(json.dumps({
        "workflow_status": data["workflow_status"],
        "current_milestone": data["current_milestone"],
        "next_executable_milestone": nxt["id"] if nxt else None,
        "next_title": nxt["title"] if nxt else None,
        "summary": {m["id"]: m["status"] for m in data["milestones"]},
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_start(args) -> int:
    data = load_progress()
    m = get_milestone(data, args.milestone)
    completed = {x["id"] for x in data["milestones"] if x["status"] == "PASSED"}
    missing_deps = [d for d in m["depends_on"] if d not in completed]
    if missing_deps:
        print(f"Cannot start {m['id']}: unmet dependencies {missing_deps}", file=sys.stderr)
        return 1
    m["status"] = "IN_PROGRESS"
    data["current_milestone"] = m["id"]
    data["history"].append({
        "timestamp": utc_now(),
        "event": "MILESTONE_STARTED",
        "milestone": m["id"],
        "detail": f"Orchestrator assigned {m['id']} ({m['title']}) to Coding Agent.",
    })
    save_progress(data)
    print(f"Started {m['id']}: {m['title']}")
    return 0


def cmd_verify(args) -> int:
    """Run deliverable existence checks + verification_command for a milestone.
    If passed: mark PASSED, update progress.json & PROJECT_STATUS.md, create Git Checkpoint, advance next_step.
    If failed: increment attempts, record failure reason, allow retry if attempts < max_attempts.
    """
    data = load_progress()
    m = get_milestone(data, args.milestone)
    m["attempts"] += 1

    missing_files = [rel for rel in m["deliverables"] if not (ROOT_DIR / rel).exists()]
    if missing_files:
        reason = f"Missing deliverables: {', '.join(missing_files)}"
        m["failure_reasons"].append(reason)
        m["status"] = "FAILED" if m["attempts"] < m["max_attempts"] else "BLOCKED"
        data["history"].append({
            "timestamp": utc_now(),
            "event": "VERIFICATION_FAILED",
            "milestone": m["id"],
            "detail": f"Attempt {m['attempts']}/{m['max_attempts']} failed: {reason}",
        })
        save_progress(data)
        print(f"[FAIL] {m['id']}: {reason}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        m["verification_command"],
        cwd=ROOT_DIR,
        shell=True,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        out_tail = (proc.stdout + "\n" + proc.stderr).strip()[-600:].replace("\n", " | ")
        reason = f"Command `{m['verification_command']}` exited {proc.returncode}: {out_tail}"
        m["failure_reasons"].append(reason)
        m["status"] = "FAILED" if m["attempts"] < m["max_attempts"] else "BLOCKED"
        data["history"].append({
            "timestamp": utc_now(),
            "event": "VERIFICATION_FAILED",
            "milestone": m["id"],
            "detail": f"Attempt {m['attempts']}/{m['max_attempts']} failed: {reason[:240]}",
        })
        save_progress(data)
        print(f"[FAIL] {m['id']} verification command failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
        return 1

    # Verification succeeded!
    summary_line = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    evidence_str = args.evidence or (summary_line[-1] if summary_line else "All checks passed.")
    m["status"] = "PASSED"
    m["evidence"] = evidence_str

    nxt = next_pending_milestone(data)
    if nxt:
        m["next_step"] = f"Proceed to {nxt['id']}: {nxt['title']}"
        data["current_milestone"] = nxt["id"]
    else:
        m["next_step"] = "All milestones completed."
        data["workflow_status"] = "COMPLETED"

    data["history"].append({
        "timestamp": utc_now(),
        "event": "MILESTONE_PASSED",
        "milestone": m["id"],
        "detail": f"Attempt {m['attempts']} passed gate verification. Evidence: {evidence_str}",
    })
    save_progress(data)

    # Create Git Checkpoint including updated progress.json & PROJECT_STATUS.md
    cp = create_git_checkpoint(m["id"], m["title"])
    m["git_checkpoint"] = cp
    data["history"].append({
        "timestamp": utc_now(),
        "event": "GIT_CHECKPOINT_CREATED",
        "milestone": m["id"],
        "detail": f"Created git tag {cp['tag']} at commit {cp['commit'][:7]}",
    })
    save_progress(data)
    # Amend commit so progress.json and PROJECT_STATUS.md contain the exact commit/tag metadata
    subprocess.run(["git", "add", "progress.json", "PROJECT_STATUS.md"], cwd=ROOT_DIR, check=True)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit"],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )
    final_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(["git", "tag", "-f", cp["tag"], final_hash], cwd=ROOT_DIR, check=True)
    m["git_checkpoint"]["commit"] = final_hash
    save_progress(data)

    print(f"[PASS] {m['id']} verified and checkpointed at {cp['tag']} ({final_hash[:7]})")
    return 0


def cmd_block(args) -> int:
    data = load_progress()
    m = get_milestone(data, args.milestone)
    m["status"] = "BLOCKED"
    m["failure_reasons"].append(args.reason)
    m["next_step"] = args.next_step or "Awaiting user authorization / external account access."
    data["workflow_status"] = "PAUSED_AWAITING_USER_APPROVAL"
    data["history"].append({
        "timestamp": utc_now(),
        "event": "MILESTONE_BLOCKED_ON_GATE",
        "milestone": m["id"],
        "detail": args.reason,
    })
    save_progress(data)
    cp = create_git_checkpoint(f"{m['id']}-blocked", f"Blocked {m['id']}: {args.reason[:50]}")
    m["git_checkpoint"] = cp
    save_progress(data)
    print(f"[BLOCKED] {m['id']}: {args.reason}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CloudPilot Task Orchestrator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show current workflow status and sync PROJECT_STATUS.md")

    p_start = sub.add_parser("start", help="Mark a milestone IN_PROGRESS")
    p_start.add_argument("milestone", help="Milestone ID (e.g. M0)")

    p_verify = sub.add_parser("verify", help="Verify deliverables, run gate test, checkpoint git")
    p_verify.add_argument("milestone", help="Milestone ID (e.g. M0)")
    p_verify.add_argument("--evidence", default=None, help="Optional evidence summary")

    p_block = sub.add_parser("block", help="Record an explicit approval/hardware block on a milestone")
    p_block.add_argument("milestone", help="Milestone ID (e.g. M8)")
    p_block.add_argument("--reason", required=True, help="Block reason")
    p_block.add_argument("--next-step", default=None, help="Next step needed to unblock")

    sub.add_parser("check-publication", help="Check if public release URLs are configured and authorized")

    args = parser.parse_args()
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "start":
        return cmd_start(args)
    if args.cmd == "verify":
        return cmd_verify(args)
    if args.cmd == "block":
        return cmd_block(args)
    if args.cmd == "check-publication":
        print("Public internet publication requires explicit user approval per agent.md Section 2.2.", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
