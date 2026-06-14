from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def _mock_db_engine(*, db_ok: bool = True) -> MagicMock:
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()

    mock_context = AsyncMock()
    if db_ok:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
    else:
        mock_context.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_engine.connect.return_value = mock_context
    return mock_engine


def test_app_has_title() -> None:
    assert app.title == "Price Pulse Pro API"


def test_health_ok_when_db_reachable() -> None:
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    with (
        patch("app.main.get_engine", return_value=_mock_db_engine(db_ok=True)),
        patch("app.main.Redis.from_url", return_value=mock_redis),
    ):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"


def test_health_fails_closed_when_db_unreachable() -> None:
    with patch("app.main.get_engine", return_value=_mock_db_engine(db_ok=False)):
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "down"


def test_api_v1_unknown_route_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
