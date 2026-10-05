from __future__ import annotations

import ast
import csv
import operator
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from agent.paths import DATA_DIR, NOTES_DIR

CUSTOMERS_PATH = DATA_DIR / "customers.csv"
KIND = {
    "calculator": "compute",
    "lookup_customer": "read",
    "write_customer_note": "write",
}

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def load_customers() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with CUSTOMERS_PATH.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["account_id"]] = row
    return rows


def _eval_expr(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_BINOPS:
        return float(_ALLOWED_BINOPS[type(node.op)](_eval_expr(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return float(_ALLOWED_BINOPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right)))
    raise ValueError("expression uses a disallowed operation")


def calculator(expression: str) -> dict[str, Any]:
    tree = ast.parse(expression, mode="eval")
    value = _eval_expr(tree.body)
    return {"expression": expression, "value": value}


def lookup_customer(account_id: str) -> dict[str, Any]:
    customers = load_customers()
    row = customers.get(account_id)
    if row is None:
        return {
            "error": (
                f"no record matches {account_id}; "
                "the identifier is one letter, a hyphen, four digits, for example A-1001"
            )
        }
    return row


def write_customer_note(account_id: str, note: str, idempotency_key: str) -> dict[str, Any]:
    customers = load_customers()
    if account_id not in customers:
        return {"error": f"cannot write note: no record matches {account_id}"}
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    line = f"{stamp}\t{idempotency_key}\t{account_id}\t{note}\n"
    path = NOTES_DIR / "customer_notes.tsv"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if idempotency_key in existing:
            return {"ok": True, "deduplicated": True, "account_id": account_id}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    return {"ok": True, "deduplicated": False, "account_id": account_id}


IMPLEMENTATIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "calculator": calculator,
    "lookup_customer": lookup_customer,
    "write_customer_note": write_customer_note,
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "calculator",
        "description": (
            "Evaluate a numeric expression. Use for arithmetic, dates in days, and unit conversions. "
            "Do not use for account balances or policy text. Returns the numeric value. "
            "If the expression is invalid, returns an error naming the problem."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["expression"],
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A numeric expression using + - * / // % **, for example 8900 / 100",
                }
            },
        },
    },
    {
        "type": "function",
        "name": "lookup_customer",
        "description": (
            "Fetch one customer row from the system of record. Use when the question needs a plan, "
            "status, signup date, or balance. Do not use for FAQ or policy questions. "
            "Returns the row, or an error if the identifier does not exist."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["account_id"],
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account identifier, one letter, hyphen, four digits, for example A-1001",
                }
            },
        },
    },
    {
        "type": "function",
        "name": "write_customer_note",
        "description": (
            "Append a note against a customer. Use only after a human or the permission layer has allowed a write. "
            "Do not use to answer a question. Do not retry this tool. "
            "Returns ok, or an error if the account does not exist."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["account_id", "note", "idempotency_key"],
            "properties": {
                "account_id": {"type": "string"},
                "note": {"type": "string"},
                "idempotency_key": {
                    "type": "string",
                    "description": "Caller-generated key so a lost response does not write twice",
                },
            },
        },
    },
]


def new_idempotency_key() -> str:
    return uuid.uuid4().hex
