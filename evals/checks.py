from __future__ import annotations


def run_check(check: str, actual: str, expected: str) -> bool:
    actual_l = actual.lower()
    expected_l = expected.lower()
    if check == "exact":
        return actual.strip() == expected.strip()
    if check == "substring":
        return expected_l in actual_l
    if check == "not_substring":
        return expected_l not in actual_l
    if check == "schema":
        return bool(actual)
    raise ValueError(f"unknown check: {check}")
