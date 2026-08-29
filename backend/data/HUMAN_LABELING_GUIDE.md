# Human-Labeled Seed v1 — Guide (placeholder until real data)

Currently the benchmark/calibration are synthetic (bench-_/pad-_). This file
documents how to replace them with real, consented human data.

## What to collect (target 30–50 rows for v1)

- Real Hinglish queries (romanized Hindi + English mid-sentence code-switch)
- Anonymized at collection time: no names, phones, emails, group IDs
- Each row: `id`, `original` (Hinglish), `reference_answer` (checkable), `task_type` (factual/arithmetic/logic/support/code), `lang_tag=hi-en`, `is_synthetic=false`
- Consent: user told anonymized query may be used for research; lightweight ethics sign-off from supervisor in week 1.

## Where it lives

- `backend/data/seed_human.jsonl` — committed placeholder (5 rows) with `is_synthetic:false`
- `backend/data/benchmark_human.jsonl` — future expanded set (ignored, like `benchmark.jsonl`)
- Pipeline: `src/gateway/modules/m1_pipeline/pipeline.py:build_synthetic_benchmark` remains synthetic; human rows are merged in eval via `m7_eval` if present.

## How to graduate from synthetic

1. Collect 30–50 anonymized queries via Telegram bot pilot (or friends/group chats with consent).
2. Add to `seed_human.jsonl`, run `python -m gateway.modules.m1_pipeline.pipeline` to regenerate benchmark, or manually curate `benchmark_human.jsonl`.
3. Re-run `python -m gateway.modules.m10_train.distill` and recalibrate (`POST /v1/calibration/ingest`).
4. Update `calibration.meta.json` and `healthz` bench_n/pad_n — is_real will flip to true via bench rows.

## Status

Placeholder file exists; real collection starts with pilot (week 10). See `seed_human.jsonl`.
