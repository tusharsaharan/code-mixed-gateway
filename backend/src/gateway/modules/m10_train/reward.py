from __future__ import annotations

import math
from collections import Counter
from difflib import SequenceMatcher


def reward(
    original: str,
    compressed: str,
    reference_answer: str,
    predicted_answer: str,
) -> float:
    """Lexical-proxy reward in [0, 1] for a compressed prompt.

    Honesty note (research plan §6): despite the historical name, this is NOT
    measured downstream task correctness — it combines unigram-overlap /
    fuzzy-match proxies. P0-grade task scoring requires structured scoring or
    blinded judgement (see experiments/token_study/). Do not relabel this as
    accuracy in research endpoints or reports.
    """
    answer_score = _answer_score(predicted_answer, reference_answer)
    faithfulness = _faithfulness(compressed, original)
    return round(0.7 * answer_score + 0.3 * faithfulness, 6)


def _answer_score(hyp: str, ref: str) -> float:
    if not hyp or not ref:
        return 0.0
    def norm(s: str) -> str:
        return " ".join(s.split()).strip().lower()

    if norm(hyp) == norm(ref):
        return 1.0
    hyp_t = norm(hyp).split()
    ref_t = norm(ref).split()
    if not hyp_t or not ref_t:
        return 0.0
    ref_c = Counter(ref_t)
    overlap = sum(min(hyp_t.count(t), ref_c[t]) for t in set(hyp_t))
    p = overlap / len(hyp_t) if hyp_t else 0.0
    bp = 1.0 if len(hyp_t) >= len(ref_t) else math.exp(1 - len(ref_t) / len(hyp_t))
    bleu1 = bp * p
    fuzzy = SequenceMatcher(None, norm(ref), norm(hyp)).ratio()
    return max(bleu1, fuzzy * 0.9)


def _faithfulness(compressed: str, original: str) -> float:
    if not compressed or not original:
        return 0.0
    # ROUGE-L recall via longest common subsequence (char-level proxy)
    lcs = SequenceMatcher(None, original, compressed).find_longest_match(
        0, len(original), 0, len(compressed)
    ).size
    return lcs / len(original) if original else 0.0
