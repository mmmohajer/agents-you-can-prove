from __future__ import annotations

from dataclasses import dataclass

from agent.llm import DEFAULT_MODEL
from agent.loop import run_tool_loop
from agent.prompts import load
from agent.retrieve import format_context, retrieve
from agent.state import AgentState

COST_CEILING_USD = 0.50
MAX_ITERATIONS = 8
STALL_LIMIT = 3


@dataclass
class AgentRun:
    text: str
    stop_reason: str
    state: AgentState
    tools: list


def answer_question(question: str, model: str = DEFAULT_MODEL) -> AgentRun:
    chunks = retrieve(question, k=3)
    context = format_context(chunks)
    prompt, version = load("answer_from_context", context=context, user_question=question)
    from agent.llm import generate

    result = generate(prompt, model=model, prompt_version=version)
    return AgentRun(
        text=result.text,
        stop_reason="single_call",
        state=AgentState(goal=question),
        tools=[],
    )


def run_agent(
    goal: str,
    *,
    model: str = DEFAULT_MODEL,
    allow_write: bool = False,
    cost_ceiling_usd: float = COST_CEILING_USD,
) -> AgentRun:
    state = AgentState(goal=goal)
    last_text = ""
    tools: list = []

    for iteration in range(MAX_ITERATIONS):
        if state.cost_usd >= cost_ceiling_usd:
            return AgentRun("stopped: cost ceiling", "cost_ceiling", state, tools)
        if state.stall_count >= STALL_LIMIT:
            return AgentRun("stopped: no progress", "stall", state, tools)

        result = run_tool_loop(
            f"{state.render()}\n\nCurrent goal: {goal}",
            model=model,
            allow_write=allow_write,
        )
        last_text = result["text"]
        tools.extend(result["tools"])
        learned = None
        if result["tools"]:
            learned = result["tools"][-1]["name"]
            state.record(learned, "ran", "do_not_retry" if learned == "write_customer_note" else "ok", learned)
        else:
            state.record("answer", "completed", "do_not_retry", "final")
            return AgentRun(last_text, "goal_achieved", state, tools)

    return AgentRun(last_text or "stopped: iteration ceiling", "iteration_ceiling", state, tools)


if __name__ == "__main__":
    run = answer_question("How long do I have to return a defective Standard purchase?")
    print(run.stop_reason)
    print(run.text)
