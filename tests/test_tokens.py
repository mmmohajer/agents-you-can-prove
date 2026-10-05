from agent.tokens import budget, count_tokens


def test_count_tokens_is_positive() -> None:
    assert count_tokens("the refund window is fourteen days") > 0


def test_code_uses_more_tokens_than_similar_prose() -> None:
    prose = "look up the customer account status please"
    code = "def lookup_customer_account_status():\n    return None"
    assert count_tokens(code) >= count_tokens(prose)


def test_budget_leaves_output_reserve() -> None:
    result = budget(128000, {"system": 300, "passages": 2500, "history": 1800}, 1000)
    assert result["remaining"] == 128000 - 300 - 2500 - 1800 - 1000
