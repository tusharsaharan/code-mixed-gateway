from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .protected_spans import detect_spans, mask_text, reinject_text, span_recall
from .schemas import CompressionAttempt
from .study_common import BACKEND_DIR, append_jsonl, load_config, read_jsonl

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
    TOKENIZER_ID = "tiktoken:cl100k_base"
except Exception:
    _ENC = None
    TOKENIZER_ID = "whitespace-fallback"


def count_tokens(text: str) -> int:
    if _ENC is not None:
        return len(_ENC.encode(text))
    return len(text.split())


def _compress_heuristic(masked_history: str) -> str:
    from gateway.modules.m2_compressor.compressor import _heuristic_compress

    return _heuristic_compress(masked_history)


def _compress_llmlingua2(masked_history: str, force_markers: list[str], rate: float, checkpoint: str) -> str | None:
    """Single-flight real classifier call. None on any failure (never heuristic)."""
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor, is_available

    if not is_available():
        raise RuntimeError("llmlingua package not installed")
    got = get_compressor(checkpoint).compress_masked([masked_history], [force_markers], rate=rate)[0]
    return got


def _compress_batch_llmlingua(
    histories: list[str], arm: str, rate: float, cfg: dict
) -> list[tuple[str, str, list, float, str | None]]:
    """One model call for a whole batch. Returns per-row
    (compressed_history, status, spans, recall, error). Never raises for
    model failures (rows fall back individually); raises RuntimeError only
    when the library itself is missing (plan: never heuristic-as-A1)."""
    from gateway.modules.m2_compressor.llmlingua2 import get_compressor, is_available

    if not is_available():
        raise RuntimeError("llmlingua package not installed")
    spans_list = [detect_spans(h) for h in histories]
    if arm == "llmlingua2_protected":
        masked = [mask_text(h, s) for h, s in zip(histories, spans_list)]
        markers = [[s.placeholder for s in spans] for spans in spans_list]
    else:
        masked = list(histories)
        markers = [[] for _ in histories]
    try:
        got = get_compressor(cfg["compression"]["checkpoint"]).compress_masked(masked, markers, rate=rate)
    except Exception:
        got = [None] * len(histories)
    out = []
    for h, spans, c in zip(histories, spans_list, got):
        if c is None:
            out.append((h, "fallback_original", spans, span_recall(h, spans), "compressor_failed"))
        elif arm == "llmlingua2_protected":
            final, ok, err = reinject_text(c, spans)
            if not ok:
                out.append((h, "fallback_original", spans, 0.0, err))
            elif count_tokens(final) > count_tokens(h) * 1.02:
                out.append((h, "fallback_original", spans, span_recall(final, spans), "compression_inflated"))
            else:
                out.append((final, "ok", spans, span_recall(final, spans), None))
        else:
            out.append((c, "ok", spans, span_recall(c, spans), None))
    return out


def run_one(
    history_block: str,
    arm: str,
    rate: float,
    cfg: dict,
) -> tuple[str, str, list, float, str | None]:
    """Returns (compressed_history, status, spans, recall, error_type).

    Raises RuntimeError for A1/A2 when the real library is missing — the plan
    forbids substituting the heuristic under the llmlingua2 name.
    """
    if arm == "none":
        return history_block, "ok", [], 1.0, None
    if arm == "heuristic":
        return _compress_heuristic(history_block), "ok", [], 1.0, None

    spans = detect_spans(history_block)
    if arm == "llmlingua2_protected":
        masked = mask_text(history_block, spans)
        force = [s.placeholder for s in spans] + list(cfg["compression"].get("force_tokens", []))
        got = _compress_llmlingua2(masked, force, rate, cfg["compression"]["checkpoint"])
        if got is None:
            return history_block, "fallback_original", spans, span_recall(history_block, spans), "compressor_failed"
        final, ok, err = reinject_text(got, spans)
        if not ok:
            return history_block, "fallback_original", spans, 0.0, err
        if count_tokens(final) > count_tokens(history_block) * 1.02:
            return history_block, "fallback_original", spans, span_recall(final, spans), "compression_inflated"
        return final, "ok", spans, span_recall(final, spans), None

    if arm == "llmlingua2":
        force = list(cfg["compression"].get("force_tokens", []))
        got = _compress_llmlingua2(history_block, force, rate, cfg["compression"]["checkpoint"])
        if got is None:
            return history_block, "fallback_original", spans, span_recall(history_block, spans), "compressor_failed"
        return got, "ok", spans, span_recall(got, spans), None
    raise ValueError(f"unknown arm {arm!r}")


