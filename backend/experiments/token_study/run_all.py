from __future__ import annotations

import argparse
import json

from .run_answers import run_split as run_answers_split
from .run_compression import run_split as run_compression_split
from .study_common import BACKEND_DIR, assert_no_demo_contamination, build_manifest, config_sha256, git_sha, groq_keys, load_config, utcnow


def _write_manifest(cfg: dict, run_id: str, split: str, extra: dict) -> str:
    run_dir = BACKEND_DIR / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(cfg, run_id, {
        "split": split,
        "tokenizer_note": "provider usage authoritative when present; else tiktoken counts labelled estimates",
        **extra,
    })
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return str(run_dir / "manifest.json")


def run_all(cfg: dict, split: str, run_id: str, mock_answers: bool, arms: str) -> None:
    _write_manifest(cfg, run_id, split, {
        "git_sha": git_sha(), "config_sha256": config_sha256(cfg),
        "mock_answers": mock_answers, "arms": arms, "created_utc": utcnow(),
        "provider_keys_n": len(groq_keys()) if not mock_answers else 0,
    })
    run_compression_split(cfg, split, [a.strip() for a in arms.split(",") if a.strip()], run_id)
    assert_no_demo_contamination(BACKEND_DIR / "results" / run_id)
    run_answers_split(cfg, split, run_id, mock_answers=mock_answers)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--split", required=True, choices=["smoke", "dev", "test"])
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mock-answers", action="store_true")
    ap.add_argument("--arms", default="none,llmlingua2,llmlingua2_protected,heuristic")
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.split == "test" and not cfg["study"].get("locked_test"):
        raise ValueError("refusing test run: study.locked_test is not true (freeze first)")
    if args.split == "test" and args.mock_answers:
        raise ValueError("refusing test run with --mock-answers: mocks can never enter a locked result")
    run_all(cfg, args.split, args.run_id, args.mock_answers, args.arms)
    print(f"run_all {args.split} complete. Next: score_structured, analyze, render_report.")


if __name__ == "__main__":
    main()
