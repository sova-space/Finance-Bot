"""Tests for buy list domain queries."""

import uuid
from datetime import UTC

from sqlmodel import Session

from finance_api.domains.buy_list import queries


def test_create_item_appears_in_unbought_list(session: Session) -> None:
    """Created item appears in the default (unbought) list."""
    queries.create_buy_list_item(
        session,
        name="AirPods Pro",
        target_price=9000.0,
        currency="UAH",
        url=None,
        notes=None,
    )

    result = queries.list_buy_list(session, bought="false")
    assert len(result) == 1
    assert result[0]["name"] == "AirPods Pro"
    assert result[0]["bought_at"] is None


def test_mark_bought_moves_item_to_bought_list(session: Session) -> None:
    """Marking an item as bought removes it from unbought, adds it to bought."""
    created = queries.create_buy_list_item(
        session,
        name="Keyboard",
        target_price=5000.0,
        currency="UAH",
        url=None,
        notes=None,
    )
    item_id = uuid.UUID(created["id"])

    from datetime import datetime

    queries.update_buy_list_item(
        session,
        item_id,
        {"bought_at": datetime.now(UTC).replace(tzinfo=None)},
    )

    unbought = queries.list_buy_list(session, bought="false")
    bought = queries.list_buy_list(session, bought="true")
    all_items = queries.list_buy_list(session, bought="all")

    assert not any(i["id"] == str(item_id) for i in unbought)
    assert any(i["id"] == str(item_id) for i in bought)
    assert any(i["id"] == str(item_id) for i in all_items)


def test_patch_nonexistent_item_returns_none(session: Session) -> None:
    """Updating a non-existent item returns None (router maps to 404)."""
    result = queries.update_buy_list_item(session, uuid.uuid4(), {"name": "Ghost"})
    assert result is None
