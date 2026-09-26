from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
from decimal import Decimal

from .schemas import JudgeAttempt

RUBRIC_V1 = """You are grading a task-oriented assistant. You receive the dialogue
context, the gold state/response, and ONE candidate response. You do NOT know
how the candidate was produced. Return JSON only:
{"label": "correct|partially_correct|incorrect", "error_tags": [...], "rationale": "<=40 words"}.
Mark correct only if the candidate completes the user's current task without
contradicting the dialogue and contains all decision-critical slot values
(domain, intent, item/service, amount, date/time, count, location, IDs,
explicit negations/corrections). Mark partially_correct if intent is handled
but a non-critical detail is missing. Mark incorrect on wrong intent/state,
lost/changed critical values, fabrications, or no answer. Error tags from:
missing_slot, wrong_slot_value, wrong_intent, hallucination, no_answer,
language_breakdown."""

SCORE = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}


def judge_prompt(context: str, gold_state, gold_response: str | None, candidate: str | None) -> str:
    return (
        RUBRIC_V1 + "\n\nCONTEXT:\n" + context + "\n\nGOLD STATE:\n"
        + json.dumps(gold_state, ensure_ascii=False) + "\n\nGOLD RESPONSE:\n"
        + (gold_response or "") + "\n\nCANDIDATE:\n" + (candidate or "")
    )


def _parse_judge_output(text: str | None) -> tuple[str, list[str], str, bool]:
    """Returns (label, error_tags, rationale, valid)."""
    if not text:
        return "incorrect", ["no_answer"], "", False
    try:
        obj = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        try:
            obj = json.loads(text[start : end + 1]) if start >= 0 and end > start else None
        except Exception:
            obj = None
    if not isinstance(obj, dict) or obj.get("label") not in SCORE:
        return "incorrect", ["judge_invalid"], (text or "")[:200], False
    tags = obj.get("error_tags", [])
    tags = [str(t) for t in tags] if isinstance(tags, list) else []
    return obj["label"], tags, str(obj.get("rationale", ""))[:500], True


