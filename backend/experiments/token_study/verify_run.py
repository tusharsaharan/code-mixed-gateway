from __future__ import annotations

import argparse
import json

from .study_common import BACKEND_DIR, load_config, read_jsonl

GATES = ("compression-smoke", "end-to-end-smoke", "dev-freeze", "final")


def check_compression_smoke(run_dir, cfg: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    rows = read_jsonl(run_dir / "compression_smoke.jsonl")
    if not rows:
        return False, ["no compression_smoke.jsonl rows"]
    llm2 = [r for r in rows if r["arm"] in ("llmlingua2", "llmlingua2_protected")]
    if not llm2:
        return False, ["no llmlingua2 arm rows in smoke"]
    fallback = [r for r in llm2 if r["compression_status"] != "ok"]
    if fallback:
        notes.append(f"{len(fallback)}/{len(llm2)} llmlingua2 rows fell back (counted, not hidden)")
    a0 = [r for r in rows if r["arm"] == "none"]
    a1 = [r for r in llm2 if r["compression_status"] == "ok"]
    if a0 and a1:
        import numpy as np

        if not float(np.mean([r["achieved_kept_ratio"] for r in a1])) < float(
            np.mean([r["achieved_kept_ratio"] for r in a0])
        ):
            return False, ["A1 aggregate kept ratio not lower than A0"]
    mock = [r for r in llm2 if r.get("method_simulated")]
    if mock:
        return False, [f"{len(mock)} rows flagged simulated inside an llmlingua2 arm"]
    notes.append(f"smoke rows={len(rows)} arms={sorted({r['arm'] for r in rows})}")
    return True, notes


def check_end_to_end_smoke(run_dir, cfg: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    ans = read_jsonl(run_dir / "answers_smoke.jsonl")
    if not ans:
        return False, ["no answers_smoke.jsonl rows"]
    models = {r.get("model") for r in ans}
    if models == {"mock-plumbing"}:
        notes.append("answer model is mock-plumbing: plumbing validated, NOT a measurement")
        return True, notes  # plumbing gate passes; measurement gate stays shut (see below)
    missing = [r for r in ans if r.get("prompt_tokens") is None]
    if missing:
        notes.append(f"{len(missing)} rows lack provider usage (cost rows must be labelled estimates)")
    ok, sub = check_compression_smoke(run_dir, cfg)
    notes.extend(sub)
    return ok, notes


def check_final(run_dir, cfg: dict) -> tuple[bool, list[str]]:
    notes: list[str] = []
    sump = run_dir / "summary_test.json"
    if not sump.exists():
        return False, ["no summary_test.json — run analyze first"]
    s = json.loads(sump.read_text(encoding="utf-8"))
    if s.get("join_lost"):
        notes.append(f"join lost rows: {s['join_lost']} (investigated, not averaged away)")
    if s.get("join_multiple"):
        return False, [f"duplicate pairs joined: {s['join_multiple']}"]
    mock = any("mock" in str(r.get("arm", "")) for r in s.get("main_table", []))
    if mock:
        return False, ["mock rows present in final main table"]
    notes.append(f"final main rows={len(s.get('main_table', []))} failures={s.get('failure_count')}")
    return True, notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--gate", required=True, choices=GATES)
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    run_dir = BACKEND_DIR / "results" / args.run_id
    checker = {
        "compression-smoke": check_compression_smoke,
        "end-to-end-smoke": check_end_to_end_smoke,
        "dev-freeze": lambda d, c: (True, ["freeze is a human decision; run freeze --run-id after review"]),
        "final": check_final,
    }[args.gate]
    ok, notes = checker(run_dir, cfg)
    print(f"gate {args.gate}: {'PASS' if ok else 'FAIL'}")
    for n in notes:
        print(" -", n)
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
