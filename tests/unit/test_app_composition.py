"""Smoke test: verify create_app() assembles without import or prefix errors."""

from fastapi import FastAPI


def test_create_app_returns_fastapi_instance() -> None:
    """create_app() builds a FastAPI app with all Phase 3 routers registered."""
    from finance_api.composition import create_app

    app = create_app()

    assert isinstance(app, FastAPI)

    # Collect all registered route paths
    paths = {route.path for route in app.routes}  # type: ignore[attr-defined]

    # Phase 3 routes are present
    assert "/debts" in paths
    assert "/goals" in paths
    assert "/trips" in paths
    assert "/buy-list" in paths
    assert "/forecast" in paths
    assert "/recurring" in paths
    assert "/income" in paths