def run_judge_split(cfg: dict, split: str, run_id: str) -> str:
    """Blind LLM judge over answer rows. The judge never sees arm/rate/cost."""
    from .study_common import BACKEND_DIR, read_jsonl

    jcfg = cfg["judging"]
    if str(jcfg.get("model", "")).startswith("FILL"):
        raise ValueError("judging.model is unfilled")
    import itertools

    from .study_common import groq_keys

    key_pool = itertools.cycle(groq_keys())
    key = next(key_pool)
    snap = cfg.get("price_snapshot") or {}
    pin = Decimal(str(snap.get("judge_input_per_mtok_usd", snap.get("input_per_mtok_usd", "0"))))
    pout = Decimal(str(snap.get("judge_output_per_mtok_usd", snap.get("output_per_mtok_usd", "0"))))
    out_dir = BACKEND_DIR / "results" / run_id
    prompts = {json.loads(line)["pair_id"]: json.loads(line) for line in
               (BACKEND_DIR / "data" / "processed" / "token_study" / f"prompts_{split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    out_path = out_dir / f"judge_{split}.jsonl"
    done = {(r["pair_id"], r["arm"], r["requested_kept_rate"]) for r in read_jsonl(out_path)}
    import httpx

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    n_new = 0
    with httpx.Client(timeout=60, headers=headers) as client:
        for line in (out_dir / f"answers_{split}.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            a = json.loads(line)
            key3 = (a["pair_id"], a["arm"], a["requested_kept_rate"])
            if key3 in done:
                continue
            p = prompts.get(a["pair_id"], {})
            prompt = judge_prompt(
                (p.get("history_block", "") + "\n" + p.get("current_block", ""))[:4000],
                p.get("gold_state"), p.get("gold_response"), a.get("response"))
            label, tags, rationale, valid = "incorrect", ["judge_invalid"], "", False
            usage, retries, status_note = None, 0, "ok"
            for attempt in range(2):
                try:
                    key = next(key_pool)  # rotate keys to spread rate limits
                    r = client.post(
                        f"{cfg['answering']['provider'].rstrip('/')}/chat/completions",
                        json={"model": jcfg["model"],
                              "messages": [{"role": "user", "content": prompt}],
                              "temperature": 0, "max_tokens": 256})
                    r.raise_for_status()
                    data = r.json()
                    usage = data.get("usage")
                    label, tags, rationale, valid = _parse_judge_output(
                        (data.get("choices") or [{}])[0].get("message", {}).get("content"))
                    retries = attempt
                    break
                except Exception as e:  # noqa: BLE001 — one retry, then recorded
                    status_note = f"judge_error: {type(e).__name__}"
                    time.sleep(min(2.0 * (attempt + 1), 8.0))
            pt = (usage or {}).get("prompt_tokens")
            ct = (usage or {}).get("completion_tokens")
            cost = ((Decimal(pt) * pin + Decimal(ct) * pout) / Decimal(1_000_000)
                    if pt is not None and ct is not None else None)
            rec = JudgeAttempt(
                pair_id=a["pair_id"], arm=a["arm"], requested_kept_rate=a["requested_kept_rate"],
                judge_model=jcfg["model"], label=label,  # type: ignore[arg-type]
                error_tags=tags, rationale=rationale, score=SCORE[label])
            row = rec.model_dump()
            row.update({"split": split, "run_id": run_id, "judge_valid": valid,
                        "judge_status": status_note, "judge_cost_usd": str(cost) if cost is not None else None,
                        "retry_count": retries,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            from .study_common import append_jsonl
            append_jsonl(out_path, row)
            done.add(key3)
            n_new += 1
    print(f"judge {split}: +{n_new} rows -> {out_path}")
    return str(out_path)


def export_audit(prompts_path, answers_path, out_path, seed: int = 20260926, n: int = 100) -> list[dict]:
    """Blinded human-audit export: randomized order, arms replaced by anonymous labels."""
    rng = random.Random(seed)
    prompts = {json.loads(line)["pair_id"]: json.loads(line) for line in
               prompts_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    rows = [json.loads(line) for line in answers_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rng.shuffle(rows)
    arms = sorted({r["arm"] for r in rows})
    rng.shuffle(arms)
    anon = {a: f"system_{chr(65 + i)}" for i, a in enumerate(arms)}
    sample = rows[:n]
    out_rows = []
    for r in sample:
        p = prompts.get(r["pair_id"], {})
        out_rows.append({
            "pair_id": r["pair_id"],
            "system": anon[r["arm"]],
            "context": (p.get("history_block", "") + "\n" + p.get("current_block", ""))[:4000],
            "gold_state": p.get("gold_state"),
            "gold_response": p.get("gold_response"),
            "candidate": r.get("response"),
            "human_label": "",
            "human_error_tags": [],
            "human_note": "",
        })
    out_path.write_text(json.dumps({"rows": out_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    key_path = out_path.with_name(out_path.stem + ".arm_key.json")
    key_path.write_text(json.dumps(anon, indent=2), encoding="utf-8")
    print(f"audit export: {len(out_rows)} rows -> {out_path} (key sealed in {key_path.name})")
    return out_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--split", default="smoke")
    ap.add_argument("--export-audit", action="store_true")
    ap.add_argument("--run-judge", action="store_true", help="blind LLM judge over answers (needs judging.model credentials)")
    ap.add_argument("--audit-n", type=int, default=100)
    args = ap.parse_args()
    from .study_common import BACKEND_DIR, load_config

    cfg = load_config(args.config)
    out_dir = BACKEND_DIR / "results" / args.run_id
    if args.run_judge:
        run_judge_split(cfg, args.split, args.run_id)
    if args.export_audit:
        export_audit(
            BACKEND_DIR / "data" / "processed" / "token_study" / f"prompts_{args.split}.jsonl",
            out_dir / f"answers_{args.split}.jsonl",
            out_dir / f"human_audit_{args.split}.json",
            seed=int(cfg["study"]["run_seed"]),
            n=args.audit_n,
        )
    else:
        print("LLM judge runs are configured but require judging.model credentials; "
              "use --export-audit for the blinded human-audit export (no credentials needed).")


if __name__ == "__main__":
    main()
