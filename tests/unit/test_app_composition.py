"""Smoke test: verify create_app() assembles without import or prefix errors."""

from fastapi import FastAPI


def test_create_app_returns_fastapi_instance() -> None:
    """create_app() builds a FastAPI app with all Phase 3 routers registered."""
    from finance_api.composition import create_app

    app = create_app()

    assert isinstance(app, FastAPI)

    # Collect all registered route paths. FastAPI/Starlette internals can wrap
    # included routers differently across versions; OpenAPI is the stable view.
    paths = set(app.openapi()["paths"])

    # Phase 3 routes are present
    assert "/debts" in paths
    assert "/goals" in paths
    assert "/trips" in paths
    assert "/buy-list" in paths
    assert "/forecast" in paths
    assert "/recurring" in paths
    assert "/income" in paths
    assert "/accounts/summary" in paths
    assert "/accounts/manual-balances" in paths
    assert "/brief" in paths
    assert "/blockers" in paths
    assert "/actions" in paths
