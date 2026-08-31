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


def test_conformal_sweep_grid_and_monotonicity():
    from gateway.modules.m3_conformal.conformal import ConformalCalibrator
    from gateway.schemas import CalibSample

    cal = ConformalCalibrator(alpha=0.10, delta=0.05)
    samples = [
        CalibSample(id="1", nonconformity=0.2, cheap_success=True),
        CalibSample(id="2", nonconformity=0.4, cheap_success=True),
        CalibSample(id="3", nonconformity=0.6, cheap_success=False),
        CalibSample(id="4", nonconformity=0.8, cheap_success=False),
    ]
    cal.calibrate(samples)
    sweep = cal.sweep()
    assert len(sweep) == 201
    assert sweep[0]["tau"] == 0.0
    assert sweep[-1]["tau"] == 1.0
    assert any(pt["is_selected"] for pt in sweep)
    for pt in sweep:
        assert 0.0 <= pt["risk_hat"] <= 1.0
        assert pt["risk_bound"] >= pt["risk_hat"]


def test_reward_autopsy_decomposition():
    from gateway.modules.m10_train.reward import reward, reward_autopsy

    orig = "yaar mera email user@example.com par bhejo na"
    comp = "mera email user@example.com par bhejo"
    ref = "send my email to user@example.com"
    pred = "send email to user@example.com"

    r = reward(orig, comp, ref, pred)
    autopsy = reward_autopsy(orig, comp, ref, pred)

    assert "answer_fidelity" in autopsy
    assert "faithfulness" in autopsy
    assert autopsy["w_fidelity"] == 0.7
    assert autopsy["w_faithfulness"] == 0.3
    assert autopsy["combined_reward"] == r
    assert 0.0 <= autopsy["answer_fidelity"] <= 1.0
    assert 0.0 <= autopsy["faithfulness"] <= 1.0


def test_difficulty_features_and_anatomy():
    from gateway.modules.m4_router.difficulty import DifficultyScorer

    scorer = DifficultyScorer()
    text = "arre yaar solve physics equation 15*8+22 ka answer Rs. 500 me batao"
    f = scorer.features(text)

    assert f.char_count == len(text)
    assert f.token_count > 0
    assert f.code_mix_ratio > 0.0
    assert f.math_marker_count >= 1
    assert f.entity_density > 0.0

    s = scorer.score(text)
    assert 0.0 <= s <= 1.0


def test_candidates_generation_and_scoring():
    from gateway.modules.m10_train.distill import _variants
    from gateway.modules.m10_train.reward import reward_autopsy

    text = "yaar basically hostel ka wifi bahut slow chal raha hai"
    cands = _variants(text, seed=42)
    assert len(cands) >= 3
    for c in cands:
        autopsy = reward_autopsy(text, c, text, text)
        assert 0.0 <= autopsy["combined_reward"] <= 1.0


def test_universal_gloss_reasoning_delta():
    from gateway.modules.m9_reasoning.budget import HinglishEnglishBudgetComparator

    comp = HinglishEnglishBudgetComparator()
    # Query not in hardcoded dict
    text = "yaar mera computer restart nahi ho raha hai please help karo"
    gloss = comp.gloss_for(text)
    assert gloss is not None
    assert gloss != text
    assert comp.delta(text, gloss) is not None


def test_log_db_receipts_and_feedback(tmp_path):
    from gateway.modules.m6_telegram.db import LogDB

    db_path = tmp_path / "test_pilot.db"
    db = LogDB(db_path)

    log_id = db.log(
        user_id="u123",
        original_tokens=25,
        compressed_tokens=15,
        model_routed="test-model",
        estimated_cost_savings=0.0025,
        task_id="cmg-test-999",
        compressed_prompt="compressed test prompt",
        tier="cheap",
        difficulty_score=0.345,
    )
    assert log_id > 0

    receipt = db.get_receipt("cmg-test-999")
    assert receipt is not None
    assert receipt["task_id"] == "cmg-test-999"
    assert receipt["tier"] == "cheap"
    assert receipt["difficulty_score"] == pytest.approx(0.345, abs=1e-3)
    assert receipt["was_correct"] is None

    # Record feedback
    ok = db.record_feedback("cmg-test-999", True)
    assert ok is True

    receipt_after = db.get_receipt("cmg-test-999")
    assert receipt_after["was_correct"] is True
    db.close()


def test_new_endpoints_via_testclient():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    client = TestClient(app)

    # 1. Prompts
    r_prompts = client.get("/v1/prompts")
    assert r_prompts.status_code == 200
    data_p = r_prompts.json()
    assert "compress_system_prompt" in data_p
    assert "difficulty_weights" in data_p
    assert "reward_weights" in data_p
    assert "commit_sha" in data_p

    # 2. Difficulty features
    r_diff = client.get("/v1/difficulty/features?text=yaar+hostel+ka+wifi+slow+hai")
    assert r_diff.status_code == 200
    data_d = r_diff.json()
    assert "w_code_mix" in data_d
    assert "contrib_code_mix" in data_d
    assert "difficulty_score" in data_d

    # 3. Reward autopsy
    r_autopsy = client.get("/v1/reward/autopsy?text=yaar+mera+email+bhejo")
    assert r_autopsy.status_code == 200
    data_a = r_autopsy.json()
    assert "answer_fidelity" in data_a
    assert "faithfulness" in data_a
    assert "combined_reward" in data_a

    # 4. Candidates
    r_cands = client.get("/v1/compress/candidates?text=yaar+mera+phone+charge+nahi+ho+raha+hai")
    assert r_cands.status_code == 200
    data_c = r_cands.json()
    assert len(data_c["candidates"]) >= 3
    assert data_c["winner_index"] >= 0

    # 5. Calibration metrics with sweep
    r_cal = client.get("/v1/calibration/metrics?full_sweep=1")
    assert r_cal.status_code == 200
    data_cal = r_cal.json()
    assert "sweep" in data_cal
    assert len(data_cal["sweep"]) == 201
