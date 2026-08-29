from __future__ import annotations

from pathlib import Path

from gateway.config import get_settings
from gateway.modules.m6_telegram.db import LogDB
from gateway.schemas import DashboardStats, SeriesPoint


def dashboard_stats(db: LogDB) -> DashboardStats:
    s = get_settings()
    raw = db.stats()
    savings = float(raw["total_cost_savings"])
    return DashboardStats(
        queries=int(raw["queries"]),
        total_original_tokens=int(raw["total_original_tokens"]),
        total_compressed_tokens=int(raw["total_compressed_tokens"]),
        total_cost_savings_usd=round(savings, 8),
        total_cost_savings_inr=round(savings * s.fx_rate_inr_per_usd, 4),
        tier_split=db.model_split(),
    )


def dashboard_series(db: LogDB, window_seconds: int = 3600) -> list[SeriesPoint]:
    return [
        SeriesPoint(bucket=str(ts), queries=queries, savings_usd=round(savings, 8))
        for ts, queries, savings in db.series(window_seconds)
    ]


def dashboard_recent(db: LogDB, limit: int = 20) -> list[dict]:
    return db.recent(limit)


def dashboard_html() -> str:
    return Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")