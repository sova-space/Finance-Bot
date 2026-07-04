from __future__ import annotations

from finance_api.routers import operator


def test_finance_brief_completed_sync(monkeypatch) -> None:
    monkeypatch.setattr(
        operator,
        "get_sync_health",
        lambda: {"status": "completed", "tx_imported": 3},
    )

    brief = operator._finance_brief()

    assert brief["domain"] == "finance"
    assert brief["status"] == "ok"
    assert brief["blockers"] == []
    assert brief["actions"][0]["id"] == "finance.refresh"


def test_finance_brief_failed_sync(monkeypatch) -> None:
    monkeypatch.setattr(
        operator,
        "get_sync_health",
        lambda: {"status": "failed", "error": "boom"},
    )

    brief = operator._finance_brief()

    assert brief["status"] == "blocked"
    assert brief["blockers"] == [
        {
            "id": "finance.sync_failed",
            "severity": "blocked",
            "summary": "Monobank sync failed",
            "needs_human": False,
            "details": "boom",
        }
    ]


def test_finance_blockers_db_unavailable(monkeypatch) -> None:
    def raise_db_error() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(operator, "get_sync_health", raise_db_error)

    brief = operator._finance_brief()

    assert brief["status"] == "blocked"
    assert brief["blockers"][0]["id"] == "finance.db_unavailable"