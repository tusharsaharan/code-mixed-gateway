from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ts REAL NOT NULL,
    original_tokens INTEGER NOT NULL,
    compressed_tokens INTEGER NOT NULL,
    model_routed TEXT NOT NULL,
    estimated_cost_savings REAL NOT NULL
);
"""


class LogDB:
    """SQLite store for the live pilot dashboard (WAL mode, thread-safe)."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def log(
        self,
        user_id: str,
        original_tokens: int,
        compressed_tokens: int,
        model_routed: str,
        estimated_cost_savings: float,
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO logs "
                "(user_id, ts, original_tokens, compressed_tokens, model_routed, "
                "estimated_cost_savings) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    time.time(),
                    original_tokens,
                    compressed_tokens,
                    model_routed,
                    estimated_cost_savings,
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def stats(self) -> dict[str, float]:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(original_tokens),0), "
                "COALESCE(SUM(compressed_tokens),0), "
                "COALESCE(SUM(estimated_cost_savings),0) FROM logs"
            ).fetchone()
        return {
            "queries": row[0],
            "total_original_tokens": row[1],
            "total_compressed_tokens": row[2],
            "total_cost_savings": row[3],
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def model_split(self) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT model_routed, COUNT(*) FROM logs GROUP BY model_routed"
            ).fetchall()
        return {str(r[0]): int(r[1]) for r in rows}

    def series(self, window_seconds: int) -> list[tuple[int, int, float]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT CAST((ts / ?) AS INTEGER) * ? AS bucket, COUNT(*), "
                "COALESCE(SUM(estimated_cost_savings),0) FROM logs GROUP BY bucket ORDER BY bucket",
                (window_seconds, window_seconds),
            ).fetchall()
        return [(int(r[0]), int(r[1]), float(r[2])) for r in rows]

    def recent(self, limit: int = 20) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT user_id, ts, original_tokens, compressed_tokens, model_routed, "
                "estimated_cost_savings FROM logs ORDER BY id DESC LIMIT ?",
                (max(0, limit),),
            ).fetchall()
        return [
            {
                "user_id": r[0],
                "ts": r[1],
                "original_tokens": r[2],
                "compressed_tokens": r[3],
                "model_routed": r[4],
                "estimated_cost_savings": r[5],
            }
            for r in rows
        ]