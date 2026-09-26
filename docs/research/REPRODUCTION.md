# REPRODUCTION — LLMLingua-2 baseline readiness (Stage C)

Date: 2026-09-26. Run slot: `smoke-g2-001` (manifest in `backend/results/smoke-g2-001/manifest.json`).

## Environment (command + result)

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[compression,eval,dev]"
python -m pip freeze  # archived per-run in each run manifest (packages list)
```

Recorded this session: `llmlingua 0.2.2`, `torch 2.14.0+cpu`,
`transformers 5.17.0`, `tiktoken 0.14.0`, Python 3.13.3, Windows CPU-only.
Checkpoint: `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`
(the paper's LLMLingua-2-small; downloads once to the HF cache, ~700MB).

## G2 smoke result (measured, synthetic prompts)

- 20 synthetic Hinglish task dialogues → 20 rendered prompts (stable template,
  compressible history only) → 260 compression rows across
  `none / llmlingua2 / llmlingua2_protected / heuristic × {0.90, 0.70, 0.50, 0.30}`.
- Gate `compression-smoke`: **PASS**. 260/260 `ok`, **0 fallbacks, 0 errors**;
  every protected placeholder reinjected byte-for-byte.
- Aggregate kept ratio: A0 `1.00`, A1 `0.879`, A2 `0.877`, A3 `0.988`.
  The trained arms compress measurably below A0 on code-mixed history text.
- End-to-end plumbing (`--mock-answers` → structured scoring → bootstrap
  analysis → figures): **PASS (plumbing only)**. 13 arm×rate rows, 0 failures,
  2 figures rendered. Mock outputs are labelled `mock-plumbing` and can never
  enter a result (enforced by `run_all` refusals + gate checks).

## Upstream reproduction (MeetingBank/LongBench/GSM8K scripts)

**Not run — blocked, not skipped.** The official evaluation path
(`experiments/llmlingua2/evaluation/`) scores downstream answers from an LLM,
and no answer-model provider credentials exist in this environment
(no `backend/.env`, no provider env vars). Reproducing published numbers also
needs the MeetingBank-derived eval inputs. What IS validated instead:
real library import, real checkpoint load, output/input alignment on batched
calls, monotonic rate control (0.3→0.9 kept fractions verified live during
development), and protected-span survival via `force_tokens` + digit
reservation. Deviation from the plan: bert-base-multilingual checkpoint
instead of xlm-roberta-large (one config line to upgrade; recorded in
`docs/research/DECISIONS.md`).

## Reproduce this smoke yourself

```powershell
cd C:\RM_Project\backend
$env:PYTHONPATH = "src;."
python -m experiments.token_study.run_compression --split smoke --run-id <NEW_ID>
python -m experiments.token_study.verify_run --run-id <NEW_ID> --gate compression-smoke
```

Requires `data/processed/token_study/{examples.jsonl,splits.json,prompts_smoke.jsonl}`
(local synthetic fixture, gitignored) and the `[compression]` extra.
