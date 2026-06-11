"""Account balance endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from finance_api.core.db.engine import engine
from finance_api.domains.accounts.models import Account
from finance_api.domains.insights.queries import get_account_balances
from finance_api.schemas import AccountBalance

router = APIRouter()


class AccountPatch(BaseModel):
    """Request body for PATCH /accounts/{id}."""

    is_fop: bool


@router.get(
    "",
    response_model=list[AccountBalance],
    summary="List account balances",
    description=(
        "Returns the current balance for every Monobank account that has been synced. "
        "Returns an empty list if no sync has run yet — call `POST /sync` first."
    ),
)
def list_accounts() -> list[dict[str, object]]:
    """Return current balances for all synced accounts."""
    return get_account_balances()


@router.patch(
    "/{account_id}",
    response_model=AccountBalance,
    summary="Update account flags",
    description="Toggle is_fop to mark an account as a salary/FOP account.",
)
def patch_account(account_id: str, body: AccountPatch) -> dict[str, object]:
    """Toggle is_fop flag on an account."""
    with Session(engine) as session:
        account = session.exec(select(Account).where(Account.id == account_id)).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        account.is_fop = body.is_fop
        session.add(account)
        session.commit()
        session.refresh(account)
        return {
            "account_id": str(account.id),
            "name": account.name,
            "currency": account.currency,
            "balance": account.balance,
            "type": account.account_type,
            "is_fop": account.is_fop,
            "synced_at": account.synced_at.isoformat() if account.synced_at else None,
        }
