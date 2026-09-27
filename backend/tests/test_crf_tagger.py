"""Unit tests for the CRF tagger (features + prediction gates)."""

from pathlib import Path

import pytest

from gateway.modules.m2_compressor.crf_tagger import (
    apply_safety_gates,
    extract_features,
    featurize,
    is_available,
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "crf_compressor.pkl"


def test_feature_extraction_shape():
    tokens = ["mera", "wifi", "slow", "hai"]
    feats = featurize(tokens)
    assert len(feats) == 4
    assert all(isinstance(f, dict) for f in feats)
    assert "token.phash" in feats[0]
    assert "token.is_protected" in feats[0]
    assert "token.tfidf_score" in feats[0]


def test_protected_token_flagged():
    tokens = ["wifi", "nahi", "chal", "raha"]
    assert extract_features(tokens, 1)["token.is_protected"] is True
    assert extract_features(tokens, 0)["token.is_protected"] is False


def test_marker_flagged():
    tokens = ["bhejo", "[[PS0]]", "ko"]
    assert extract_features(tokens, 1)["token.is_marker"] is True


def test_neighbor_features_at_boundaries():
    tokens = ["hello", "world"]
    assert extract_features(tokens, 0)["-1.BOS"] is True
    assert extract_features(tokens, 0)["-2.BOS"] is True
    assert extract_features(tokens, 1)["+1.EOS"] is True


def test_safety_gates_force_keep():
    tokens = ["yaar", "wifi", "nahi", "chal", "raha"]
    labels = ["D", "K", "D", "K", "D"]
    fixed = apply_safety_gates(tokens, labels)
    assert fixed[2] == "K"  # nahi forced


def test_safety_gates_marker_kept():
    tokens = ["bhejo", "[[PS0]]", "ko"]
    fixed = apply_safety_gates(tokens, ["K", "D", "K"])
    assert fixed[1] == "K"


def test_safety_gates_minimum_floor():
    fixed = apply_safety_gates(["yaar", "toh"], ["D", "D"])
    assert fixed.count("K") >= 1


def test_is_available():
    assert is_available() is True


@pytest.fixture
def tagger():
    from gateway.modules.m2_compressor.crf_tagger import CRFTagger

    if not MODEL_PATH.exists():
        pytest.skip("CRF model not trained yet")
    return CRFTagger(MODEL_PATH)


def test_predict_protected_always_kept(tagger):
    labels = tagger.predict(["yaar", "wifi", "nahi", "chal", "raha", "hai"])
    assert labels[2] == "K"


def test_predict_markers_always_kept(tagger):
    labels = tagger.predict(["bhejo", "[[PS0]]", "ko", "mail"])
    assert labels[1] == "K"


def test_predict_length_matches(tagger):
    tokens = ["mera", "wifi", "slow", "hai"]
    assert len(tagger.predict(tokens)) == len(tokens)
