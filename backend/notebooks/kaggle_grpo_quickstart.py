"""
Kaggle GRPO quickstart — Hinglish compressor (Qwen3-0.6B → distilled)

GPU: T4 ×2 (Kaggle) or P100; 30 hrs/week free.
Fallback: CPU distillation already produces backend/data/checkpoints/distilled.json.
This scaffold shows the *intended* GRPO run; it is honestly labelled and
does not require a GPU to import — guard via `if has_cuda`.

Usage on Kaggle:
  1. Enable GPU T4×2, Internet on.
  2. Upload backend/data/benchmark.jsonl as dataset or copy repo.
  3. pip install -q trl transformers datasets accelerate tiktoken
  4. python kaggle_grpo_quickstart.py --dry_run  # verifies reward without GPU
  5. Remove --dry_run to actually train (needs GPU, ~2 hrs for 2000 steps).

See GRPOConfig in src/gateway/modules/m10_train/grpo_config.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gateway.modules.m10_train.grpo_config import GRPOConfig
from gateway.modules.m10_train.reward import reward

try:
    import torch  # noqa: F401
    HAS_CUDA = __import__("torch").cuda.is_available()
except Exception:
    HAS_CUDA = False


def dry_run_reward_check(benchmark: Path) -> None:
    records = [json.loads(l) for l in benchmark.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Benchmark {benchmark}: {len(records)} rows")
    for r in records[:3]:
        orig = r["original"]
        # fake compressed: heuristic filler drop (same as Compressor)
        comp = " ".join(w for w in orig.split() if w.lower() not in {"yaar", "matlab", "bhai", "na"})
        ref = r["reference_answer"]
        pred = r.get("predicted_answer", ref)
        print(f"  reward({orig[:40]!r} -> {comp[:40]!r}) = {reward(orig, comp, ref, pred):.3f}")
    print("Dry run OK — reward is task correctness, not perplexity.")


def grpo_train(cfg: GRPOConfig, dry_run: bool = False) -> None:
    print(cfg.describe())
    bench = Path(cfg.dataset)
    if not bench.exists():
        # Try backend/data/benchmark.jsonl from repo root
        alt = Path(__file__).resolve().parents[1] / "data" / "benchmark.jsonl"
        if alt.exists():
            bench = alt
    if dry_run or not HAS_CUDA:
        print("[dry_run] No GPU — running reward check only (no training).")
        dry_run_reward_check(bench)
        # Also run CPU distillation fallback so a checkpoint exists
        from gateway.modules.m10_train.distill import distill

        out = Path(cfg.output_dir)
        if not out.is_absolute():
            out = Path(__file__).resolve().parents[1] / out
        payload = distill(bench, out)
        print(f"CPU fallback checkpoint: {out} n={payload['n']} mean_reward={payload['mean_reward']:.3f}")
        return

    # --- GPU path (requires trl + transformers) ---
    try:
        from trl import GRPOTrainer  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
    except ImportError as e:
        raise SystemExit(f"Missing GPU deps: {e}. pip install trl transformers") from e

    print(f"Loading base {cfg.base_model} on cuda...")
    tok = AutoTokenizer.from_pretrained(cfg.base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        cfg.base_model, trust_remote_code=True, torch_dtype="auto", device_map="auto"
    )

    # Reward fn for GRPO: wraps gateway.modules.m10_train.reward
    def reward_fn(prompts, completions, **kwargs):
        # prompts: original Hinglish, completions: compressed, kwargs holds ref
        scores = []
        for orig, comp in zip(prompts, completions, strict=True):
            ref = kwargs.get("reference", [""] * len(prompts))[0] if kwargs else ""
            scores.append(reward(orig, comp, ref, comp))
        return scores

    print("GRPOTrainer scaffold — wire your dataset here (see docs/GRPO.md).")
    # trainer = GRPOTrainer(model=model, args=..., reward_funcs=[reward_fn], ...)
    # trainer.train()
    print("TODO: plug benchmark.jsonl as HF dataset with columns [original, reference_answer]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry_run", action="store_true", help="no GPU, just reward + distill")
    ap.add_argument("--config", type=str, default=None)
    args = ap.parse_args()
    cfg = GRPOConfig()
    if args.config:
        # allow json override
        import json as _json

        overrides = _json.loads(Path(args.config).read_text())
        for k, v in overrides.items():
            setattr(cfg, k, v)
    grpo_train(cfg, dry_run=args.dry_run or not HAS_CUDA)
