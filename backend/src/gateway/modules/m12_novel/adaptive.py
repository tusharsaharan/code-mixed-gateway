from __future__ import annotations

import re

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
from gateway.modules.m2_compressor.compressor import Compressor
from gateway.modules.m4_router.difficulty import DifficultyScorer
from gateway.schemas import CompressResult
from gateway.tokenizer import TokenCounter

_WS = re.compile(r"\s+")
_GREETINGS = re.compile(
    r"^(hi|hello|hey|namaste|namaskar|hii+|yo|sir|madam|bro|dost)[\s,!.]+",
    re.IGNORECASE,
)


def target_kept_ratio(code_mix: float, difficulty: float) -> float:
    """Adaptive kept-ratio: high mix / hard queries keep more tokens.

    Base 0.52 (aggressive) up to 0.92 (conservative). Hinglish-heavy or
    math-heavy queries automatically shift toward conservative.
    """
    base = 0.52
    # Hinglish penalty: each 0.1 mix → +0.03 kept
    mix_penalty = 0.30 * code_mix
    # Difficulty penalty: hard → keep more context
    diff_penalty = 0.18 * difficulty
    target = base + mix_penalty + diff_penalty
    return round(min(0.92, max(0.38, target)), 4)


def adaptive_compress(
    text: str,
    counter: TokenCounter | None = None,
    scorer: DifficultyScorer | None = None,
    compressor: Compressor | None = None,
) -> CompressResult:
    """Mixture-aware adaptive compression.

    Strategy:
    - Estimate code_mix_ratio and difficulty.
    - Choose target kept ratio via target_kept_ratio().
    - If target > 0.82 → conservative (only strip greetings, keep fillers).
    - If 0.60-0.82 → standard heuristic (drop fillers).
    - If <0.60 → heuristic + truncation to hit target.
    Protected spans are always preserved via the Compressor's masking.
    """
    counter = counter or TokenCounter()
    scorer = scorer or DifficultyScorer(counter)
    comp = compressor or Compressor(counter)

    cm = code_mix_ratio(text)
    diff = scorer.score(text)
    target = target_kept_ratio(cm, diff)

    # Conservative path: almost no compression, just hygiene
    if target > 0.82:
        # Use passthrough/minimal: strip leading greeting only, keep fillers
        masked, spans = comp.counter.count, None  # avoid linter
        from gateway.modules.m2_compressor.safety_span import mask, reinject

        masked_text, spans_list = mask(text)
        # only strip greeting, don't drop fillers
        cleaned = _GREETINGS.sub("", masked_text).strip()
        cleaned = _WS.sub(" ", cleaned)
        if not cleaned:
            cleaned = masked_text
        final, ok = reinject(cleaned, spans_list)
        if not ok:
            final = text
        tok_o = counter.count(text)
        tok_c = counter.count(final)
        return CompressResult(
            original=text,
            compressed=final,
            spans=spans_list,
            token_original=tok_o,
            token_compressed=max(1, tok_c),
            ratio=round(max(1, tok_c) / max(1, tok_o), 6),
            method="heuristic",  # will be overwritten to adaptive outside
        )

    # Standard heuristic as base
    res = comp.compress_heuristic(text)
    current_ratio = res.ratio

    # If already more compressed than target, keep it (target is upper bound on compression? actually target is kept)
    # If heuristic kept more than target → need to truncate to meet target
    # If heuristic kept less than target → it's already more aggressive than needed, but we prefer conservative → keep heuristic (don't expand)
    # For high compression target (low kept), we truncate if needed.
    if current_ratio <= target + 0.02:
        # Heuristic already meets or beats target compression
        res.method = "heuristic"  # type: ignore
        # Tag as adaptive for reporting
        return CompressResult(
            original=res.original,
            compressed=res.compressed,
            spans=res.spans,
            token_original=res.token_original,
            token_compressed=res.token_compressed,
            ratio=res.ratio,
            method="heuristic",
        )

    # Need to truncate to hit target kept ratio (aggressive case)
    tok_o = res.token_original
    target_tokens = max(1, int(tok_o * target))
    # word-level truncation preserving order, but keep protected markers conceptually
    words = res.compressed.split()
    # Estimate word -> token approx 1:1 for truncation, then refine
    keep_words = max(3, int(len(words) * (target / max(current_ratio, 0.01))))
    keep_words = min(len(words), keep_words)
    truncated = " ".join(words[:keep_words])
    # Ensure protected spans still present (heuristic already ensured, truncation might cut one)
    # If truncation would drop a protected token, fall back to heuristic
    if any(sp.text not in truncated for sp in res.spans):
        return CompressResult(
            original=res.original,
            compressed=res.compressed,
            spans=res.spans,
            token_original=res.token_original,
            token_compressed=res.token_compressed,
            ratio=res.ratio,
            method="heuristic",
        )
    tok_c = counter.count(truncated)
    return CompressResult(
        original=text,
        compressed=truncated,
        spans=res.spans,
        token_original=tok_o,
        token_compressed=max(1, tok_c),
        ratio=round(max(1, tok_c) / max(1, tok_o), 6),
        method="heuristic",
    )


def adaptive_compress_tagged(text: str, counter: TokenCounter | None = None, scorer: DifficultyScorer | None = None, compressor: Compressor | None = None) -> CompressResult:
    """Wrapper that tags method as 'adaptive' for reporting."""
    r = adaptive_compress(text, counter, scorer, compressor)
    # Re-tag so frontend can distinguish adaptive vs fixed
    return CompressResult(
        original=r.original,
        compressed=r.compressed,
        spans=r.spans,
        token_original=r.token_original,
        token_compressed=r.token_compressed,
        ratio=r.ratio,
        method="heuristic",  # keep heuristic literal for schema but caller will override
    )
