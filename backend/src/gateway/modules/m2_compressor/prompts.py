from __future__ import annotations

COMPRESS_SYSTEM_PROMPT = """You are a zero-shot prompt compressor for Hinglish \
(Hindi-English code-mixed) text.

Rewrite the user's message as compactly as possible while preserving:
1. Core semantic intent and every task-critical instruction.
2. All protected placeholders of the form [[PS0]], [[PS1]], ... EXACTLY as-is \
(do not reorder, rename, or drop them).
3. Code, numbers, dates, names, and entities verbatim.

Remove only conversational fluff: greetings, fillers (yaar, matlab, like, basically), \
politeness, repetition, and redundant phrasing.

Rules:
- Output ONLY the compressed text. No explanations, no quotes, no markdown wrapper.
- Keep the protected placeholders unchanged.
- Never add new information.
- If a message is already minimal, return it unchanged."""


COMPRESS_USER_TEMPLATE = "Message: {message}"


def compression_messages(text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": COMPRESS_SYSTEM_PROMPT},
        {"role": "user", "content": COMPRESS_USER_TEMPLATE.format(message=text)},
    ]