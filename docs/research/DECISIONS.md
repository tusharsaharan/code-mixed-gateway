# P0 study decisions (Stage A freeze)

Date: 2026-09-26. Branch: `shivam`. Source of truth: `RESEARCH_IMPLEMENTATION_PLAN.md`.
This file is committed BEFORE any full-test run, per plan Stage A.3.

## 1. P0 scope (locked)

Evaluation study only. Registered primary metric: **structured dialogue-state
exact match (EM)** with slot micro-F1 secondary; response-judge score tertiary.
Non-inferiority margin: **-0.05 absolute** on `score_variant - score_A0`
(lower 95% dialogue-clustered paired-bootstrap bound, 10,000 replicates,
seed 20260926). Protected-span recall bar: lower 95% CI >= 0.995.
Rates (requested kept): {0.90, 0.70, 0.50, 0.30}. Arms: A0 none, A1 real
LLMLingua-2, A2 LLMLingua-2 + protected spans, A3 heuristic (comparator only).
`delta = 0.05`. "No loss" is never declared from a p-value alone.

Out of P0 (untouched, Stage E only): conformal router, reasoning budgets,
live bot/pilot, GRPO/DPO training, HF release. They must not block P0.

## 2. Models and checkpoint

- Compressor: `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank`
  via the official `llmlingua` package (`use_llmlingua2=True`, CPU).
  Rationale (decided, measurable): the plan's config names the xlm-roberta-large
  checkpoint, but the bert-base-multilingual checkpoint is the paper's own
  LLMLingua-2-small, multilingual by construction, CPU-runnable on free-tier
  hardware, and already installed + verified live in this repo
  (`m2_compressor/llmlingua2.py`, 9 passing tests). Deviation recorded here,
  not hidden: checkpoint differs from plan §11; upgrade path is one config line.
- Answer model / judge model / provider / pricing snapshot: FILL_AT_RUN_TIME.
  **No credentials exist in this environment** (no `backend/.env`, no provider
  env vars, dry-run defaults). Answer and judge runs are therefore BLOCKED
  until the owner supplies a provider, model snapshot, and price sheet.
  `run_answers.py` ships with an explicit `--mock-answers` plumbing mode that
  labels every record `answer_model="mock-plumbing"`; gates refuse to certify
  any result from it. Mock outputs can never enter `summary.json`.

## 3. Dataset decision (RESOLVED 2026-09-26: PRESTO pivot)

X-RiSAWOZ attempt logged: precog page (HTTP 200) has no download/license;
ACL paper page links no repo/data; HF search empty. Per plan §9, pivoting to
**PRESTO v1** (`google-research-datasets/presto`, CC BY 4.0):
direct download `https://storage.googleapis.com/gresearch/presto/presto_v1.zip`
(416MB, sha256 `1fc67169…cca2167f`), 550K+ human task-oriented conversations
with structured semantic parses as gold and explicit `code-mixing` partitions.
Locked test: **500 hi-IN code-mixing dialogues** (all `code-mixing`
phenomenon; script `mixed` 397 / `devanagari` 103); dev 150 hi-IN; smoke 20.
Script audit finding (recorded deviation): PRESTO Hindi is Devanagari+English
(0 romanized rows in 5,804 code-mixing items) — the romanized-Hinglish stratum
is therefore covered later via GupShup/judge-scored summaries, not here.
`gold_response` is absent in PRESTO, so the response-judge secondary metric
drops out; human audit validates structured outputs instead (deviation noted).
Unit of split: `metadata.example_id` (independent items, no shared dialogue).

## 3b. Provider, models, pricing (2026-09-26)

- Provider: Groq (`https://api.groq.com/openai/v1`), key in gitignored
  `backend/.env` as `GROQ_API_KEY`. **Correction (2026-09-26): the first two
  keys were never broken — my `urllib` test client was blocked by Cloudflare
  bot management (HTTP 403 + `error code: 1010` body). Retest with a normal
  TLS fingerprint returns 200 with 11 models. Lesson recorded: all provider
  calls use httpx with a browser-like UA (`run_answers.py`).
  Current key verified live: models 200, both study models listed.
