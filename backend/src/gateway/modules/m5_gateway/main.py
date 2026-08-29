from __future__ import annotations

import json as _json
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
            [{"role": "user", "content": compressed.compressed}], temperature=request.temperature
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
    else:
        res = await gw.compressor.compress(text)
    return res.model_dump()


@app.get("/v1/compress/methods")
async def compress_methods() -> dict:
    return {
        "methods": ["heuristic", "distilled", "model", "auto"],
        "default": "auto",
        "notes": "auto uses distilled if available, else model when not dry_run, else heuristic",
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
    append_many(path, parsed)
    # also reload calibrator via new gateway instance? Note: gateway() is singleton
    # so we need to re-calibrate in place
    gw = gateway()
    # reload from disk to ensure consistency
    from gateway.service import load_calibration

    gw.calibration = load_calibration(s.data_dir)
    gw.calibrator.calibrate(gw.calibration)
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