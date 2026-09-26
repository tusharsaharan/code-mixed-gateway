from __future__ import annotations

import hashlib
import re

from .schemas import ProtectedSpan

# Conservative detectors with priority: on identical start offsets, specific
# patterns (date/currency/email/...) beat generic ones (phone/integer), so
# "12-05-2026" is a datetime while "+91-98765-43210" stays a phone
# (its datetime-shaped substring starts later, and earliest start wins).
_PATTERNS: list[tuple[str, int, re.Pattern]] = [
    ("code_fenced", 9, re.compile(r"```.*?```", re.DOTALL)),
    ("email", 8, re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("url", 8, re.compile(r"https?://\S+|www\.\S+")),
    ("datetime", 7, re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")),
    ("currency", 7, re.compile(r"(?:Rs\.?|INR|₹|\$)\s?\d[\d,]*(?:\.\d+)?")),
    ("decimal", 6, re.compile(r"(?<!\d)\d+\.\d+(?!\d)")),
    ("booking_id", 5, re.compile(r"\b[A-Z]{2,}[-\s]?\d{3,}\b")),
    ("phone", 4, re.compile(r"(?<!\d)\+?\d[\d\s().-]{7,}\d")),
    ("integer", 3, re.compile(r"(?<![\d.])\d{4,}(?![\d.])")),
]

_SALT = "token-study-v1"


def _placeholder(value: str, idx: int) -> str:
    digest = hashlib.sha256(f"{_SALT}|{idx}|{value}".encode("utf-8")).hexdigest()[:4]
    return f"ZXQPROTECTED_{idx:04d}_{digest}"


def detect_spans(text: str) -> list[ProtectedSpan]:
    """Find candidate spans; overlapping hits are merged deterministically
    (earliest start wins, longer match wins ties)."""
    cands: list[tuple[int, int, int, str, str]] = []
    for kind, prio, rx in _PATTERNS:
        for m in rx.finditer(text):
            cands.append((m.start(), prio, m.end(), kind, m.group(0)))
    cands.sort(key=lambda c: (c[0], -c[1], -(c[2] - c[0])))
    kept: list[tuple[int, int, str, str]] = []
    for s, _, e, kind, val in cands:
        if any(not (e <= ks or s >= ke) for ks, ke, _, _ in kept):
            continue
        kept.append((s, e, kind, val))
    spans = []
    for i, (s, e, kind, val) in enumerate(sorted(kept)):
        spans.append(ProtectedSpan(type=kind, value=val, start=s, end=e, placeholder=_placeholder(val, i)))
    return spans


def mask_text(text: str, spans: list[ProtectedSpan]) -> str:
    out = text
    for sp in sorted(spans, key=lambda s: s.start, reverse=True):
        out = out[: sp.start] + sp.placeholder + out[sp.end :]
    return out


def reinject_text(masked_compressed: str, spans: list[ProtectedSpan]) -> tuple[str, bool, str | None]:
    """Reinject in reverse placeholder order. Returns (text, ok, error)."""
    out = masked_compressed
    for sp in sorted(spans, key=lambda s: s.start, reverse=True):
        if out.count(sp.placeholder) != 1:
            return masked_compressed, False, "placeholder_lost"
        out = out.replace(sp.placeholder, sp.value)
    for sp in spans:
        if sp.value not in out:
            return masked_compressed, False, "span_changed"
    if "ZXQPROTECTED_" in out:
        return masked_compressed, False, "placeholder_lost"
    return out, True, None


def span_recall(final_text: str, spans: list[ProtectedSpan]) -> float:
    if not spans:
        return 1.0
    norm = lambda s: " ".join(s.split())
    hit = sum(1 for sp in spans if norm(sp.value) in norm(final_text))
    return hit / len(spans)
