# Kaggle GRPO — Hinglish Compressor

This folder is the _intended_ GPU training path for Pillar A.

- `kaggle_grpo_quickstart.py` — runnable on Kaggle T4×2 (free 30 hrs/week). `--dry_run` verifies the reward (task correctness) without GPU and falls back to CPU distillation (`data/checkpoints/distilled.json`).
- `GRPOConfig` lives in `src/gateway/modules/m10_train/grpo_config.py` (base `Qwen/Qwen2.5-0.5B-Instruct` → compressor `Qwen/Qwen3-0.6B`).
- Dataset: `backend/data/benchmark.jsonl` (50 synthetic now, `seed_human.jsonl` v1 placeholder for real data).

## On Kaggle

1. New Notebook → GPU T4×2, Internet ON.
2. Add this repo as dataset or `!git clone https://github.com/tusharsaharan/code-mixed-gateway.git`.
3. `!pip install -q trl transformers datasets accelerate tiktoken`
4. `!python backend/notebooks/kaggle_grpo_quickstart.py --dry_run`
5. Remove `--dry_run` for real GRPO (needs GPU; ~2 hrs for 2000 steps, saves to `data/checkpoints/distilled.json`).

## Fallback

If GPU unavailable or training unstable, the CPU fallback (`distill.py` rejection sampling) already produces a runnable checkpoint. The gateway's `compressor_method=auto` will use `distilled` when present, else `heuristic`.

## Pricing

`pricing.py` is single source; counts via `tiktoken` if installed else whitespace (~1.5× diff, documented).
