from fastapi.testclient import TestClient

from gateway.modules.m5_gateway.main import app


def test_redteam_safe():
    with TestClient(app) as client:
        r = client.post("/v1/compress/redteam", json={"text": "hello world this is safe", "method": "heuristic"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in {"safe", "break"}
    assert "critical_dropped" in body
    assert "reward" in body


def test_redteam_protected_break():
    # protected span should be detected if compressed drops it - use a known protected amount
    text = "please do NOT refund my order, amount Rs. 2,500 must stay"
    with TestClient(app) as client:
        r = client.post("/v1/compress/redteam", json={"text": text, "method": "heuristic"})
    assert r.status_code == 200
    # heuristic keeps spans, so should be safe
    assert r.json()["verdict"] == "safe"


def test_redteam_challenges_board():
    with TestClient(app) as client:
        # create one attempt first
        client.post("/v1/compress/redteam", json={"text": "test challenge board", "method": "adaptive"})
        r = client.get("/v1/compress/challenges?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "total_attempts" in body
    assert "recent" in body
    assert "by_type" in body


def test_calibration_tri_state():
    with TestClient(app) as client:
        r = client.get("/v1/calibration/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "data_state" in body
    assert body["data_state"] in {"live", "mixed", "synthetic"}
    assert "real_n" in body
    assert "live_threshold" in body
    assert "sweep" in body


def test_calibration_rolling_window():
    with TestClient(app) as client:
        r = client.get("/v1/calibration/metrics?window=200&real_only=true&full_sweep=true")
    assert r.status_code == 200
    assert "rolling_window" in r.json()
    assert r.json()["real_only"] is True
    assert "sweep" in r.json()


def test_difficulty_features():
    with TestClient(app) as client:
        r = client.get("/v1/difficulty/features", params={"text": "yaar mera phone charge nahi ho raha hai, solve this 15*8+22"})
    assert r.status_code == 200
    body = r.json()
    assert "difficulty_score" in body
    assert "contrib_code_mix" in body


def test_reward_autopsy():
    with TestClient(app) as client:
        r = client.get("/v1/reward/autopsy", params={"text": "hello world", "compressed": "hello"})
    assert r.status_code == 200
    assert "combined_reward" in r.json()


def test_prompts_exposed():
    with TestClient(app) as client:
        r = client.get("/v1/prompts")
    assert r.status_code == 200
    assert "compress_system_prompt" in r.json()


def test_receipt_and_feedback():
    payload = {"model": "cascade", "messages": [{"role": "user", "content": "yaar receipt test"}]}
    with TestClient(app) as client:
        chat = client.post("/v1/chat/completions", json=payload).json()
        task_id = chat["id"]
        rec = client.get(f"/v1/receipt/{task_id}")
        assert rec.status_code == 200
        fb = client.post("/v1/feedback", json={"task_id": task_id, "was_correct": True})
        assert fb.status_code == 200
        assert fb.json()["ok"] is True
