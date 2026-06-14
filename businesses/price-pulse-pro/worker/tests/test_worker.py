from app.queue import ScrapeJob, process_job


def test_scrape_job_from_payload() -> None:
    job = ScrapeJob.from_payload(
        {"competitor_id": 7, "product_url": "https://example.com/product"}
    )
    assert job.competitor_id == 7
    assert job.product_url == "https://example.com/product"


def test_process_job_without_api_returns_recorded_false() -> None:
    job = ScrapeJob(competitor_id=1, product_url="https://example.com/p")
    result = process_job(job)
    assert result["competitor_id"] == 1
    assert result["recorded"] is False
