"""Integration tests for competitor product (plan tier) API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def competitor_id(client: TestClient) -> int:
    response = client.post(
        "/api/v1/competitors",
        json={
            "name": "Acme Pricing",
            "pricing_page_url": "https://acme.example/pricing",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def other_competitor_id(client: TestClient) -> int:
    response = client.post(
        "/api/v1/competitors",
        json={
            "name": "Beta Pricing",
            "pricing_page_url": "https://beta.example/pricing",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _product_payload(
    name: str,
    *,
    selector_hint: str = ".plan-price",
    expected_currency: str = "USD",
    display_order: int = 0,
) -> dict:
    return {
        "name": name,
        "selector_hint": selector_hint,
        "expected_currency": expected_currency,
        "display_order": display_order,
    }


def test_list_products_empty(client: TestClient, competitor_id: int) -> None:
    response = client.get(f"/api/v1/competitors/{competitor_id}/products")
    assert response.status_code == 200
    assert response.json() == []


def test_bulk_upsert_creates_products(client: TestClient, competitor_id: int) -> None:
    payload = {
        "products": [
            _product_payload("Starter", selector_hint="#starter-price", display_order=1),
            _product_payload("Pro", selector_hint="//div[@data-plan='pro']", display_order=0),
        ]
    }
    response = client.put(f"/api/v1/competitors/{competitor_id}/products", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    names = {item["name"] for item in body}
    assert names == {"Starter", "Pro"}
    pro = next(item for item in body if item["name"] == "Pro")
    assert pro["selector_hint"] == "//div[@data-plan='pro']"
    assert pro["expected_currency"] == "USD"
    assert pro["display_order"] == 0
    assert pro["competitor_id"] == competitor_id


def test_bulk_upsert_replaces_product_set_atomically(
    client: TestClient, competitor_id: int
) -> None:
    first = client.put(
        f"/api/v1/competitors/{competitor_id}/products",
        json={
            "products": [
                _product_payload("Basic", selector_hint=".basic"),
                _product_payload("Enterprise", selector_hint=".enterprise"),
            ]
        },
    )
    assert first.status_code == 200
    assert len(first.json()) == 2

    second = client.put(
        f"/api/v1/competitors/{competitor_id}/products",
        json={"products": [_product_payload("Team", selector_hint=".team", display_order=2)]},
    )
    assert second.status_code == 200
    body = second.json()
    assert len(body) == 1
    assert body[0]["name"] == "Team"

    listed = client.get(f"/api/v1/competitors/{competitor_id}/products")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Team"]


def test_bulk_upsert_requires_selector_hint(client: TestClient, competitor_id: int) -> None:
    response = client.put(
        f"/api/v1/competitors/{competitor_id}/products",
        json={"products": [{"name": "Basic", "expected_currency": "USD", "display_order": 0}]},
    )
    assert response.status_code == 422


def test_bulk_upsert_rejects_duplicate_names_in_payload(
    client: TestClient, competitor_id: int
) -> None:
    response = client.put(
        f"/api/v1/competitors/{competitor_id}/products",
        json={
            "products": [
                _product_payload("Pro", selector_hint=".pro-a"),
                _product_payload("Pro", selector_hint=".pro-b"),
            ]
        },
    )
    assert response.status_code == 422


def test_products_scoped_to_competitor(
    client: TestClient, competitor_id: int, other_competitor_id: int
) -> None:
    client.put(
        f"/api/v1/competitors/{competitor_id}/products",
        json={"products": [_product_payload("Shared Name", selector_hint=".acme")]},
    )
    client.put(
        f"/api/v1/competitors/{other_competitor_id}/products",
        json={"products": [_product_payload("Shared Name", selector_hint=".beta")]},
    )

    acme = client.get(f"/api/v1/competitors/{competitor_id}/products")
    beta = client.get(f"/api/v1/competitors/{other_competitor_id}/products")
    assert acme.status_code == 200
    assert beta.status_code == 200
    assert len(acme.json()) == 1
    assert len(beta.json()) == 1
    assert acme.json()[0]["selector_hint"] == ".acme"
    assert beta.json()[0]["selector_hint"] == ".beta"


def test_unique_name_per_competitor_on_create(
    client: TestClient, competitor_id: int
) -> None:
    first = client.post(
        f"/api/v1/competitors/{competitor_id}/products",
        json=_product_payload("Growth", selector_hint=".growth"),
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/api/v1/competitors/{competitor_id}/products",
        json=_product_payload("Growth", selector_hint=".growth-duplicate"),
    )
    assert duplicate.status_code == 409


def test_create_product_requires_selector_hint(client: TestClient, competitor_id: int) -> None:
    response = client.post(
        f"/api/v1/competitors/{competitor_id}/products",
        json={"name": "Solo", "expected_currency": "EUR", "display_order": 0},
    )
    assert response.status_code == 422


def test_list_products_returns_404_for_unknown_competitor(client: TestClient) -> None:
    response = client.get("/api/v1/competitors/999999/products")
    assert response.status_code == 404
