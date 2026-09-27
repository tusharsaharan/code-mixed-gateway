"""Integration tests for the CRF linguistic compressor (end-to-end)."""

from pathlib import Path

import pytest

from gateway.modules.m2_compressor.linguistic import LinguisticCompressor
from gateway.schemas import DropRecord
from gateway.tokenizer import TokenCounter

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "crf_compressor.pkl"
IDF_PATH = Path(__file__).resolve().parents[1] / "data" / "tfidf" / "hinglish_idf.json"

ALL_NEG = {
    "nahi", "nahin", "nhi", "nai", "mat", "mtt",
    "not", "never", "n't", "no", "don't", "doesn't", "didn't",
}


@pytest.fixture
def compressor():
    if not MODEL_PATH.exists():
        pytest.skip("CRF model not trained yet")
    return LinguisticCompressor(
        TokenCounter(), crf_model_path=MODEL_PATH, tfidf_path=IDF_PATH
    )


def test_basic_compression(compressor):
    text = "yaar basically mera hostel ka wifi bahut slow chal raha hai"
    result = compressor.compress(text)
    assert result.ratio < 0.80
    assert "wifi" in result.compressed
    assert "slow" in result.compressed
    assert result.method == "crf"


def test_safety_spans_preserved(compressor):
    result = compressor.compress("yaar user@example.com ko mail bhej do")
    assert "user@example.com" in result.compressed


@pytest.mark.parametrize(
    "text",
    [
        "wifi nahi chal raha hai",
        "mat karo ye",
        "assignment submit nahin hua",
        "never do this again",
        "phone charge nhi ho rha",
        "wifi nai chal rha",
        "ye theek nahi hai bilkul bhi",
    ],
)
def test_negation_preserved(compressor, text):
    result = compressor.compress(text)
    assert any(neg in result.compressed.lower() for neg in ALL_NEG), (
        f"Negation lost: {text} -> {result.compressed}"
    )


@pytest.mark.parametrize(
    "text",
    [
        "kya wifi chal raha hai",
        "kahan hai mera assignment",
        "kaise fix karein ye",
        "kab tak deadline hai",
    ],
)
def test_question_words_preserved(compressor, text):
    q_words = {"kya", "kahan", "kaise", "kab", "kaun", "kyun", "kidhar"}
    result = compressor.compress(text)
    words = set(result.compressed.lower().split())
    assert words & q_words, f"Question word lost: {text} -> {result.compressed}"


def test_empty_input(compressor):
    assert compressor.compress("").compressed == ""


def test_already_minimal(compressor):
    result = compressor.compress("wifi fix karo")
    assert result.ratio <= 1.0
    assert "wifi" in result.compressed


def test_code_blocks_untouched(compressor):
    result = compressor.compress("yaar `index out of range` error aa raha hai")
    assert "index out of range" in result.compressed


def test_amounts_preserved(compressor):
    result = compressor.compress("total Rs. 2,500 hai, 15 items order kiye")
    assert "Rs. 2,500" in result.compressed
    assert "15" in result.compressed


def test_idempotent(compressor):
    text = "yaar mera wifi bahut slow chal raha hai"
    r1 = compressor.compress(text)
    r2 = compressor.compress(r1.compressed)
    assert r1.compressed == r2.compressed


def test_drops_audited(compressor):
    result = compressor.compress("arre yaar basically mera phone charge nahi ho raha hai")
    assert len(result.drops) > 0
    assert all(isinstance(d, DropRecord) for d in result.drops)
    dropped = {d.token.lower() for d in result.drops}
    assert "phone" not in dropped


def test_devanagari_passthrough(compressor):
    result = compressor.compress("मेरा wifi काम नहीं कर रहा")
    assert "मेरा" in result.compressed
    assert "wifi" in result.compressed
    assert "नहीं" in result.compressed


@pytest.mark.parametrize(
    "text",
    [
        "mera wifi nahi chal raha hai",
        "mra wifi nhi chal rha h",
        "mera wifi nahin chal raha hai",
    ],
)
def test_spelling_variants_handled(compressor, text):
    result = compressor.compress(text)
    assert result.ratio < 0.95
    assert "wifi" in result.compressed
