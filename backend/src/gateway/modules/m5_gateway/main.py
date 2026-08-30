from __future__ import annotations

import json as _json
import threading as _threading
import time as _time
from typing import Annotated

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from gateway.config import get_settings
from gateway.modules.m6_telegram.db import LogDB
from gateway.modules.m7_eval.evaluate import curve_points
from gateway.modules.m8_dashboard.dashboard import (
    dashboard_html,
    dashboard_recent,
    dashboard_series,
    dashboard_stats,
)
from gateway.modules.m11_calibration.ece import expected_calibration_error, reliability_diagram
from gateway.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    DashboardStats,
    DispatchResult,
    OpenAIErrorResponse,
    SeriesPoint,
)
from gateway.service import Gateway, get_log_db

_calibration_lock = _threading.Lock()

app = FastAPI(
    title="Code-Mixed Gateway",
    version="0.2.0",
    description=(
        "Open Hinglish compression + conformal cascade gateway — "
        "OpenAI-compatible. Dry-run by default."
    ),
)

_origins = get_settings().cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins != ["*"] else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_gateway: Gateway | None = None


def gateway() -> Gateway:
    global _gateway
    if _gateway is None:
        _gateway = Gateway(get_settings())
    return _gateway


def _error(
    status: int,
    message: str,
    err_type: str = "invalid_request_error",
    code: int | None = None,
) -> JSONResponse:
    body = OpenAIErrorResponse(error={"message": message, "type": err_type, "code": code})
    return JSONResponse(status_code=status, content=body.model_dump())


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return _error(400, str(exc))


