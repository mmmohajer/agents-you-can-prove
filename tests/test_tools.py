from agent.permissions import PermissionDenied, dispatch
from agent.tools import calculator, lookup_customer, write_customer_note


def test_calculator() -> None:
    assert calculator("8900 / 100")["value"] == 89


def test_lookup_found() -> None:
    row = lookup_customer("A-1001")
    assert row["plan"] == "standard"


def test_lookup_missing() -> None:
    result = lookup_customer("A-9999")
    assert "no record matches" in result["error"]


def test_write_is_denied_without_approval() -> None:
    try:
        dispatch(
            "write_customer_note",
            {"account_id": "A-1001", "note": "hello", "idempotency_key": "k1"},
            allow_write=False,
        )
    except PermissionDenied as error:
        assert "approval" in error.reason
    else:
        raise AssertionError("expected PermissionDenied")


def test_write_is_idempotent() -> None:
    first = write_customer_note("A-1001", "called support", "test-key-1")
    second = write_customer_note("A-1001", "called support", "test-key-1")
    assert first["ok"] is True
    assert second["deduplicated"] is True
