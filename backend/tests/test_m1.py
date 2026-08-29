import random

import pytest

from gateway.modules.m1_pipeline.pipeline import build_seed, inject_fluff, normalize
from gateway.modules.m1_pipeline.tokenizer_bench import TokenizerBench


def test_normalize_strips_zero_width_and_collapses_whitespace():
    assert normalize("a\u200bb") == "ab"
    assert normalize("hello   \t world") == "hello world"


def test_inject_fluff_inserts_filler_and_placeholder():
    rng = random.Random(0)
    out = inject_fluff("physics ka numerical samajh nahi aaya", rng)
    markers = ("user@example.com", "def foo", "+91-", "Rs. 2,500")
    assert any(m in out for m in markers)
    assert len(out.split()) >= 7


def test_build_seed_records_are_valid(tmp_path):
    from gateway.modules.m1_pipeline.pipeline import SEED_HINGLISH

    recs = build_seed(tmp_path, seed=0)
    assert len(recs) == len(SEED_HINGLISH)
    assert all(r.id.startswith("seed-") for r in recs)
    assert all(r.fluff_ratio == 0.25 for r in recs)


def test_tokenizer_bench_run_and_columns(tmp_path):
    recs = build_seed(tmp_path, seed=1)
    bench = TokenizerBench()
    rows = bench.run(recs)
    assert len(rows) == len(recs) * len(bench.tokenizers)
    first = rows[0]
    assert first.tokens_per_char > 0


def test_inflation_baseline_is_one(tmp_path):
    recs = build_seed(tmp_path, seed=2)
    bench = TokenizerBench()
    inf = bench.inflation(recs)
    assert inf[bench.baseline] == pytest.approx(1.0, abs=1e-6)
    assert "whitespace" in inf
    assert "char4_proxy" in inf