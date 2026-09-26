# DATA CARD — P0 study data status

## Primary source (ACQUIRED 2026-09-26: PRESTO pivot, CC BY 4.0)

- Dataset: PRESTO v1 (Goel et al., arXiv 2303.08954) — 550K+ human
  task-oriented conversations with structured semantic parses and explicit
  per-locale `code-mixing` test partitions.
- Release: `google-research-datasets/presto` (archived, read-only),
  download `https://storage.googleapis.com/gresearch/presto/presto_v1.zip`
  (415,990,813 bytes, sha256
  `1fc671692cceb31fbda17e351e47f2cc52ee8779042f92dc26674cc0cca2167f`).
- License: CC BY 4.0 (repo README). Attribution + citation required on release.
- X-RiSAWOZ attempt (for the record): precog page has no link/license, ACL
  paper page links no repo/data, HF search empty — nothing downloaded there.

## Splits (deterministic, seed 20260926, dialogue=`example_id` level)

- smoke 20 / dev 150 hi-IN / **test 500 hi-IN `code-mixing`** (verified 500/500).
- Script: test `mixed` (Devanagari+English) 397 / `devanagari` 103 /
  `romanized` 0. **Limitation: no romanized Hinglish in PRESTO** — the
  tokenizer-fairness/romanized claim needs the GupShup secondary arm later.
- Context: all rows have ≥2 previous turns (plan minimum); median history 10 turns.
- Adapter: `experiments/token_study/adapters/presto_adapter.py` (hi-IN only,
  `targets` → `{intent, slots}` gold_state, 100% parse rate, 21,495 unique).
  Validation: 0 schema exclusions; inventory + splits committed as logic
  (data itself gitignored).

## Gold outputs

- `gold_state`: structured parse (primary EM + slot micro-F1). `gold_response`:
  absent in PRESTO → response-judge secondary metric dropped (documented
  deviation); human audit validates structured outputs instead.
- No private data: public benchmark only; pilot-user text structurally barred
  from experiment dirs (`assert_no_demo_contamination`).

## What exists instead (explicitly non-evidence)

- `backend/data/processed/token_study/examples.jsonl` — 20 synthetic Hinglish
  dialogues (`source_revision: synthetic-smoke-fixture-v1`), gitignored.
  Purpose: compressor-machinery smoke test only.
- `splits.json` — `{"smoke": [...20 ids], "dev": [], "test": []}`.
  No real dev/test split exists until the owner resolves the dataset decision.
- Demo gateway data (`seed_hinglish.jsonl`, `benchmark.jsonl`, `pilot.sqlite`)
  remains synthetic and is structurally barred from experiment runs
  (`assert_no_demo_contamination`).

## Transformations / filtering

None applied to any external data (none acquired). The validation pipeline
(`download_and_validate.py`) is implemented and tested: schema validation,
exclusion table, inventory CSV, deterministic dialogue-level splits
(seed 20260926), SHA-256 manifest. It refuses non-allowlisted URLs by design.

## Limitations

No representativeness claim can be made until the official release is
acquired. The owner decision in `docs/research/DECISIONS.md` §3 is the
unblock: (a) official URL + license, (b) authorized PRESTO pivot, or
(c) another named source with license evidence.
