# Research implementation plan: token optimization without response-quality loss

**Status:** board-ready plan for an AI implementation agent.
**Primary claim to test:** Does the published prompt-compression quality/cost trade-off of LLMLingua-2 transfer to Hindi-English code-mixed task-oriented prompts?

## 0. Scope decision (non-negotiable)

This plan follows the submitted proposal, which is an **evaluation study**, not a model-training project. The required deliverable is a reproducible, measured compression-versus-quality-versus-cost study. It must not describe synthetic scores, heuristic pruning, estimated token counts, or mock model outputs as a reproduction of LLMLingua-2.

The existing gateway can support the study, but it is not evidence yet. Its current 60-row Hinglish seed is synthetic; its five-row `seed_human.jsonl` is explicitly a placeholder; the dashboard's curve can therefore not be presented as a real result. Do not change these labels unless a run manifest proves the relevant data and calls are real.

### Required study; optional product extensions

| Priority | Work | Completion criterion |
|---|---|---|
| P0 | Baseline reproduction | Real LLMLingua-2 run on its published benchmark protocol; model, data revision, command, output and score all archived. |
| P0 | New-domain experiment | Held-out code-mixed task-oriented prompts at four compression settings; genuine downstream generations and task scores. |
| P0 | Cost and statistical analysis | Actual API usage where available, dated price sheet, paired uncertainty intervals and failure analysis. |
| P1 | Protected-span fix | A pre-registered entity/code/number protection treatment compared to unprotected LLMLingua-2. |
| P2 | Conformal routing, reasoning budgets, live bot, training | Separate experiments only after P0 passes. They are not evidence for the submitted proposal and must never block P0. |

## 1. Research questions and pre-registered hypotheses

Let `x` be a complete task prompt, `c_r(x)` its compressed form at requested kept-token rate `r`, `M` a fixed answer model, and `y` the gold task output.

1. **RQ1 (transfer):** At what achieved compression level does code-mixed task success decline relative to the uncompressed prompt?
2. **RQ2 (economics):** What input-token and end-to-end API-cost reduction follows at each level, for a stated model and pricing date?
3. **RQ3 (failure mechanism):** Are losses concentrated in entities, digits, code, mixed-language spans, or dialogue-state references?
4. **RQ4 (optional):** Does protected-span handling recover quality at the same achieved rate, and what compression cost does it impose?

Primary null hypothesis at a rate `r`: `E[S(c_r(x), y) - S(x, y)] <= -delta`, where `S` is the task score and `delta = 0.05` (five percentage points). Report the effect and its 95% confidence interval; do not declare “no loss” solely because a p-value is above 0.05.

Primary success threshold: the lower 95% confidence bound of retained task score is at least 0.95 at an achieved token saving that is useful in practice (report the observed value; do not promise 15x or 20x in advance). A negative result is still a valid result if it precisely identifies the safe operating region.

## 2. Dataset recommendation and why

### Primary dataset: X-RiSAWOZ English-Hindi code-mixed split

