from __future__ import annotations

import re

_WS = re.compile(r"\s+")


class TokenCounter:
    """Count tokens; uses tiktoken when available, else a whitespace heuristic."""

    def __init__(self, encoding: str = "cl100k_base") -> None:
        self.encoding = encoding
        self._enc = self._load_encoding()

    @staticmethod
    def _load_encoding():
        try:
            import tiktoken

            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None

    def count(self, text: str) -> int:
        if self._enc is not None:
            try:
                return len(self._enc.encode(text))
            except Exception:
                pass
        return len(_WS.sub(" ", text).strip().split()) if text.strip() else 0