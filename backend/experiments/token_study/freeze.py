from __future__ import annotations

import argparse
import hashlib
import json

from .study_common import BACKEND_DIR, load_config, utcnow


def main() -> None:
    """Freeze a dev run: snapshot the test split IDs + config hash into an
    immutable lock file. Human-gated: prints the lock for explicit review."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    splits = json.loads(
        (BACKEND_DIR / "data" / "processed" / "token_study" / "splits.json").read_text(encoding="utf-8")
    )
    lock = {
        "frozen_utc": utcnow(),
        "dev_run_id": args.run_id,
        "test_dialogue_ids_sha256": hashlib.sha256(
            json.dumps(sorted(splits["test"]), sort_keys=True).encode()
        ).hexdigest(),
        "test_n_dialogues": len(splits["test"]),
        "config_sha256": hashlib.sha256(
            json.dumps(cfg, sort_keys=True).encode()
        ).hexdigest(),
        "prompt_template_hash_note": "template hash recorded per prompt row; changing it invalidates results",
    }
    out = BACKEND_DIR / "results" / args.run_id / "test_lock.json"
    out.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(f"LOCKED test set ({lock['test_n_dialogues']} dialogues). Review {out}, then run test with a NEW run_id.")


if __name__ == "__main__":
    main()
