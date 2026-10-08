"""SQLite storage for case snapshots and immutable audit events."""

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any


class CaseRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL UNIQUE,
                    workflow_status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT NOT NULL,
                    event_key TEXT NOT NULL UNIQUE,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_state(self, case_id: str, thread_id: str, state: dict[str, Any]) -> None:
        safe_state = {key: value for key, value in state.items() if key != "__interrupt__"}
        with self._connection() as connection:
            connection.execute("""
                INSERT INTO cases(case_id, thread_id, workflow_status, state_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    workflow_status=excluded.workflow_status,
                    state_json=excluded.state_json,
                    updated_at=CURRENT_TIMESTAMP
            """, (case_id, thread_id, safe_state.get("workflow_status", "unknown"), json.dumps(safe_state, default=str)))
            for event in safe_state.get("audit_log", []):
                event_json = json.dumps(event, sort_keys=True)
                event_key = sha256(f"{case_id}:{event_json}".encode()).hexdigest()
                connection.execute(
                    "INSERT OR IGNORE INTO audit_events(case_id, event_key, event_json) VALUES (?, ?, ?)",
                    (case_id, event_key, event_json),
                )

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if row is None:
                return None
            events = connection.execute("SELECT event_json FROM audit_events WHERE case_id = ? ORDER BY event_id", (case_id,)).fetchall()
        state = json.loads(row["state_json"])
        state["audit_log"] = [json.loads(event["event_json"]) for event in events]
        return {"case_id": row["case_id"], "thread_id": row["thread_id"], "workflow_status": row["workflow_status"], "state": state}

    def list_cases(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute("SELECT case_id, workflow_status, updated_at, state_json FROM cases ORDER BY updated_at DESC").fetchall()
        return [
            {"case_id": row["case_id"], "workflow_status": row["workflow_status"], "updated_at": row["updated_at"], "patient_id": json.loads(row["state_json"]).get("patient_id"), "risk_level": json.loads(row["state_json"]).get("risk_level")}
            for row in rows
        ]
