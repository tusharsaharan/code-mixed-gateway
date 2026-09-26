import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from gateway.modules.m2_compressor import llmlingua2 as llm2_mod
from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m5_gateway.main import app
from gateway.tokenizer import TokenCounter

needs_lib = pytest.mark.skipif(not llm2_mod.is_available(), reason="llmlingua not installed")


@needs_lib
def test_real_compression_preserves_spans_and_compresses():
    comp = Compressor(TokenCounter())
    text = "yaar mera email user@example.com par bhejo na, total Rs. 2,500 ka refund chahiye tha"
    res = comp.compress_llmlingua2(text, rate=0.5)
    assert res.method == "llmlingua2"
    assert "user@example.com" in res.compressed
    assert "Rs. 2,500" in res.compressed
    assert res.token_compressed < res.token_original


@needs_lib
def test_rate_control_is_real_and_monotonic():
    comp = Compressor(TokenCounter())
    text = (
        "yaar mera phone charge nahi ho raha hai, charger bhi change kar liya "
        "phir bhi nahi on ho raha, kal se yehi problem aa rahi hai bar bar"
    )
    loose = comp.compress_llmlingua2(text, rate=0.9)
    tight = comp.compress_llmlingua2(text, rate=0.3)
    assert loose.method == "llmlingua2" and tight.method == "llmlingua2"
    assert loose.token_compressed >= tight.token_compressed


@needs_lib
def test_batch_helper_stays_aligned():
    from gateway.modules.m7_eval.evaluate import _real_llmlingua2_batch

    originals = [
        "yaar mera email user@example.com par bhejo na",
        "hostel ka wifi slow hai complaint karo jaldi",
        "kal exam hai maths ka integration ke questions bhejo",
    ]
    got = _real_llmlingua2_batch(originals, rate=0.5)
    assert got is not None and len(got) == len(originals)
    assert "user@example.com" in got[0]


def test_falls_back_to_heuristic_when_library_missing(monkeypatch):
    monkeypatch.setattr(llm2_mod, "is_available", lambda: False)
    comp = Compressor(TokenCounter())
    res = comp.compress_llmlingua2("yaar mera phone charge nahi ho raha hai")
    assert res.method == "heuristic"


def test_auto_dispatch_uses_llmlingua2_when_enabled():
    if not llm2_mod.is_available():
        pytest.skip("llmlingua not installed")
    comp = Compressor(TokenCounter(), use_llmlingua2=True)
    res = asyncio.run(comp.compress("yaar mera phone charge nahi ho raha hai, kal se problem hai"))
    assert res.method == "llmlingua2"


def test_auto_dispatch_stays_heuristic_by_default():
    comp = Compressor(TokenCounter())
    res = asyncio.run(comp.compress("yaar mera phone charge nahi ho raha hai"))
    assert res.method == "heuristic"


@needs_lib
def test_curve_points_llmlingua2_is_measured_not_simulated(tmp_path):
    from gateway.modules.m7_eval.evaluate import curve_points

    bench = tmp_path / "bench.jsonl"
    rows = [
        {
            "id": f"bench-{i:03d}",
            "original": t,
            "compressed": t,
            "reference_answer": "ok",
            "predicted_answer": "ok",
            "protected": [],
        }
        for i, t in enumerate(
            [
                "yaar mera email user@example.com par bhejo na refund chahiye",
                "hostel ka wifi slow hai complaint karo jaldi kal se",
                "kal exam hai maths ka integration ke questions bhejo na",
                "bhai ye 15*8+22 ka answer batao jaldi please",
            ]
        )
    ]
    bench.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    points = curve_points(bench, checkpoint=tmp_path / "nope.json")
    llm2 = next(p for p in points if p["method"] == "llmlingua2")
    assert llm2["is_simulated"] is False
    assert 0.0 < llm2["ratio"] <= 1.0


@needs_lib
def test_compress_endpoint_serves_real_llmlingua2():
    with TestClient(app) as client:
        r = client.post(
            "/v1/compress",
            json={"text": "yaar mera email user@example.com par bhejo na", "method": "llmlingua2"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "llmlingua2"
    assert "user@example.com" in body["compressed"]


def test_compress_methods_reports_availability():
    with TestClient(app) as client:
        r = client.get("/v1/compress/methods")
    assert r.status_code == 200
    assert "llmlingua2" in r.json()["methods"]