def run_split(cfg: dict, split: str, arms: list[str], run_id: str) -> Path:
    base = BACKEND_DIR / "data" / "processed" / "token_study"
    prompts = [json.loads(line) for line in (base / f"prompts_{split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir = BACKEND_DIR / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"compression_{split}.jsonl"
    done = {(r["pair_id"], r["arm"], r["requested_kept_rate"]) for r in read_jsonl(out_path)}
    cfg_sha = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:16]
    n_new = 0

    def _write_row(p, history, tok_orig_hist, sys_block, cur_block, fmt_block,
                   arm, rate, comp_hist, status, spans, recall, err, latency_ms):
        nonlocal n_new
        final_prompt = "\n\n".join([sys_block, comp_hist, cur_block, fmt_block])
        tok_full_orig = count_tokens("\n\n".join([sys_block, history, cur_block, fmt_block]))
        tok_full_comp = count_tokens(final_prompt)
        rec = CompressionAttempt(
            pair_id=p["pair_id"],
            arm=arm,  # type: ignore[arg-type]
            requested_kept_rate=float(rate),
            original_prompt="\n\n".join([sys_block, history, cur_block, fmt_block]),
            compressible_context=history,
            compressed_context=comp_hist,
            final_prompt=final_prompt,
            original_token_count=tok_full_orig,
            compressed_token_count=tok_full_comp,
            achieved_kept_ratio=round(tok_full_comp / max(1, tok_full_orig), 6),
            protected_spans=spans,
            span_recall=round(recall, 6),
            compression_status=status,  # type: ignore[arg-type]
            error_type=err,
        )
        row = rec.model_dump()
        row.update({
            "split": split,
            "run_id": run_id,
            "config_sha16": cfg_sha,
            "tokenizer": TOKENIZER_ID,
            "history_tokens_original": tok_orig_hist,
            "latency_compress_ms": round(latency_ms, 1),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        append_jsonl(out_path, row)
        done.add((p["pair_id"], arm, float(rate)))
        n_new += 1

    for arm in arms:
        rates = [1.0] if arm == "none" else cfg["compression"]["requested_kept_rates"]
        for rate in rates:
            pending = [p for p in prompts if (p["pair_id"], arm, float(rate)) not in done]
            if not pending:
                continue
            if arm in ("llmlingua2", "llmlingua2_protected"):
                t0 = time.perf_counter()
                try:
                    results = _compress_batch_llmlingua(
                        [p["history_block"] for p in pending], arm, float(rate), cfg)
                except RuntimeError as e:
                    results = [(p["history_block"], "failed", [], 0.0,
                                f"compressor_unavailable: {e}") for p in pending]
                per_row_ms = (time.perf_counter() - t0) * 1000.0 / max(1, len(pending))
                for p, (comp_hist, status, spans, recall, err) in zip(pending, results):
                    history = p["history_block"]
                    _write_row(p, history, count_tokens(history), p["system_block"],
                               p["current_block"], p["output_format_block"],
                               arm, rate, comp_hist, status, spans, recall, err, per_row_ms)
            else:
                for p in pending:
                    history = p["history_block"]
                    t0 = time.perf_counter()
                    comp_hist, status, spans, recall, err = run_one(history, arm, float(rate), cfg)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    _write_row(p, history, count_tokens(history), p["system_block"],
                               p["current_block"], p["output_format_block"],
                               arm, rate, comp_hist, status, spans, recall, err, latency_ms)
    print(f"compression {split}: +{n_new} rows -> {out_path}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--split", required=True, choices=["smoke", "dev", "test"])
    ap.add_argument("--arms", default="none,llmlingua2,llmlingua2_protected,heuristic")
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    run_split(cfg, args.split, [a.strip() for a in args.arms.split(",") if a.strip()], args.run_id)


if __name__ == "__main__":
    main()
