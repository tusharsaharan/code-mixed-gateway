from gateway.modules.m9_reasoning.budget import (
    HinglishEnglishBudgetComparator,
    ReasoningBudgetEstimator,
)
from gateway.tokenizer import TokenCounter


def test_budget_monotonic_with_math():
    est = ReasoningBudgetEstimator(TokenCounter())
    easy = est.estimate("bhai kal chutti hai kya")
    hard = est.estimate("arre yaar physics ka numerical solve karo 5*3+2 ka formula se")
    assert hard.reasoning_tokens > easy.reasoning_tokens


def test_budget_respects_max():
    est = ReasoningBudgetEstimator(TokenCounter(), max_budget=512)
    b = est.estimate("integrate derive solve prove numerical equation " * 30)
    assert b.reasoning_tokens <= 512


def test_code_mix_raises_budget():
    est = ReasoningBudgetEstimator(TokenCounter())
    en = est.estimate("solve this equation for x")
    code = est.estimate("ये equation solve karo x ke liye")
    assert code.reasoning_tokens >= en.reasoning_tokens


def test_comparator_delta_sign_is_reported():
    cmp = HinglishEnglishBudgetComparator()
    out = cmp.compare(
        "ये integrate solve karo formula se", "integrate this using the formula"
    )
    assert "hinglish_budget" in out
    assert "english_budget" in out
    assert out["delta_hinglish_minus_english"] == out["hinglish_budget"] - out["english_budget"]


def test_estimate_returns_core_fields():
    est = ReasoningBudgetEstimator(TokenCounter())
    b = est.estimate("hello world")
    assert b.reasoning_tokens >= 0
    assert 0.0 <= b.code_mix_ratio <= 1.0
    assert b.math_marker_count >= 0
    assert b.logic_marker_count >= 0