@app.exception_handler(httpx.HTTPError)
async def upstream_error_handler(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    return _error(502, f"Upstream model error: {exc}", "api_error", 502)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(500, f"Internal error: {exc}", "server_error", 500)


@app.get("/healthz")
async def healthz():
    s = get_settings()
    gw = gateway()
    cal_path = s.data_dir / "calibration.jsonl"
    # Honest is_real: bench-derived samples indicate grounding, pure pad-only is synthetic
    bench_n = 0
    pad_n = 0
    if cal_path.exists() and cal_path.stat().st_size > 0:
        try:
            for line in cal_path.read_text(encoding="utf-8").splitlines():
                if "bench-" in line:
                    bench_n += 1
                elif "pad-" in line:
                    pad_n += 1
        except Exception:
            pass
    is_real = bench_n > 0
    from gateway.tokenizer import TokenCounter

    return {
        "status": "ok",
        "dry_run": s.dry_run,
        "version": app.version,
        "calibration_n": len(gw.calibration),
        "calibration_real": is_real,
        "calibration_bench_n": bench_n,
        "calibration_pad_n": pad_n,
        "threshold": gw.calibrator.threshold,
        "cheap_model": s.cheap.model,
        "premium_model": s.premium.model,
        "tokenizer_backend": TokenCounter().backend,
        "pricing_date": s.pricing_date,
    }


class CompressRequest(BaseModel):
    text: str
    method: str | None = None  # heuristic | distilled | model | auto


class ReasoningBudgetRequest(BaseModel):
    text: str
    english_gloss: str | None = None


@app.get("/v1/models")
async def models():
    s = get_settings()
    return {
        "object": "list",
        "data": [
            {"id": s.cheap.model, "object": "model", "tier": "cheap"},
            {"id": s.premium.model, "object": "model", "tier": "premium"},
            {"id": s.local.model, "object": "model", "tier": "local-compressor"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):  # type: ignore[no-untyped-def]
    if request.stream:
        return StreamingResponse(
            _stream_chat(request), media_type="text/event-stream"
        )
    result: ChatCompletionResponse = await gateway().handle(request)
    return result


async def _stream_chat(request: ChatCompletionRequest):  # type: ignore[no-untyped-def]
    gw = gateway()
    user_text = gw._last_user_text(request)
    compressed = await gw.compressor.compress(user_text)
    score = gw.router.scorer.score(compressed.compressed)
    tier = "premium" if gw.calibrator.route_premium(score) else "cheap"
    client = gw.router.premium_client if tier == "premium" else gw.router.cheap_client
    task_id = f"cmg-{int(_time.time() * 1e6)}"
    created = int(_time.time())
    # Build full x_gateway for the first SSE chunk via shared helper
    # so stream and non-stream return identical shapes. Prompt-only cost
    # is reported in the first chunk (completion unknown until stream ends).
    prompt_tokens = gw.counter.count(compressed.compressed)
    stub_dispatch = DispatchResult(
        task_id=task_id,
        model_routed=client.model,
        score=score,
        threshold=gw.calibrator.threshold,
        tier=tier,  # type: ignore[arg-type]
        response="",
        prompt_tokens=prompt_tokens,
        completion_tokens=0,
        cost_est_usd=gw.router._estimate_cost(tier, prompt_tokens, 0),
        dry_run=gw.settings.dry_run,
    )
    meta_obj = gw.build_meta(compressed, stub_dispatch, user_text)
    meta = meta_obj.model_dump()
    first = {
        "id": task_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": client.model,
        "choices": [
            {"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}
        ],
        "x_gateway": meta,
    }
    yield f"data: {_json.dumps(first)}\n\n".encode()
    full = ""
    try:
        async for token in client.stream_chat(
            [{"role": "user", "content": compressed.compressed}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            full += token
            chunk = {
                "id": task_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": client.model,
                "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
            }
            yield f"data: {_json.dumps(chunk)}\n\n".encode()
    except Exception as exc:
        err = {
            "id": task_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": client.model,
            "choices": [{"index": 0, "delta": {"content": f"\n[upstream error: {exc}]"}, "finish_reason": "stop"}],
        }
        yield f"data: {_json.dumps(err)}\n\n".encode()
    yield b"data: [DONE]\n\n"
    if gw.settings.log_requests:
        try:
            # Prefer provider usage if available (stream_options.include_usage)
            usage = getattr(client, "last_usage", None)
            if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
                prompt_tokens = int(usage.get("prompt_tokens") or gw.counter.count(compressed.compressed))
                completion_tokens = int(usage.get("completion_tokens") or gw.counter.count(full))
            else:
                prompt_tokens = gw.counter.count(compressed.compressed)
                completion_tokens = gw.counter.count(full)
            cost = gw.router._estimate_cost(tier, prompt_tokens, completion_tokens)
            premium_cost = gw.router._estimate_cost("premium", prompt_tokens, completion_tokens)
            savings = max(0.0, premium_cost - cost)
            get_log_db().log(
                user_id=request.user or "anonymous",
                original_tokens=compressed.token_original,
                compressed_tokens=compressed.token_compressed,
                model_routed=client.model,
                estimated_cost_savings=float(savings),
            )
        except Exception:
            pass


@app.post("/v1/compress")
async def compress_endpoint(req: CompressRequest) -> dict:
    gw = gateway()
    text = req.text or ""
    if not text.strip():
        raise ValueError("empty text: provide non-empty 'text' field")
    method = (req.method or "auto").lower()
    if method == "heuristic":
        res = gw.compressor.compress_heuristic(text)
    elif method == "distilled":
        res = gw.compressor.compress_distilled(text)
    elif method == "model":
        res = await gw.compressor.compress_model(text)
    elif method == "adaptive":
        # Mixture-aware adaptive (novel)
        from gateway.modules.m1_pipeline.hinglish import code_mix_ratio as _cm
        from gateway.modules.m12_novel.adaptive import target_kept_ratio as _tgt

        score = gw.router.scorer.score(text)
        cm = _cm(text)
        tgt = _tgt(cm, score)
        # Reuse novel adaptive logic (import to avoid circular)
        import re as _re

        from gateway.modules.m2_compressor.safety_span import mask as _mask
        from gateway.modules.m2_compressor.safety_span import reinject as _reinject

        _GREET = _re.compile(r"^(hi|hello|hey|namaste|namaskar|hii+|yo|sir|madam|bro|dost)[\s,!.]+", _re.IGNORECASE)
        _WS2 = _re.compile(r"\s+")
        if tgt > 0.82:
            masked, spans = _mask(text)
            cleaned = _GREET.sub("", masked).strip()
            cleaned = _WS2.sub(" ", cleaned) if cleaned else masked
            final, ok = _reinject(cleaned, spans)
            if not ok:
                final = text
            from gateway.schemas import CompressResult as _CR

            tok_o = gw.counter.count(text)
            tok_c = gw.counter.count(final)
            res = _CR(
                original=text,
                compressed=final,
                spans=spans,
                token_original=tok_o,
                token_compressed=max(1, tok_c),
                ratio=round(max(1, tok_c) / max(1, tok_o), 6),
                method="heuristic",
            )
            d = res.model_dump()
            d["method"] = "adaptive"
            d["adaptive_target"] = tgt
            d["code_mix_ratio"] = cm
            d["difficulty"] = score
            return d
        # else use heuristic+truncate adaptive path
        base = gw.compressor.compress_heuristic(text)
        if base.ratio <= tgt + 0.02:
            d = base.model_dump()
            d["method"] = "adaptive"
            d["adaptive_target"] = tgt
            d["code_mix_ratio"] = cm
            d["difficulty"] = score
            return d
        words = base.compressed.split()
        keep = max(3, int(len(words) * (tgt / max(base.ratio, 0.01))))
        keep = min(len(words), keep)
        trunc = " ".join(words[:keep])
        if any(sp.text not in trunc for sp in base.spans):
            d = base.model_dump()
            d["method"] = "adaptive"
            d["adaptive_target"] = tgt
            d["code_mix_ratio"] = cm
            d["difficulty"] = score
            return d
        from gateway.schemas import CompressResult as _CR2

        tok_c = gw.counter.count(trunc)
        res2 = _CR2(
            original=text,
            compressed=trunc,
            spans=base.spans,
            token_original=base.token_original,
            token_compressed=max(1, tok_c),
            ratio=round(max(1, tok_c) / max(1, base.token_original), 6),
            method="heuristic",
        )
        d = res2.model_dump()
        d["method"] = "adaptive"
        d["adaptive_target"] = tgt
        d["code_mix_ratio"] = cm
        d["difficulty"] = score
        return d
    else:
        res = await gw.compressor.compress(text)
    return res.model_dump()


@app.get("/v1/compress/methods")
async def compress_methods() -> dict:
    return {
        "methods": ["heuristic", "distilled", "model", "adaptive", "auto"],
        "default": "auto",
        "notes": (
            "auto uses distilled if available, else model when not dry_run, "
            "else heuristic; adaptive is code-mix-aware (novel)"
        ),
    }


@app.post("/v1/reasoning/budget")
async def reasoning_budget(req: ReasoningBudgetRequest) -> dict:
    gw = gateway()
    est = gw.budget_estimator.estimate(req.text)
    out: dict = est.model_dump()
    if req.english_gloss:
        delta = gw.budget_comparator.delta(req.text, req.english_gloss)
        be = gw.budget_estimator.estimate(req.english_gloss)
        out["english_budget"] = be.reasoning_tokens
        out["delta_hinglish_minus_english"] = delta
    else:
        gloss = gw.budget_comparator.gloss_for(req.text)
        if gloss is not None:
            delta = gw.budget_comparator.delta(req.text, gloss)
            be = gw.budget_estimator.estimate(gloss)
            out["english_gloss"] = gloss
            out["english_budget"] = be.reasoning_tokens
            out["delta_hinglish_minus_english"] = delta
    return out


@app.get("/v1/reasoning/compare")
async def reasoning_compare(hinglish: str, english: str) -> dict:
    gw = gateway()
    return gw.budget_comparator.compare(hinglish, english)


@app.get("/v1/tokenizer/encode")
async def tokenizer_encode(text: str, tokenizer: str = "gpt4o_cl100k") -> dict:
    """Live encode for visualizer — returns token count, tokens per char, and chip texts.

    Supports: gpt4o_cl100k (tiktoken if installed else whitespace), whitespace, char4_proxy,
    and any HF tokenizer listed in tokenizer_bench.HF_TOKENIZER_SPECS (lazy-loaded).
    """
    from gateway.modules.m1_pipeline.tokenizer_bench import DEFAULT_TOKENIZERS
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD
    from gateway.tokenizer import TokenCounter

    tok = tokenizer.strip()
    fn = DEFAULT_TOKENIZERS.get(tok)
    counter = TokenCounter()
    # Fallback to whitespace if unknown
    if fn is None:
        fn = DEFAULT_TOKENIZERS.get("whitespace")  # type: ignore
        tok = "whitespace"
    n = max(1, fn(text)) if text.strip() else 0
    # Backend truth for cost (always cl100k if available else whitespace)
    backend_tokens = counter.count(text)
    chars = len(text)
    tpc = round(n / max(1, chars), 6) if text else 0
    # Build chips only for small texts (avoid large payloads)
    chips: list[dict] = []
    if text and len(text) < 600:
        # Try to get per-token strings if tokenizer is tiktoken-like
        try:
            import tiktoken

            if tok == "gpt4o_cl100k":
                enc = tiktoken.get_encoding("cl100k_base")
                ids = enc.encode(text)
                for i, tid in enumerate(ids[:80]):
                    try:
                        piece = enc.decode([tid])
                    except Exception:
                        piece = ""
                    chips.append({"id": i, "token": int(tid), "text": piece})
        except Exception:
            # Fallback: word chips
            words = text.split()
            for i, w in enumerate(words[:40]):
                chips.append({"id": i, "token": i, "text": w})
    return {
        "text": text,
        "tokenizer": tok,
        "tokens": n,
        "chars": chars,
        "tokens_per_char": tpc,
        "backend_tokens": backend_tokens,
        "backend": counter.backend,
        "cost_cheap_usd": round(n * CHEAP_PER_1K_USD / 1000, 8),
        "cost_premium_usd": round(n * PREMIUM_PER_1K_USD / 1000, 8),
        "chips": chips,
        "pricing_date": get_settings().pricing_date,
    }


@app.post("/v1/tokenizer/encode_batch")
async def tokenizer_encode_batch(payload: dict) -> dict:
    texts: list[str] = payload.get("texts") or []
    tokenizer: str = payload.get("tokenizer") or "gpt4o_cl100k"
    from gateway.modules.m1_pipeline.tokenizer_bench import DEFAULT_TOKENIZERS
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD

    fn = DEFAULT_TOKENIZERS.get(tokenizer) or DEFAULT_TOKENIZERS.get("whitespace")  # type: ignore
    out = []
    for t in texts[:12]:
        n = max(1, fn(t)) if t.strip() else 0
        out.append(
            {
                "text": t[:120],
                "tokens": n,
                "cost_premium_usd": round(n * PREMIUM_PER_1K_USD / 1000, 8),
                "cost_cheap_usd": round(n * CHEAP_PER_1K_USD / 1000, 8),
            }
        )
    return {"results": out, "tokenizer": tokenizer, "pricing_date": get_settings().pricing_date}


class CodeMixInterpolateRequest(BaseModel):
    text: str
    steps: int = 5


@app.post("/v1/code_mix/interpolate")
async def code_mix_interpolate(req: CodeMixInterpolateRequest) -> dict:
    """Interpolate a sentence between Hinglish (0) and English (1) for the code-switch slider.

    Generates `steps` variants where level=0 keeps original Hinglish, level=1 is full
    English gloss, and intermediate levels replace a proportion of Hinglish tokens.
    Each variant is annotated with code_mix, tokens, cost, adaptive target, and compression preview.
    """
    from gateway.modules.m1_pipeline.hinglish import code_mix_ratio
    from gateway.modules.m12_novel.gloss import HINGLISH_TO_EN, to_english_gloss
    from gateway.pricing import CHEAP_PER_1K_USD, PREMIUM_PER_1K_USD
    from gateway.tokenizer import TokenCounter

    text = (req.text or "").strip()
    if not text:
        raise ValueError("text required")
    steps = max(2, min(7, req.steps or 5))
    # Build reverse map for debugging but interpolate via gloss proportion
    # Generate intermediate texts by progressively applying gloss
    variants: list[dict] = []
    counter = TokenCounter()
    # Identify hinglish token positions in original
    tokens = text.split()
    hinglish_positions = []
    for idx, tok in enumerate(tokens):
        low = tok.lower().strip(",.!?;:\"'()[]{}")
        if low in HINGLISH_TO_EN and HINGLISH_TO_EN[low] != "":
            hinglish_positions.append(idx)
    # Also include particles that would be dropped
    n_hing = len(hinglish_positions) or 1
    for s in range(steps):
        level = s / (steps - 1) if steps > 1 else 0
        # Number to replace at this level
        n_replace = int(round(level * n_hing))
        # Deterministic: replace first n_replace positions
        replace_set = set(hinglish_positions[:n_replace])
        if level >= 0.99:
            interp_text = to_english_gloss(text)
        elif level <= 0.01:
            interp_text = text
        else:
            # Build intermediate by selectively replacing
            out_tokens: list[str] = []
            for idx, tok in enumerate(tokens):
                if idx in replace_set:
                    low = tok.lower().strip(",.!?;:\"'()[]{}")
                    # preserve punctuation
                    m = __import__("re").match(r"^([A-Za-z]+)([.,!?;:]*)$", tok)
                    if m:
                        core, punct = m.group(1), m.group(2)
                        eng = HINGLISH_TO_EN.get(core.lower(), core)
                        if eng == "":
                            continue
                        if core[0].isupper():
                            eng = eng.capitalize()
                        out_tokens.append(eng + punct)
                    else:
                        eng = HINGLISH_TO_EN.get(low, tok)
                        if eng == "":
                            continue
                        out_tokens.append(eng)
                else:
                    out_tokens.append(tok)
            interp_text = " ".join(out_tokens)
            interp_text = __import__("re").sub(r"\s+", " ", interp_text).strip()
        cm = code_mix_ratio(interp_text)
        n_tok = counter.count(interp_text)
        cost_cheap = round(n_tok * CHEAP_PER_1K_USD / 1000, 8)
        cost_prem = round(n_tok * PREMIUM_PER_1K_USD / 1000, 8)
        # Adaptive target for this variant
        from gateway.modules.m4_router.difficulty import DifficultyScorer
        from gateway.modules.m12_novel.adaptive import target_kept_ratio

        scorer = DifficultyScorer(counter)
        diff = scorer.score(interp_text)
        tgt = target_kept_ratio(cm, diff)
        # Compression preview (heuristic ratio)
        from gateway.modules.m2_compressor.compressor import Compressor

        comp = Compressor(counter)
        h = comp.compress_heuristic(interp_text)
        variants.append(
            {
                "level": round(level, 3),
                "text": interp_text,
                "code_mix_ratio": cm,
                "tokens": n_tok,
                "tokens_per_char": round(n_tok / max(1, len(interp_text)), 4),
                "cost_cheap_usd": cost_cheap,
                "cost_premium_usd": cost_prem,
                "difficulty": diff,
                "adaptive_target": tgt,
                "heuristic_kept_ratio": h.ratio,
                "heuristic_compressed": h.compressed,
            }
        )
    return {"original": text, "steps": steps, "variants": variants, "pricing_date": get_settings().pricing_date}


@app.get("/v1/tokenizer/report")
async def tokenizer_report() -> dict:
    from gateway.modules.m1_pipeline.pipeline import iter_jsonl
    from gateway.modules.m1_pipeline.tokenizer_bench import TokenizerBench

    s = get_settings()
    records = iter_jsonl(s.data_dir / "seed_hinglish.jsonl")
    bench = TokenizerBench()
    inflation = bench.inflation(records) if records else {}
    rows = bench.run(records[:8]) if records else []
    return {
        "n_records": len(records),
        "inflation_vs_gpt4o": inflation,
        "sample_rows": [r.model_dump() for r in rows[:24]],
        "pricing_date": s.pricing_date,
    }


@app.get("/v1/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats_endpoint(db: Annotated[LogDB, Depends(get_log_db)]) -> DashboardStats:
    return dashboard_stats(db)


@app.get("/v1/dashboard/series", response_model=list[SeriesPoint])
async def dashboard_series_endpoint(
    window: int = 3600, db: Annotated[LogDB, Depends(get_log_db)] = None
) -> list[SeriesPoint]:
    return dashboard_series(db, window)


@app.get("/v1/dashboard/recent")
async def dashboard_recent_endpoint(
    limit: int = 20, db: Annotated[LogDB, Depends(get_log_db)] = None
) -> list:
    return dashboard_recent(db, limit)


@app.get("/v1/eval/curve")
async def eval_curve() -> list[dict]:
    s = get_settings()
    bench = s.data_dir / "benchmark.jsonl"
    if not bench.exists():
        return []
    return curve_points(bench, s.distilled_checkpoint)


@app.get("/v1/eval/curve/sweep")
async def eval_curve_sweep() -> list[dict]:
    from gateway.modules.m7_eval.evaluate import curve_sweep

    s = get_settings()
    bench = s.data_dir / "benchmark.jsonl"
    if not bench.exists():
        return []
    return curve_sweep(bench, s.distilled_checkpoint)


@app.get("/v1/eval/summary")
async def eval_summary() -> dict:
    from gateway.modules.m7_eval.evaluate import HinglishEvaluator, load_records

    s = get_settings()
    path = s.data_dir / "benchmark.jsonl"
    if not path.exists():
        return {"n": 0, "message": "no benchmark found", "pricing_date": s.pricing_date}
    records = load_records(path)
    summary = HinglishEvaluator(fx_rate_inr_per_usd=s.fx_rate_inr_per_usd).evaluate(
        records, pricing_date=s.pricing_date
    )
    return summary.model_dump()


@app.get("/v1/eval/novel")
async def eval_novel() -> dict:
    """Novel analyses: adaptive vs fixed, tokenizer tax, Hinglish-En delta, conformal compression."""
    from gateway.modules.m12_novel.analysis import build_novel_report

    s = get_settings()
    return build_novel_report(s.data_dir)


@app.get("/v1/eval/novel/summary")
async def eval_novel_summary() -> dict:
    from gateway.modules.m12_novel.analysis import build_novel_report

    s = get_settings()
    r = build_novel_report(s.data_dir)
    return {"summary_bullets": r["summary_bullets"], "n_benchmark": r["n_benchmark"], "generated_at": r["generated_at"]}


@app.get("/v1/calibration/metrics")
async def calibration_metrics() -> dict:
    gw = gateway()
    scores = [s.nonconformity for s in gw.calibration]
    labels = [s.cheap_success for s in gw.calibration]
    ece = expected_calibration_error(scores, labels)
    n = len(gw.calibration)
    simple_bound = round(gw.calibrator.alpha + 1.0 / (n + 1), 6) if n else gw.calibrator.alpha
    hoeffding_bound = round(gw.calibrator.risk_bound, 6)
    s = get_settings()
    cal_path = s.data_dir / "calibration.jsonl"
    bench_n = 0
    pad_n = 0
    if cal_path.exists() and cal_path.stat().st_size > 0:
        try:
            for line in cal_path.read_text(encoding="utf-8").splitlines():
                if "bench-" in line:
                    bench_n += 1
                elif "pad-" in line:
                    pad_n += 1
        except Exception:
            pass
        is_real = bench_n > 0
    else:
        is_real = False
    return {
        "n": n,
        "alpha": gw.calibrator.alpha,
        "delta": gw.calibrator.delta,
        "threshold": gw.calibrator.threshold,
        "error_bound_simple": simple_bound,
        "error_bound_hoeffding": hoeffding_bound,
        "error_bound": hoeffding_bound,
        "risk_hat": round(gw.calibrator.risk_hat, 6),
        "ece": ece,
        "reliability": reliability_diagram(scores, labels),
        "is_real": is_real,
        "bench_n": bench_n,
        "pad_n": pad_n,
        "real_path": str(cal_path),
    }


class CalibrationIngestRequest(BaseModel):
    samples: list[dict]


@app.post("/v1/calibration/ingest")
async def calibration_ingest(req: CalibrationIngestRequest) -> dict:
    from gateway.modules.m3_conformal.calibration_store import append_many
    from gateway.schemas import CalibSample

    s = get_settings()
    path = s.data_dir / "calibration.jsonl"
    parsed: list[CalibSample] = []
    for row in req.samples:
        try:
            parsed.append(CalibSample.model_validate(row))
        except Exception as e:
            raise ValueError(f"invalid sample {row}: {e}") from e
    with _calibration_lock:
        append_many(path, parsed)
        gw = gateway()
        from gateway.service import load_calibration

        gw.calibration = load_calibration(s.data_dir)
        gw.calibrator.calibrate(gw.calibration)
        # lineage for audit
        try:
            meta_path = s.data_dir / "calibration.meta.json"
            bench_n = sum(1 for c in gw.calibration if str(c.id).startswith("bench-"))
            pad_n = sum(1 for c in gw.calibration if str(c.id).startswith("pad-"))
            meta = {
                "updated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "n_total": len(gw.calibration),
                "bench_n": bench_n,
                "pad_n": pad_n,
                "alpha": gw.calibrator.alpha,
                "delta": gw.calibrator.delta,
                "threshold": gw.calibrator.threshold,
                "risk_hat": gw.calibrator.risk_hat,
                "risk_bound": gw.calibrator.risk_bound,
            }
            meta_path.write_text(_json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass
        return {"ingested": len(parsed), "n_total": len(gw.calibration), "threshold": gw.calibrator.threshold}


@app.post("/telegram/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    import hmac as _hmac

    s = get_settings()
    expected = s.telegram_webhook_secret or (s.telegram_token[-8:] if s.telegram_token else "")
    # Support Telegram's X-Telegram-Bot-Api-Secret-Token header (constant-time)
    header_secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    provided = header_secret or secret
    if not expected or not _hmac.compare_digest(provided, expected):
        return JSONResponse(status_code=403, content={"error": "invalid webhook secret"})
    if not s.telegram_token:
        return JSONResponse(status_code=503, content={"error": "telegram not configured"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid JSON"})
    # Telegram Update minimal parsing
    msg = (body.get("message") or body.get("edited_message") or {})
    text = (msg.get("text") or "").strip()
    from_user = (msg.get("from") or {})
    chat = msg.get("chat") or {}
    user_id = str(from_user.get("id") or chat.get("id") or "unknown")
    chat_id = chat.get("id")
    if not text or not chat_id:
        return {"ok": True}
    # no commands except /start
    if text.startswith("/start"):
        reply_text = "namaste! apna sawal bhejo — Hinglish me bhi chalega."
    else:
        try:
            # Direct internal call — avoids hardcoded localhost HTTP loop and double logging
            gw = gateway()
            from gateway.schemas import ChatCompletionRequest, ChatMessage

            req = ChatCompletionRequest(
                model="cascade",
                messages=[ChatMessage(role="user", content=text)],
                user=f"tg:{user_id}",
            )
            resp = await gw.handle(req)
            reply_text = resp.choices[0].message.content if resp.choices else ""
        except Exception as exc:
            reply_text = f"sorry, gateway error: {exc}"
    # send via Telegram Bot API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{s.telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": reply_text},
            )
    except Exception:
        pass
    return {"ok": True}


@app.get("/telegram/webhook/{secret}")
async def telegram_webhook_info(secret: str):
    import hmac as _hmac

    s = get_settings()
    expected = s.telegram_webhook_secret or (s.telegram_token[-8:] if s.telegram_token else "")
    # Do not oracle secret via timing — constant-time but do not reveal
    ok = bool(expected and _hmac.compare_digest(secret, expected)) if expected else False
    return {"configured": bool(s.telegram_token), "secret_ok": ok}


@app.get("/v1/diagnostics/upstream")
async def diagnostics_upstream() -> dict:
    import time as _t

    s = get_settings()
    results: dict = {}
    for tier, cfg in [("cheap", s.cheap), ("premium", s.premium), ("local", s.local)]:
        start = _t.time()
        ok = False
        err: str | None = None
        try:
            import httpx as _httpx

            # cheap probe: try GET on base_url with short timeout; many providers return 404 but that's reachable
            async with _httpx.AsyncClient(timeout=3.0) as client:
                # try a GET on base_url/models or just base_url
                url = cfg.base_url.rstrip("/") + "/models"
                resp = await client.get(url, headers={"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {})
                ok = resp.status_code < 500
        except Exception as e:
            err = str(e)[:200]
        elapsed = round((_t.time() - start) * 1000, 1)
        results[tier] = {
            "model": cfg.model,
            "base_url": cfg.base_url,
            "reachable": ok,
            "latency_ms": elapsed,
            "error": err,
        }
    results["note"] = (
        "Ollama local expected at http://localhost:11434/v1 — "
        "run `ollama serve` and `ollama pull qwen3:0.6b` if not reachable."
    )
    return results


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


def run() -> None:
    uvicorn.run("gateway.modules.m5_gateway.main:app", host="127.0.0.1", port=8000)