"""Transaction spending modes."""

SOLO = "solo"
COUPLE = "couple"

ALL: frozenset[str] = frozenset({SOLO, COUPLE})
