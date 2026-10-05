# Agents you can prove

Companion repo for the course **Prompt & Context Engineering: Build AI Agents That Work in Production**.

Clone: [github.com/mmmohajer/agents-you-can-prove](https://github.com/mmmohajer/agents-you-can-prove)

This is not a prompt-pack and not a framework tour. You build **one** internal research assistant over a product FAQ, a policy document, and a customer table. The point of the assistant is to give you something real to measure.

The problem it solves: a prompt works in the demo, fails on real users, you reword it, something else breaks, and you cannot tell if you made it better or worse. The habit this repo teaches is: write a case for the failure you saw, run the suite, then change one thing.

You should be able to say, with a file to back it up: here is the success rate, here is the cost, here are the three ways it fails.

Daily model: `gpt-6-luna`. Comparison model, when a lesson asks for it: `gpt-6.1-sol`.

Python 3.11, 3.12, or 3.13. An OpenAI API key. A few dollars of credit.

## What is in here

| Path | Role |
|---|---|
| `agent/` | Wrapper, tokens, prompts, retrieval, tools, the loop |
| `prompts/` | Versioned templates, not strings buried in Python |
| `data/` | FAQ, policy, customer table |
| `evals/` | Cases and the pass/fail runner |
| `traces/` | One JSON line per model call (gitignored) |
| `notes/` | Output from the write tool (gitignored) |
| `tests/` | Checks that run without an API key |

Three tools, and only three: a calculator, a customer lookup, and one write (a note on a customer). Writes need an explicit approval in code.

## Setup

Do this from the repo root. Do not `cd` into a nested `courses/course_1` folder — that path was local only.

### 1. Clone

**macOS / Linux**

```bash
git clone https://github.com/mmmohajer/agents-you-can-prove.git
cd agents-you-can-prove
```

**Windows (PowerShell or Command Prompt)**

```bat
git clone https://github.com/mmmohajer/agents-you-can-prove.git
cd agents-you-can-prove
```

### 2. Virtual environment and packages

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this once for your user, then try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Windows (Command Prompt)**

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Leave the venv on. Your prompt should show `(.venv)`.

### 3. API key

Copy the sample env file, then put your key in `.env`. Never commit `.env`.

**macOS / Linux**

```bash
cp .env.sample .env
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.sample .env
```

**Windows (Command Prompt)**

```bat
copy .env.sample .env
```

Open `.env` and set:

```
OPENAI_API_KEY=sk-...
```

Use your real key. There is no key in this repository.

## Check that it works

These do **not** need a key:

```bash
pytest
```

You want 14 passed.

These **do** need a key and will call the API:

```bash
python -m agent.llm
python -m agent.tokens
python -m agent.agent
python -m evals.runner
```

On Windows, run the same commands after the venv is active. Use `python`, not `python3`, if `python3` is not on your PATH.

| Command | What it does |
|---|---|
| `python -m agent.llm` | One short call. Prints text, tokens, cost, status. Writes `traces/calls.jsonl`. |
| `python -m agent.tokens` | Local token counts. No API spend. |
| `python -m agent.agent` | Retrieves policy/FAQ and answers a refund question. You want fourteen days, not thirty. |
| `python -m evals.runner` | Runs the exam. Prints `ok` / `FAIL` per case, then `N/10 passed`. Exits `1` if anything failed. |

`evals.runner` spends a little on the FAQ and policy cases. The calculator and missing-customer cases stay local.

## How accuracy is measured

Not by reading answers and deciding they look fine.

`evals/cases.json` is a list of cases: a fixed input, an expected string, and a check (`substring`, `not_substring`, and so on). The runner produces an answer and scores pass or fail. Accuracy is passed / total.

A failing case means the **system** failed — prompt, retrieval, or a tool. Open the trace and the retrieved chunks to see which layer. Then add a case for the next failure you see. That is the whole method.
