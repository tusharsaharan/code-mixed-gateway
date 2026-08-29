import pytest
from fastapi.testclient import TestClient

from gateway.modules.m5_gateway.main import app
from gateway.modules.m6_telegram.db import LogDB
from gateway.modules.m8_dashboard.dashboard import (
    dashboard_recent,
    dashboard_series,
    dashboard_stats,
)
from gateway.service import get_log_db


def test_dashboard_stats_from_db(db):
    db.log("u1", 100, 40, "cheap-model", 0.0005)
    db.log("u2", 80, 20, "premium-model", 0.0)
    s = dashboard_stats(db)
    assert s.queries == 2
    assert s.total_original_tokens == 180
    assert s.total_compressed_tokens == 60
    assert s.tier_split == {"cheap-model": 1, "premium-model": 1}
    assert s.total_cost_savings_inr == pytest.approx(0.0005 * 83.5, abs=5e-5)


def test_dashboard_series_and_recent(db):
    db.log("u1", 100, 40, "cheap-model", 0.0005)
    series = dashboard_series(db, 3600)
    assert series and series[0].queries == 1
    recent = dashboard_recent(db, 5)
    assert len(recent) == 1
    assert recent[0]["model_routed"] == "cheap-model"


def test_dashboard_endpoints(tmp_path):
    db = LogDB(tmp_path / "p.sqlite")
    db.log("u1", 100, 40, "cheap-model", 0.0005)
    app.dependency_overrides[get_log_db] = lambda: db
    try:
        with TestClient(app) as client:
            stats = client.get("/v1/dashboard/stats")
            assert stats.status_code == 200
            assert stats.json()["queries"] == 1
            page = client.get("/dashboard")
            assert page.status_code == 200
            assert "Pilot Dashboard" in page.text
    finally:
        app.dependency_overrides.pop(get_log_db, None)
        db.close()