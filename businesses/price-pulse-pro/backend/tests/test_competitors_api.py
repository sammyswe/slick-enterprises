"""Integration tests for /api/v1/competitors CRUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _valid_payload(**overrides: object) -> dict:
    payload = {
        "name": "Acme Pricing",
        "pricing_page_url": "https://example.com/pricing",
        "scrape_strategy": "html",
        "currency": "USD",
        "active": True,
    }
    payload.update(overrides)
    return payload


def test_create_competitor_returns_201_with_persisted_id(client: TestClient) -> None:
    response = client.post("/api/v1/competitors", json=_valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] >= 1
    assert body["name"] == "Acme Pricing"
    assert body["pricing_page_url"] == "https://example.com/pricing"
    assert body["scrape_strategy"] == "html"
    assert body["currency"] == "USD"
    assert body["active"] is True

    get_response = client.get(f"/api/v1/competitors/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_invalid_pricing_page_url_returns_422_with_field_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/competitors",
        json=_valid_payload(pricing_page_url="not-a-valid-url"),
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    field_errors = [err["loc"][-1] for err in body["detail"]]
    assert "pricing_page_url" in field_errors


def test_list_supports_pagination_and_active_filter(client: TestClient) -> None:
    client.post(
        "/api/v1/competitors",
        json=_valid_payload(name="Active One", active=True),
    )
    client.post(
        "/api/v1/competitors",
        json=_valid_payload(name="Inactive One", active=False),
    )
    client.post(
        "/api/v1/competitors",
        json=_valid_payload(name="Active Two", active=True),
    )

    page = client.get("/api/v1/competitors", params={"offset": 0, "limit": 2})
    assert page.status_code == 200
    page_body = page.json()
    assert page_body["total"] == 3
    assert page_body["offset"] == 0
    assert page_body["limit"] == 2
    assert len(page_body["items"]) == 2

    active_only = client.get("/api/v1/competitors", params={"active": True})
    assert active_only.status_code == 200
    active_body = active_only.json()
    assert active_body["total"] == 2
    assert all(item["active"] for item in active_body["items"])

    inactive_only = client.get("/api/v1/competitors", params={"active": False})
    assert inactive_only.status_code == 200
    inactive_body = inactive_only.json()
    assert inactive_body["total"] == 1
    assert inactive_body["items"][0]["name"] == "Inactive One"


def test_get_update_and_delete_competitor(client: TestClient) -> None:
    created = client.post("/api/v1/competitors", json=_valid_payload()).json()
    competitor_id = created["id"]

    updated = client.patch(
        f"/api/v1/competitors/{competitor_id}",
        json={
            "name": "Updated Name",
            "scrape_strategy": "playwright",
            "active": False,
        },
    )
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["name"] == "Updated Name"
    assert updated_body["scrape_strategy"] == "playwright"
    assert updated_body["active"] is False

    deleted = client.delete(f"/api/v1/competitors/{competitor_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/competitors/{competitor_id}")
    assert missing.status_code == 404
