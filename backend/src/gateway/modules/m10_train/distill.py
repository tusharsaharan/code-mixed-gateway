from __future__ import annotations

import json
import random
import re
from pathlib import Path

from gateway.modules.m10_train.reward import reward

_WS = re.compile(r"\s+")
_FILLERS = {"yaar", "matlab", "like", "basically", "actually", "arre", "na", "bhai"}


def _variants(text: str, seed: int) -> list[str]:
    rng = random.Random(seed)
    tokens = _WS.sub(" ", text).split()
    cands: list[str] = []
    # 0: heuristic (drop fillers)
    cands.append(" ".join(t for t in tokens if t.lower().strip(",.!?") not in _FILLERS))
    # 1..3: stochastic filler-drop at increasing aggressiveness
    for p in (0.3, 0.6, 0.9):
        kept = [
            t
            for t in tokens
            if t.lower().strip(",.!?") in _FILLERS and rng.random() > p
            or t.lower().strip(",.!?") not in _FILLERS
        ]
        # keep at least 40% of tokens
        if len(kept) < max(3, int(0.4 * len(tokens))):
            kept = tokens[: max(3, int(0.4 * len(tokens)))]
        cands.append(" ".join(kept))
    # 4: truncated (first 60%)
    cands.append(" ".join(tokens[: max(3, int(0.6 * len(tokens)))]))
    # deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def distill(
    benchmark: Path,
    output: Path,
    seed: int = 7,
) -> dict:
    """Rejection-sampling distillation that runs offline (the report's fallback).

    For each benchmark record, generates candidate compressions, scores each by
    the task-correctness reward, and keeps the best. Emits a checkpoint JSON
    that the Compressor can load as method='distilled'.
    """
    records = [
        json.loads(line)
        for line in benchmark.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    mapping: dict[str, str] = {}
    rows: list[dict] = []
    total_reward = 0.0
    for rec in records:
        rid = rec.get("id", "")
        original = rec.get("original", "")
        ref = rec.get("reference_answer", "")
        pred = rec.get("predicted_answer", ref)
        cands = _variants(original, seed + hash(rid) % 10000)
        best = max(cands, key=lambda c: reward(original, c, ref, pred))
        best_r = reward(original, best, ref, pred)
        mapping[original] = best
        total_reward += best_r
        rows.append(
            {
                "id": rid,
                "original": original,
                "distilled": best,
                "reward": best_r,
                "candidates": len(cands),
            }
        )
    payload = {
        "method": "distilled",
        "seed": seed,
        "benchmark": str(benchmark),
        "n": len(records),
        "mean_reward": round(total_reward / max(1, len(records)), 6),
        "mapping": mapping,
        "rows": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def load_mapping(checkpoint: Path) -> dict[str, str]:
    if not checkpoint.exists():
        return {}
    try:
        data = json.loads(checkpoint.read_text(encoding="utf-8"))
        return dict(data.get("mapping", {}))
    except Exception:
        return {}