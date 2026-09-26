"""Phase 1 tests: equivalence-gated translation + /v1/gloss endpoint."""

import pytest

from gateway.llm import MockLLMClient
from gateway.modules.m12_novel.gloss import to_english_gloss
from gateway.modules.m12_novel.translate import (
    AMBER_THRESHOLD,
    LEXICAL_AMBER_THRESHOLD,
    LEXICAL_PASS_THRESHOLD,
    PASS_THRESHOLD,
    TranslationResult,
    _lexical_similarity,
    equivalence_ok,
    gate_score,
    translate,
)


def test_gate_score_bands():
    assert gate_score(0.95, engine="embedding") == "pass"
    assert gate_score(0.60, engine="embedding") == "amber"
    assert gate_score(0.20, engine="embedding") == "reject"
    # lexical profile has its own scale
    assert gate_score(0.35, engine="lexical") == "pass"
    assert gate_score(0.22, engine="lexical") == "amber"
    assert gate_score(0.10, engine="lexical") == "reject"


def test_equivalence_ok_includes_amber_by_default():
    assert equivalence_ok(TranslationResult("x", 0.95, "pass", "model", "embedding"))
    assert equivalence_ok(TranslationResult("x", 0.60, "amber", "model", "embedding"))
    assert not equivalence_ok(TranslationResult("x", 0.20, "reject", "model", "embedding"))
    assert not equivalence_ok(
        TranslationResult("x", 0.60, "amber", "model", "embedding"), include_amber=False
    )


def test_lexical_similarity_identical_and_unrelated():
    assert _lexical_similarity("hostel wifi slow", "hostel wifi slow") > 0.9
    assert _lexical_similarity("hostel wifi slow", "quantum flux capacitor") < 0.3


@pytest.mark.asyncio
async def test_translate_no_client_uses_dictionary():
    res = await translate(
        "yaar mera hostel ka wifi slow hai",
        "en",
        client=None,
        dictionary_fallback=to_english_gloss,
    )
    assert res.source == "dictionary"
    assert res.engine == "lexical"
    assert res.gate in ("pass", "amber", "reject")
    # dictionary gloss keeps recognizable content
    assert "wifi" in res.text or "hostel" in res.text


@pytest.mark.asyncio
async def test_translate_passthrough_hi_without_client():
    res = await translate("hostel wifi slow hai", "hi", client=None)
    assert res.source == "passthrough"
    assert res.text == "hostel wifi slow hai"


@pytest.mark.asyncio
async def test_translate_rejects_garbage_model_output():
    """Model returns unrelated text → gate rejects → dictionary fallback."""
    canned = "[[COMPRESSED]]"  # canned MockLLMClient reply — unrelated to input
    client = MockLLMClient(model="mock", canned=canned)
    res = await translate(
        "yaar mera hostel ka wifi slow hai",
        "en",
        client=client,
        dictionary_fallback=to_english_gloss,
    )
    assert res.gate == "reject"
    assert res.source == "dictionary"
    # similarity reflects the rejected candidate (lexically unrelated)
    assert res.similarity < LEXICAL_PASS_THRESHOLD


@pytest.mark.asyncio
async def test_translate_accepts_equivalent_model_output():
    src = "yaar mera hostel ka wifi slow hai complaint kahan karun"
    good = "my hostel's wifi is slow, where should I file a complaint?"
    client = MockLLMClient(model="mock", canned=good)
    res = await translate(src, "en", client=client, dictionary_fallback=to_english_gloss)
    assert res.source == "model"
    assert res.gate in ("pass", "amber")
    assert "complaint" in res.text


@pytest.mark.asyncio
async def test_translate_empty_text():
    res = await translate("", "en", client=None)
    assert res.text == ""
    assert res.gate == "pass"


def test_gloss_endpoint_offline_dictionary_mode():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/gloss", json={"text": "yaar mera hostel ka wifi slow hai"})
        assert r.status_code == 200
        body = r.json()
        assert body["model_used"] is False
        assert "en" in body and "hi" in body
        assert body["en"]["source"] == "dictionary"
        assert body["hi"]["source"] == "passthrough"
        assert body["en"]["gate"] in ("pass", "amber", "reject")


def test_gloss_endpoint_validation():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/gloss", json={"text": "   "})
        assert r.status_code == 400
        r2 = client.post("/v1/gloss", json={"text": "ok", "target": "fr"})
        assert r2.status_code == 400


def test_gloss_endpoint_en_only():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/gloss", json={"text": "hostel ka wifi slow hai", "target": "en"})
        assert r.status_code == 200
        assert "en" in r.json()
        assert "hi" not in r.json()


def test_thresholds_sane():
    # model/engine thresholds
    assert 0 < AMBER_THRESHOLD < PASS_THRESHOLD < 1.0
    # lexical profile is strictly looser (cross-lingual overlap is lower-scale)
    assert 0 < LEXICAL_AMBER_THRESHOLD < LEXICAL_PASS_THRESHOLD < PASS_THRESHOLD
