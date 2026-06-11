"""Named time periods used across queries and bot handlers."""

THIS_MONTH = "this_month"
LAST_MONTH = "last_month"
LAST_7D = "last_7d"
LAST_30D = "last_30d"
LAST_90D = "last_90d"

ALL: frozenset[str] = frozenset({THIS_MONTH, LAST_MONTH, LAST_7D, LAST_30D, LAST_90D})

SALARY_ANCHORED: frozenset[str] = frozenset({THIS_MONTH, LAST_MONTH})
