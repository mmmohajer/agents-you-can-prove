from __future__ import annotations

import json
import sys
from pathlib import Path

from evals.checks import run_check

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.agent import answer_question  # noqa: E402
from agent.paths import EVALS_DIR  # noqa: E402
from agent.tools import calculator, lookup_customer  # noqa: E402


def load_cases() -> list[dict]:
    return json.loads((EVALS_DIR / "cases.json").read_text(encoding="utf-8"))


def _produce(case: dict) -> str:
    tags = case.get("tags") or []
    if "tool" in tags and case["id"] == "customer-missing":
        return str(lookup_customer(case["input"]))
    if "tool" in tags and case["id"] == "calc-cents":
        return str(calculator(case["input"]))
    return answer_question(case["input"]).text


def run_suite(limit: int | None = None) -> dict:
    cases = load_cases() if limit is None else load_cases()[:limit]
    rows = []
    for case in cases:
        actual = _produce(case)
        passed = run_check(case["check"], actual, case["expected"])
        rows.append({**case, "actual": actual, "passed": passed})
    passed = sum(1 for row in rows if row["passed"])
    return {
        "total": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "rows": rows,
    }


if __name__ == "__main__":
    report = run_suite()
    print(f"{report['passed']}/{report['total']} passed")
    for row in report["rows"]:
        mark = "ok" if row["passed"] else "FAIL"
        print(f"{mark:4} {row['id']}")
    raise SystemExit(0 if report["failed"] == 0 else 1)
