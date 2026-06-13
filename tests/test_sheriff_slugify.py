from gateway.sheriff_flow import slugify, APPROVAL_PATTERNS


def test_slugify_basic():
    assert slugify("Example AI Lead Scraper!") == "example-ai-lead-scraper"


def test_slugify_empty_fallback():
    assert slugify("***") == "new-business"


def test_approval_patterns():
    assert APPROVAL_PATTERNS.search("yes, approved, go ahead")
    assert APPROVAL_PATTERNS.search("ship it")
    assert not APPROVAL_PATTERNS.search("what do you think?")
