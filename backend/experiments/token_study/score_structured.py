from __future__ import annotations

import argparse
import json
from collections import Counter

from .study_common import BACKEND_DIR, load_config


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if isinstance(value, str):
        return " ".join(value.casefold().split())
    return value


def parse_state(text: str | None) -> tuple[dict | None, str]:
    """Extract the `state` object from a JSON answer. Returns (state, status)."""
    if not text:
        return None, "empty"
    try:
        obj = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None, "invalid_json"
        try:
            obj = json.loads(text[start : end + 1])
        except Exception:
            return None, "invalid_json"
    if not isinstance(obj, dict) or "state" not in obj or not isinstance(obj["state"], dict):
        return None, "invalid_json"
    return canonical(obj["state"]), "ok"


def flatten_slots(state: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for k, v in state.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            flat.update(flatten_slots(v, key))
        elif isinstance(v, list):
            flat[key] = " | ".join(canonical(x) if isinstance(x, str) else json.dumps(canonical(x)) for x in v)
        elif v is None or (isinstance(v, str) and v == ""):
            continue  # absent/empty: scored by the source-aware rule below
        else:
            flat[key] = v if not isinstance(v, str) else canonical(v)
    return flat


def score_pair(gold_state: dict | None, pred_text: str | None) -> dict:
    gold = canonical(gold_state or {})
    pred, status = parse_state(pred_text)
    if status != "ok" or pred is None:
        return {"em": 0.0, "slot_p": 0.0, "slot_r": 0.0, "slot_f1": 0.0, "parse": status}
    em = 1.0 if pred == gold else 0.0
    gf, pf = flatten_slots(gold), flatten_slots(pred)
    # Absent and empty slots: a predicted empty slot for an absent gold slot is
    # not a false positive; a missing gold-filled slot is a false negative.
    tp = sum(1 for k, v in pf.items() if k in gf and gf[k] == v)
    fp = sum(1 for k in pf if k not in gf)
    fn = sum(1 for k in gf if k not in pf or pf[k] != gf[k])
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {"em": em, "slot_p": round(prec, 6), "slot_r": round(rec, 6), "slot_f1": round(f1, 6), "parse": "ok"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--split", default="smoke")
    args = ap.parse_args()
    load_config(args.config)  # validated for provenance even though unused in pure scoring
    out_dir = BACKEND_DIR / "results" / args.run_id
    prompts = {json.loads(line)["pair_id"]: json.loads(line) for line in
               (BACKEND_DIR / "data" / "processed" / "token_study" / f"prompts_{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    scored, counts = [], Counter()
    for line in (out_dir / f"answers_{args.split}.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        gold = (prompts.get(a["pair_id"]) or {}).get("gold_state")
        s = score_pair(gold, a.get("response"))
        counts[s["parse"]] += 1
        scored.append({**a, **s})
    out = out_dir / f"structured_scores_{args.split}.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in scored) + "\n", encoding="utf-8")
    print(f"structured scores -> {out} ({len(scored)} rows, parse={dict(counts)})")


if __name__ == "__main__":
    main()
