"""TTL cache for public evidence responses; never stores a patient payload."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


class ExternalEvidenceCache:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS external_evidence_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def get(self, namespace: str, query: dict[str, str]) -> dict[str, Any] | None:
        cache_key = self._key(namespace, query)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json, expires_at FROM external_evidence_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
        if row is None or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            return None
        return json.loads(row["payload_json"])

    def set(self, namespace: str, query: dict[str, str], payload: dict[str, Any], ttl_hours: int = 24) -> None:
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            connection.execute("""
                INSERT INTO external_evidence_cache(cache_key, payload_json, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json=excluded.payload_json, expires_at=excluded.expires_at, created_at=excluded.created_at
            """, (self._key(namespace, query), json.dumps(payload), (now + timedelta(hours=ttl_hours)).isoformat(), now.isoformat()))

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _key(namespace: str, query: dict[str, str]) -> str:
        serialized = json.dumps([namespace, query], sort_keys=True, separators=(",", ":"))
        return sha256(serialized.encode("utf-8")).hexdigest()
