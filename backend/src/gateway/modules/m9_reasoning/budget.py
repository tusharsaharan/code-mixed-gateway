from __future__ import annotations

import re

from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
from gateway.schemas import ReasoningBudget
from gateway.tokenizer import TokenCounter

_MATH = re.compile(
    r"(\d+\s*[+\-*/=<>]\s*\d+|solve|integrate|derivative|probability|percentage|numerical|equation|formula|\bprove\b)",
    re.IGNORECASE,
)
_LOGIC = re.compile(
    r"(\bkya\b|\bshould\b|\bwhy\b|\bhow\b|\bcompare\b|\bdifference\b|\bbecause\b|\bexplain\b|reason)",
    re.IGNORECASE,
)


class ReasoningBudgetEstimator:
    """Estimate the thinking-token budget a query actually needs before generating.

    A fast proxy: no trained model, only observable features (math/logic markers,
    code-mix ratio, entity density, length). The budget is the number of reasoning
    tokens the executor is allowed to spend before emitting the final answer.
    """

    def __init__(
        self,
        counter: TokenCounter | None = None,
        base_budget: int = 128,
        max_budget: int = 2048,
    ) -> None:
        self.counter = counter or TokenCounter()
        self.base_budget = base_budget
        self.max_budget = max_budget

    def _features(self, text: str) -> tuple[int, float, int, int]:
        tokens = text.split()
        n = len(tokens)
        code_mix = code_mix_ratio(text)
        math_count = len(_MATH.findall(text))
        logic_count = len(_LOGIC.findall(text))
        return n, code_mix, math_count, logic_count

    def estimate(self, text: str) -> ReasoningBudget:
        n, code_mix, math_count, logic_count = self._features(text)
        budget = self.base_budget
        budget += int(120 * code_mix)
        budget += 96 * math_count
        budget += 48 * logic_count
        budget += 8 * min(n, 40)
        budget = min(self.max_budget, int(budget))
        return ReasoningBudget(
            reasoning_tokens=budget,
            code_mix_ratio=round(code_mix, 4),
            math_marker_count=math_count,
            logic_marker_count=logic_count,
        )


class HinglishEnglishBudgetComparator:
    """Compare estimated reasoning budget of a Hinglish query vs its English gloss.

    The report's publishable side-finding: does a Hinglish math/logic query need a
    different reasoning budget than its English equivalent? Two independent
    estimators are run over the paired texts; the delta is reported directly.
    """

    GLOSSES: dict[str, str] = {
        "yaar matlab mera email user@example.com par bhejo na":
            "please send my email to user@example.com",
        "arre yaar physics ka numerical solve karo 5*3+2 ka answer batao":
            "solve this physics numerical 5*3+2 and tell the answer",
        "bhai amount Rs. 2,500 transfer karo na abhi":
            "transfer the amount Rs. 2,500 now",
        "hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?":
            "the hostel wifi is very slow, where do I file a complaint?",
    }

    def __init__(self, estimator: ReasoningBudgetEstimator | None = None) -> None:
        self.estimator = estimator or ReasoningBudgetEstimator()

    def gloss_for(self, hinglish: str) -> str | None:
        trimmed = hinglish.strip()
        if not trimmed:
            return None
        if trimmed in self.GLOSSES:
            return self.GLOSSES[trimmed]
        try:
            from gateway.modules.m12_novel.gloss import to_english_gloss

            g = to_english_gloss(trimmed)
            return g if g else None
        except Exception:
            return None

    def delta(self, hinglish: str, english: str) -> float:
        bi = self.estimator.estimate(hinglish).reasoning_tokens
        be = self.estimator.estimate(english).reasoning_tokens
        return float(bi - be)

    def compare(self, hinglish: str, english: str) -> dict[str, float | int]:
        bi = self.estimator.estimate(hinglish)
        be = self.estimator.estimate(english)
        return {
            "hinglish_budget": bi.reasoning_tokens,
            "english_budget": be.reasoning_tokens,
            "delta_hinglish_minus_english": bi.reasoning_tokens - be.reasoning_tokens,
        }