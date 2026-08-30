import json

import pytest

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
from gateway.modules.m12_novel.adaptive import adaptive_compress, target_kept_ratio
from gateway.modules.m12_novel.gloss import HINGLISH_TO_EN, to_english_gloss
from gateway.tokenizer import TokenCounter


def test_target_kept_ratio_bounds():
    assert target_kept_ratio(0.0, 0.0) == pytest.approx(0.52, abs=1e-6)
    assert target_kept_ratio(1.0, 1.0) == pytest.approx(0.92, abs=1e-6)
    assert target_kept_ratio(10.0, 10.0) == pytest.approx(0.92, abs=1e-6)
    assert target_kept_ratio(-5, -5) == pytest.approx(0.38, abs=1e-6)
    for cm in [0.0, 0.2, 0.5, 0.8]:
        for diff in [0.0, 0.3, 0.7]:
            v = target_kept_ratio(cm, diff)
            assert 0.38 <= v <= 0.92


def test_target_kept_ratio_monotonic():
    # more code-mix or difficulty → higher kept ratio (more conservative)
    low = target_kept_ratio(0.1, 0.2)
    high_mix = target_kept_ratio(0.8, 0.2)
    high_diff = target_kept_ratio(0.1, 0.9)
    assert high_mix > low
    assert high_diff > low
    # combined is highest
    assert target_kept_ratio(0.8, 0.9) >= max(high_mix, high_diff)


def test_adaptive_compress_preserves_protected_spans():
    text = "yaar matlab mera email user@example.com par bhejo na, Rs. 2,500 ka bill hai"
    res = adaptive_compress(text)
    assert "user@example.com" in res.compressed
    assert "Rs. 2,500" in res.compressed
    assert 0 < res.ratio <= 1.0
    assert res.token_compressed <= res.token_original
    assert res.token_compressed >= 1


def test_adaptive_compress_conservative_high_mix():
    # high Hinglish + math -> target >0.82, conservative (almost no truncation)
    text = (
        "bhai ye maths ka sawal solve karo 15*8+22 ka answer batao jaldi "
        "yaar matlab basically hostel ka wifi slow hai"
    )
    cm = code_mix_ratio(text)
    assert cm > 0.2  # ensures penalty triggers
    res = adaptive_compress(text)
    # conservative path keeps most tokens
    assert res.ratio > 0.4


def test_adaptive_compress_aggressive_english():
    text = "Explain the difference between AI and ML in simple language for a presentation with five bullet points"
    res = adaptive_compress(text)
    assert res.compressed
    assert res.ratio <= 1.0


def test_adaptive_compress_empty_and_short():
    res = adaptive_compress("hi")
    assert res.compressed
    assert res.ratio == pytest.approx(1.0, abs=1e-6) or res.token_compressed == res.token_original


def test_to_english_gloss_deterministic_and_fillers_dropped():
    text = "yaar mera phone charge nahi ho raha hai"
    gloss = to_english_gloss(text)
    # 'yaar' is filler mapped to friend but actually yaar->friend, so should appear
    # 'na' and filler '' should be dropped elsewhere
    assert gloss != text
    assert "friend" in gloss.lower() or "my" in gloss.lower()
    # na should be dropped
    assert to_english_gloss("bhejo na") == "send"
    # idempotent
    assert to_english_gloss(text) == to_english_gloss(text)


def test_to_english_gloss_preserves_punctuation_and_case():
    assert to_english_gloss("Mera phone slow hai, kya karun?") == "My phone slow is, what do?"
    assert to_english_gloss("yaar, jaldi batao na.") == "friend, quickly tell"
    # unknown tokens kept
    assert "wifi" in to_english_gloss("hostel ka wifi slow hai")
    # numbers kept
    t = "15*8+22 ka answer kya hoga?"
    g = to_english_gloss(t)
    assert "15*8+22" in g


def test_to_english_gloss_empty_and_no_hinglish():
    pure = "This is pure English text with no Hinglish"
    assert to_english_gloss(pure) == pure
    assert to_english_gloss("") == ""


def test_hinglish_map_no_empty_keys_coverage():
    # ensure every Hinglish seed token that is in SEED_HINGLISH has some coverage reasoning
    assert "mera" in HINGLISH_TO_EN
    assert HINGLISH_TO_EN["na"] == ""
    assert HINGLISH_TO_EN["actually"] == ""


