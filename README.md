# Course 1 — research assistant

Python project for **Prompt & Context Engineering**. One internal research assistant over a product FAQ, a policy document, and a customer table.

Daily model: `gpt-6-luna`. Comparison model: `gpt-6.1-sol`.

## Setup

```bash
cd courses/course_1
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
```

Put your OpenAI key in `.env`:

```
OPENAI_API_KEY=sk-...
```

## Tests that do not need a key

```bash
pytest
```

## Calls that need a key

```bash
python -m agent.llm
python -m agent.tokens
python -m agent.agent
python -m evals.runner
```

`evals.runner` will spend a little money on FAQ and policy cases. Tool cases are local.

## Layout

- `agent/` — wrapper, tokens, prompts, retrieval, tools, loop
- `prompts/` — versioned templates
- `data/` — FAQ, policy, customers
- `evals/` — cases and the gate
- `traces/` — one JSON line per model call (gitignored)
- `notes/` — write-tool output (gitignored)
