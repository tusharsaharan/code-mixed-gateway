"""Unit tests for heuristic pre-pruning passes."""

import pytest

from gateway.modules.m2_compressor.heuristic_passes import (
    UNCONDITIONAL_FILLERS,
    collapse_reduplication,
    strip_greeting_enhanced,
    strip_unconditional_fillers,
)


@pytest.mark.parametrize(
    "tokens,expected",
    [
        (["jaldi", "jaldi", "karo"], ["jaldi", "karo"]),
        (["bahut", "bahut", "slow"], ["bahut", "slow"]),
        (["ek", "do", "teen"], ["ek", "do", "teen"]),
        (["chai", "vai", "pi", "lo"], ["chai", "pi", "lo"]),
        (["kaam", "vaam", "karo"], ["kaam", "karo"]),
        (["wifi", "slow", "hai"], ["wifi", "slow", "hai"]),
    ],
)
def test_reduplication_collapse(tokens, expected):
    out, drops = collapse_reduplication(tokens)
    assert out == expected
    assert len(drops) == len(tokens) - len(expected)


def test_reduplication_markers_untouched():
    out, drops = collapse_reduplication(["bhejo", "[[PS0]]", "[[PS0]]"])
    assert out == ["bhejo", "[[PS0]]", "[[PS0]]"]
    assert drops == []


@pytest.mark.parametrize(
    "text",
    [
        "hello sir, mera form bharna hai",
        "namaste, hostel ka wifi slow hai",
        "good morning, assignment ka deadline kya hai",
        "hi bhai, wifi nahi chal raha",
        "heyy, mera phone kharab hai",
    ],
)
def test_greeting_removed(text):
    out, drop = strip_greeting_enhanced(text)
    assert drop is not None
    assert not out.lower().startswith(("hello", "namaste", "good morning", "hi ", "hey"))


def test_greeting_only_message_kept():
    out, drop = strip_greeting_enhanced("hello")
    assert out == "hello"
    assert drop is None
    out2, drop2 = strip_greeting_enhanced("namaste")
    assert out2 == "namaste"
    assert drop2 is None


def test_greeting_mid_sentence_kept():
    out, drop = strip_greeting_enhanced("form me hello likhna hai")
    assert "hello" in out.lower().split()
    assert drop is None


def test_unconditional_fillers_only_tiny_set():
    # yaar/basically/toh are NOT unconditional -- CRF owns them.
    assert "yaar" not in UNCONDITIONAL_FILLERS
    assert "basically" not in UNCONDITIONAL_FILLERS
    assert "toh" not in UNCONDITIONAL_FILLERS
    assert "arre" in UNCONDITIONAL_FILLERS
    assert "hmm" in UNCONDITIONAL_FILLERS


def test_strip_unconditional_fillers():
    out, drops = strip_unconditional_fillers(["arre", "wifi", "slow", "hmm", "hai"])
    assert out == ["wifi", "slow", "hai"]
    assert len(drops) == 2


def test_strip_unconditional_markers_kept():
    out, drops = strip_unconditional_fillers(["arre", "[[PS0]]", "um"])
    assert out == ["[[PS0]]"]
