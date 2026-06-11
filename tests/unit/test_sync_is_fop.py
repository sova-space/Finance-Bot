"""Test that is_fop is never overwritten on the account UPDATE path (Bug #3)."""

from sqlmodel import Session

from finance_api.domains.accounts.models import Account
from finance_api.domains.sync.monobank import _get_or_create_account


def test_is_fop_preserved_on_update(session: Session) -> None:
    """Create an account with is_fop=True, then update it; flag must survive."""
    # Arrange: create an account flagged as FOP
    account = Account(
        monobank_id="fop_account_1",
        name="Monobank FOP UAH",
        currency="UAH",
        account_type="black",  # not 'fop' by type — flag was set manually
        balance=1000.0,
        is_fop=True,
    )
    session.add(account)
    session.commit()

    # Act: simulate the UPDATE path with account_type != 'fop'
    updated = _get_or_create_account(
        session=session,
        mono_id="fop_account_1",
        name="Monobank FOP UAH",
        currency="UAH",
        account_type="black",
        balance=2000.0,
    )
    session.commit()
    session.expire_all()

    # Assert: balance updated, is_fop unchanged
    assert abs(updated.balance - 2000.0) < 0.01
    assert updated.is_fop is True, "is_fop must not be overwritten on the update path"


def test_is_fop_set_on_create_for_fop_type(session: Session) -> None:
    """New accounts with account_type='fop' get is_fop=True."""
    account = _get_or_create_account(
        session=session,
        mono_id="new_fop_account",
        name="Monobank FOP UAH",
        currency="UAH",
        account_type="fop",
        balance=500.0,
    )
    session.commit()

    assert account.is_fop is True


def test_is_fop_false_on_create_for_regular_type(session: Session) -> None:
    """New accounts with account_type='black' get is_fop=False."""
    account = _get_or_create_account(
        session=session,
        mono_id="new_black_account",
        name="Monobank Black UAH",
        currency="UAH",
        account_type="black",
        balance=500.0,
    )
    session.commit()

    assert account.is_fop is False
