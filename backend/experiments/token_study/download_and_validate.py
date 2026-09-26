from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import urllib.request
from collections import Counter
from pathlib import Path

from .schemas import SourceExample
from .study_common import (
    BACKEND_DIR,
    OFFICIAL_URL_ALLOWLIST,
    append_jsonl,
    assert_official_url,
    load_config,
    sha256_file,
    utcnow,
)

RAW_BASE = BACKEND_DIR / "data" / "raw" / "token_study"
PROCESSED_BASE = BACKEND_DIR / "data" / "processed" / "token_study"


def download_official(url: str, dest_dir: Path) -> Path:
    assert_official_url(url)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = url.rstrip("/").rsplit("/", 1)[-1] or "archive"
    dest = dest_dir / fname
    if dest.exists():
        print(f"immutable raw archive already present: {dest} (never overwritten)")
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "code-mixed-gateway-research"})
    with urllib.request.urlopen(req, timeout=300) as r, dest.open("wb") as fh:
        shutil.copyfileobj(r, fh)
    return dest


def write_manifest(cfg: dict, archive: Path | None, revision: str, out: Path) -> dict:
    manifest = {
        "source_name": cfg["data"]["source_name"],
        "source_url": cfg["data"]["source_url"],
        "source_revision": revision,
        "raw_sha256": sha256_file(archive) if archive and archive.exists() else None,
        "archive_name": archive.name if archive else None,
        "download_utc": utcnow(),
        "allowlist": list(OFFICIAL_URL_ALLOWLIST),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def summarize_examples(examples: list[SourceExample]) -> dict:
    domains = Counter(e.domain for e in examples)
    mixes = Counter()
    turn_counts = []
    for e in examples:
        text = " ".join(t.text for t in e.history) + " " + e.final_user_turn
        import re

        dev = bool(re.search(r"[\u0900-\u097F]", text))
        roman = bool(re.search(r"[A-Za-z]", text))
        mixes["mixed" if dev and roman else ("devanagari" if dev else ("romanized" if roman else "unknown"))] += 1
        turn_counts.append(len(e.history))
    return {
        "n_examples": len(examples),
        "domains": dict(domains),
        "script_mix": dict(mixes),
        "history_turns_min": min(turn_counts) if turn_counts else 0,
        "history_turns_median": sorted(turn_counts)[len(turn_counts) // 2] if turn_counts else 0,
    }


def build_splits(
    dialogue_ids: list[str],
    cfg: dict,
    phenomena: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Deterministic dialogue-level splits. The locked test is drawn from the
    configured test phenomenon up to test_n (cost-bounded); dev/smoke come
    from the remaining pool. No dialogue appears in two splits."""
    rng = random.Random(int(cfg["data"]["split_seed"]))
    test_phen = cfg["data"].get("test_phenomenon", "")
    test_n = int(cfg["data"].get("test_n", 10**9))
    smoke_n = int(cfg["data"]["smoke_n"])
    dev_n = int(cfg["data"]["dev_n"])
    ids = sorted(set(dialogue_ids))
    rng.shuffle(ids)
    test_pool = [d for d in ids if phenomena and phenomena.get(d) == test_phen] if test_phen else list(ids)
    test = test_pool[:test_n]
    rest = [d for d in ids if d not in set(test)]
    smoke = rest[:smoke_n]
    dev = [d for d in rest[smoke_n:] if d not in smoke][:dev_n]
    return {"smoke": smoke, "dev": dev, "test": test}


def validate_examples(rows: list[dict], revision: str) -> tuple[list[SourceExample], list[dict]]:
    """Validate raw rows into SourceExample; returns (valid, exclusion_table)."""
    valid: list[SourceExample] = []
    excluded: list[dict] = []
    seen_dialogues: set[str] = set()
    for i, row in enumerate(rows):
        try:
            ex = SourceExample.model_validate({**row, "source_revision": revision})
        except Exception as e:
            excluded.append({"index": i, "reason": f"schema: {str(e)[:160]}"})
            continue
        if not ex.history or not ex.final_user_turn.strip():
            excluded.append({"index": i, "reason": "empty_history_or_final_turn"})
            continue
        if ex.gold_state is None and (ex.gold_response or "").strip() == "":
            excluded.append({"index": i, "reason": "no_gold_output"})
            continue
        seen_dialogues.add(ex.source_dialogue_id)
        valid.append(ex)
    return valid, excluded


def write_inventory(examples: list[SourceExample], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["dialogue_id_hash", "domain", "turn_index", "history_turns", "chars", "script_mix"])
        import hashlib

        for e in examples:
            text = " ".join(t.text for t in e.history) + " " + e.final_user_turn
            import re

            dev = bool(re.search(r"[\u0900-\u097F]", text))
            roman = bool(re.search(r"[A-Za-z]", text))
            mix = "mixed" if dev and roman else ("devanagari" if dev else ("romanized" if roman else "unknown"))
            w.writerow([
                hashlib.sha256(e.source_dialogue_id.encode()).hexdigest()[:16],
                e.domain,
                e.turn_index,
                len(e.history),
                len(text),
                mix,
            ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--from-jsonl", default=None, help="adapter input: raw rows JSONL (schema-checked, never trusted)")
    ap.add_argument("--revision", default="unknown")
    args = ap.parse_args()
    cfg = load_config(args.config)
    url = cfg["data"]["source_url"]
    if url.startswith("FILL"):
        raise ValueError("data.source_url is unfilled — set the verified official release URL in config.yaml first")

    RAW_BASE.mkdir(parents=True, exist_ok=True)
    PROCESSED_BASE.mkdir(parents=True, exist_ok=True)

    archive: Path | None = None
    if args.from_jsonl:
        # Adapter path: owner-supplied conversion of the official release into
        # raw rows; every row is schema-validated below, nothing trusted blindly.
        src = Path(args.from_jsonl)
        rows = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
        archive = src
        revision = args.revision
    else:
        archive = download_official(url, RAW_BASE / (args.revision or "v1"))
        raise ValueError(
            f"downloaded {archive} — no built-in extractor for this release. "
            "Inspect the archive, write a small adapter emitting raw-row JSONL, "
            "and re-run with --from-jsonl + --revision. Transformations belong in adapters, not here."
        )

    manifest = write_manifest(cfg, archive, revision, BACKEND_DIR / "data" / "raw" / "token_study" / "MANIFEST.json")
    valid, excluded = validate_examples(rows, revision)
    ex_path = PROCESSED_BASE / "examples.jsonl"
    if ex_path.exists():
        ex_path.unlink()
    for e in valid:
        append_jsonl(ex_path, e.model_dump())
    exc_path = PROCESSED_BASE / "exclusions.json"
    exc_path.write_text(json.dumps(excluded, indent=2), encoding="utf-8")
    write_inventory(valid, PROCESSED_BASE / "inventory.csv")
    splits = build_splits([e.source_dialogue_id for e in valid], cfg,
                          {e.source_dialogue_id: e.phenomenon for e in valid})
    (PROCESSED_BASE / "splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
    report = {
        "manifest": manifest,
        "summary": summarize_examples(valid),
        "n_excluded": len(excluded),
        "exclusion_reasons": dict(Counter(x["reason"].split(":")[0] for x in excluded)),
        "splits": {k: len(v) for k, v in splits.items()},
    }
    (PROCESSED_BASE / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:2000])


if __name__ == "__main__":
    main()
