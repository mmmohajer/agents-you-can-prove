from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.tools import IMPLEMENTATIONS, KIND


@dataclass
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionDenied(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def decide(name: str, allow_write: bool) -> PermissionDecision:
    kind = KIND.get(name)
    if kind is None:
        return PermissionDecision(False, f"unknown tool: {name}")
    if kind == "write" and not allow_write:
        return PermissionDecision(False, "write requires an explicit approval")
    return PermissionDecision(True, "ok")


def dispatch(
    name: str,
    arguments: dict[str, Any],
    *,
    allow_write: bool = False,
    seen: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    decision = decide(name, allow_write)
    if not decision.allowed:
        raise PermissionDenied(decision.reason)
    key = f"{name}:{sorted(arguments.items())}"
    if seen is not None and key in seen:
        return {**seen[key], "replayed": True}
    impl = IMPLEMENTATIONS[name]
    result = impl(**arguments)
    if seen is not None:
        seen[key] = result
    return result
