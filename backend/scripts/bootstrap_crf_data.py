"""LLM-bootstrap Keep/Drop labels for CRF training (offline, run once).

Pipeline per prompt: mask() -> LLM compress (local Ollama qwen3:0.6b by
default, temperature 0.0) -> reinject check -> greedy token alignment on
normalized forms -> quality gates -> JSONL with (tokens, labels).

Usage:
    python scripts/bootstrap_crf_data.py --prompts data/training/prompts.jsonl \\
        --out data/training/bootstrap_filtered.jsonl [--limit 500] [--no-llm]

--no-llm uses the deterministic lexicon prune() as the teacher (fast,
offline, good enough to validate the pipeline end-to-end before spending
LLM time). Real training should use the LLM teacher.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from gateway.lexicons import prune as lexicon_prune  # noqa: E402
from gateway.modules.m2_compressor.phonetic import (  # noqa: E402
    PROTECTED_TOKENS,
    normalize_chars,
)
from gateway.modules.m2_compressor.safety_span import mask, reinject  # noqa: E402

BOOTSTRAP_SYSTEM = (
    "You are a Hinglish text compressor. Given a Hinglish (Hindi-English mixed) "
    "message, output ONLY the compressed version by dropping words that are "
    "unnecessary -- fillers, greetings, redundant particles, auxiliary verbs, "
    "and pleasantries.\n"
    "CRITICAL RULES:\n"
    "1. NEVER drop negation words (nahi, nahin, mat, not, never)\n"
    "2. NEVER drop question words (kya, kahan, kaise, kab, kyun, kaun)\n"
    "3. NEVER drop nouns, main verbs, numbers, names, or entities\n"
    "4. NEVER add new words -- only remove existing ones\n"
    "5. NEVER reorder words -- keep the original word order\n"
    "6. Keep [[PSi]] placeholders exactly as-is\n"
    "7. Output ONLY the compressed text on a single line, nothing else\n"
    "\n"
    "Examples:\n"
    "Input: yaar basically mera hostel ka wifi bahut slow chal raha hai\n"
    "Output: mera hostel ka wifi bahut slow chal\n"
    "Input: hello sir please mera form approve kar do na\n"
    "Output: mera form approve kar do\n"
    "Input: mra wifi nhi chal rha h\n"
    "Output: mra wifi nhi chal"
)


def align_tokens(original: list[str], compressed: list[str]) -> list[str]:
    """Greedy forward alignment: K if the normalized token appears next in
    the compressed stream, else D."""
    labels: list[str] = []
    comp_norm = [normalize_chars(t) for t in compressed]
    j = 0
    for tok in original:
        norm = normalize_chars(tok)
        if j < len(comp_norm) and norm == comp_norm[j]:
            labels.append("K")
            j += 1
        else:
            labels.append("D")
    return labels


def quality_ok(orig_tokens: list[str], labels: list[str]) -> tuple[bool, str]:
    """Quality gates: negation/question survival + sane compression amount."""
    dropped = {normalize_chars(t) for t, lab in zip(orig_tokens, labels, strict=True) if lab == "D"}
    if dropped & set(PROTECTED_TOKENS):
        return False, "protected_dropped"
    if content_guard_violated(orig_tokens, labels):
        return False, "content_dropped"
    if not labels:
        return False, "empty"
    drop_ratio = sum(1 for lab in labels if lab == "D") / len(labels)
    if drop_ratio > 0.70:
        return False, "over_compression"
    if drop_ratio < 0.05:
        return False, "no_compression"
    return True, "ok"


#: English/homograph content words the lexicon deliberately never drops as
#: bare unigrams. If the LLM teacher drops one, the example is rejected --
#: the label noise would teach the CRF to eat content words.
HOMOGRAPH_GUARD: frozenset[str] = frozenset({"you", "know", "sun", "like", "log", "well"})


def content_guard_violated(orig_tokens: list[str], labels: list[str]) -> bool:
    """True if a guarded content word (or tech/initial matlab) was dropped."""
    from gateway.lexicons import _lexicons as _load_lexicons

    tech_words = frozenset(
        w.lower()
        for w in _load_lexicons()["fillers_tech_guarded"].get("matlab", {}).get("tech_context", [])
    )
    norms = [normalize_chars(t) for t in orig_tokens]
    for i, (norm, lab) in enumerate(zip(norms, labels, strict=True)):
        if lab != "D":
            continue
        if norm in HOMOGRAPH_GUARD:
            return True
        if norm == "matlab" and (i == 0 or bool(set(norms) & tech_words)):
            return True
    return False


def subset_ok(orig_tokens: list[str], comp_tokens: list[str]) -> bool:
    """Every normalized compressed token must come from the original.

    Rejects hallucinations/rewordings (e.g. small local models inventing
    synonyms) that greedy alignment would otherwise mislabel as content
    drops. Multiset comparison so duplicated tokens are accounted for.
    """
    from collections import Counter

    remaining = Counter(normalize_chars(t) for t in orig_tokens)
    for t in comp_tokens:
        norm = normalize_chars(t)
        if remaining.get(norm, 0) <= 0:
            return False
        remaining[norm] -= 1
    return True


def clean_output(raw: str) -> str:
    """First non-empty line, surrounding quotes stripped (small models chat)."""
    for line in raw.splitlines():
        line = line.strip().strip("\"'").strip()
        if line:
            # Drop common chatty prefixes.
            for prefix in ("output:", "compressed:", "compressed text:"):
                if line.lower().startswith(prefix):
                    line = line[len(prefix):].strip().strip("\"'").strip()
            return line
    return ""


async def _llm_compress(
    texts: list[str],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    concurrency: int = 8,
    timeout: float = 120.0,
) -> list[str | None]:
    import os

    from gateway.config import get_settings
    from gateway.llm import build_client

    settings = get_settings()
    client = build_client(
        "local",
        model or settings.local.model,
        base_url or settings.local.base_url,
        api_key if api_key else settings.local.api_key or os.environ.get("OPENAI_API_KEY", ""),
        dry_run=False,
        timeout=timeout,
    )
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(text: str) -> str | None:
        async with sem:
            try:
                res = await client.chat(
                    [
                        {"role": "system", "content": BOOTSTRAP_SYSTEM},
                        {"role": "user", "content": text},
                    ],
                    temperature=0.0,
                )
                return clean_output(res.content)
            except Exception:
                return None

    return await asyncio.gather(*[one(t) for t in texts])


def _hf_compress(
    texts: list[str],
    hf_model: str,
    batch_size: int = 4,
    max_new_tokens: int = 60,
    load_4bit: bool = True,
    on_batch=None,
) -> list[str | None]:
    """Synchronous HuggingFace GPU teacher (for Colab: device_map=auto).

    Batched text-generation with the same few-shot system prompt as the API
    path. Requires transformers + accelerate + a CUDA GPU. With 4-bit
    quantization (default, needs bitsandbytes) a 7B model fits fully on a
    16GB T4 with no CPU offload -- roughly 10-20x faster than fp16 spillover.
    When `on_batch` is given, it is called as on_batch(start_index,
    batch_outputs) after every batch so callers can flush results
    incrementally (crash-safe).
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(hf_model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    # Left-padding is required for correct batched generation with
    # decoder-only models (right-padding lets short sequences in a batch
    # attend to trailing pad tokens, degrading their outputs).
    tok.padding_side = "left"
    use_bf16 = torch.cuda.is_bf16_supported()
    if load_4bit:
        try:
            from transformers import BitsAndBytesConfig
        except ImportError as exc:
            raise ImportError("4-bit teacher needs bitsandbytes (pip install bitsandbytes)") from exc
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        model = AutoModelForCausalLM.from_pretrained(
            hf_model, device_map="auto", quantization_config=quant
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            hf_model,
            device_map="auto",
            torch_dtype=torch.bfloat16 if use_bf16 else torch.float16,
        )
    model.eval()

    out: list[str | None] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        chats = [
            tok.apply_chat_template(
                [
                    {"role": "system", "content": BOOTSTRAP_SYSTEM},
                    {"role": "user", "content": t},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
            for t in batch
        ]
        enc = tok(chats, return_tensors="pt", padding=True, truncation=True, max_length=512)
        enc = {k: v.to(model.device) for k, v in enc.items()}
        try:
            with torch.no_grad():
                gen = model.generate(
                    **enc,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    pad_token_id=tok.pad_token_id,
                    eos_token_id=tok.eos_token_id,
                )
            for i, _t in enumerate(batch):
                prompt_len = enc["input_ids"][i].shape[0]
                decoded = tok.decode(gen[i][prompt_len:], skip_special_tokens=True)
                out.append(clean_output(decoded))
        except Exception:
            out.extend([None] * len(batch))
        print(f"hf teacher: {min(start + batch_size, len(texts))}/{len(texts)}", flush=True)
        if on_batch is not None:
            on_batch(start, out[start : start + len(batch)])
    return out


def _teacher_no_llm(masked: str) -> str:
    """Deterministic teacher: lexicon prune + auxiliary-verb drop.

    The lexicon prune handles fillers/greetings/vocatives; the aux pass
    teaches what the LLM teacher would do with progressive/present
    auxiliaries (raha/rahi/rahe + hai/hain/ho...), which carry almost no
    information once the main verb survives. Comparison is on normalized
    forms so spelling variants (rha/h) are dropped too.
    """
    pruned, _ = lexicon_prune(masked)
    toks = pruned.split()
    kept: list[str] = []
    for t in toks:
        if not kept:
            kept.append(t)
            continue
        from gateway.modules.m2_compressor.phonetic import is_marker as _is_marker

        if _is_marker(t):
            kept.append(t)
            continue
        if normalize_chars(t) in AUX_TOKENS:
            continue  # drop auxiliary
        kept.append(t)
    return " ".join(kept)


#: Normalized auxiliary-verb forms (progressive + present/past be).
#: Disjoint from PROTECTED_TOKENS by construction (asserted in tests).
AUX_TOKENS: frozenset[str] = frozenset(
    {"raha", "rahi", "rahe", "hai", "hain", "hun", "tha", "thi", "the", "hoga", "hogi", "honge"}
)


def process_one(
    rec_id: str,
    masked: str,
    spans: list,
    comp: str | None,
    apply_subset_gate: bool,
) -> tuple[str | None, dict | None]:
    """Align + gate a single teacher output.

    Returns (skip_reason, row): skip_reason is None when the row is kept.
    """
    if not comp or not comp.strip():
        return "empty_response", None
    restored, ok = reinject(comp.strip(), spans)
    if not ok:
        return "marker_lost", None
    orig_tokens = masked.split()
    comp_tokens = comp.strip().split()
    if len(comp_tokens) >= len(orig_tokens):
        return "not_shorter", None
    if apply_subset_gate and not subset_ok(orig_tokens, comp_tokens):
        return "hallucinated_tokens", None
    labels = align_tokens(orig_tokens, comp_tokens)
    good, reason = quality_ok(orig_tokens, labels)
    if not good:
        return reason, None
    return None, {"id": rec_id, "tokens": orig_tokens, "labels": labels}


def load_done_ids(out_path: Path) -> set[str]:
    """Ids already present in a (possibly partial) output file."""
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                continue
    return done


async def main_async(args) -> None:
    prompts_path = Path(args.prompts)
    if not prompts_path.is_absolute():
        prompts_path = BACKEND_ROOT / prompts_path
    records = [
        json.loads(line)
        for line in prompts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit:
        records = records[: args.limit]

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = BACKEND_ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.resume:
        done_ids = load_done_ids(out_path)
        before = len(records)
        records = [r for r in records if r.get("id") not in done_ids]
        print(f"resume: {len(done_ids)} already done, {len(records)}/{before} remaining")
        mode = "a"
    else:
        mode = "w"

    masked_texts: list[str] = []
    span_lists: list = []
    for rec in records:
        masked, spans = mask(rec["text"])
        masked_texts.append(masked)
        span_lists.append(spans)

    kept = skipped = 0
    skip_reasons: dict[str, int] = {}

    def _record(skip_reason: str | None, row: dict | None, fh) -> None:
        nonlocal kept, skipped
        if skip_reason is not None:
            skipped += 1
            skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
            return
        assert row is not None
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        kept += 1

    with out_path.open(mode, encoding="utf-8") as fh:
        if args.no_llm:
            for rec, masked, spans in zip(records, masked_texts, span_lists, strict=True):
                reason, row = process_one(rec["id"], masked, spans, _teacher_no_llm(masked), False)
                _record(reason, row, fh)
        elif args.hf_model:
            def _on_batch(start: int, outs: list[str | None]) -> None:
                for offset, comp in enumerate(outs):
                    idx = start + offset
                    reason, row = process_one(
                        records[idx]["id"], masked_texts[idx], span_lists[idx], comp, True
                    )
                    _record(reason, row, fh)
                fh.flush()

            _hf_compress(masked_texts, args.hf_model, args.hf_batch, load_4bit=args.hf_4bit, on_batch=_on_batch)
        else:
            compressed_list = await _llm_compress(
                masked_texts,
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                concurrency=args.concurrency,
                timeout=args.timeout,
            )
            for rec, masked, spans, comp in zip(
                records, masked_texts, span_lists, compressed_list, strict=True
            ):
                reason, row = process_one(rec["id"], masked, spans, comp, True)
                _record(reason, row, fh)
    print(f"kept {kept} / skipped {skipped} -> {out_path}")
    if skip_reasons:
        print("skip reasons:", json.dumps(skip_reasons, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="data/training/prompts.jsonl")
    ap.add_argument("--out", default="data/training/bootstrap_filtered.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--model", default="", help="LLM model (default: settings.local.model)")
    ap.add_argument("--base-url", default="", help="API base URL (default: settings.local.base_url)")
    ap.add_argument("--api-key", default="", help="API key (default: settings key or OPENAI_API_KEY)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--hf-model", default="", help="HF model id for local GPU teacher (Colab)")
    ap.add_argument("--hf-batch", type=int, default=4)
    ap.add_argument("--hf-4bit", action=argparse.BooleanOptionalAction, default=True,
                    help="4-bit quantize the HF teacher (needs bitsandbytes; fits 7B fully on a T4)")
    ap.add_argument("--resume", action="store_true", help="Skip ids already in --out (crash-safe reruns)")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
