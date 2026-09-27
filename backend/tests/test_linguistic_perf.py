"""Latency / throughput benchmarks for the CRF linguistic compressor."""

import time
from pathlib import Path

import pytest

from gateway.modules.m2_compressor.linguistic import LinguisticCompressor
from gateway.tokenizer import TokenCounter

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "crf_compressor.pkl"
IDF_PATH = Path(__file__).resolve().parents[1] / "data" / "tfidf" / "hinglish_idf.json"

PROMPTS = [
    "yaar wifi slow hai",
    "arre bhai basically mera phone charge nahi ho raha hai",
    "hello sir, mera hostel room 305 ka wifi bahut slow chal raha hai, "
    "matlab kuch bhi load nahi ho raha, assignment ka deadline kal hai, "
    "please jaldi se fix karo, dhanyavaad",
]


@pytest.fixture
def compressor():
    if not MODEL_PATH.exists():
        pytest.skip("CRF model not trained yet")
    return LinguisticCompressor(
        TokenCounter(), crf_model_path=MODEL_PATH, tfidf_path=IDF_PATH
    )


@pytest.mark.parametrize("prompt", PROMPTS)
def test_latency_under_10ms(compressor, prompt):
    compressor.compress(prompt)  # warm up
    n = 200
    start = time.perf_counter()
    for _ in range(n):
        compressor.compress(prompt)
    elapsed_ms = (time.perf_counter() - start) / n * 1000
    assert elapsed_ms < 10, f"Latency {elapsed_ms:.2f}ms exceeds 10ms budget"


def test_batch_throughput(compressor):
    prompts = PROMPTS * 100
    start = time.perf_counter()
    for p in prompts:
        compressor.compress(p)
    throughput = len(prompts) / (time.perf_counter() - start)
    assert throughput > 200, f"Throughput {throughput:.0f}/s below 200/s target"


QUALITY_CORPUS = [
    ("yaar matlab mera email user@example.com par bhejo na", 0.85),
    ("arre bhai hostel ka wifi basically slow chal raha hai", 0.75),
    ("hello sir, mera form bharna hai, deadline kab hai", 0.75),
    ("suno, actually mera phone charge nahi ho raha, charger kharab hai", 0.80),
]


@pytest.mark.parametrize("text,max_ratio", QUALITY_CORPUS)
def test_achieves_compression(compressor, text, max_ratio):
    result = compressor.compress(text)
    assert result.ratio <= max_ratio, (
        f"Ratio {result.ratio:.3f} > target {max_ratio} for: {text}"
    )
