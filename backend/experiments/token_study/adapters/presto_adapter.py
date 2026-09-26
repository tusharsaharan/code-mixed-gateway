from __future__ import annotations

"""PRESTO v1 (CC BY 4.0) → raw-row JSONL adapter (versioned transformation).

Reads the locally extracted Hindi files, keeps rows with >= minimum_context_turns
previous turns, parses `targets` ("Intent ( slot « value » ...)") into gold_state.
Writes raw rows for download_and_validate --from-jsonl (which schema-checks
every row; nothing here is trusted downstream).
"""
import argparse
import json
import re
from pathlib import Path

from ..study_common import BACKEND_DIR, load_config

RAW_DIR = BACKEND_DIR / "data" / "raw" / "token_study" / "presto-v1"

TARGET_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*(?:\((.*)\))?\s*$", re.DOTALL)
SLOT_RE = re.compile(r"([\w]+)\s*[«‹<]\s*(.*?)\s*[»›>]", re.DOTALL)
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def parse_targets(targets: str) -> tuple[str, dict]:
    m = TARGET_RE.match(targets or "")
    if not m:
        raise ValueError(f"unparseable targets: {targets[:100]!r}")
    intent, body = m.group(1), m.group(2) or ""
    slots = {k: v for k, v in SLOT_RE.findall(body)}
    return intent, slots


def script_mix_of(text: str) -> str:
    dev = bool(_DEVANAGARI.search(text))
    roman = bool(re.search(r"[A-Za-z]", text))
    if dev and roman:
        return "mixed"
    if dev:
        return "devanagari"
    if roman:
        return "romanized"
    return "unknown"


def adapt_file(path: Path, min_turns: int, revision: str, locale: str | None = "hi-IN") -> tuple[list[dict], dict]:
    rows: list[dict] = []
    skipped: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        md = r.get("metadata", {})
        if locale and md.get("locale") != locale:
            skipped["other_locale"] = skipped.get("other_locale", 0) + 1
            continue
        turns = md.get("previous_turns", []) or []
        if len(turns) < min_turns:
            skipped["short_context"] = skipped.get("short_context", 0) + 1
            continue
        history = []
        for t in turns:
            uq = (t.get("user_query") or "").strip()
            rp = (t.get("response_text") or "").strip()
            if uq:
                history.append({"role": "user", "text": uq})
            if rp:
                history.append({"role": "assistant", "text": rp})
        if not history:
            skipped["empty_history"] = skipped.get("empty_history", 0) + 1
            continue
        try:
            intent, slots = parse_targets(r.get("targets", ""))
        except ValueError:
            skipped["unparseable_targets"] = skipped.get("unparseable_targets", 0) + 1
            continue
        full_text = " ".join([h["text"] for h in history] + [r.get("inputs", "")])
        rows.append({
            "source_dialogue_id": str(md.get("example_id")),
            "turn_index": len(turns),
            "domain": intent,
            "history": history,
            "final_user_turn": r.get("inputs", ""),
            "gold_state": {"intent": intent, "slots": slots},
            "gold_response": None,
            "script_mix": script_mix_of(full_text),
            "locale": md.get("locale", ""),
            "phenomenon": md.get("linguistic_phenomena", ""),
        })
    return rows, {"file": path.name, "kept": len(rows), "skipped": skipped, "revision": revision}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--revision", default="presto-v1")
    ap.add_argument("--locale", default="hi-IN", help="keep only this locale (empty = all)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config(args.config)
    min_turns = int(cfg["data"]["minimum_context_turns"])
    all_rows: list[dict] = []
    report = []
    for fname in ("presto_dev.jsonl",
                  "test_partitions_hi-IN_test.jsonl",
                  "test_partitions_hi-IN_hi-IN_code-mixing_test.jsonl"):
        rows, rep = adapt_file(RAW_DIR / fname, min_turns, args.revision, locale=args.locale or None)
        all_rows.extend(rows)
        report.append(rep)
    # de-duplicate on example_id (code-mixing rows repeat inside hi-IN test)
    seen, uniq = set(), []
    for r in all_rows:
        if r["source_dialogue_id"] not in seen:
            seen.add(r["source_dialogue_id"])
            uniq.append(r)
    out = Path(args.out) if args.out else RAW_DIR / "presto_raw_rows.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in uniq) + "\n", encoding="utf-8")
    print(json.dumps({"files": report, "total": len(all_rows), "unique": len(uniq), "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
