"""Model-aware token counting with a safe approximation fallback."""

from __future__ import annotations

import math


def count_tokens(text: str, model: str = "") -> int:
    if not text:
        return 0
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text))
    except (ImportError, ValueError):
        return max(1, math.ceil(len(text) / 4))
