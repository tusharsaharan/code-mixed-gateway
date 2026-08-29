from __future__ import annotations

import csv
import math
import re
from collections.abc import Callable
from pathlib import Path

from gateway.modules.m1_pipeline.pipeline import iter_jsonl, normalize
from gateway.schemas import PromptRecord, TokenizerReport

_WS = re.compile(r"\s+")


def count_whitespace(text: str) -> int:
    return len(_WS.sub(" ", text).strip().split()) if text.strip() else 0


def count_char_proxy(text: str) -> int:
    """Byte-token proxy: rough upper bound for non-Latin scripts (Petrov tokenizer-fairness)."""
    return max(1, math.ceil(len(text.encode("utf-8")) / 4))


def _gpt4o_count() -> Callable[[str], int]:
    cache: dict[str, object] = {}

    def fn(text: str) -> int:
        if "enc" not in cache:
            try:
                import tiktoken

                cache["enc"] = tiktoken.get_encoding("cl100k_base")
            except Exception:
                cache["enc"] = None
        enc = cache["enc"]
        if enc is None:
            return count_whitespace(text)
        return len(enc.encode(text))  # type: ignore[attr-defined]

    return fn


HF_TOKENIZER_SPECS: dict[str, str] = {
    "qwen2.5": "Qwen/Qwen2.5-0.5B-Instruct",
    "llama3.1": "meta-llama/Llama-3.1-8B-Instruct",
    "gemma2": "google/gemma-2-2b",
}


def _hf_factory(hub_id: str) -> Callable[[str], int]:
    cache: dict[str, object] = {}

    def fn(text: str) -> int:
        if hub_id not in cache:
            try:
                from tokenizers import Tokenizer

                cache[hub_id] = Tokenizer.from_pretrained(hub_id)
            except Exception:
                cache[hub_id] = None
        tok = cache[hub_id]
        if tok is None:
            return count_whitespace(text)
        return len(tok.encode(text).ids)  # type: ignore[union-attr]

    return fn


def _build_default_tokenizers() -> dict[str, Callable[[str], int]]:
    tokenizers: dict[str, Callable[[str], int]] = {
        "whitespace": count_whitespace,
        "gpt4o_cl100k": _gpt4o_count(),
        "char4_proxy": count_char_proxy,
    }
    for name, hub_id in HF_TOKENIZER_SPECS.items():
        tokenizers[name] = _hf_factory(hub_id)
    return tokenizers


DEFAULT_TOKENIZERS: dict[str, Callable[[str], int]] = _build_default_tokenizers()


class TokenizerBench:
    """Benchmark token counts across tokenizers; compute code-mix token inflation.

    The inflation ratio is relatively tokenized length vs the ``baseline`` tokenizer
    (default GPT-4o cl100k), which is the metric that makes Hinglish cost visible.
    """

    def __init__(
        self,
        tokenizers: dict[str, Callable[[str], int]] | None = None,
        baseline: str = "gpt4o_cl100k",
    ) -> None:
        self.tokenizers = tokenizers or DEFAULT_TOKENIZERS
        self.baseline = baseline

    def per_tokenizer(self, text: str, rec_id: str) -> list[TokenizerReport]:
        chars = len(text)
        rows: list[TokenizerReport] = []
        for name, fn in self.tokenizers.items():
            n = max(1, fn(text))
            rows.append(
                TokenizerReport(
                    id=rec_id,
                    tokenizer=name,
                    num_tokens=n,
                    chars=chars,
                    tokens_per_char=round(n / chars, 6),
                )
            )
        return rows

    def run(self, records: list[PromptRecord]) -> list[TokenizerReport]:
        rows: list[TokenizerReport] = []
        for rec in records:
            rows.extend(self.per_tokenizer(normalize(rec.text), rec.id))
        return rows

    def inflation(self, records: list[PromptRecord]) -> dict[str, float]:
        """Average token ratio of each tokenizer vs the baseline across records."""
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for rec in records:
            text = normalize(rec.text)
            baseline = max(1, self.tokenizers[self.baseline](text))
            for name, fn in self.tokenizers.items():
                sums[name] = sums.get(name, 0.0) + fn(text) / baseline
                counts[name] = counts.get(name, 0) + 1
        return {name: round(sums[name] / counts[name], 6) for name in sums}

    def write_csv(self, rows: list[TokenizerReport], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "tokenizer", "num_tokens", "chars", "tokens_per_char"])
            for r in rows:
                w.writerow([r.id, r.tokenizer, r.num_tokens, r.chars, r.tokens_per_char])


def run_benchmark(data_dir: Path) -> dict[str, float]:
    src = data_dir / "seed_hinglish.jsonl"
    out = data_dir / "tokenizer_report.csv"
    records = iter_jsonl(src)
    bench = TokenizerBench()
    rows = bench.run(records)
    bench.write_csv(rows, out)
    return bench.inflation(records)