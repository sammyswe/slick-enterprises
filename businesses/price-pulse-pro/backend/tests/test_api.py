from fastapi.testclient import TestClient

from app.main import app


def test_root_lists_service_metadata() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "price-pulse-pro-api"
    assert body["health"] == "/health"


def test_health_returns_dependency_status() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_context

    with patch("app.main.get_engine", return_value=mock_engine):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "price-pulse-pro-api"
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] == "ok"
    assert "redis" in body