- Answer model: `openai/gpt-oss-120b`; judge model: `openai/gpt-oss-20b`
  (both with published per-MTok list prices on
  `https://console.groq.com/docs/models`, accessed 2026-09-26: 0.15/0.60 and
  0.075/0.30 USD; Llama 3.1/3.3 listed as ContactSales-enterprise, hence the
  gpt-oss choice). Recorded in `config.yaml` + run manifests.
- Cost estimate for locked test (500×13) + dev (150×13): under $5 at these rates.

## 4. Measurement and analysis rules (locked)

- Independent variable is the ACHIEVED kept ratio (measured post-reinjection),
  never the requested rate. Tokenizer: provider usage when available (absent
  now) else `tiktoken`, always labelled with source; numerator/denominator
  never mixed across tokenizers.
- Design is paired on `pair_id = sha256(source|dialogue|turn|template)[:16]`;
  bootstrap resamples whole dialogues (PCG64, seed from config).
- Failures/fallbacks are rows, never deletions (`fallback_original` status,
  CONSORT-style flow table). Missing provider usage => cost rows labelled
  estimates or excluded from the cost primary metric.
- Records: append-only JSONL (pyarrow is not installed; parquet compaction
  deferred with this note). Resume key: (pair_id, arm, rate, model, config_sha).
- Safe-rate rule per plan §18.3 verbatim, applied per predeclared stratum;
  "no safe rate" is a reportable outcome.

## 5. Existing-code corrections (P0 honesty, implemented alongside)

- `HinglishEvaluator._task_success` (string similarity) is NOT task accuracy:
  relabelled as a lexical diagnostic wherever shown; structured/blinded
  scoring lives only in the experiment package (blocked on judge+humans).
- Simulation branches: `is_simulated` flags stay and now mean exactly
  "library/weights absent OR mock path used"; with `llmlingua` installed the
  llmlingua2 curve point is measured. `/v1/eval/*` responses gain explicit
  dataset/run/provenance fields; experiment outputs live under
  `results/<run_id>/`, never mixed with demo data (`research_mode` guard).
- Calibration/budget dashboard figures remain engineering scaffolding until
  fed by real held-out outputs; they are not P0 evidence.

## 6. Protocol fixes from smoke (software, pre-freeze — allowed)

- gpt-oss reasons before answering: `max_output_tokens: 256` truncated 209/260
  smoke answers (148 empty at exactly 256 tokens). Fix: 1024 + low
  reasoning effort via `answering.extra_body`. Changed before any dev/test
  run; smoke data is tuning-eligible by design.
- Provider calls require browser-like TLS fingerprint (Cloudflare 1010 on
  urllib); httpx + Mozilla UA verified 200.
- Groq 429 storms under sequential fire: honor `Retry-After`, exp backoff,
  `max_retries: 4`, `pacing_seconds: 1.0`; distinct `rate_limited` status +
  `error_note` on every failed row. Changed pre-freeze, recorded here.
- G1 mechanical pre-check (2026-09-26): 20/20 smoke prompts well-formed
  (shell sections byte-identical, gold present, turn roles, Devanagari
  present). Human bilingual sign-off still owed before freeze counts as human-gated.

## 6. Deliverables status

Shipped now: this file, `config.example.yaml` + ignored `config.yaml`,
full `experiments/token_study/` package with gate-enforced CLIs, unit tests,
G2 compressor smoke evidence (real library+checkpoint, synthetic prompts,
labelled non-evidence), `REPRODUCTION.md`, `DATA_CARD.md` (blocked attempt
recorded), `RESULTS_NOT_RUN.md` with the exact unblock list. `RESEARCH.md`
is deliberately NOT written (plan §19: no fabricated results).
