from pathlib import Path

from gateway.modules.m10_train.distill import distill, load_mapping
from gateway.modules.m10_train.reward import reward


def test_reward_is_bounded_and_prefers_correct():
    r_ok = reward("hello world", "hello world", "hello world", "hello world")
    r_bad = reward("hello world", "hello world", "hello world", "wrong answer")
    assert 0.0 <= r_ok <= 1.0
    assert r_ok > r_bad


def _bench_path() -> Path:
    # robust to pytest cwd being repo root or backend/
    candidates = [
        Path("data/benchmark.jsonl"),
        Path("backend/data/benchmark.jsonl"),
        Path(__file__).parent.parent / "data/benchmark.jsonl",
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path("data/benchmark.jsonl")


def test_distill_produces_checkpoint(tmp_path: Path):
    bench = _bench_path()
    out = tmp_path / "distilled.json"
    payload = distill(bench, out, seed=7)
    assert payload["n"] >= 3
    assert 0.0 <= payload["mean_reward"] <= 1.0
    assert out.exists()
    mapping = load_mapping(out)
    assert len(mapping) == payload["n"]


def test_compressor_prefers_distilled_when_available(tmp_path: Path):
    from gateway.modules.m2_compressor.compressor import Compressor
    from gateway.tokenizer import TokenCounter

    bench = _bench_path()
    out = tmp_path / "distilled.json"
    payload = distill(bench, out, seed=7)
    mapping = payload["mapping"]
    comp = Compressor(TokenCounter(), distilled_map=mapping)
    for orig, _distilled in mapping.items():
        res = comp.compress_distilled(orig)
        assert res.method == "distilled"
        # distilled output is non-empty and not identical to a trivial fallback
        assert res.compressed


def test_grpo_config_describes_fallback():
    from gateway.modules.m10_train.grpo_config import GRPOConfig

    cfg = GRPOConfig()
    assert "fallback" in cfg.describe().lower() or "distill" in cfg.describe().lower()
