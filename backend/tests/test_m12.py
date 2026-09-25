import pytest
from fastapi.testclient import TestClient

from gateway.modules.m12_semantic.embeddings import SemanticEmbedder, get_embedder
from gateway.modules.m12_semantic.translate import gloss_sync, rule_gloss, translate_hinglish
from gateway.modules.m5_gateway.main import app
from gateway.modules.m7_eval.evaluate import HinglishEvaluator
from gateway.schemas import EvalRecord


@pytest.fixture(scope="module")
def emb():
    return SemanticEmbedder(use_st=False)


def test_identical_scores_one(emb):
    assert emb.similarity("mujhe refund chahiye", "mujhe refund chahiye") == 1.0


def test_filler_drop_preserves_meaning(emb):
    sim, ok = emb.meaning_preserved(
        "yaar mera phone charge nahi ho raha hai, charger bhi change kar liya",
        "mera phone charge nahi ho raha hai, charger change kar liya",
    )
    assert ok is True
    assert sim >= 0.8


def test_unrelated_scores_lower_than_paraphrase(emb):
    para = emb.similarity("mujhe refund chahiye", "mujhe refund chahiye tha kal")
    unrelated = emb.similarity("mujhe refund chahiye", "hostel ka wifi slow chal raha hai")
    assert para > unrelated


def test_empty_inputs_score_zero(emb):
    assert emb.similarity("", "kuch bhi") == 0.0
    assert emb.similarity("   ", "kuch bhi") == 0.0


def test_nearest_lookup_finds_paraphrase(emb):
    cands = ["hostel ka wifi slow hai", "mujhe refund chahiye tha", "exam kab hai"]
    best, score = emb.nearest("mujhe refund chahiye", cands)
    assert best == "mujhe refund chahiye tha"
    assert score >= 0.55


def test_nearest_returns_none_when_nothing_close(emb):
    best, _ = emb.nearest("quantum gravity equations", ["mess ka menu kya hai"], threshold=0.99)
    assert best is None


def test_rule_gloss_preserves_entities():
    gloss, coverage, uncovered = rule_gloss("yaar mera email user@example.com par bhejo na Rs. 2,500")
    assert "user@example.com" in gloss
    assert "Rs. 2,500" in gloss
    assert "yaar" not in gloss.split()
    assert 0.0 < coverage <= 1.0


def test_gloss_sync_offline_result_shape():
    res = gloss_sync("mujhe refund chahiye")
    assert res.is_rule_based is True
    assert "refund" in res.gloss
    assert 0.0 <= res.similarity <= 1.0
    assert res.backend == "rule"


def test_translate_mock_client_uses_rule_path():
    import asyncio

    from gateway.llm import MockLLMClient

    res = asyncio.run(translate_hinglish("mujhe refund chahiye", client=MockLLMClient(model="cheap")))
    assert res.is_rule_based is True


def test_evaluator_reports_semantic_fields():
    ev = HinglishEvaluator(embedder=SemanticEmbedder(use_st=False))
    rec = EvalRecord(
        id="s1",
        original="yaar mujhe refund chahiye na kal se",
        compressed="mujhe refund chahiye",
        reference_answer="refund issued to your account",
        predicted_answer="refund issued to your account",
        protected=[],
    )
    out = ev.score(rec)
    assert 0.0 <= out.semantic_sim <= 1.0
    assert 0.0 <= out.prompt_sim <= 1.0
    assert out.semantic_sim == 1.0  # identical answers
    assert out.prompt_sim >= 0.55  # filler-drop preserves meaning
    summary = ev.evaluate([rec])
    assert summary.mean_semantic_sim == pytest.approx(out.semantic_sim)


def test_semantic_similarity_endpoint():
    with TestClient(app) as client:
        r = client.post("/v1/semantic/similarity", json={"a": "mujhe refund chahiye", "b": "mujhe refund chahiye"})
    assert r.status_code == 200
    body = r.json()
    assert body["similarity"] == 1.0
    assert body["preserves_meaning"] is True
    assert body["backend"] in {"hash", "st"}


def test_translate_gloss_endpoint_dry_run_is_rule_based():
    with TestClient(app) as client:
        r = client.post("/v1/translate/gloss", json={"text": "mujhe refund chahiye user@example.com par"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_rule_based"] is True
    assert "user@example.com" in body["gloss"]


def test_singleton_embedder_shared():
    assert get_embedder() is get_embedder()
