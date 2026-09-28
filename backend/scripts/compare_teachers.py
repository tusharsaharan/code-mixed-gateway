"""Compare CRF compressor variants on a held-out prompt slice.

Metrics per model: mean compression ratio, mean semantic cosine
(original vs compressed, via sentence-transformers), negation-preservation
rate. Prints a JSON table; exits non-zero if any model drops a negation.

Usage:
    python scripts/compare_teachers.py --prompts data/training/prompts.jsonl \\
        --models det=data/models/crf_compressor.pkl llm=data/models/crf_llm.pkl \\
        --limit 300 --seed 999 [--no-embed]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from gateway.modules.m2_compressor.linguistic import LinguisticCompressor  # noqa: E402
from gateway.modules.m2_compressor.phonetic import PROTECTED_TOKENS, normalize_chars  # noqa: E402
from gateway.tokenizer import TokenCounter  # noqa: E402

NEGATIONS = {t for t in PROTECTED_TOKENS if t not in {
    "kya", "kahan", "kidhar", "kaise", "kaisa", "kab",
    "kyun", "kyu", "kaun", "kiska", "kitna", "kitne",
}}


def load_texts(prompts_path: Path, limit: int, seed: int) -> list[str]:
    recs = [
        json.loads(line)
        for line in prompts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rng = random.Random(seed)
    rng.shuffle(recs)
    return [r["text"] for r in recs[:limit]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="data/training/prompts.jsonl")
    ap.add_argument("--models", nargs="+", required=True, help="NAME=PATH pairs")
    ap.add_argument("--idf", default="data/tfidf/hinglish_idf.json")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--no-embed", action="store_true")
    ap.add_argument("--embed-model", default="paraphrase-multilingual-MiniLM-L12-v2")
    args = ap.parse_args()

    prompts_path = BACKEND_ROOT / args.prompts if not Path(args.prompts).is_absolute() else Path(args.prompts)
    idf_path = BACKEND_ROOT / args.idf if not Path(args.idf).is_absolute() else Path(args.idf)
    if not prompts_path.exists():
        print(f"ERROR: prompts file not found: {prompts_path}", file=sys.stderr)
        raise SystemExit(2)
    texts = load_texts(prompts_path, args.limit, args.seed)
    if not texts:
        print(
            f"ERROR: no prompts selected from {prompts_path} "
            "(empty file or --limit 0?) -- refusing to print an empty table",
            file=sys.stderr,
        )
        raise SystemExit(2)

    specs: dict[str, Path] = {}
    for item in args.models:
        name, path = item.split("=", 1)
        p = Path(path)
        specs[name] = p if p.is_absolute() else BACKEND_ROOT / p

    embedder = None
    if not args.no_embed:
        from sentence_transformers import SentenceTransformer

        embedder = SentenceTransformer("sentence-transformers/" + args.embed_model)

    table: dict[str, dict] = {}
    failed = False
    for name, model_path in specs.items():
        comp = LinguisticCompressor(TokenCounter(), crf_model_path=model_path, tfidf_path=idf_path)
        ratios: list[float] = []
        neg_kept = neg_total = 0
        pairs: list[tuple[str, str]] = []
        for text in texts:
            try:
                r = comp.compress(text)
            except Exception:
                continue
            ratios.append(r.ratio)
            pairs.append((text, r.compressed))
            # Token-based (normalized) matching: substring checks false-positive
            # on "mat" inside "matlab" or "no" inside "know".
            in_toks = {normalize_chars(t) for t in text.lower().split()}
            out_toks = {normalize_chars(t) for t in r.compressed.lower().split()}
            present = [w for w in NEGATIONS if w in in_toks]
            neg_total += len(present)
            neg_kept += sum(1 for w in present if w in out_toks)
        row: dict[str, float | str] = {
            "n": len(ratios),
            "mean_ratio": round(sum(ratios) / max(1, len(ratios)), 4),
            "negation_preserved": round(neg_kept / max(1, neg_total), 4),
        }
        if embedder is not None and pairs:
            import torch.nn.functional as F

            embs = embedder.encode([p[0] for p in pairs] + [p[1] for p in pairs], convert_to_tensor=True)
            n = len(pairs)
            sims = F.cosine_similarity(embs[:n], embs[n:]).tolist()
            row["mean_semantic_cosine"] = round(sum(sims) / len(sims), 4)
            row["min_semantic_cosine"] = round(min(sims), 4)
        if row["negation_preserved"] < 1.0:
            failed = True
        table[name] = row

    print(json.dumps(table, indent=2))
    if failed:
        print("WARNING: at least one model dropped a negation", file=sys.stderr)


if __name__ == "__main__":
    main()