Use the code-mixed English-Hindi portion of **X-RiSAWOZ** as the principal external evaluation corpus. It is the best fit because it is an open, human-verified, multi-domain, end-to-end task-oriented dialogue benchmark with more than 18,000 utterances per language; it has dialogue context and task state, rather than isolated social-media sentences. That means it supports a real downstream task: predict the next assistant turn and/or structured dialogue state from prior turns. The project source confirms its code-mixed English-Hindi split and open release: [X-RiSAWOZ project description](https://precog.iiit.ac.in/projects/codemix_project/).

### Why not use one Hinglish dataset alone

* **COMI-LINGUA** is a valuable CC BY 4.0 corpus (181,463 expert-annotated instances) for measuring language mix, noise, named entities and normalization robustness, but its main tasks are LID/POS/NER/MT rather than response generation. Use it as a *stress-test/characterization set*, not the primary quality metric. [Dataset and license](https://github.com/lingo-iitgn/COMI-LINGUA)
* The older **Code-Mixed Dialog** repository is a useful independent restaurant-dialogue test, but is smaller and constructed from DSTC2. Use it only as an external replication set if its license and split files allow the required use. [Repository](https://github.com/sumanbanerjee1/Code-Mixed-Dialog)
* The **Code-Mixed QA Challenge** has 1,694 Hinglish factoid QA pairs, so it is useful for a small external QA robustness check, but short questions alone cannot demonstrate meaningful prompt-token savings. [Paper/dataset description](https://www.cs.cmu.edu/~awb/papers/W18-3204.pdf)
* Do **not** scrape WhatsApp, Telegram, support tickets, or social media. A later small opt-in pilot can test external validity after ethics/consent approval; it is not a substitute for the public benchmark.

### Dataset construction specification

1. Pin exact source commit/revision, license text, download date, SHA-256, and code-mixed language split in `data/raw/MANIFEST.json`.
2. Inspect the schema before writing conversions. Build prompts from only the official train/dev/test partition; never redistribute material whose license forbids it.
3. The unit of splitting is **dialogue**, never individual turns. Keep every turn from one dialogue in exactly one split to prevent context leakage.
4. Make a locked test set of at least 300 eligible dialogues/contexts (or every eligible official test instance if smaller); use a development/calibration set of at least 150 and a smoke-test set of 20. Stratify by domain and context-length quartile. State final counts, not targets, in the paper.
5. Keep only examples with: a non-empty multi-turn context, a target assistant response or structured state, and a reasonable raw prompt length. Publish the deterministic filter script and a table showing exclusions by reason.
6. Render each example as one stable prompt template: system instruction + dialogue history + optional structured context + final user turn. Keep the template, ordering, separator tokens, and answer model fixed across variants. This is essential: compressing a bare 10-token query is not the study.
7. Use two task views when source annotations permit:
   * **Primary:** structured dialogue-state/slot exact match or slot micro-F1.
   * **Secondary:** next assistant response quality, assessed by a blinded rubric-based judge plus human audit.
8. Extract protected spans from gold context: phone/email/URL-like strings, currency/amounts, dates/times, booking IDs, named entities, JSON keys/values, code blocks, and explicitly annotated slots. Store their character offsets and normalized values.

## 3. Exact experimental arms

All variants see the same prompt template and the same fixed downstream answer model. Set temperature to 0; set a seed where the provider supports it; cap output length identically. Record any provider/model version returned by the API.

| ID | Compressor | Purpose |
|---|---|---|
| A0 | None | Uncompressed reference; required denominator. |
| A1 | LLMLingua-2 multilingual MeetingBank checkpoint | Required published-method baseline. Use the real library; `method=llmlingua2` is permitted only if library import, checkpoint load, and per-row output succeeded. |
| A2 | LLMLingua-2 + protected-span masking/reinjection | P1 targeted intervention. Mask spans with collision-proof placeholders, compress, reinject, then fail closed to original prompt if a required placeholder is lost. |
| A3 | Existing heuristic compressor | Engineering comparator only. Never call this LLMLingua-2, never use it to claim a paper reproduction. |

Requested kept-token settings: `r in {0.90, 0.70, 0.50, 0.30}`. The actual independent variable is the **achieved** kept ratio, `K = T(c_r(x)) / T(x)`, and savings `1-K`; both requested and achieved values must be reported. Rate 0.30 may be infeasible on short/entity-heavy prompts, which is a finding rather than an error.

Run A0/A1/A2 for every locked-test example. A3 is optional but should be included if already maintained. Perform the compressor baseline reproduction before the new-domain run using the upstream evaluation structure, which explicitly includes MeetingBank, LongBench, ZeroScrolls, and GSM8K evaluation scripts: [official LLMLingua evaluation script](https://github.com/microsoft/LLMLingua/blob/main/experiments/llmlingua2/evaluation/scripts/evaluate.sh). Use the official multilingual LLMLingua-2 checkpoint invocation, not a local simulated substitute: [official usage](https://github.com/microsoft/LLMLingua/blob/main/README.md).

## 4. Measurement definitions (implement exactly)

### 4.1 Token measurement

For tokenizer `v`, raw prompt tokens are `T_v(x)` and compressed tokens are `T_v(c)`. Report both:

`kept_v = T_v(c) / T_v(x)`

`token_saving_v = 1 - kept_v`

`compression_factor_v = T_v(x) / max(1, T_v(c))`

Use the downstream provider's tokenizer/returned `prompt_tokens` for billing results. Separately report `tiktoken` or model tokenizer counts for reproducibility. Do not mix tokenizers in the numerator and denominator. Measure strings after placeholder reinjection.

### 4.2 Quality

* **Structured task:** exact match after canonicalizing case, whitespace, key order, and known slot normalization; also report slot micro precision/recall/F1.
* **Response task:** a judge receives the gold response, model response, and a task-specific rubric but not the compressor arm or token count. It returns `correct / partially_correct / incorrect` and error tags. Convert to a predeclared score of `1 / 0.5 / 0`.
* **Human validation:** randomly sample at least 100 judged outputs, stratified by arm and rate. Two bilingual annotators independently label them blinded to condition. Report agreement (Cohen's kappa or Krippendorff's alpha) and judge-vs-human agreement. Adjudicate disagreements into a final analysis label.
* BLEU, ROUGE-L, embedding similarity, and text overlap are diagnostic only. They are not primary correctness measures for a support/dialogue task.

### 4.3 Protected-span safety

For required span set `P(x)`, report:

`span_recall = sum_x sum_p I(normalize(p) in normalize(c(x))) / sum_x |P(x)|`

Also calculate record-level all-span preservation and the rate of fail-closed fallback. Verify reinjected strings byte-for-byte before the answer call. A good language score does not excuse a lost amount, date, code fragment, or identifier.

### 4.4 Cost and latency

For model `m`, use provider-specific input/output price per million tokens, `p_in,m` and `p_out,m`, pinned in a dated `pricing_snapshot.json` with source URL and currency conversion source.

`C_m = (T_in * p_in,m + T_out * p_out,m) / 1,000,000`

`end_to_end_cost = compressor_cost + answer_cost + judge_cost` (report all three separately).

`cost_saving = 1 - end_to_end_cost(compressed) / end_to_end_cost(uncompressed)`

Where an API returns usage, treat that as authoritative. Otherwise label estimates as estimates and show the tokenizer/version used. Report median and p95 wall-clock latency separately for compression and answer generation. Do not claim a lower bill if compression moved cost into an uncounted compressor call.

## 5. Statistical analysis

1. The design is paired: each item is run uncompressed and under every compressor/rate. Store a `pair_id` and never compare unrelated averages alone.
2. For each arm/rate, report `n`, mean and median achieved token saving, primary task score, absolute score change from A0, relative retained score, span recall, mean/median end-to-end cost, cost saving, and latency.
3. Use a **clustered paired bootstrap by dialogue** (10,000 resamples, fixed seed) for 95% percentile confidence intervals of score change, cost saving, and span recall. Resample whole dialogues, not turns.
4. For the primary non-inferiority result, use the lower confidence bound of `score_variant - score_A0`; it must be at least `-0.05` to satisfy the predeclared five-point margin. State that this is a practical margin, not a proof of semantic equivalence.
5. Correct exploratory pairwise p-values (if reported) with Holm adjustment. Do not use statistical significance to conceal a practically harmful score difference.
6. Generate subgroup plots by domain, context-length quartile, code-mix ratio, Devanagari vs Romanized Hindi, and protected-span count. Mark subgroup results exploratory unless pre-registered and adequately powered.
7. Predefine missing/failure handling: preserve the original prompt if compression errors; retry transient API errors once with logged backoff; exclude neither failed compression nor failed answer calls silently. Report every status in the CONSORT-like flow table.

## 6. Implementation architecture and required changes

Create a new, isolated experiment package rather than modifying the production gateway until it works:

```text
backend/
  data/
    raw/                 # ignored; source manifest only is committed
    processed/           # derived records, IDs but no restricted raw data
    splits/              # deterministic dialogue-level IDs
  experiments/token_study/
    download_and_validate.py
    build_prompts.py
    protected_spans.py
    run_compression.py
    run_answers.py
    score_structured.py
    score_responses.py
    analyze.py
    render_report.py
    schemas.py
    config.example.yaml
  results/<run_id>/
    manifest.json
    records.parquet
    summary.json
    figures/
    failures.jsonl
```

### Record schema (minimum)

`run_id, pair_id, dialogue_id_hash, split, source_dataset, source_revision, domain, context_length_bin, script_mix, code_mix_ratio, protected_spans, prompt_template_hash, compressor_arm, requested_rate, achieved_kept_ratio, raw_prompt, compressed_prompt, compression_status, fallback_used, raw_tokens_provider, compressed_tokens_provider, compressor_input_tokens, compressor_output_tokens, answer_model, answer_model_version, answer_prompt_tokens, answer_completion_tokens, answer_text, gold_state, gold_response, structured_em, slot_f1, judge_label, human_label, span_recall, compressor_cost_usd, answer_cost_usd, judge_cost_usd, latency_compress_ms, latency_answer_ms, retry_count, timestamp_utc`.

Store only data permitted by the source license. Hash source dialogue IDs with a documented non-secret, dataset-specific salt if public IDs need not be exposed. Never log pilot-user text in this research artifact.

### Existing-code corrections before any result is shown

* Replace `HinglishEvaluator._task_success`, which currently uses string similarity, with task-specific structured scoring and/or blinded judgement. Its current values cannot be called accuracy or reward.
* Remove all simulation branches from research endpoints or make requests fail loudly with `is_simulated=true`. The frontend must never chart simulated data beside a real method without a prominent, separate watermark.
* Make `GET /v1/eval/*` read a signed/validated run manifest, not generic `benchmark.jsonl`. It must return dataset, run ID, n, real/synthetic status, model versions, price date, and a link/path to artifacts.
* Preserve the existing protected-span design, but test it against official-data spans and log all reinjection failures. Do not assume it is correct merely because a unit test passes on one email and currency sample.
* Keep router calibration and reasoning-budget measurements out of the P0 dashboard until they use real held-out outputs. The current calibration and budget modules are engineering scaffolding, not P0 evidence.
* Add a `research_mode` guard: production/demo data and experimental outputs cannot be mixed in the same directory or endpoint response.

## 7. Execution protocol for the AI agent

### Stage A — audit and freeze (first)

1. Read this plan, the proposal, backend README, `backend/data/HUMAN_LABELING_GUIDE.md`, compressor/evaluator/router code, and every existing test.
2. Run `git status`; preserve unrelated user work. Create no fake results and do not overwrite original source documents.
3. Add a `docs/research/DECISIONS.md` stating the exact P0 scope, registered primary metric, non-inferiority margin, models, planned rates, and dataset revision. Commit it before running the full test.
4. Make a machine-readable `config.yaml` and derive every run setting from it. Hash the config into the manifest.

### Stage B — data acquisition and validation

1. Download X-RiSAWOZ only through its documented official source. Record license and SHA-256; stop and report if access/license is unclear.
2. Write schema assertions and a data card: count dialogues/turns, domains, language/script distribution, missing fields, duplicate content, context length, and protected-span rates.
3. Build dialogue-level deterministic splits with seed 20260926. Save only IDs and split logic in source control.
4. Manually review 30 randomly sampled rendered prompts with a bilingual reviewer. Confirm the target turn, context order, code switching, and gold output are correct. Fix the builder before full runs.

### Stage C — validate the baseline before the contribution

1. Create a clean environment from `backend/pyproject.toml` plus the compression, evaluation, and dataset extras. Install the official `llmlingua` package and record `pip freeze`, OS, CPU/GPU, Python version, and model/checkpoint revision.
2. Run a 20-example smoke test. Require: real `llmlingua` import, downloaded checkpoint, output alignment, lower mean token count than A0, and all protected placeholder reinjections successful. If any fails, fix or report it; do not fall back and call it A1.
3. Reproduce one official LLMLingua-2 benchmark path as closely as practical. Document every unavoidable deviation (model provider availability, exact data version, compute). Compare to published/official outputs qualitatively and quantitatively; call it a partial reproduction if the protocol differs.
4. Archive raw logs, resulting data, and a short reproduction note. Only after this gate may the new-domain study run.

### Stage D — run the locked code-mixed experiment

1. Launch a 20-item pilot across all arms/rates. Validate cost calculations against at least five provider usage receipts and inspect outputs/errors manually.
2. Lock the test IDs and configs. Do not tune rates, templates, prompts, judge rubric, or protected-span rules using test outputs.
3. Run all arms on dev; use dev only to fix software or choose a documented final protected-span rule. Then freeze code/config version.
4. Run all locked-test records with idempotent resume support. Write one append-only row per attempted item; log retries and failures.
5. Conduct blinded judge scoring and the human audit. Keep arm labels hidden until annotations are finalized.
6. Run the analysis script from raw records only. It should fail if any row lacks a source revision, output, usage accounting, or real/synthetic status.

### Stage E — optional extensions, only after Stage D

* **Protected-span ablation:** compare A1/A2 at same requested rates.
* **Tokenizer fairness:** on the same raw/compressed prompts, compare token count inflation across relevant provider tokenizers; it is a cost characterization, not an answer-quality substitute.
* **Router:** collect cheap-vs-premium correctness labels on a separate calibration split, calibrate once, then evaluate once on a held-out test split. The current Hoeffding threshold is a useful engineering start but must not be advertised as a general conformal guarantee without a correct protocol and independent test validation.
* **Pilot:** obtain supervisor approval, consent text, retention/deletion policy, PII minimization, and a separate pilot dataset. Do not merge it into public data automatically.

## 8. Required deliverables and board presentation

The agent must leave these artifacts, all generated from the same `run_id`:

1. `REPRODUCTION.md`: command, environment, deviations, upstream result comparison.
2. `DATA_CARD.md`: provenance, license, split, transformations, representativeness and limitations.
3. `RESULTS.md`: primary table, statistical intervals, failure counts, and plain-language conclusion.
4. `results/<run_id>/manifest.json`: immutable configuration, Git SHA, dataset revision/hash, packages, model IDs, tokenizer, price snapshot, timestamps, and whether every component is real.
5. Figures (PNG + CSV data):
   * accuracy/structured-F1 versus achieved token saving, with 95% CIs;
   * end-to-end cost versus retained score (Pareto chart);
   * raw versus compressed token distributions;
   * protected-span recall/failure categories;
   * subgroup forest plot; and
   * a cost waterfall (compression, answer, judge).
6. A 10-slide presentation: problem/gap, hypothesis, data provenance, protocol, baseline reproduction, primary curve, cost curve, failure examples, limitations/ethics, conclusion/next step.
7. A one-page oral-defense factsheet containing exact `n`, achieved savings, score change and CI, cost source/date, what is real, and what remains future work.

### Mandatory result tables

**Main table:** arm × requested rate, `n`, median achieved kept ratio, token saving, structured EM/F1, response score, score delta vs A0 (95% CI), span recall, total and per-query cost, cost saving (95% CI), p50/p95 latency, failure/fallback count.

**Failure table:** category (lost amount/date/entity, code corruption, wrong state, wrong language, over-compression, API failure), count, rate, two anonymized public-dataset examples, and whether A2 fixed it.

### Claims that are allowed vs forbidden

Allowed: “On this held-out X-RiSAWOZ-derived code-mixed task prompt set, real LLMLingua-2 at the measured rate achieved X% token saving with a Y-point task-score change (95% CI…).”

Forbidden: “LLMLingua-2 gives 20x compression with no loss for Hinglish,” “the system saves X% in production,” “the curve is real” when it includes heuristic/synthetic values, or “provably safe router” without a completed, held-out calibration study.

## 9. Risks and stop conditions

| Risk | Mitigation / stop rule |
|---|---|
| Dataset does not provide enough usable long contexts or state labels | Report audit; pivot to PRESTO's structured context/code-mixing subset only after documenting license, exact filter and revised protocol. PRESTO includes native-speaker task dialogue, structured context, and explicitly marked code mixing: [documentation](https://research.google/blog/presto-a-multilingual-dataset-for-parsing-realistic-task-oriented-dialogues/). |
| Full test costs more than budget | Do a power/cost calculation from the 20-item pilot, reduce the number of *rates* before reducing held-out examples, and retain A0/A1. Report budget and all sampling decisions. |
| Downstream model changes while running | Pin model snapshot/version if possible; run all arms within a short window; record provider response model ID; never combine silently across versions. |
| Judge is biased or unstable | Use structured score as primary where available; blind judge; audit with two bilingual humans; publish agreement. |
| Compression breaks identifiers | Keep A2 fail-closed; make span recall a co-primary safety metric and show the loss honestly. |
| Reproduction differs from paper | Publish the deviation and call it partial; do not modify score labels or simulate missing dependencies. |

## 10. Completion checklist

- [ ] No dashboard or report calls synthetic/heuristic data a real LLMLingua-2 result.
- [ ] Official baseline library/checkpoint and upstream reproduction evidence are archived.
- [ ] Dataset license, revision, checksum, transformations and split IDs are recorded.
- [ ] Test set remained untouched during tuning.
- [ ] Every score has the appropriate ground truth/judge/audit provenance.
- [ ] Every cost number identifies provider/model, input/output rates, price date, token source and included stages.
- [ ] Every main result has a dialogue-clustered paired 95% CI.
- [ ] Every safety failure and fallback is counted.
- [ ] Presentation conclusions state scope and limitations precisely.

## 11. Exact configuration contract (copy this before implementation)

Create `backend/experiments/token_study/config.example.yaml` with the following shape. The working `config.yaml` is ignored by Git because it may contain provider endpoint names/keys; the redacted resolved configuration is copied to each run manifest.

```yaml
study:
  name: hinglish_prompt_compression_transfer
  run_seed: 20260926
  primary_margin_abs_score: 0.05
  bootstrap_replicates: 10000
  locked_test: true
data:
  source_name: x_risawoz
  source_url: FILL_FROM_OFFICIAL_RELEASE_ONLY
  source_revision: FILL_AFTER_DOWNLOAD
  raw_sha256: FILL_AFTER_DOWNLOAD
  language_variant: en_hi_codemixed
  unit_of_split: dialogue
  smoke_n: 20
  dev_n: 150
  test_min_n: 300
  minimum_context_turns: 2
  split_seed: 20260926
prompt:
  template_version: v1
  system_instruction: "You are a task-oriented assistant. Use only the supplied dialogue context. Return the required structured state and a concise assistant response."
  compress_system_instruction: false
  compress_final_user_turn: false
  compress_dialogue_history: true
  max_context_tokens_before_compression: 2048
compression:
  arms: [none, llmlingua2, llmlingua2_protected, heuristic]
  requested_kept_rates: [0.90, 0.70, 0.50, 0.30]
  checkpoint: microsoft/llmlingua-2-xlm-roberta-large-meetingbank
  context_level_filter: false
  force_tokens: ["\n", "?", ".", ":", "{", "}", "[", "]"]
  force_reserve_digit: true
  max_force_token: 100
answering:
  provider: FILL_AT_RUN_TIME
  model: FILL_AT_RUN_TIME
  temperature: 0
  max_output_tokens: 256
  timeout_s: 60
  max_retries: 1
judging:
  enabled: true
  model: FILL_AT_RUN_TIME
  temperature: 0
  rubric_version: v1
cost:
  currency: USD
  pricing_date: FILL_AT_RUN_TIME
  fx_inr_per_usd: FILL_FROM_NAMED_SOURCE_AT_RUN_TIME
```

**No setting may be hard-coded outside this file.** Any command must copy this resolved configuration, its SHA-256, and the Git commit SHA into the output manifest. A changed prompt, model, checkpoint, scoring rule, rate, price, or dataset revision creates a new run ID.

## 12. File-level build specification

Implement the files below in this order. Each file owns one job. Keep network calls, scoring, and analysis separate so a partial failure cannot silently affect a score.

### `schemas.py`

Use Pydantic models (or dataclasses plus explicit JSON Schema) with `extra="forbid"`. Reject malformed rows rather than dropping fields.

```python
class SourceExample(BaseModel):
    source_dialogue_id: str
    turn_index: int
    domain: str
    history: list[Turn]
    final_user_turn: str
    gold_state: dict[str, Any] | None
    gold_response: str | None
    script_mix: Literal["romanized", "devanagari", "mixed", "unknown"]
    source_revision: str

class CompressionAttempt(BaseModel):
    pair_id: str
    arm: Literal["none", "llmlingua2", "llmlingua2_protected", "heuristic"]
    requested_kept_rate: float
    original_prompt: str
    compressible_context: str
    compressed_context: str
    final_prompt: str
    original_token_count: int
    compressed_token_count: int
    achieved_kept_ratio: float
    protected_spans: list[ProtectedSpan]
    span_recall: float
    compression_status: Literal["ok", "fallback_original", "failed"]
    error_type: str | None

class AnswerAttempt(BaseModel):
    pair_id: str
    arm: str
    requested_kept_rate: float
    model: str
    model_version: str | None
    response: str | None
    raw_provider_usage: dict[str, Any] | None
    prompt_tokens: int | None
    completion_tokens: int | None
    answer_cost_usd: Decimal | None
    latency_ms: float | None
    status: Literal["ok", "api_error", "timeout", "invalid_output"]
    retry_count: int
```

Required invariants:

1. `pair_id` is deterministic: `sha256(source_name + source_dialogue_id + turn_index + template_version)[:16]`.
2. `achieved_kept_ratio` is `final_prompt_tokens / original_prompt_tokens`, never a target-rate echo.
3. `none` returns the exact original prompt and has a kept ratio of 1.0.
4. A record with `status != ok` cannot enter a score mean; it must enter the failure table.
5. A fallback remains a measured record, with `compression_status=fallback_original`, not an erased record.

### `download_and_validate.py`

Inputs: configuration and an explicit official archive/repository URL. Outputs: immutable raw file, `MANIFEST.json`, validation report.

Algorithm:

1. Refuse URLs outside the known official release declared in the study decision record.
2. Download once into `data/raw/<source>/<revision>/`; never overwrite an existing archive.
3. Compute SHA-256 with `hashlib.sha256`; capture archive filenames, byte sizes, download UTC time, license URL/text, and source revision.
4. Read every official split. Assert the expected language marker/files exist before filtering.
5. Detect duplicate normalized dialogue text across source train/dev/test. Write a duplicate report and fail if a duplicate would cross the derived study split.
6. Write a data inventory CSV: domain, dialogue ID, turns, character count, provider-token count, script-mix estimate, potential protected-span count, and eligibility reason.
7. Do not make an undocumented “cleanup” rewrite. Transformations belong in `build_prompts.py` and are versioned.

Success gate: all source fields used by the task exist, at least 30 rendered examples are human-readable, and a source/license manifest exists. Otherwise stop and ask for a dataset decision; do not substitute a random Hugging Face dataset.

### `build_prompts.py`

The prompt needs a stable non-compressed shell and a separately compressible context. Use exact labels and newline separators. Preserve original utterance text verbatim; do not translate or normalize it.

```text
SYSTEM (never compress)
You are a task-oriented assistant. Use only the supplied dialogue context.
Return JSON with keys `state` and `response`.

DIALOGUE HISTORY (compressible)
USER: <turn 1>
ASSISTANT: <turn 2>
...

CURRENT USER REQUEST (never compress)
USER: <final user turn>

OUTPUT FORMAT (never compress)
{"state": {"domain": "...", "slots": {}}, "response": "..."}
```

Implementation details:

* The original and compressed conditions must have byte-identical system, final-user-turn, and output-format sections.
* Create one eligible example per target user turn with at least two preceding turns; cap only by the predeclared raw-token cap. Log exclusions due to cap.
* Add a `segment_map.json` with exact character start/end offsets for system/history/current/output sections. The compressor receives **only history**, then that result is reassembled into the full prompt. This prevents a compressor from deleting instructions or output schema and makes the experiment interpretable.
* Create a `prompt_template_sha256`. If it changes after dev inspection, invalidate prior experimental results.
* Derive `script_mix` using Unicode ranges plus token-level language identifiers only as a descriptive field; manually audit the classifier on 100 records and report its error rate.

### `protected_spans.py`

Implement exact masking rather than asking LLMLingua-2 to preserve arbitrary multiword text. The library supports `force_tokens` and digit reservation, but those are safeguards—not a substitute for a byte-exact span guarantee. Its documented LLMLingua-2 parameters include `force_tokens`, `force_reserve_digit`, and `max_force_token`: [official implementation](https://github.com/microsoft/LLMLingua/blob/main/llmlingua/prompt_compressor.py).

1. Detect candidates with conservative patterns: email, URL, phone, currency, decimal/integer, date/time, booking/transaction IDs, JSON/code fenced content and official state-slot values.
2. Sort spans by descending start offset; reject overlapping spans unless they are merged deterministically.
3. Replace each span with a collision-resistant token, such as `ZXQPROTECTED_0001_9f4a`, that cannot occur naturally. Store original string, normalized form, type, source offsets and placeholder.
4. Send only masked context to the compressor. After compression, require every placeholder exactly once. Reinject in reverse placeholder order.
5. Validate: every required original string appears byte-for-byte in the reinjected result; placeholder tokens are absent; output is non-empty; final token count is not greater than raw by more than 2%. If any check fails, use the original history and write `fallback_original` with the reason.
6. Unit-test nested JSON, repeated identical values, overlapping regex hits, a span at string boundaries, emoji, Devanagari, and malicious text containing a fake placeholder.

### `run_compression.py`

Run no-compression first, then each non-null arm. Cache only by `(prompt_sha256, arm, requested_rate, compressor_checkpoint_revision, config_sha256)`; cache misses must never reuse outputs from another rate or checkpoint.

For real LLMLingua-2:

```python
compressor = PromptCompressor(
    model_name=config.compression.checkpoint,
    use_llmlingua2=True,
    device_map="cpu",  # or logged CUDA device for a separately identifiable run
)
result = compressor.compress_prompt(
    masked_history,
    rate=requested_kept_rate,
    use_context_level_filter=False,
    use_token_level_filter=True,
    force_tokens=config.compression.force_tokens,
    force_reserve_digit=True,
)
```

The precise public API can differ by package version; run a 20-item smoke test and retain `pip freeze` plus a small serializable capability report. If the call returns a sequence/list, join only according to the official package result contract and log that version-specific behavior. Never route an exception to the heuristic arm under the name `llmlingua2`.

### `run_answers.py`

* Use one answer model for A0/A1/A2/A3. Do not compare a cheap model on compressed prompts with a premium model on raw prompts in the primary compression result.
* Use strict JSON output when provider support exists. Validate JSON; if invalid, make **one** repair-format retry using the same prompt and record it. Do not silently parse arbitrary prose as correct JSON.
* Create a durable append-only JSONL record immediately after each API response, then periodically compact to Parquet. Resume only rows that have a matching `pair_id`, arm, rate, model, and config hash.
* Capture response headers/model ID/usage payload without API keys. Store request timestamps in UTC and a request fingerprint, never raw user identifiers.
* Rate-limit with bounded exponential backoff. `429`, `5xx`, network error and invalid JSON must have distinct status codes. A 401/403 is a configuration failure: stop the run rather than producing partial totals.

### `score_structured.py` and `score_responses.py`

`score_structured.py` must canonicalize recursively:

```python
def canonical(value):
    if isinstance(value, dict): return {k: canonical(value[k]) for k in sorted(value)}
    if isinstance(value, list): return [canonical(v) for v in value]
    if isinstance(value, str): return " ".join(value.casefold().split())
    return value
```

Calculate exact-state match plus per-slot micro-F1. Treat absent and empty slots according to a written source-aware rule; add tests for both. Do not score fields that the reference data does not reliably annotate.

The response judge receives: target task, original dialogue context, gold state/response, candidate response, and a literal JSON rubric. It **must not** receive compressor arm, rate, cost, or “compressed” terminology. The required output is:

```json
{"label":"correct|partially_correct|incorrect","error_tags":["missing_slot"],"rationale":"<=40 words"}
```

Validate against schema. Reject invalid judge output, retry once, then record failure. The human-audit export randomizes row order and replaces arm names by anonymous labels. Provide annotators with an annotation guide containing examples and an adjudication process.

### `analyze.py`

1. Read only immutable `records.parquet` plus manifest. Fail if config/dataset/model hashes differ inside a requested comparison.
2. Join A0 and every variant on `pair_id`; check 1:1 joins and print lost/multiple pair counts before calculating a mean.
3. Compute **per dialogue**, then bootstrap dialogue IDs with replacement. For every replicate calculate score delta, token saving, cost saving and span recall. Use NumPy `Generator(PCG64(run_seed))` and save the seed.
4. Save `summary.json`, machine-readable `main_table.csv`, `failure_table.csv`, and plot-data CSVs before rendering figures. Figures cannot be the only result.
5. The report narrative is generated from summary values, never hand-typed. It must say `N`, dataset revision, test split, answer model, price date, and confidence interval in every headline result.

## 13. Command sequence and gates

Run from `C:\RM_Project\backend`. The agent must adapt executable paths to the current environment but retain equivalent commands in the run manifest.

```powershell
# 0. Never run research from an uninspected dirty worktree.
git status --short

# 1. Create isolated environment and install declared extras.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[compression,eval,hf,dev]"
.\.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding utf8 results\environment-pip-freeze.txt

# 2. Static checks before network/compute.
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src experiments

# 3. Dataset manifest and prompt audit.
.\.venv\Scripts\python.exe -m experiments.token_study.download_and_validate --config experiments/token_study/config.yaml
.\.venv\Scripts\python.exe -m experiments.token_study.build_prompts --config experiments/token_study/config.yaml --split smoke

# 4. Manually inspect 30 prompt-audit rows before proceeding.
.\.venv\Scripts\python.exe -m experiments.token_study.export_prompt_audit --split smoke --n 30

# 5. Real-compressor smoke test. Must NOT use fallback outputs as A1.
.\.venv\Scripts\python.exe -m experiments.token_study.run_compression --split smoke --arms none,llmlingua2,llmlingua2_protected
.\.venv\Scripts\python.exe -m experiments.token_study.verify_run --run-id RUN_ID --gate compression-smoke

# 6. Answer/scoring smoke test and cost-receipt validation.
.\.venv\Scripts\python.exe -m experiments.token_study.run_answers --split smoke --run-id RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.score_structured --run-id RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.verify_run --run-id RUN_ID --gate end-to-end-smoke

# 7. Only now run dev, freeze, then locked test.
.\.venv\Scripts\python.exe -m experiments.token_study.run_all --split dev --run-id DEV_RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.freeze --run-id DEV_RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.run_all --split test --run-id TEST_RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.analyze --run-id TEST_RUN_ID
.\.venv\Scripts\python.exe -m experiments.token_study.render_report --run-id TEST_RUN_ID
```

### Gate rules

| Gate | Automatic requirement | Human requirement | On failure |
|---|---|---|---|
| G0 environment | tests/linter pass; source versions captured | inspect dependency changes | fix code, do not collect results |
| G1 data | checksum/license/schema/inventory pass | 30 prompts correct and relevant | change builder/data decision and restart |
| G2 compressor | real library+checkpoint; A1 token count lower on aggregate; no unlogged fallback | inspect 20 raw/masked/compressed examples | fix span/mapping logic |
| G3 answer | JSON/schema/usage receipt valid; costs recompute | inspect 20 responses | fix answer or scorer |
| G4 dev freeze | all intended variants complete; decision log updated | explicitly lock test IDs/config | create immutable test run |
| G5 final | exact 1:1 pairs, bootstrap artifacts, failures counted | human-audit agreement reviewed | report limitation or rerun cleanly |

## 14. Failure taxonomy and deterministic remediation

Every non-success must map to exactly one primary category and optional secondary categories. The agent must not make up a “successful” answer to close a missing row.

| Category | Detect | Required action |
|---|---|---|
| `compressor_unavailable` | import/checkpoint error | stop A1/A2 study; install/repair; never substitute heuristic |
| `placeholder_lost` | zero or !=1 occurrence | fallback original; count it; add regression fixture |
| `span_changed` | byte comparison fails after reinjection | fallback original; record span type/value length only if data license permits |
| `compression_inflated` | final tokens > raw * 1.02 | fallback original; count as no saving |
| `answer_timeout` | deadline exceeded | retry once; otherwise failure row |
| `provider_usage_missing` | response lacks usage | calculate labelled estimate or exclude from cost primary metric; do not invent receipt |
| `invalid_json` | schema validation fails | one format retry; otherwise response failure |
| `judge_invalid` | rubric JSON invalid | one judge retry; otherwise audit failure |
| `dataset_leakage` | same dialogue/content crosses splits | invalidate split/run and recreate |
| `config_drift` | config/model/template hash mismatch | do not aggregate; start new run ID |

## 15. Human annotation instructions (provide verbatim)

Give each bilingual reviewer this text:

> You will see a task dialogue, the required output, a reference answer, and one candidate answer. You will not be told how the candidate was produced. Mark **correct** only if the candidate completes the user’s current task without contradicting the dialogue and contains all decision-critical slot values. Mark **partially correct** if the intent is handled but a non-critical detail is missing or unclear. Mark **incorrect** if it selects the wrong intent/state, loses or changes a critical entity/number/date, fabricates unsupported information, or fails to answer. Do not reward brevity, fluency, English-only wording, or similarity to the reference when task success differs. Select all applicable error tags and add a concise note.

Critical fields are domain, intent, requested item/service, amount, date/time, count, location, entity/booking ID and explicit negation/correction. Resolve reviewer disagreement with a third bilingual adjudicator; retain both original labels and the adjudicated result. Never let an LLM “adjudicate” human disagreement silently.

## 16. Exact board-result interpretation rules

Use one of these templates generated from actual `summary.json` values:

* **Positive:** “On `N` held-out code-mixed task-dialogue prompts from X-RiSAWOZ revision `R`, LLMLingua-2 with protected spans reduced end-to-end input tokens by median `S%` at requested kept rate `r`; structured task score changed by `D` points (95% CI `L` to `U`) relative to uncompressed prompts. Span recall was `P%`. Under the named provider/model price snapshot dated `DATE`, end-to-end cost changed by `C%`.”
* **Boundary:** “The five-point non-inferiority criterion held at `r=...` but not at `r=...`; the safe measured operating region is therefore `...`, not the full published range.”
* **Negative:** “On this domain, aggressive compression lost dialogue-state information / protected spans at `...`; this falsifies transfer at that setting and motivates the documented protected-span treatment.”

Never say “best possible response,” “lossless,” “guaranteed,” “production savings,” or “generalizes to all Hinglish” unless a separately designed test supports that exact claim.

## 17. Paste-this task prompt for the implementation AI

```text
Implement the P0 research study described in C:\RM_Project\RESEARCH_IMPLEMENTATION_PLAN.md. Treat that file as the source of truth.

Goal: produce a reproducible, real LLMLingua-2 prompt-compression transfer study on the code-mixed English-Hindi X-RiSAWOZ task-dialogue dataset. The output is evidence, not a demo.

Mandatory constraints:
1. Do not use synthetic seed data, simulated LLMLingua-2 values, heuristics renamed as LLMLingua-2, or string-similarity values renamed as task accuracy.
2. Do not change the locked test set, prompt template, model, scoring rubric, compression checkpoint, or pricing snapshot after looking at locked-test outputs.
3. Do not hide or drop failures, retries, compression fallbacks, missing provider usage, invalid JSON, or span-loss events.
4. Only download datasets from the official source after verifying license and schema. Stop and report if the official source, access, or license is ambiguous.
5. Preserve existing unrelated project changes. Do not rewrite git history.
6. Separate experiment outputs from the demo gateway. Existing endpoints must show real/synthetic status prominently and must not aggregate the two.
7. Every headline number must be traceable to a run manifest containing Git SHA, config SHA, data checksum/revision, package versions, model/version, token source, price source/date, records count, and bootstrap seed.

Execution order:
A. Audit the current repository and write the decision/config files specified in the plan.
B. Implement schemas, deterministic source validation, dialogue-level splits, prompt builder, protected masking/reinjection, real compressor wrapper, answer runner, task-specific scorer, judge/audit export, analysis, and run verification gates.
C. Add focused tests for every invariant and failure category in the plan. Run tests/linter.
D. Download/validate data, perform the 20-example smoke test, and stop for human review at each gate. Do not run a paid full test without configured credentials and explicit provider price information.
E. If a fully authorized, configured run is possible, produce final artifacts and report only observed results. Otherwise deliver a tested implementation and a precise list of the blocked external inputs.

Report after each gate: commands run, files changed, validation evidence, failures, and the next gate. Finish with links/paths to all artifacts and an honest distinction between completed measurements and unrun steps.
```

## 18. How to find the best compression rate (the actual research result)

The correct question is not “what percentage is best for every statement?” There is no scientifically honest single percentage that is best for all prompts. A 10-turn booking dialogue containing dates, money and IDs may tolerate much less compression than a repetitive support history. The study must therefore estimate a **safe operating point per predeclared prompt stratum**.

### 18.1 Define the strata before viewing locked-test results

Use these groups, provided each final group contains at least 30 dialogue-level examples; merge undersized groups into `other` and report that decision.

| Dimension | Groups | Reason |
|---|---|---|
| Task/domain | each official source domain | Different task information is required to answer correctly. |
| Context length | raw-token quartiles Q1–Q4, calculated on the development set | Longer contexts can contain more redundancy, but also more dependencies. |
| Script/mix | Romanized Hinglish, Devanagari+English, mixed/other | Tokenization and compression behavior can differ by writing system. |
| Critical-content load | 0, 1–2, 3+ protected spans | Tests whether IDs, amounts, dates and entities make compression unsafe. |
| Dialogue behavior | correction/revision present vs absent, where source labels permit | A compressor may drop a late correction such as “not Monday, Tuesday.” |

Do **not** create categories by examining which test rows failed. That would turn failures into an overfitted story. The table above determines the categories in advance.

### 18.2 Measure every arm at every rate for every group

For each group `g`, compressor arm `a`, and requested kept rate `r`, calculate:

`Q[g,a,r] = mean(primary_task_score)`

`DeltaQ[g,a,r] = Q[g,a,r] - Q[g,none,1.00]`

`S[g,a,r] = median(1 - achieved_kept_ratio)`

`P[g,a,r] = protected_span_recall`

`C[g,a,r] = mean(end_to_end_cost_usd)`

and produce 95% dialogue-clustered bootstrap confidence intervals for `DeltaQ`, `S`, `P`, and `1 - C[g,a,r]/C[g,none,1.00]`.

Use **achieved saving**, not nominal 30/50/70/90% labels, because a requested rate can produce a different actual token reduction on a short or entity-heavy prompt.

### 18.3 Predeclared safe-rate rule

For each group and arm, a rate is *eligible* only if all of the following hold:

1. `lower_95CI(DeltaQ[g,a,r]) >= -0.05` — quality loss is no worse than five absolute points within the uncertainty bound.
2. `lower_95CI(P[g,a,r]) >= 0.995` — protected-span recall remains at least 99.5% at the conservative bound. For high-risk transactional fields, require 100% observed recall and no fallback-masked loss.
3. Completion/error/fallback rate is not more than 2 percentage points worse than the uncompressed condition.
4. The rate actually saves at least 5% end-to-end cost at its point estimate. Otherwise there is no practical reason to compress.

Choose the group-specific optimum as the eligible configuration with the **largest median achieved token saving**. Break a tie using: (i) higher lower confidence bound for quality, (ii) lower end-to-end cost, then (iii) lower p95 latency. If no configuration is eligible, report “no safe compression rate found for this group under the chosen quality and safety criteria.” That is a valuable result, not a failure.

```python
def choose_safe_rate(rows_for_group):
    eligible = [x for x in rows_for_group if (
        x.delta_quality_ci_low >= -0.05
        and x.span_recall_ci_low >= 0.995
        and x.failure_rate_delta <= 0.02
        and x.end_to_end_cost_saving > 0.05
    )]
    if not eligible:
        return {"status": "no_safe_rate"}
    return sorted(
        eligible,
        key=lambda x: (
            x.median_achieved_token_saving,
            x.delta_quality_ci_low,
            x.end_to_end_cost_saving,
            -x.p95_latency_ms,
        ),
        reverse=True,
    )[0]
```

This produces a usable policy table, for example: “For short Romanized Hinglish support contexts without critical spans, use protected LLMLingua-2 up to X% measured saving; for date/amount/ID-heavy contexts, use the original prompt.” The X values must be filled only by completed measurement.

### 18.4 How the system should use the result

The paper reports each group’s safe rate. The later gateway may use a conservative lookup policy:

```text
classify prompt -> assign predeclared group -> retrieve group's safe requested rate
-> mask protected spans -> compress -> validate spans/inflation
-> if any validation fails, send original prompt
```

Do not deploy a group-specific setting if the group is small, was created after looking at test failures, or has a wide/unsafe confidence interval. Default to the global conservative rate or no compression.

## 19. `RESEARCH.md`: the finished research-paper artifact

Yes. The implementation agent must create a final [RESEARCH.md](C:/RM_Project/RESEARCH.md) after a completed run. It is a reproducible report designed to convert directly to PDF. It must be generated from the final run artifacts where possible, then reviewed by a human for prose clarity. It must never contain placeholder or invented values.

### Required structure and content

```markdown
# Does Prompt Compression Transfer to Code-Mixed Task Dialogues?

## Abstract
State dataset, N, compressor, answer model, highest safe observed saving, score change with 95% CI,
cost result, and the most important limitation in 150–250 words.

## 1. Introduction
Problem: token-billed LLM inference; gap: published compression results need not transfer to code-mixed task dialogue.
State the four RQs and the contribution without claiming a new compressor.

## 2. Related Work
LLMLingua / LongLLMLingua / LLMLingua-2; code-mixed task dialogue; tokenizer inequity.
Every factual external claim has a citation.

## 3. Research Questions and Pre-registration
List RQ1–RQ4, five-point quality margin, protected-span threshold, strata and safe-rate rule verbatim.

## 4. Data and Ethics
Source, official URL, version/commit, license, checksum, download date, source data properties, filtering,
dialogue-level split counts, exclusions, no private-data collection, and limitations of translated/code-mixed data.

## 5. Method
Prompt template, what is compressible, arms A0–A3, LLMLingua-2 checkpoint/version, masking/reinjection,
fixed answer model/temperature, output validation, pricing snapshot, and reproducibility manifest.

## 6. Metrics and Mathematics
Define kept ratio, token saving, compression factor, quality score, span recall, API cost, score delta,
paired bootstrap and non-inferiority/safe-rate equations. Define all symbols immediately below equations.

## 7. Experimental Protocol
Smoke/dev/test gates, test locking, retries/failure handling, human audit/blinding, and statistical procedure.

## 8. Results
8.1 Baseline reproduction result and deviations.
8.2 Overall A0/A1/A2/A3 × rate table, with N and 95% CIs.
8.3 Accuracy/quality vs achieved saving figure.
8.4 Cost vs retained quality Pareto figure and cost waterfall.
8.5 Protected-span safety table.
8.6 Best safe rate per predeclared group table.
8.7 Failure analysis with anonymized public-data examples.

## 9. Discussion
Answer every research question, explain where results agree/disagree with published baselines,
and distinguish observed result from plausible explanation.

## 10. Limitations and Threats to Validity
Dataset construction/translation, answer-model dependence, judge limitations, benchmark-to-production gap,
price volatility, sample size, and no claim of universal Hinglish coverage.

## 11. Conclusion
Two short paragraphs: measured boundary and practical deployment recommendation.

## Reproducibility Appendix
Run ID, Git SHA, config/data/checkpoint hashes, environment, exact commands, file paths and how to recreate figures.

## References
BibTeX/CSL-generated bibliography. Do not hand-type inconsistent citations.

## Appendix A: Full tables
All stratum × arm × rate rows, including no-safe-rate rows, failures and confidence intervals.
## Appendix B: Annotation rubric and agreement
## Appendix C: Pricing snapshot
```

### Required tables and figures in `RESEARCH.md`

| Artifact | Minimum columns / visual requirements |
|---|---|
| Table 1: Dataset | source/revision/license, dialogues/eligible contexts, domains, script groups, split counts, exclusions |
| Table 2: Overall result | arm, requested rate, N, median achieved saving, score, score delta [95% CI], span recall, cost, cost saving [95% CI], p50/p95 latency, failures |
| Table 3: Safe rate policy | predeclared group, N, selected arm/rate, median saving, score delta CI, span recall CI, cost saving, decision/reason no rate was selected |
| Table 4: Failure analysis | category, count, proportion, rate/arm, impact, whether protected treatment prevented it |
| Figure 1 | x=achieved token saving, y=primary quality; 95% CI error bars; one series per arm; uncompressed reference marked |
| Figure 2 | x=end-to-end cost saving, y=retained quality; Pareto frontier labelled; never imply a causal frontier beyond measured points |
| Figure 3 | grouped safe-rate chart by domain/length/span count, with “no safe rate” visible rather than omitted |
| Figure 4 | protected-span recall and fallback frequency by rate/arm |

### Citation requirements

Use a checked `references.bib` and Pandoc/Quarto citation processing; cite the original work, official software/dataset repository, and official pricing page. At minimum cite:

* [LLMLingua (Jiang et al., 2023)](https://arxiv.org/abs/2310.05736)
* [LongLLMLingua](https://arxiv.org/abs/2310.06839)
* [LLMLingua-2 (Pan et al., 2024)](https://arxiv.org/abs/2403.12968)
* [official LLMLingua-2 experiment workflow](https://github.com/microsoft/LLMLingua/blob/main/experiments/llmlingua2/README.md)
* [X-RiSAWOZ](https://arxiv.org/abs/2306.17674)
* [COMI-LINGUA](https://aclanthology.org/2025.findings-emnlp.422/), if used
* [tokenizer fairness research](https://arxiv.org/abs/2305.15425), if tokenizer analysis is reported

The agent must validate every URL and bibliography entry before rendering. Price citations are time-sensitive: they must be collected at run time, recorded with an access date, and never recycled from this plan.

### Render/export procedure

1. Generate all tables as CSV first and all figures as vector SVG/PDF or 300-DPI PNG.
2. Generate `RESEARCH.md` from a results template plus `summary.json`; include a `RESULTS_NOT_RUN.md` instead if external calls have not been authorized or completed.
3. Convert with Pandoc or Quarto only after link/citation validation. Example:

```powershell
pandoc RESEARCH.md --citeproc --bibliography=references.bib --csl=ieee.csl `
  --number-sections --toc --pdf-engine=xelatex -o output\RESEARCH.pdf
```

4. Render the produced PDF to PNGs, inspect every page for clipped tables, unreadable figures, missing citations, broken equations and empty reference entries. Fix and re-render until clean.
5. Preserve the Markdown, bibliography, CSVs, figures, manifest and final PDF together. The PDF alone is not reproducible.

## 20. Add this to the implementation-AI task prompt

Append this instruction to the prompt in Section 17:

```text
After the locked test run, generate C:\RM_Project\RESEARCH.md as a full research-paper draft following Section 19. Include only measured results from `summary.json` and table CSVs. It must cover abstract, research questions, data, method, mathematics, protocol, all results, the safe compression rate for every predeclared prompt group, failures, limitations, ethics, citations, reproducibility appendix and full tables. If the experiment cannot run because of missing credentials/approval/data access, create RESULTS_NOT_RUN.md and complete every implementable part; do not fill RESEARCH.md with fabricated results. Generate and visually QA a PDF only after `RESEARCH.md` contains real final results.
```
