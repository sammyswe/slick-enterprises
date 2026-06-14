"""Integration tests for competitor and product configuration APIs."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _competitor_payload(**overrides: object) -> dict:
    payload = {
        "name": "Acme Pricing",
        "pricing_page_url": "https://example.com/pricing",
        "scrape_strategy": "html",
        "currency": "USD",
        "active": True,
    }
    payload.update(overrides)
    return payload


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


def _create_competitor(client: TestClient, **overrides: object) -> dict:
    response = client.post("/api/v1/competitors", json=_competitor_payload(**overrides))
    assert response.status_code == 201
    return response.json()


class TestCompetitorLifecycle:
    def test_create_read_update_delete_happy_path(self, client: TestClient) -> None:
        created = _create_competitor(client, name="Lifecycle Co")
        competitor_id = created["id"]

        fetched = client.get(f"/api/v1/competitors/{competitor_id}")
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Lifecycle Co"

        updated = client.patch(
            f"/api/v1/competitors/{competitor_id}",
            json={
                "name": "Lifecycle Co Updated",
                "scrape_strategy": "playwright",
                "currency": "eur",
                "active": False,
            },
        )
        assert updated.status_code == 200
        body = updated.json()
        assert body["name"] == "Lifecycle Co Updated"
        assert body["scrape_strategy"] == "playwright"
        assert body["currency"] == "EUR"
        assert body["active"] is False

        deleted = client.delete(f"/api/v1/competitors/{competitor_id}")
        assert deleted.status_code == 204

        missing = client.get(f"/api/v1/competitors/{competitor_id}")
        assert missing.status_code == 404

    def test_validation_errors_on_create_and_update(self, client: TestClient) -> None:
        invalid_url = client.post(
            "/api/v1/competitors",
            json=_competitor_payload(pricing_page_url="not-a-url"),
        )
        assert invalid_url.status_code == 422
        assert "pricing_page_url" in {err["loc"][-1] for err in invalid_url.json()["detail"]}

        empty_name = client.post(
            "/api/v1/competitors",
            json=_competitor_payload(name=""),
        )
        assert empty_name.status_code == 422

        invalid_strategy = client.post(
            "/api/v1/competitors",
            json=_competitor_payload(scrape_strategy="selenium"),
        )
        assert invalid_strategy.status_code == 422

        created = _create_competitor(client)
        bad_update = client.patch(
            f"/api/v1/competitors/{created['id']}",
            json={"pricing_page_url": "ftp://bad"},
        )
        assert bad_update.status_code == 422

    def test_pagination_and_active_filter(self, client: TestClient) -> None:
        for index, (name, active) in enumerate(
            [
                ("Alpha", True),
                ("Bravo", False),
                ("Charlie", True),
                ("Delta", True),
            ],
            start=1,
        ):
            _create_competitor(client, name=name, active=active)

        first_page = client.get("/api/v1/competitors", params={"offset": 0, "limit": 2})
        assert first_page.status_code == 200
        page = first_page.json()
        assert page["total"] == 4
        assert page["offset"] == 0
        assert page["limit"] == 2
        assert len(page["items"]) == 2

        second_page = client.get("/api/v1/competitors", params={"offset": 2, "limit": 2})
        assert second_page.status_code == 200
        page_two = second_page.json()
        assert page_two["total"] == 4
        assert len(page_two["items"]) == 2

        beyond_total = client.get("/api/v1/competitors", params={"offset": 10, "limit": 5})
        assert beyond_total.status_code == 200
        assert beyond_total.json()["items"] == []

        active_only = client.get("/api/v1/competitors", params={"active": True})
        assert active_only.status_code == 200
        active_body = active_only.json()
        assert active_body["total"] == 3
        assert all(item["active"] for item in active_body["items"])

        inactive_only = client.get("/api/v1/competitors", params={"active": False})
        assert inactive_only.status_code == 200
        inactive_body = inactive_only.json()
        assert inactive_body["total"] == 1
        assert inactive_body["items"][0]["name"] == "Bravo"


class TestProductLifecycle:
    def test_create_list_bulk_replace_and_delete_via_competitor_removal(
        self, client: TestClient
    ) -> None:
        competitor = _create_competitor(client, name="Plan Host")
        competitor_id = competitor["id"]

        empty = client.get(f"/api/v1/competitors/{competitor_id}/products")
        assert empty.status_code == 200
        assert empty.json() == []

        created = client.post(
            f"/api/v1/competitors/{competitor_id}/products",
            json=_product_payload("Starter", selector_hint="#starter", display_order=1),
        )
        assert created.status_code == 201
        starter = created.json()
        assert starter["name"] == "Starter"
        assert starter["competitor_id"] == competitor_id

        bulk = client.put(
            f"/api/v1/competitors/{competitor_id}/products",
            json={
                "products": [
                    _product_payload("Pro", selector_hint=".pro", display_order=0),
                    _product_payload("Enterprise", selector_hint=".enterprise", display_order=2),
                ]
            },
        )
        assert bulk.status_code == 200
        bulk_body = bulk.json()
        assert {item["name"] for item in bulk_body} == {"Pro", "Enterprise"}
        assert bulk_body[0]["name"] == "Pro"

        listed = client.get(f"/api/v1/competitors/{competitor_id}/products")
        assert listed.status_code == 200
        assert [item["name"] for item in listed.json()] == ["Pro", "Enterprise"]

        removed = client.delete(f"/api/v1/competitors/{competitor_id}")
        assert removed.status_code == 204

        missing_products = client.get(f"/api/v1/competitors/{competitor_id}/products")
        assert missing_products.status_code == 404

    def test_product_validation_errors(self, client: TestClient) -> None:
        competitor_id = _create_competitor(client)["id"]

        missing_selector = client.post(
            f"/api/v1/competitors/{competitor_id}/products",
            json={"name": "Solo", "expected_currency": "USD", "display_order": 0},
        )
        assert missing_selector.status_code == 422

        duplicate_in_bulk = client.put(
            f"/api/v1/competitors/{competitor_id}/products",
            json={
                "products": [
                    _product_payload("Pro", selector_hint=".pro-a"),
                    _product_payload("Pro", selector_hint=".pro-b"),
                ]
            },
        )
        assert duplicate_in_bulk.status_code == 422

        first = client.post(
            f"/api/v1/competitors/{competitor_id}/products",
            json=_product_payload("Growth", selector_hint=".growth"),
        )
        assert first.status_code == 201

        duplicate_create = client.post(
            f"/api/v1/competitors/{competitor_id}/products",
            json=_product_payload("Growth", selector_hint=".growth-dup"),
        )
        assert duplicate_create.status_code == 409

        unknown_competitor = client.get("/api/v1/competitors/999999/products")
        assert unknown_competitor.status_code == 404


class TestConfigurationFlow:
    def test_end_to_end_competitor_and_product_configuration(self, client: TestClient) -> None:
        alpha = _create_competitor(
            client,
            name="Alpha SaaS",
            pricing_page_url="https://alpha.example/pricing",
            scrape_strategy="html",
        )
        beta = _create_competitor(
            client,
            name="Beta SaaS",
            pricing_page_url="https://beta.example/pricing",
            scrape_strategy="playwright",
            active=False,
        )

        alpha_products = client.put(
            f"/api/v1/competitors/{alpha['id']}/products",
            json={
                "products": [
                    _product_payload("Basic", selector_hint=".alpha-basic", display_order=0),
                    _product_payload("Plus", selector_hint=".alpha-plus", display_order=1),
                ]
            },
        )
        assert alpha_products.status_code == 200

        beta_products = client.put(
            f"/api/v1/competitors/{beta['id']}/products",
            json={"products": [_product_payload("Team", selector_hint=".beta-team")]},
        )
        assert beta_products.status_code == 200

        competitors = client.get("/api/v1/competitors", params={"limit": 10})
        assert competitors.status_code == 200
        competitor_body = competitors.json()
        assert competitor_body["total"] == 2

        alpha_list = client.get(f"/api/v1/competitors/{alpha['id']}/products")
        beta_list = client.get(f"/api/v1/competitors/{beta['id']}/products")
        assert [item["name"] for item in alpha_list.json()] == ["Basic", "Plus"]
        assert [item["name"] for item in beta_list.json()] == ["Team"]

        patched = client.patch(
            f"/api/v1/competitors/{beta['id']}",
            json={"active": True, "name": "Beta SaaS Live"},
        )
        assert patched.status_code == 200
        assert patched.json()["active"] is True

        active_competitors = client.get("/api/v1/competitors", params={"active": True})
        assert active_competitors.json()["total"] == 2
