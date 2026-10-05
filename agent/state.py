from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    goal: str
    facts: dict[str, str] = field(default_factory=dict)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    stall_count: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0

    def record(self, approach: str, outcome: str, retry: str, learned: str | None) -> None:
        self.attempts.append(
            {
                "approach": approach,
                "outcome": outcome,
                "retry": retry,
                "learned": learned,
            }
        )
        if learned:
            self.stall_count = 0
        else:
            self.stall_count += 1

    def render(self) -> str:
        facts = "\n".join(f"- {key}: {value}" for key, value in self.facts.items()) or "- none"
        attempts = "\n".join(
            f"- {item['approach']} → {item['outcome']} ({item['retry']})"
            for item in self.attempts[-8:]
        ) or "- none"
        return f"goal: {self.goal}\nfacts:\n{facts}\nattempts:\n{attempts}"
