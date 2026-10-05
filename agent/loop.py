from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from agent.llm import DEFAULT_MODEL, generate
from agent.permissions import PermissionDenied, dispatch
from agent.tools import KIND, TOOL_DEFINITIONS


def _function_calls(response: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    output = getattr(response, "output", None) or []
    for item in output:
        item_type = getattr(item, "type", None)
        if item_type in {"function_call", "tool_call"}:
            raw_args = getattr(item, "arguments", "{}")
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args or {})
            calls.append(
                {
                    "name": getattr(item, "name", ""),
                    "arguments": args,
                    "call_id": getattr(item, "call_id", None) or getattr(item, "id", ""),
                    "item": item,
                }
            )
    return calls


def run_tool_loop(
    question: str,
    *,
    model: str = DEFAULT_MODEL,
    allow_write: bool = False,
    max_turns: int = 8,
) -> dict[str, Any]:
    messages: list[Any] = [{"role": "user", "content": question}]
    seen: dict[str, dict[str, Any]] = {}
    tool_trace: list[dict[str, Any]] = []

    for turn in range(max_turns):
        result = generate(
            question,
            model=model,
            extra_input=messages,
            tools=TOOL_DEFINITIONS,
            instructions=(
                "You are an internal research assistant. Use lookup_customer for account facts, "
                "calculator for arithmetic, and write_customer_note only when explicitly asked to record a note. "
                "Do not invent balances or policy windows."
            ),
        )
        calls = _function_calls(result.raw)
        if not calls:
            return {
                "text": result.text,
                "turns": turn + 1,
                "tools": tool_trace,
                "trace_id": result.trace_id,
            }

        writes = [call for call in calls if KIND.get(call["name"]) == "write"]
        reads = [call for call in calls if KIND.get(call["name"]) != "write"]
        if writes and reads:
            reads = []
            # A write never runs in parallel with anything else.
            calls = writes[:1]

        def _run(call: dict[str, Any]) -> dict[str, Any]:
            try:
                payload = dispatch(
                    call["name"],
                    call["arguments"],
                    allow_write=allow_write,
                    seen=seen,
                )
                return {"call": call, "output": payload, "ok": True}
            except (PermissionDenied, TypeError, ValueError) as error:
                return {"call": call, "output": {"error": str(error)}, "ok": False}

        if len(reads) > 1 and not writes:
            with ThreadPoolExecutor(max_workers=len(reads)) as pool:
                executed = list(pool.map(_run, reads))
        else:
            executed = [_run(call) for call in calls]

        messages.append(result.raw)
        for item in executed:
            call = item["call"]
            tool_trace.append(
                {"name": call["name"], "arguments": call["arguments"], "output": item["output"]}
            )
            messages.append(
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": json.dumps(item["output"]),
                }
            )

    return {
        "text": "stopped: iteration ceiling",
        "turns": max_turns,
        "tools": tool_trace,
        "trace_id": None,
    }
