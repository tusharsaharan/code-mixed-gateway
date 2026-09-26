from __future__ import annotations

import argparse
import json
import random

from .study_common import BACKEND_DIR, load_config


def main() -> None:
    """Export N randomly sampled rendered prompts for the G1 human review gate."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--split", default="smoke")
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()
    cfg = load_config(args.config)
    rng = random.Random(int(cfg["study"]["run_seed"]))
    rows = [json.loads(line) for line in
            (BACKEND_DIR / "data" / "processed" / "token_study" / f"prompts_{args.split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    sample = rng.sample(rows, min(args.n, len(rows)))
    out = BACKEND_DIR / "results" / "prompt_audit" / f"audit_{args.split}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"prompt audit: {len(sample)} rows -> {out}. Reviewer: confirm target turn, order, code-switching, gold output.")


if __name__ == "__main__":
    main()
