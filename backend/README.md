# Code-Mixed Gateway — Backend

Hinglish (Hindi-English code-mixed) prompt compression + conformally-calibrated cascade
routing, exposed as an OpenAI-compatible `/v1/chat/completions` endpoint.

## Modules

| #   | Module                              | File                                 | Verifies                                                                 |
| --- | ----------------------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| 1   | Data pipeline + tokenizer benchmark | `src/gateway/modules/m1_pipeline/`   | token counts across tokenizers, code-mix token inflation                 |
| 2   | Compressor                          | `src/gateway/modules/m2_compressor/` | safety-span masking, heuristic/LLM compression, fail-closed re-injection |
| 3   | Conformal calibrator                | `src/gateway/modules/m3_conformal/`  | split-conformal error-bound threshold                                    |
| 4   | Cascade router                      | `src/gateway/modules/m4_router/`     | difficulty scoring + cheap/premium dispatch                              |
| 5   | FastAPI gateway                     | `src/gateway/modules/m5_gateway/`    | OpenAI-compatible `/v1/chat/completions`                                 |
| 6   | Telegram bot + SQLite               | `src/gateway/modules/m6_telegram/`   | webhook/polling bridge + cost-savings logging                            |
| 7   | Evaluation suite                    | `src/gateway/modules/m7_eval/`       | Hinglish BLEU/ROUGE-L, token savings, span preservation, $/₹ cost        |
| 8   | Live dashboard                      | `src/gateway/modules/m8_dashboard/`  | `/v1/dashboard/*` endpoints + static HTML dashboard                      |

## Setup

```sh
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"         # or: uv sync --extra dev
# optional: real tokenizers (tiktoken + HF Qwen/Llama/Gemma) for the fairness benchmark
pip install -e ".[tokenizers]"
```

Copy `.env.example` to `.env`. With `GATEWAY_DRY_RUN=true` (default) everything runs
offline with deterministic mocks — no API keys or GPUs required.

## Run

```sh
# gateway
uvicorn gateway.modules.m5_gateway.main:app --host 127.0.0.1 --port 8000
# or
cg-gateway
```

## Tests

```sh
pytest -q tests/test_m1.py   # then m2..m6
pytest -q tests/             # all
ruff check src tests
```

## Dashboard

`GET /dashboard` — self-contained HTML dashboard (no build step) backing onto
`/v1/dashboard/stats`, `/v1/dashboard/series`, `/v1/dashboard/recent`.

## Data

- `data/seed_hinglish.jsonl` — synthetic Hinglish seed (fluff + protected placeholders).
- `data/tokenizer_report.csv` — per-tokenizer token counts (written by module 1).
- `data/calibration.jsonl` — optional calibration samples for the conformal router
  (synthetic defaults are used if absent).
