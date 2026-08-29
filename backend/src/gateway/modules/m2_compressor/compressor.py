from __future__ import annotations

import re

from gateway.llm import BaseLLMClient
from gateway.modules.m2_compressor.prompts import compression_messages
from gateway.modules.m2_compressor.safety_span import mask, reinject
from gateway.schemas import CompressResult, SafetySpan
from gateway.tokenizer import TokenCounter

_FILLERS = {
    "yaar",
    "matlab",
    "like",
    "basically",
    "actually",
    "arre",
    "na",
    "bhai",
    "sun",
    "dekho",
    "you",
    "know",
}
_GREETINGS = re.compile(
    r"^(hi|hello|hey|namaste|namaskar|hii+|yo|sir|madam|bro|dost)[\s,!.]+",
    re.IGNORECASE,
)
_WS = re.compile(r"\s+")


def _heuristic_compress(text: str) -> str:
    tokens = _WS.sub(" ", text).split()
    if not tokens:
        return text
    tokens = [t for t in tokens if t.lower().strip(",.!?") not in _FILLERS]
    while tokens and tokens[0].lower().strip(",.!?") in _FILLERS:
        tokens.pop(0)
    joined = " ".join(tokens)
    return _GREETINGS.sub("", joined).strip()


class Compressor:
    """Zero-shot Hinglish prompt compressor (heuristic fast path + optional local-model path)."""

    def __init__(
        self,
        counter: TokenCounter,
        client: BaseLLMClient | None = None,
        use_model: bool = False,
        distilled_map: dict[str, str] | None = None,
    ) -> None:
        self.counter = counter
        self.client = client
        self.use_model = use_model and client is not None
        self.distilled_map = distilled_map or {}

    def _result(
        self,
        original: str,
        compressed: str,
        spans: list[SafetySpan],
        method: str,
    ) -> CompressResult:
        tok_orig = self.counter.count(original)
        tok_comp = self.counter.count(compressed)
        tok_comp = max(1, tok_comp)
        return CompressResult(
            original=original,
            compressed=compressed,
            spans=spans,
            token_original=tok_orig,
            token_compressed=tok_comp,
            ratio=round(tok_comp / max(1, tok_orig), 6),
            method=method,
        )

    def compress_distilled(self, text: str) -> CompressResult:
        if text in self.distilled_map:
            masked, spans = mask(text)
            distilled = self.distilled_map[text]
            if not spans:
                return self._result(text, distilled, spans, "distilled")
            if "[[PS" in distilled:
                final, ok = reinject(distilled, spans)
                if not ok:
                    final = text
                return self._result(text, final, spans, "distilled")
            # distilled checkpoint stores raw text (no markers) — ensure
            # protected spans are still present verbatim, otherwise fall back
            # to heuristic which preserves spans via masking.
            if all(sp.text in distilled for sp in spans):
                return self._result(text, distilled, spans, "distilled")
            return self.compress_heuristic(text)
        return self.compress_heuristic(text)

    def compress_heuristic(self, text: str) -> CompressResult:
        masked, spans = mask(text)
        compressed_masked = _heuristic_compress(masked)
        final, ok = reinject(compressed_masked, spans)
        if not ok:
            final = text
        return self._result(text, final, spans, "heuristic")

    async def compress_model(self, text: str) -> CompressResult:
        masked, spans = mask(text)
        if self.client is None:
            final = _heuristic_compress(masked)
            method = "heuristic"
        else:
            result = await self.client.chat(compression_messages(masked), temperature=0.0)
            final, ok = reinject(result.content.strip(), spans)
            method = "model"
            if not ok:
                final = text
        return self._result(text, final, spans, method)

    async def compress(self, text: str) -> CompressResult:
        if text in self.distilled_map:
            return self.compress_distilled(text)
        if self.use_model:
            return await self.compress_model(text)
        return self.compress_heuristic(text)