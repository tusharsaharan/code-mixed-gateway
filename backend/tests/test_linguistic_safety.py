"""Adversarial / safety tests for the CRF linguistic compressor."""

from pathlib import Path

import pytest

from gateway.modules.m2_compressor.linguistic import LinguisticCompressor
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


def test_single_token_input(compressor):
    assert compressor.compress("help").compressed == "help"
    assert compressor.compress("nahi").compressed == "nahi"


def test_all_droppable_input(compressor):
    result = compressor.compress("arre yaar basically toh um hmm")
    assert isinstance(result.compressed, str)
    assert result.ratio <= 1.0


def test_very_long_input(compressor):
    result = compressor.compress(" ".join(["yaar mera wifi slow hai"] * 50))
    assert isinstance(result.compressed, str)
    assert result.ratio < 1.0


def test_mixed_scripts(compressor):
    result = compressor.compress("yaar मेरा phone 充电 nahi ho raha")
    assert "充电" in result.compressed


def test_no_info_added(compressor):
    text = "hello sir, basically mera phone charge nahi ho raha hai, please help karo na yaar"
    result = compressor.compress(text)
    orig = set(text.lower().split())
    comp = set(result.compressed.lower().split())
    new_tokens = comp - orig - {"", ",", ".", "!"}
    assert not new_tokens, f"New tokens added: {new_tokens}"


def test_crf_model_missing_fallback():
    comp = LinguisticCompressor(
        TokenCounter(), crf_model_path=Path("/nonexistent/model.pkl")
    )
    result = comp.compress("arre yaar wifi slow hai")
    assert isinstance(result.compressed, str)
    # Heuristic passes still apply without the CRF.
    assert "arre" not in result.compressed.split()


def test_greeting_only_survives(compressor):
    assert compressor.compress("hello").compressed == "hello"
    assert compressor.compress("namaste").compressed == "namaste"


def test_stacked_greeting_stripped(compressor):
    result = compressor.compress("hello sir, mera form bharna hai")
    assert not result.compressed.lower().startswith(("hello", "sir"))


NEGATION_CASES = [
    "nahi aaya",
    "nahin chahiye",
    "mat karo",
    "nhi hora",
    "kuch nahi hua",
    "wifi not working",
    "never submit late",
    "wifi nai chal rha",
    "ye theek nahi hai bilkul bhi",
]


@pytest.mark.parametrize("text", NEGATION_CASES)
def test_negation_invariant(compressor, text):
    all_neg = {
        "nahi", "nahin", "nhi", "nai", "ni", "mat", "mtt",
        "not", "never", "n't", "no",
    }
    result = compressor.compress(text)
    assert any(neg in result.compressed.lower() for neg in all_neg), (
        f"Negation lost: {text} -> {result.compressed}"
    )
