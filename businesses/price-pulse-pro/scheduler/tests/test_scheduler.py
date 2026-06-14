from app.queue import ScrapeJob


def test_scrape_job_dataclass() -> None:
    job = ScrapeJob(competitor_id=3, product_url="https://example.com/item")
    assert job.competitor_id == 3
    assert job.product_url == "https://example.com/item"
