"""APScheduler jobs for the pockets domain."""

import structlog
from sqlmodel import Session

from finance_api.core.db.engine import engine
from finance_api.domains.pockets.queries import reset_all_pockets

log = structlog.get_logger(__name__)


def reset_pockets_job() -> None:
    """Reset all pocket balances to their monthly_budget.

    Scheduled to run on the 1st of each month at 00:05 UTC.
    """
    with Session(engine) as session:
        count = reset_all_pockets(session)
    log.info("pocket_monthly_reset_complete", pockets_reset=count)
