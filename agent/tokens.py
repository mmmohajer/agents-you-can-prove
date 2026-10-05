from __future__ import annotations

import tiktoken

from agent.llm import DEFAULT_MODEL

FALLBACK_ENCODING = "o200k_base"


def get_encoding(model: str = DEFAULT_MODEL):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding(FALLBACK_ENCODING)


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    return len(get_encoding(model).encode(text))


def budget(window_tokens: int, sections: dict[str, int], output_reserve: int) -> dict[str, int]:
    allocated = sum(sections.values())
    remaining = window_tokens - allocated - output_reserve
    return {
        "window": window_tokens,
        "allocated": allocated,
        "output_reserve": output_reserve,
        "remaining": remaining,
    }


if __name__ == "__main__":
    samples = {
        "prose": "The refund window for standard plans is fourteen days from the delivery date.",
        "code": "def lookup_customer(account_id: str) -> dict | None:\n    return CUSTOMERS.get(account_id)",
        "numbers": "4471 1200 14 30 2024-03-05 99.50 1000003",
        "arabic": "سياسة الاسترجاع للمنتجات المعيبة هي أربعة عشر يوماً من تاريخ التسليم.",
    }
    for name, text in samples.items():
        tokens = count_tokens(text)
        chars = len(text)
        ratio = chars / tokens if tokens else 0
        print(f"{name:8} chars={chars:4} tokens={tokens:3} chars/token={ratio:.2f}")
