"""Unit tests for phonetic normalization (m2_compressor/phonetic.py)."""

import pytest

from gateway.modules.m2_compressor.phonetic import (
    hinglish_phash,
    is_marker,
    is_protected,
    normalize_chars,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("haaaaai", "hai"),
        ("pleaseee", "please"),
        ("kr", "kar"),
        ("kro", "karo"),
        ("rha", "raha"),
        ("rhi", "rahi"),
        ("rhe", "rahe"),
        ("nhi", "nahi"),
        ("ni", "nahi"),
        ("mt", "mat"),
        ("plz", "please"),
        ("mra", "mera"),
        ("fone", "phone"),
        # Unknown words pass through (lowercased, punct-stripped)
        ("wifi", "wifi"),
        ("http", "http"),
        ("Assignment", "assignment"),
        ("slow,", "slow"),
        # Markers byte-identical
        ("[[PS0]]", "[[PS0]]"),
        # Devanagari lowercased only
        ("मेरा", "मेरा"),
    ],
)
def test_normalize_chars(raw, expected):
    assert normalize_chars(raw) == expected


def test_normalize_empty():
    assert normalize_chars("") == ""


@pytest.mark.parametrize(
    "tokens",
    [
        ["raha", "rha", "rahi", "rahe"],
        ["kar", "kr", "karo"],
        ["nahi", "nhi"],
        ["basically", "bascly"],
        ["mera", "mra"],
        ["phone", "fon", "fone"],
    ],
)
def test_variant_grouping_same_hash(tokens):
    hashes = {hinglish_phash(t) for t in tokens}
    assert len(hashes) <= 2, f"{tokens} -> {hashes}"


def test_different_words_different_hash():
    assert hinglish_phash("wifi") != hinglish_phash("phone")


def test_marker_hash():
    assert hinglish_phash("[[PS0]]") == "PS"


def test_protected_flag():
    assert is_protected("nahi") is True
    assert is_protected("kya") is True
    assert is_protected("wifi") is False


def test_is_marker():
    assert is_marker("[[PS0]]") is True
    assert is_marker("wifi") is False
