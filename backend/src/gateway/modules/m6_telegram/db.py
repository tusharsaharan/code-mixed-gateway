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
    estimated_cost_savings REAL NOT NULL,
    task_id TEXT DEFAULT '',
    compressed_prompt TEXT DEFAULT '',
    tier TEXT DEFAULT 'cheap',
    difficulty_score REAL DEFAULT 0.0,
    was_correct INTEGER DEFAULT NULL
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
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add any missing columns if opened against an older schema."""
        cursor = self._conn.execute("PRAGMA table_info(logs);")
        existing_cols = {row[1] for row in cursor.fetchall()}
        columns = [
            ("task_id", "TEXT DEFAULT ''"),
            ("compressed_prompt", "TEXT DEFAULT ''"),
            ("tier", "TEXT DEFAULT 'cheap'"),
            ("difficulty_score", "REAL DEFAULT 0.0"),
            ("was_correct", "INTEGER DEFAULT NULL"),
        ]
        for col_name, col_def in columns:
            if col_name not in existing_cols:
                try:
                    self._conn.execute(f"ALTER TABLE logs ADD COLUMN {col_name} {col_def};")
                except Exception:
                    pass

    def log(
        self,
        user_id: str,
        original_tokens: int,
        compressed_tokens: int,
        model_routed: str,
        estimated_cost_savings: float,
        task_id: str = "",
        compressed_prompt: str = "",
        tier: str = "cheap",
        difficulty_score: float = 0.0,
        was_correct: bool | None = None,
    ) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO logs "
                "(user_id, ts, original_tokens, compressed_tokens, model_routed, "
                "estimated_cost_savings, task_id, compressed_prompt, tier, difficulty_score, was_correct) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    time.time(),
                    original_tokens,
                    compressed_tokens,
                    model_routed,
                    estimated_cost_savings,
                    task_id,
                    compressed_prompt,
                    tier,
                    difficulty_score,
                    None if was_correct is None else (1 if was_correct else 0),
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
                "SELECT id, user_id, ts, original_tokens, compressed_tokens, model_routed, "
                "estimated_cost_savings, task_id, compressed_prompt, tier, difficulty_score, was_correct "
                "FROM logs ORDER BY id DESC LIMIT ?",
                (max(0, limit),),
            ).fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "ts": r[2],
                "original_tokens": r[3],
                "compressed_tokens": r[4],
                "model_routed": r[5],
                "estimated_cost_savings": r[6],
                "task_id": r[7],
                "compressed_prompt": r[8],
                "tier": r[9],
                "difficulty_score": r[10],
                "was_correct": None if r[11] is None else bool(r[11]),
            }
            for r in rows
        ]

    def get_receipt(self, identifier: str | int) -> dict | None:
        with self._lock:
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                row = self._conn.execute(
                    "SELECT id, user_id, ts, original_tokens, compressed_tokens, model_routed, "
                    "estimated_cost_savings, task_id, compressed_prompt, tier, difficulty_score, was_correct "
                    "FROM logs WHERE id = ? OR task_id = ? LIMIT 1",
                    (int(identifier) if str(identifier).isdigit() else -1, str(identifier)),
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT id, user_id, ts, original_tokens, compressed_tokens, model_routed, "
                    "estimated_cost_savings, task_id, compressed_prompt, tier, difficulty_score, was_correct "
                    "FROM logs WHERE task_id = ? LIMIT 1",
                    (str(identifier),),
                ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "ts": row[2],
            "original_tokens": row[3],
            "compressed_tokens": row[4],
            "model_routed": row[5],
            "estimated_cost_savings": row[6],
            "task_id": row[7],
            "compressed_prompt": row[8],
            "tier": row[9],
            "difficulty_score": row[10],
            "was_correct": None if row[11] is None else bool(row[11]),
        }

    def record_feedback(self, identifier: str | int, was_correct: bool) -> bool:
        val = 1 if was_correct else 0
        with self._lock:
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                cur = self._conn.execute(
                    "UPDATE logs SET was_correct = ? WHERE id = ? OR task_id = ?",
                    (val, int(identifier) if str(identifier).isdigit() else -1, str(identifier)),
                )
            else:
                cur = self._conn.execute(
                    "UPDATE logs SET was_correct = ? WHERE task_id = ?",
                    (val, str(identifier)),
                )
            self._conn.commit()
            return cur.rowcount > 0