import pytest

from gateway.modules.m7_eval.evaluate import HinglishEvaluator
from gateway.schemas import EvalRecord
from gateway.tokenizer import TokenCounter


def _rec(**over):
    base = dict(
        id="r1",
        original="yaar matlab mera email user@example.com par bhejo na",
        compressed="mera email user@example.com par bhejo",
        reference_answer="bhej diya hai user@example.com par",
        predicted_answer="bhej diya hai user@example.com par",
        protected=["user@example.com"],
    )
    base.update(over)
    return EvalRecord(**base)


def test_token_savings_ratio_matches_counter():
    ev = HinglishEvaluator(TokenCounter())
    rec = _rec()
    res = ev.score(rec)
    expected = 1.0 - ev.counter.count(rec.compressed) / ev.counter.count(rec.original)
    assert res.token_savings_ratio == pytest.approx(expected, abs=1e-6)


def test_perfect_answer_scores_high():
    ev = HinglishEvaluator(TokenCounter())
    res = ev.score(_rec())
    assert res.task_success == 1.0
    assert res.bleu > 0.5
    assert res.rouge_l > 0.5


def test_span_preservation_flag():
    ev = HinglishEvaluator(TokenCounter())
    assert ev.score(_rec()).span_preserved is True
    assert ev.score(_rec(compressed="mera email par bhejo")).span_preserved is False


def test_cost_inr_conversion():
    ev = HinglishEvaluator(TokenCounter(), fx_rate_inr_per_usd=83.5)
    res = ev.score(_rec())
    assert res.cost_inr == pytest.approx(res.cost_usd * 83.5, abs=5e-5)
    assert res.savings_usd >= 0.0


def test_evaluate_summary():
    ev = HinglishEvaluator(TokenCounter())
    recs = [
        _rec(),
        _rec(
            id="r2",
            original="Rs. 2,500 transfer karo na abhi",
            compressed="Rs. 2,500 transfer karo",
            reference_answer="Rs. 2,500 transferred",
            predicted_answer="Rs. 2,500 transfer done",
            protected=["Rs. 2,500"],
        ),
    ]
    summary = ev.evaluate(recs)
    assert summary.n == 2
    assert 0.0 <= summary.mean_bleu <= 1.0
    assert 0.0 <= summary.mean_rouge_l <= 1.0
    assert summary.span_preserved_rate == 1.0
    assert summary.total_savings_usd >= 0.0