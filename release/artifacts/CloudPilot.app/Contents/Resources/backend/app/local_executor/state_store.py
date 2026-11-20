"""
CloudPilot SQLite State Store (Phase 3)
Tracks task & step states:
PENDING, AWAITING_APPROVAL, RUNNING, BLOCKED, FAILED, CANCELLED, COMPLETED
Persists idempotency keys, approved plan version, step evidence, verification outputs, and audit logs.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from protocol.versions.v1 import TaskPlanV1, TaskState


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class StateStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    plan_version INTEGER NOT NULL,
                    workspace_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    state TEXT NOT NULL,
                    approved INTEGER NOT NULL,
                    plan_json TEXT NOT NULL,
                    error_code TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS steps (
                    task_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, step_id)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    step_id TEXT,
                    event TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                );
                """
            )

    def get_task_by_idempotency_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return dict(row) if row else None

    def register_plan(self, plan: TaskPlanV1) -> Dict[str, Any]:
        existing = self.get_task_by_idempotency_key(plan.idempotency_key)
        if existing:
            return existing

        initial_state = (
            TaskState.PENDING.value
            if (plan.approvals.approved or not plan.approvals.requires_user_approval)
            else TaskState.AWAITING_APPROVAL.value
        )
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, idempotency_key, plan_version, workspace_id, goal,
                    state, approved, plan_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.task_id,
                    plan.idempotency_key,
                    plan.plan_version,
                    plan.workspace_id,
                    plan.goal,
                    initial_state,
                    1 if plan.approvals.approved else 0,
                    plan.model_dump_json(),
                    now,
                    now,
                ),
            )
            for s in plan.steps:
                conn.execute(
                    """
                    INSERT INTO steps (
                        task_id, step_id, action, args_json, state, attempts, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        plan.task_id,
                        s.step_id,
                        s.action,
                        json.dumps(s.args, ensure_ascii=False),
                        TaskState.PENDING.value,
                        now,
                    ),
                )
            self._log_in_tx(conn, plan.task_id, None, "PLAN_REGISTERED", {"state": initial_state})
        return self.get_task(plan.task_id)

    def approve_task(self, task_id: str, approved_by: str = "local_user") -> None:
        now = utc_now()
        with self._connect() as conn:
            row = conn.execute("SELECT plan_json FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                raise KeyError(f"Task {task_id} not found")
            plan_data = json.loads(row["plan_json"])
            plan_data["approvals"]["approved"] = True
            plan_data["approvals"]["approved_by"] = approved_by
            plan_data["approvals"]["approved_at"] = now
            conn.execute(
                """
                UPDATE tasks
                SET approved = 1, state = ?, plan_json = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (TaskState.PENDING.value, json.dumps(plan_data, ensure_ascii=False), now, task_id),
            )
            self._log_in_tx(conn, task_id, None, "TASK_APPROVED", {"approved_by": approved_by})

    def update_task_state(
        self,
        task_id: str,
        state: TaskState,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET state = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (state.value, error_code, error_message, now, task_id),
            )
            self._log_in_tx(
                conn,
                task_id,
                None,
                f"TASK_STATE_{state.value}",
                {"error_code": error_code, "error_message": error_message},
            )

    def update_step_state(
        self,
        task_id: str,
        step_id: str,
        state: TaskState,
        increment_attempt: bool = False,
        result: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        now = utc_now()
        with self._connect() as conn:
            if increment_attempt:
                conn.execute(
                    "UPDATE steps SET attempts = attempts + 1 WHERE task_id = ? AND step_id = ?",
                    (task_id, step_id),
                )
            conn.execute(
                """
                UPDATE steps
                SET state = ?, result_json = ?, error_code = ?, error_message = ?, updated_at = ?
                WHERE task_id = ? AND step_id = ?
                """,
                (
                    state.value,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    error_code,
                    error_message,
                    now,
                    task_id,
                    step_id,
                ),
            )
            self._log_in_tx(
                conn,
                task_id,
                step_id,
                f"STEP_{state.value}",
                {"result": result, "error_code": error_code, "error_message": error_message},
            )

    def get_task(self, task_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            t = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not t:
                raise KeyError(f"Task {task_id} not found")
            steps = conn.execute(
                "SELECT * FROM steps WHERE task_id = ? ORDER BY rowid ASC",
                (task_id,),
            ).fetchall()
            out = dict(t)
            out["steps"] = [dict(s) for s in steps]
            return out

    def get_audit_logs(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE task_id = ? ORDER BY id ASC",
                    (task_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
            return [dict(r) for r in rows]

    def _log_in_tx(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        step_id: Optional[str],
        event: str,
        detail: Dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_log (timestamp, task_id, step_id, event, detail_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (utc_now(), task_id, step_id, event, json.dumps(detail, ensure_ascii=False)),
        )
