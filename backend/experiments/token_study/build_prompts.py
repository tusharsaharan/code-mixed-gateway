from __future__ import annotations

import argparse
import hashlib
import json
import re

from .schemas import SourceExample, Turn
from .study_common import BACKEND_DIR, append_jsonl, load_config, pair_id

SYSTEM_BLOCK = (
    "SYSTEM (never compress)\n"
    "You are a task-oriented assistant. Use only the supplied dialogue context.\n"
    "Return JSON with keys `state` and `response`."
)
OUTPUT_FORMAT_BLOCK = 'OUTPUT FORMAT (never compress)\n{"state": {"intent": "...", "slots": {}}, "response": "..."}'

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


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


def render_prompt(system_instruction: str, history: list[Turn], final_user_turn: str) -> tuple[str, dict]:
    hist_lines = []
    for t in history:
        speaker = "USER" if t.role == "user" else "ASSISTANT"
        hist_lines.append(f"{speaker}: {t.text}")
    history_block = "DIALOGUE HISTORY (compressible)\n" + "\n".join(hist_lines)
    current_block = "CURRENT USER REQUEST (never compress)\nUSER: " + final_user_turn
    sys_block = "SYSTEM (never compress)\n" + system_instruction
    full = "\n\n".join([sys_block, history_block, current_block, OUTPUT_FORMAT_BLOCK])
    offsets: dict[str, list[int]] = {}
    cursor = 0
    for name, block in (
        ("system", sys_block),
        ("history", history_block),
        ("current", current_block),
        ("output_format", OUTPUT_FORMAT_BLOCK),
    ):
        start = full.index(block, cursor)
        offsets[name] = [start, start + len(block)]
        cursor = start + len(block)
    return full, offsets


def template_hash(system_instruction: str) -> str:
    canon = "|".join([SYSTEM_BLOCK, OUTPUT_FORMAT_BLOCK, system_instruction])
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def build_from_processed(processed_path, cfg: dict, split: str, out_path, allowed_dialogues: set[str] | None = None) -> list[dict]:
    """Convert validated SourceExample rows into rendered prompt records.

    Reads processed/examples.jsonl (SourceExample schema), keeps examples with
    >= minimum_context_turns history turns, renders the stable template, and
    writes prompt records + segment_map sidecar.
    """
    min_turns = int(cfg["data"]["minimum_context_turns"])
    sys_instr = cfg["prompt"]["system_instruction"]
    tver = cfg["prompt"]["template_version"]
    thash = template_hash(sys_instr)
    kept: list[dict] = []
    for line in processed_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ex = SourceExample.model_validate(json.loads(line))
        if allowed_dialogues is not None and ex.source_dialogue_id not in allowed_dialogues:
            continue
        if len(ex.history) < min_turns:
            continue
        full, offsets = render_prompt(sys_instr, ex.history, ex.final_user_turn)
        pid = pair_id(cfg["data"]["source_name"], ex.source_dialogue_id, ex.turn_index, tver)
        rec = {
            "pair_id": pid,
            "dialogue_id_hash": hashlib.sha256(ex.source_dialogue_id.encode()).hexdigest()[:16],
            "split": split,
            "source_revision": ex.source_revision,
            "domain": ex.domain,
            "script_mix": script_mix_of(full),
            "system_block": "SYSTEM (never compress)\n" + sys_instr,
            "history_block": "DIALOGUE HISTORY (compressible)\n"
            + "\n".join(f"{'USER' if t.role == 'user' else 'ASSISTANT'}: {t.text}" for t in ex.history),
            "current_block": "CURRENT USER REQUEST (never compress)\nUSER: " + ex.final_user_turn,
            "output_format_block": OUTPUT_FORMAT_BLOCK,
            "full_prompt": full,
            "segment_offsets": offsets,
            "prompt_template_hash": thash,
            "gold_state": ex.gold_state,
            "gold_response": ex.gold_response,
        }
        append_jsonl(out_path, rec)
        kept.append(rec)
    seg_path = out_path.with_name(out_path.stem + ".segment_map.json")
    seg_path.write_text(
        json.dumps({r["pair_id"]: r["segment_offsets"] for r in kept}, indent=2), encoding="utf-8"
    )
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--split", required=True, choices=["smoke", "dev", "test"])
    args = ap.parse_args()
    cfg = load_config(args.config)
    base = BACKEND_DIR / "data" / "processed" / "token_study"
    processed = base / "examples.jsonl"
    if not processed.exists():
        raise FileNotFoundError(f"no validated examples at {processed}; run download_and_validate first")
    splits_path = base / "splits.json"
    if not splits_path.exists():
        raise FileNotFoundError(f"no splits at {splits_path}; run download_and_validate first")
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    if args.split not in splits:
        raise ValueError(f"split {args.split!r} not in splits.json (keys: {sorted(splits)})")
    out = base / f"prompts_{args.split}.jsonl"
    if out.exists():
        out.unlink()
    kept = build_from_processed(processed, cfg, args.split, out, set(splits[args.split]))
    print(f"rendered {len(kept)} prompts -> {out}")


if __name__ == "__main__":
    main()
