"""Tests for business naming helpers."""

from gateway.sheriff_flow import fallback_business_identity, parse_business_identity, slugify


def test_parse_business_identity():
    text = "NAME: Amazon Affiliate Studio\nSLUG: amazon-affiliate-studio\n"
    assert parse_business_identity(text) == ("Amazon Affiliate Studio", "amazon-affiliate-studio")


def test_fallback_strips_filler():
    idea = "A mix of both initially it should target amazon affiliate links and product reviews"
    name, slug = fallback_business_identity(idea)
    assert name == "Amazon Affiliate Links Product"
    assert slug == "amazon-affiliate-links-product"


def test_slugify_still_works():
    assert slugify("Example AI Lead Scraper!") == "example-ai-lead-scraper"
