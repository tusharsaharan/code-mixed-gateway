import pytest

from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m2_compressor.safety_span import detect_spans, mask, reinject
from gateway.tokenizer import TokenCounter


def test_detect_spans_finds_email_code_amount():
    spans = detect_spans("mail user@example.com par bhejo, total Rs. 2,500")
    kinds = {s.kind for s in spans}
    assert "email" in kinds
    assert "amount" in kinds


def test_mask_reinject_roundtrip():
    text = "yaar email user@example.com par bhejo, amount Rs. 2,500 dedo"
    masked, spans = mask(text)
    assert "user@example.com" not in masked
    restored, ok = reinject(masked, spans)
    assert ok
    assert restored == text


def test_reinject_fails_closed_on_dropped_marker():
    masked, spans = mask("bhejo na user@example.com ko")
    broken = masked.replace("[[PS0]]", "")
    restored, ok = reinject(broken, spans)
    assert not ok


def test_heuristic_compressor_keeps_entities_drops_fluff():
    comp = Compressor(TokenCounter())
    text = "yaar matlab mera email user@example.com par bhejo na"
    result = comp.compress_heuristic(text)
    assert "user@example.com" in result.compressed
    assert "yaar" not in result.compressed
    assert "matlab" not in result.compressed
    assert result.ratio <= 1.0


@pytest.mark.asyncio
async def test_compress_dispatches_to_heuristic_when_no_model():
    comp = Compressor(TokenCounter(), use_model=False)
    result = await comp.compress("arre yaar ye error index out of range aa raha hai")
    assert result.method == "heuristic"
    assert "index out of range" in result.compressed