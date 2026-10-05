from evals.checks import run_check


def test_substring() -> None:
    assert run_check("substring", "refund within fourteen days", "fourteen")


def test_not_substring() -> None:
    assert run_check("not_substring", "refund within fourteen days", "thirty days")