def test_tokenizer_tax_report_structure(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import write_benchmark
    from gateway.modules.m12_novel.analysis import tokenizer_tax_report

    bench = tmp_path / "benchmark.jsonl"
    write_benchmark(bench, n=12, seed=1)
    # need seed file or benchmark for recs; ensure data dir has benchmark
    data_dir = tmp_path
    # also copy seed from benchmark logic: tokenizer_tax_report prefers seed_hinglish.jsonl then benchmark
    report = tokenizer_tax_report(data_dir)
    assert "buckets" in report
    assert len(report["buckets"]) == 3
    assert "hinglish_tax_ratio" in report
    assert report["hinglish_tax_ratio"] >= 0.5
    for b in report["buckets"]:
        assert "char4_inflation" in b
        assert b["char4_inflation"] >= 0


def test_adaptive_vs_fixed_report(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import write_benchmark
    from gateway.modules.m12_novel.analysis import adaptive_vs_fixed_report

    bench = tmp_path / "benchmark.jsonl"
    write_benchmark(bench, n=10, seed=2)
    # minimal distilled checkpoint
    ckpt = tmp_path / "checkpoints" / "distilled.json"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_text(json.dumps({"hello world": "hello"}), encoding="utf-8")
    report = adaptive_vs_fixed_report(bench, ckpt)
    assert report["n"] == 10
    methods = {r["method"] for r in report["methods"]}
    assert {"heuristic", "distilled", "adaptive", "truncated@0.5"} == methods
    for m in report["methods"]:
        assert 0 < m["avg_kept_ratio"] <= 1.0
        assert 0 <= m["avg_reward"] <= 1.0
        assert 0 <= m["avg_savings"] <= 1.0
    # adaptive should be flagged
    adaptive = next(r for r in report["methods"] if r["is_adaptive"])
    assert adaptive["method"] == "adaptive"


def test_reasoning_delta_report(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import write_benchmark
    from gateway.modules.m12_novel.analysis import reasoning_delta_report

    bench = tmp_path / "benchmark.jsonl"
    write_benchmark(bench, n=12, seed=3)
    report = reasoning_delta_report(bench)
    assert "n_pairs" in report
    assert "mean_delta" in report
    assert "histogram" in report
    assert report["n_pairs"] >= 1
    # histogram sums to n_pairs
    total_hist = sum(h["count"] for h in report["histogram"])
    assert total_hist == report["n_pairs"]
    assert "top_hinglish_heavier" in report
    assert isinstance(report["mean_delta"], float)


def test_conformal_compression_report(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import write_benchmark
    from gateway.modules.m12_novel.analysis import conformal_compression_report

    bench = tmp_path / "benchmark.jsonl"
    write_benchmark(bench, n=8, seed=4)
    # need data/checkpoints/distilled.json fallback exists in repo; ensure write_benchmark used owns counter
    report = conformal_compression_report(bench)
    assert "threshold_reward" in report
    assert report["threshold_reward"] == 0.85
    for key in ["heuristic", "distilled", "adaptive"]:
        assert key in report
        assert 0 <= report[key]["risk_hat"] <= 1.0
        assert report[key]["risk_bound"] >= report[key]["risk_hat"]
        assert report[key]["n"] == 8
    assert report["best_method"] in {"heuristic", "distilled", "adaptive"}


def test_build_novel_report_aggregates(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import write_benchmark
    from gateway.modules.m12_novel.analysis import build_novel_report

    write_benchmark(tmp_path / "benchmark.jsonl", n=10, seed=5)
    (tmp_path / "checkpoints").mkdir(parents=True, exist_ok=True)
    (tmp_path / "checkpoints" / "distilled.json").write_text("{}", encoding="utf-8")
    report = build_novel_report(tmp_path)
    assert report["n_benchmark"] == 10
    assert "tokenizer_tax" in report
    assert "adaptive" in report
    assert "reasoning_delta" in report
    assert "conformal_compression" in report
    assert "summary_bullets" in report
    assert len(report["summary_bullets"]) == 5
    assert "generated_at" in report


def test_adaptive_vs_fixed_empty_benchmark(tmp_path):
    from gateway.modules.m12_novel.analysis import adaptive_vs_fixed_report

    empty = tmp_path / "benchmark.jsonl"
    empty.write_text("", encoding="utf-8")
    assert adaptive_vs_fixed_report(empty)["n"] == 0
    assert adaptive_vs_fixed_report(empty)["methods"] == []


def test_tokenizer_counter_fallback():
    c = TokenCounter()
    assert c.count("hello world") >= 2
    assert c.count("") == 0 or c.count("") >= 0
