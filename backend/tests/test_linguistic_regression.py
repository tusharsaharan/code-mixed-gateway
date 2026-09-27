"""Regression: CRF compressor must be at least as good as the lexicon prune.

Ports the preserve/drop contracts from test_lexicon.py to the CRF path.
"""

from pathlib import Path

import pytest

from gateway.modules.m2_compressor.linguistic import LinguisticCompressor
from gateway.modules.m2_compressor.safety_span import detect_spans
from gateway.tokenizer import TokenCounter

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "crf_compressor.pkl"
IDF_PATH = Path(__file__).resolve().parents[1] / "data" / "tfidf" / "hinglish_idf.json"


@pytest.fixture
def compressor():
    if not MODEL_PATH.exists():
        pytest.skip("CRF model not trained yet")
    return LinguisticCompressor(
        TokenCounter(), crf_model_path=MODEL_PATH, tfidf_path=IDF_PATH
    )


DROP_CASES = [
    ("bhai mera assignment submit nahi hua", "bhai"),
    ("hostel ka wifi matlab bahut slow chal raha hai", "matlab"),
    ("suno mera phone charge nahi ho raha", "suno"),
]


@pytest.mark.parametrize("text,dropped", DROP_CASES)
def test_crf_drops_what_lexicon_drops(compressor, text, dropped):
    result = compressor.compress(text)
    assert dropped not in result.compressed.lower().split()


PRESERVE_CASES = [
    ("mere bhai ka phone kho gaya", "bhai"),
    ("download matlab free version for students", "matlab"),
    ("I like this hostel room", "like"),
    ("the sun rises in the east", "sun"),
]


@pytest.mark.parametrize("text,kept", PRESERVE_CASES)
def test_crf_keeps_what_lexicon_keeps(compressor, text, kept):
    result = compressor.compress(text)
    assert kept in result.compressed.lower().split()


ENTITY_CASES = [
    "yaar matlab send to user@example.com abhi",
    "total Rs. 2,500 bhejo account mein",
]


@pytest.mark.parametrize("text", ENTITY_CASES)
def test_entities_always_preserved(compressor, text):
    result = compressor.compress(text)
    for span in detect_spans(text):
        assert span.text in result.compressed
