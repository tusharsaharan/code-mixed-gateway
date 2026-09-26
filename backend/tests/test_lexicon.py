"""Phase 0 tests: canonical lexicon prune with homograph/position guards."""

import pytest

from gateway.lexicons import filler_set, prune
from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m2_compressor.safety_span import mask, reinject
from gateway.tokenizer import TokenCounter


def _has_drop(drops, token):
    return any(d.token == token or token in d.token for d in drops)


# --- n-gram homograph protection -------------------------------------------


def test_you_know_ngram_dropped_but_you_content_kept():
    out, drops = prune("can you know the answer")
    # "you know" at non-initial position? it is initial-ish (index 1).
    # sentence-initial guard: "you know" is a non-initial ngram; index 1 is not
    # sentence start, so it drops.
    assert "you know" not in out
    # But "you" as a content pronoun must survive when not part of the n-gram
    out2, _ = prune("can you submit the form")
    assert "you" in out2.split()


def test_you_know_sentence_initial_kept():
    # "you know" as the very first words is a real content phrase, not a hedge
    out, drops = prune("you know the deadline is tomorrow")
    assert out.lower().startswith("you know")


def test_sun_english_content_never_dropped():
    out, drops = prune("the sun rises in the east")
    assert "sun" in out.split()
    assert not _has_drop(drops, "sun")


def test_suno_attention_getter_dropped():
    out, drops = prune("suno mera phone charge nahi ho raha")
    assert "suno" not in out.lower().split()


# --- vocative guards ---------------------------------------------------------


def test_bhai_vocative_dropped():
    out, drops = prune("bhai mera assignment submit nahi hua")
    assert "bhai" not in out.lower().split()
    assert _has_drop(drops, "bhai")


def test_bhai_genitive_kept():
    # kinship/genitive use: preceded by possessive / followed by ka/ki/ke
    out, drops = prune("mere bhai ka phone kho gaya")
    assert "bhai" in out.lower().split()
    out2, _ = prune("mera bhai kal aayega")
    assert "bhai" in out2.lower().split()


# --- matlab tech guard -------------------------------------------------------


def test_matlab_software_context_kept():
    out, drops = prune("download matlab free version for students")
    assert "matlab" in out.lower().split()
    assert not _has_drop(drops, "matlab")


def test_matlab_filler_dropped():
    out, drops = prune("hostel ka wifi matlab bahut slow chal raha hai")
    assert "matlab" not in out.lower().split()
    assert _has_drop(drops, "matlab")


def test_matlab_sentence_initial_kept():
    # non_initial guard: sentence-initial matlab is content, keep it
    out, _ = prune("matlab ek numerical tool hai")
    assert out.lower().startswith("matlab")


# --- like hedge guard --------------------------------------------------------


def test_like_comma_hedge_dropped():
    out, drops = prune("wifi is slow, like really slow, fix it")
    assert "like" not in out.lower().split()


def test_like_content_verb_kept():
    # "like" as a real verb/preposition without comma adjacency
    out, _ = prune("I like this hostel room")
    assert "like" in out.lower().split()


# --- haan final-token guard ---------------------------------------------------


def test_haan_final_confirmation_kept():
    out, _ = prune("kal exam hai haan")
    assert out.lower().endswith("haan")


def test_haan_comma_dropped():
    out, _ = prune("haan, wifi slow hai")
    assert "haan" not in out.lower().split()


# --- protected spans ----------------------------------------------------------


def test_marker_adjacent_tokens_kept():
    masked, spans = mask("yaar matlab send to user@example.com abhi")
    out, drops = prune(masked)
    restored, ok = reinject(out, spans)
    assert ok
    assert "user@example.com" in restored
    # tokens adjacent to [[PS0]] are never pruned
    assert "send" in restored


def test_empty_prune():
    out, drops = prune("")
    assert out == ""
    assert drops == []


def test_all_fillers_noise_only_returns_empty():
    out, drops = prune("arre yaar basically actually toh")
    assert out == ""
    assert len(drops) >= 3


# --- compressor integration ----------------------------------------------------


def test_compressor_drops_audited():
    comp = Compressor(TokenCounter())
    res = comp.compress_heuristic("yaar matlab mera email user@example.com par bhejo na")
    assert "user@example.com" in res.compressed
    assert "yaar" not in res.compressed
    assert res.drops, "drop records must be populated"
    tokens_dropped = {d.token for d in res.drops}
    assert any("yaar" in t for t in tokens_dropped)


def test_filler_set_export():
    fs = filler_set()
    assert "yaar" in fs
    assert "you" not in fs  # dangerous homograph must NOT be in the flat set


# --- greetings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "hello sir, mera form bharna hai",
        "namaste, hostel ka wifi slow hai",
        "good morning, assignment ka deadline kya hai",
    ],
)
def test_greeting_strip(text):
    out, _ = prune(text)
    assert not out.lower().startswith(("hello", "namaste", "good morning"))


def test_greeting_word_mid_sentence_kept():
    out, _ = prune("form me hello likhna hai heading ke liye")
    assert "hello" in out.lower().split()
