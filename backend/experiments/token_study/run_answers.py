from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

from .schemas import AnswerAttempt
from .study_common import BACKEND_DIR, append_jsonl, groq_keys, load_config, read_jsonl


def _price(cfg: dict) -> tuple[Decimal, Decimal]:
    snap = cfg.get("price_snapshot") or {}
    pin = Decimal(str(snap.get("input_per_mtok_usd", "0")))
    pout = Decimal(str(snap.get("output_per_mtok_usd", "0")))
    return pin, pout


def call_openai_compatible(
    base_url: str, api_key: str, model: str, prompt: str, temperature: float,
    max_tokens: int, timeout_s: float, extra_body: dict | None = None,
    max_retries: int = 1,
) -> tuple[str | None, dict | None, str | None, int]:
    """Returns (text, usage, model_version, retries_used). Raises on transport errors."""
    import httpx

    # Browser-like UA: api.groq.com sits behind Cloudflare bot management,
    # which 403s default scripting TLS fingerprints (urllib verified blocked).
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        **(extra_body or {}),
    }
    last_err: Exception | None = None
    attempts = 1 + max(0, int(max_retries))
    for attempt in range(attempts):
        try:
            t0 = time.perf_counter()
            r = httpx.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=timeout_s)
            if r.status_code == 429:
                try:
                    wait = float(r.headers.get("retry-after", "0")) or 0.0
                except ValueError:
                    wait = 0.0
                last_err = RuntimeError(f"429 rate-limited (retry-after={wait}s)")
                time.sleep(min(max(wait, 2.0 * (attempt + 1)), 120.0))
                continue
            r.raise_for_status()
            data = r.json()
            msg = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            return msg, data.get("usage"), data.get("model"), attempt
        except Exception as e:  # noqa: BLE001 — classified below
            last_err = e
            time.sleep(min(2.0 * (attempt + 1), 30.0))
    raise RuntimeError(f"answer call failed after {attempts} attempts: {last_err}")


def mock_answer(prompt: str) -> tuple[str, dict]:
    """Plumbing-only stand-in. Labels every record mock-plumbing; gates refuse
    to certify results from it. Never used for measurement."""
    return '{"state": {"domain": "mock", "slots": {}}, "response": "mock plumbing response"}', {
        "prompt_tokens": -1, "completion_tokens": -1, "mock": True,
    }


def run_split(cfg: dict, split: str, run_id: str, mock_answers: bool = False) -> str:
    out_dir = BACKEND_DIR / "results" / run_id
    comp_path = out_dir / f"compression_{split}.jsonl"
    if not comp_path.exists():
        raise FileNotFoundError(f"run compression first: {comp_path} missing")
    out_path = out_dir / f"answers_{split}.jsonl"
    done = {(r["pair_id"], r["arm"], r["requested_kept_rate"]) for r in read_jsonl(out_path)}
    ans_cfg = cfg["answering"]
    pin, pout = _price(cfg)
    pace_s = float(ans_cfg.get("pacing_seconds", 1.0))
    if not mock_answers and str(ans_cfg.get("model", "")).startswith("FILL"):
        raise ValueError("answering.model is unfilled — configure a provider or pass --mock-answers (plumbing only)")
    import itertools

    key_pool = itertools.cycle(groq_keys()) if not mock_answers else None
    n_new = 0
    for row in read_jsonl(comp_path):
        key = (row["pair_id"], row["arm"], row["requested_kept_rate"])
        if key in done:
            continue
        t0 = time.perf_counter()
        status, text, usage, version, retries, err_note = "ok", None, None, None, 0, None
        try:
            if mock_answers:
                text, usage = mock_answer(row["final_prompt"])
                version = "mock-plumbing"
            else:
                key = os.environ.get(str(ans_cfg.get("api_key_env", "")), "") if key_pool is None else next(key_pool)
                if not key:
                    raise RuntimeError(f"missing env {ans_cfg.get('api_key_env')}: 401/403-class config failure, stopping")
                text, usage, version, retries = call_openai_compatible(
                    ans_cfg["provider"], key,
                    ans_cfg["model"], row["final_prompt"], float(ans_cfg.get("temperature", 0)),
                    int(ans_cfg.get("max_output_tokens", 256)), float(ans_cfg.get("timeout_s", 60)),
                    extra_body=ans_cfg.get("extra_body") or None,
                    max_retries=int(ans_cfg.get("max_retries", 1)),
                )
        except Exception as e:  # noqa: BLE001 — recorded, never hidden
            ename = type(e).__name__
            msg = str(e)[:150]
            if "429" in msg or "rate-limited" in msg:
                status = "rate_limited"
            elif "timeout" in ename.lower():
                status = "timeout"
            else:
                status = "api_error"
            err_note = f"{ename}: {msg}"
            text, usage = None, None
        latency_ms = (time.perf_counter() - t0) * 1000.0
        pt = usage.get("prompt_tokens") if usage else None
        ct = usage.get("completion_tokens") if usage else None
        cost = None
        if pt is not None and pt >= 0 and ct is not None and ct >= 0:
            cost = (Decimal(pt) * pin + Decimal(ct) * pout) / Decimal(1_000_000)
        rec = AnswerAttempt(
            pair_id=row["pair_id"], arm=row["arm"], requested_kept_rate=row["requested_kept_rate"],
            model="mock-plumbing" if mock_answers else ans_cfg["model"],
            model_version=version, response=text, raw_provider_usage=usage,
            prompt_tokens=pt, completion_tokens=ct, answer_cost_usd=cost,
            latency_ms=round(latency_ms, 1), status=status,  # type: ignore[arg-type]
            retry_count=retries, error_note=err_note,
        )
        out_row = rec.model_dump(mode="json")  # Decimal costs -> JSON-safe strings
        out_row.update({"split": split, "run_id": run_id,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        append_jsonl(out_path, out_row)
        n_new += 1
        if pace_s > 0 and not mock_answers:
            time.sleep(pace_s)
    print(f"answers {split}: +{n_new} rows -> {out_path} (mock={mock_answers})")
    return str(out_path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--split", required=True, choices=["smoke", "dev", "test"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mock-answers", action="store_true", help="plumbing test only; never measurement")
    args = ap.parse_args()
    run_split(load_config(args.config), args.split, args.run_id, mock_answers=args.mock_answers)


if __name__ == "__main__":
    main()
