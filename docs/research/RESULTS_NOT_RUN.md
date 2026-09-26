# RESULTS NOT RUN — yet (compression record complete, answers blocked)

No locked test was executed. Compression on real data IS done (below);
answer-dependent numbers do not exist yet — by design (plan §19).

## Completed since the last update (2026-09-26)

- Dataset: PRESTO pivot (CC BY 4.0), validated, splits smoke 20 / dev 150 /
  test 500 hi-IN code-mixing. See DATA_CARD.md.
- Compression record `backend/results/presto-001/`: smoke 260 + dev 1,950 +
  test 6,500 rows, **all `ok`, 0 fallbacks**, real LLMLingua-2
  (bert-multilingual). Mean achieved kept: A1 ≈ 0.69, A2 ≈ 0.69.
- Config: Groq provider, answer `openai/gpt-oss-120b`, judge
  `openai/gpt-oss-20b`, dated price snapshot in `config.yaml`.
- Prompt audit exported (`results/prompt_audit/audit_smoke.json`) — awaiting
  human G1 review (your job, ~1 hour).

## Blocked inputs (exact unblock list)

1. **Working Groq key.** The supplied key is rejected (HTTP 403 on `/models`
   AND chat completions, verified twice; safely stored in gitignored
   `backend/.env`). Generate a fresh key at console.groq.com → API Keys,
   replace the `GROQ_API_KEY=` line, tell me. Blocks: ALL answer/judge calls.
2. **G1 review + freeze sign-off (you).** Read the 20-row audit export,
   confirm prompts, say "freeze" — I lock the test set.
3. **Two bilingual annotators (you + 1 friend)** for 100 blinded structured
   outputs post-test. I export the sheets + guide.

## Blocked inputs (exact unblock list)

1. **Dataset access.** X-RiSAWOZ official download URL + license confirmation.
   Attempt log: precog project page has no link/license; ACL paper page links
   no repo/data; HF search empty. See `docs/research/DATA_CARD.md`.
   Owner decision required (DECISIONS.md §3). Unblocks: Stage B, then D.
2. **Answer-model provider + model snapshot.** No credentials in this
   environment (no `backend/.env`, no provider env vars). Required: provider
   base URL, model name/version pin, temperature-0 + seed support, and a
   dated per-million-token price sheet with source URL. Unblocks: Stage D
   answers, cost analysis.
3. **Judge model + two bilingual human annotators.** Required for response
   scores, agreement stats (kappa/alpha), and the blinded audit. Structured
   EM/F1 can run without them once (1) and (2) exist.
4. **30-prompt manual review (G1) + test lock (G4).** Human steps; the export
   (`export_prompt_audit`) and lock (`freeze`) tooling is ready.

## What is ready and tested

- `backend/experiments/token_study/`: schemas (strict, `extra="forbid"`),
  allowlisted downloader + validator, deterministic dialogue-level splits,
  stable prompt builder with segment map, collision-proof protected-span
  masking/reinjection, real-compressor runner (refuses heuristic-as-A1),
  OpenAI-compatible answer runner with retry taxonomy, structured scorer
  (canonical EM + slot micro-F1), blinded audit exporter, paired
  dialogue-clustered bootstrap analysis (10k reps), safe-rate rule, gate
  verifier, report renderer. 17 unit tests pass; full backend suite holds at
  93 passed + 3 pre-existing env failures (missing `pytest-asyncio`).
- G2 smoke evidence: real `llmlingua` + real checkpoint, 260/260 ok,
  0 fallbacks, A1/A2 kept 0.88 vs A0 1.00 (`REPRODUCTION.md`, manifest in
  `backend/results/smoke-g2-001/`).
- Frozen scope + hypotheses: `docs/research/DECISIONS.md` (committed pre-run).
- Gateway honesty corrections: lexical-proxy labels, `metric_note` on every
  eval response, provenance block on `/v1/eval/summary`, dynamic
  simulated/measured captions on the benchmark page.

## Unblock commands (after 1–4)

```powershell
cd C:\RM_Project\backend
$env:PYTHONPATH = "src;."
python -m experiments.token_study.download_and_validate --config experiments/token_study/config.yaml --from-jsonl <ADAPTER_OUT> --revision <REV>
python -m experiments.token_study.build_prompts --split dev
python -m experiments.token_study.run_all --split dev --run-id <DEV_ID>
python -m experiments.token_study.score_structured --run-id <DEV_ID> --split dev
python -m experiments.token_study.freeze --run-id <DEV_ID>
python -m experiments.token_study.run_all --split test --run-id <TEST_ID>
python -m experiments.token_study.analyze --run-id <TEST_ID> --split test
python -m experiments.token_study.render_report --run-id <TEST_ID> --split test
```
