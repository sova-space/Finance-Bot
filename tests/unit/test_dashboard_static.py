"""Browser dashboard static serving tests."""

from fastapi.testclient import TestClient

from finance_api.composition import create_app


def test_app_serves_browser_dashboard_shell() -> None:
    """The dashboard endpoint serves the built React app shell."""
    client = TestClient(create_app())

    response = client.get("/app")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root"></div>' in response.text
    assert "/app/assets/" in response.text


def test_app_serves_built_dashboard_assets() -> None:
    """The dashboard asset mount serves files referenced by the shell."""
    client = TestClient(create_app())
    shell = client.get("/app")
    asset_name = shell.text.split("/app/assets/")[1].split('"')[0]

    response = client.get(f"/app/assets/{asset_name}")

    assert response.status_code == 200
