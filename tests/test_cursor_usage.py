"""Tests for Cursor dashboard usage parsing."""

from slick_shared.cursor_usage import parse_usage_response


def test_parse_usage_response_normalises_cents_and_percents():
    raw = {
        "billingCycleStart": "1768399334000",
        "billingCycleEnd": "1771077734000",
        "planUsage": {
            "totalSpend": 23222,
            "includedSpend": 20000,
            "bonusSpend": 3222,
            "remaining": 16778,
            "limit": 40000,
            "autoPercentUsed": 5.5,
            "apiPercentUsed": 46.4,
            "totalPercentUsed": 15.48,
        },
        "spendLimitUsage": {
            "totalSpend": 100,
            "individualLimit": 10000,
        },
        "displayMessage": "You've used 46% of your usage limit",
    }
    parsed = parse_usage_response(raw)
    assert parsed["included_spend_cents"] == 20000
    assert parsed["limit_cents"] == 40000
    assert parsed["total_percent_used"] == 15.48
    assert parsed["api_percent_used"] == 46.4
    assert parsed["on_demand_spend_cents"] == 100
    assert parsed["display_message"] == "You've used 46% of your usage limit"
    assert parsed["billing_cycle_start"] is not None
