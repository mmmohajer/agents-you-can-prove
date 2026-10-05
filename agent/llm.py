# Python 3.12
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError

from agent.paths import ROOT, TRACES_DIR

load_dotenv(ROOT / ".env")

DEFAULT_MODEL = "gpt-6-luna"
FRONTIER_MODEL = "gpt-6.1-sol"
DEFAULT_TIMEOUT = 30.0
TRACE_FILE = TRACES_DIR / "calls.jsonl"

# Prices per million tokens. Date them. Check the provider page before you trust a bill.
# gpt-6-luna (checked 2026-10-04): $0.10 input / $0.50 output.
PRICE_TABLE_DATE = date(2026, 10, 4)
PRICES: dict[str, dict[str, float]] = {
    "gpt-6-luna": {
        "input": 0.10,
        "output": 0.50,
        "cache_read": 0.010,
        "cache_write": 0.125,
    },
    "gpt-6.1-sol": {
        "input": 2.00,
        "output": 10.00,
        "cache_read": 0.20,
        "cache_write": 2.50,
    },
}

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is empty. Copy .env.sample to .env and put the key there."
            )
        _client = OpenAI(timeout=DEFAULT_TIMEOUT)
    return _client


@dataclass
class LLMResult:
    text: str
    model: str
    raw: Any
    latency_ms: float
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "completed"
    time_to_first_token_ms: float | None = None
    prompt_version: str | None = None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


def _usage_ints(usage: Any) -> tuple[int, int, int, int, int]:
    if usage is None:
        return 0, 0, 0, 0, 0
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    details = getattr(usage, "input_tokens_details", None)
    cached = 0
    cache_write = 0
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
        cache_write = int(
            getattr(details, "cache_write_tokens", None)
            or getattr(details, "cached_tokens_write", 0)
            or 0
        )
    out_details = getattr(usage, "output_tokens_details", None)
    reasoning = 0
    if out_details is not None:
        reasoning = int(getattr(out_details, "reasoning_tokens", 0) or 0)
    return input_tokens, cached, cache_write, output_tokens, reasoning


def compute_cost(
    model: str,
    input_tokens: int,
    cached_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
) -> float:
    prices = PRICES.get(model) or PRICES[DEFAULT_MODEL]
    uncached = max(input_tokens - cached_tokens, 0)
    return (
        uncached * prices["input"]
        + cached_tokens * prices["cache_read"]
        + cache_write_tokens * prices["cache_write"]
        + output_tokens * prices["output"]
    ) / 1_000_000


def _result_from_response(
    response: Any,
    latency_ms: float,
    prompt_version: str | None,
    requested_model: str,
) -> LLMResult:
    usage = getattr(response, "usage", None)
    input_tokens, cached, cache_write, output_tokens, reasoning = _usage_ints(usage)
    model = getattr(response, "model", None) or requested_model
    status = getattr(response, "status", None) or "completed"
    text = getattr(response, "output_text", None) or ""
    return LLMResult(
        text=text,
        model=model,
        raw=response,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        cached_tokens=cached,
        cache_write_tokens=cache_write,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning,
        cost_usd=compute_cost(model, input_tokens, cached, cache_write, output_tokens),
        status=status,
        prompt_version=prompt_version,
    )


def write_trace(result: LLMResult) -> None:
    try:
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": result.trace_id,
            "model": result.model,
            "status": result.status,
            "input_tokens": result.input_tokens,
            "cached_tokens": result.cached_tokens,
            "cache_write_tokens": result.cache_write_tokens,
            "output_tokens": result.output_tokens,
            "reasoning_tokens": result.reasoning_tokens,
            "cost_usd": result.cost_usd,
            "duration_ms": result.latency_ms,
            "time_to_first_token_ms": result.time_to_first_token_ms,
            "prompt_version": result.prompt_version,
            "price_table_date": PRICE_TABLE_DATE.isoformat(),
            "text": result.text[:2000],
        }
        with TRACE_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort. A trace write must never mask the original error.
        return


def generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float | None = None,
    max_output_tokens: int = 1000,
    prompt_version: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    instructions: str | None = None,
    extra_input: Any | None = None,
    max_retries: int = 4,
) -> LLMResult:
    """Call the Responses API. Omit temperature unless the caller set it."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "input": extra_input if extra_input is not None else prompt,
        "max_output_tokens": max_output_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    if tools:
        kwargs["tools"] = tools
    if instructions:
        kwargs["instructions"] = instructions

    last_error: Exception | None = None
    for attempt in range(max_retries):
        started = time.perf_counter()
        try:
            response = client.responses.create(**kwargs)
            latency_ms = (time.perf_counter() - started) * 1000
            result = _result_from_response(response, latency_ms, prompt_version, model)
            write_trace(result)
            return result
        except RateLimitError as error:
            last_error = error
            delay = min(2**attempt, 16)
            time.sleep(delay)
        except Exception:
            raise
    assert last_error is not None
    raise last_error


def parse_structured(
    prompt: str,
    text_format: type,
    model: str = DEFAULT_MODEL,
    max_output_tokens: int = 1000,
    prompt_version: str | None = None,
) -> tuple[Any, LLMResult]:
    client = get_client()
    started = time.perf_counter()
    response = client.responses.parse(
        model=model,
        input=prompt,
        text_format=text_format,
        max_output_tokens=max_output_tokens,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    result = _result_from_response(response, latency_ms, prompt_version, model)
    write_trace(result)
    return response.output_parsed, result


if __name__ == "__main__":
    sample = generate("Reply with exactly three words: wrapper is ready.")
    print("text:", sample.text)
    print("model:", sample.model)
    print("status:", sample.status)
    print("latency_ms:", round(sample.latency_ms, 1))
    print("input_tokens:", sample.input_tokens)
    print("output_tokens:", sample.output_tokens)
    print("cost_usd:", sample.cost_usd)
    print("trace_id:", sample.trace_id)
