from fastapi.testclient import TestClient

from gateway.modules.m5_gateway.main import app


def test_healthz():
    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["dry_run"] is True


def test_models_listing():
    with TestClient(app) as client:
        r = client.get("/v1/models")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 3


def test_chat_completions_returns_openai_shape():
    payload = {
        "model": "cascade",
        "messages": [
            {"role": "user", "content": "yaar matlab mera email user@example.com par bhejo na"}
        ],
    }
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "user@example.com" in body["choices"][0]["message"]["content"]
    meta = body["x_gateway"]
    assert meta["tier"] in {"cheap", "premium"}
    assert meta["compression_ratio"] <= 1.0


def test_chat_completions_rejects_no_user_message():
    payload = {"model": "cascade", "messages": [{"role": "system", "content": "hi"}]}
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 400
    assert "error" in r.json()


def test_compress_endpoint():
    with TestClient(app) as client:
        r = client.post("/v1/compress", json={"text": "yaar mera phone charge nahi ho raha hai", "method": "heuristic"})
    assert r.status_code == 200
    assert r.json()["method"] == "heuristic"
    assert r.json()["token_original"] >= r.json()["token_compressed"]


def test_reasoning_budget_endpoint():
    with TestClient(app) as client:
        r = client.post("/v1/reasoning/budget", json={"text": "yaar ye equation solve karo x ke liye"})
    assert r.status_code == 200
    assert r.json()["code_mix_ratio"] > 0.0


def test_tokenizer_report():
    with TestClient(app) as client:
        r = client.get("/v1/tokenizer/report")
    assert r.status_code == 200
    assert "inflation_vs_gpt4o" in r.json()


def test_calibration_metrics_has_both_bounds():
    with TestClient(app) as client:
        r = client.get("/v1/calibration/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "error_bound_simple" in body
    assert "error_bound_hoeffding" in body
    assert "ece" in body


def test_stream_and_nonstream_meta_shape_parity():
    payload = {"model": "cascade", "messages": [{"role": "user", "content": "yaar email bhejo user@example.com"}]}
    with TestClient(app) as client:
        normal = client.post("/v1/chat/completions", json=payload).json()["x_gateway"]
        stream = client.post("/v1/chat/completions", json={**payload, "stream": True})
    assert stream.status_code == 200
    # first SSE chunk contains x_gateway
    first_line = [ln for ln in stream.text.splitlines() if "x_gateway" in ln][0]
    import json as _json

    data = _json.loads(first_line.split("data:", 1)[1].strip())
    stream_meta = data["x_gateway"]
    assert set(stream_meta.keys()) == set(normal.keys()), (set(stream_meta), set(normal))
    # key fields that were previously missing in stream should now be present
    for k in ["reasoning_budget", "budget_delta_hinglish_en", "error_bound", "calibration_n", "estimated_cost_usd"]:
        assert k in stream_meta