from __future__ import annotations

from gateway.lexicons import prune
from gateway.llm import BaseLLMClient
from gateway.modules.m2_compressor.prompts import compression_messages
from gateway.modules.m2_compressor.safety_span import mask, reinject
from gateway.schemas import CompressResult, SafetySpan
from gateway.tokenizer import TokenCounter


class Compressor:
    """Hinglish prompt compressor (distilled → llmlingua2 → model → heuristic).

    Heuristic fast path is the canonical lexicon-based prune (gateway.lexicons):
    guarded filler/vocative removal with per-drop audit records. LLMLingua-2 is
    the trained baseline: a distilled token-classifier (BERT-base multilingual,
    CPU-runnable); protected spans are masked to [[PSi]] markers and
    force-preserved because raw classifier output mangles entities
    (user@example.com → "user example com"). Optional local-model path
    (Ollama) and distilled-checkpoint path are unchanged.
    """

    def __init__(
        self,
        counter: TokenCounter,
        client: BaseLLMClient | None = None,
        use_model: bool = False,
        distilled_map: dict[str, str] | None = None,
        use_llmlingua2: bool = False,
        llmlingua2_rate: float = 0.5,
    ) -> None:
        self.counter = counter
        self.client = client
        self.use_model = use_model and client is not None
        self.distilled_map = distilled_map or {}
        self.use_llmlingua2 = use_llmlingua2
        self.llmlingua2_rate = llmlingua2_rate

    def _result(
        self,
        original: str,
        compressed: str,
        spans: list[SafetySpan],
        method: str,
        drops: list | None = None,
    ) -> CompressResult:
        tok_orig = self.counter.count(original)
        tok_comp = self.counter.count(compressed)
        tok_comp = max(1, tok_comp)
        return CompressResult(
            original=original,
            compressed=compressed,
            spans=spans,
            drops=drops or [],
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
        compressed_masked, drops = prune(masked)
        final, ok = reinject(compressed_masked, spans)
        if not ok:
            final = text
        return self._result(text, final, spans, "heuristic", drops)

    def compress_llmlingua2(self, text: str, rate: float | None = None) -> CompressResult:
        """Trained-baseline compression. Falls back to heuristic (honestly
        labelled) when the library/weights are unavailable or a row fails."""
        from gateway.modules.m2_compressor.llmlingua2 import get_compressor, is_available

        rate = self.llmlingua2_rate if rate is None else rate
        # Explicit call: always try the real classifier when installed.
        # (The auto path below separately respects use_llmlingua2.)
        if not is_available():
            return self.compress_heuristic(text)
        masked, spans = mask(text)
        markers = [f"[[PS{i}]]" for i in range(len(spans))]
        try:
            got = get_compressor().compress_masked([masked], [markers], rate=rate)[0]
        except ImportError:
            return self.compress_heuristic(text)
        if got is None:
            return self.compress_heuristic(text)
        final, ok = reinject(got, spans)
        if not ok:
            return self.compress_heuristic(text)
        return self._result(text, final, spans, "llmlingua2")

    async def compress_model(self, text: str) -> CompressResult:
        masked, spans = mask(text)
        if self.client is None:
            compressed_masked, drops = prune(masked)
            method = "heuristic"
        else:
            result = await self.client.chat(compression_messages(masked), temperature=0.0)
            final, ok = reinject(result.content.strip(), spans)
            method = "model"
            if not ok:
                final = text
            return self._result(text, final, spans, method)
        final, ok = reinject(compressed_masked, spans)
        if not ok:
            final = text
        return self._result(text, final, spans, method, drops)

    async def compress(self, text: str) -> CompressResult:
        if text in self.distilled_map:
            return self.compress_distilled(text)
        if self.use_llmlingua2:
            res = self.compress_llmlingua2(text)
            if res.method == "llmlingua2":
                return res
            # Trained path unavailable/failed → continue down the chain.
        if self.use_model:
            return await self.compress_model(text)
        return self.compress_heuristic(text)
