"""Cost controller worker.

Polls cumulative spend, emits an alert every $COST_ALERT_STEP_USD, and signals a
hard pause at $COST_HARD_CAP_USD (all LLM work pauses except Sheriff S messages).
Also syncs Cursor dashboard usage every CURSOR_USAGE_SYNC_INTERVAL_SEC when configured.

Enforcement note: the authoritative `can_spend()` check lives in
`slick_shared.cost` and reads spend straight from the DB, so the gateway/orchestrator
enforce the cap even if this worker is down. This worker handles *alerting* + *reporting*.
"""

from __future__ import annotations

import asyncio
import time

from slick_shared.config import get_settings
from slick_shared.cost import build_summary, crossed_alert_boundary, total_spent
from slick_shared.cursor_usage import sync_cursor_usage
from slick_shared.db import get_sessionmaker
from slick_shared.logging import setup_logging
from slick_shared.queue import publish_event

logger = setup_logging("cost-controller")
settings = get_settings()

POLL_SECONDS = 10


async def _maybe_sync_cursor_usage(last_sync: float) -> float:
    """Return updated last_sync timestamp."""
    interval = max(60, settings.cursor_usage_sync_interval_sec)
    if time.monotonic() - last_sync < interval:
        return last_sync
    sessionmaker = get_sessionmaker()
    try:
        async with sessionmaker() as session:
            row, err = await sync_cursor_usage(session)
        if err:
            logger.warning("Cursor usage sync failed: %s", err)
        elif row:
            logger.info(
                "Cursor usage synced: %.1f%% spent, included=%dc limit=%dc",
                row.total_percent_used,
                row.included_spend_cents,
                row.limit_cents,
            )
    except Exception as exc:  # pragma: no cover
        logger.exception("Cursor usage sync error: %s", exc)
    return time.monotonic()


async def main() -> None:
    sessionmaker = get_sessionmaker()
    previous_spend = 0.0
    paused_announced = False
    last_cursor_sync = 0.0

    logger.info(
        "Cost controller started. budget=$%.2f alert_step=$%.2f hard_cap=$%.2f "
        "cursor_sync_interval=%ds",
        settings.cost_budget_usd,
        settings.cost_alert_step_usd,
        settings.cost_hard_cap_usd,
        settings.cursor_usage_sync_interval_sec,
    )

    while True:
        try:
            last_cursor_sync = await _maybe_sync_cursor_usage(last_cursor_sync)

            async with sessionmaker() as session:
                spent = await total_spent(session)

                if crossed_alert_boundary(previous_spend, spent, settings.cost_alert_step_usd):
                    summary = await build_summary(session)
                    await publish_event(
                        {
                            "type": "cost_alert",
                            "channel": "costs",
                            "spent_usd": round(spent, 2),
                            "budget_usd": settings.cost_budget_usd,
                            "remaining_usd": round(summary.remaining_usd, 2),
                            "message": f"💸 Spend crossed ${int(spent // settings.cost_alert_step_usd) * int(settings.cost_alert_step_usd)}. "
                            f"${spent:.2f} of ${settings.cost_budget_usd:.2f} used.",
                        }
                    )
                    logger.info("Cost alert emitted at $%.2f", spent)

                if spent >= settings.cost_hard_cap_usd and not paused_announced:
                    await publish_event(
                        {
                            "type": "budget_hard_cap",
                            "channel": "system-alerts",
                            "spent_usd": round(spent, 2),
                            "message": "🛑 Hard cap reached. All LLM work paused except Sheriff S "
                            "messages. Manual override required to resume.",
                        }
                    )
                    logger.warning("HARD CAP reached at $%.2f - LLM work paused.", spent)
                    paused_announced = True
                elif spent < settings.cost_hard_cap_usd:
                    paused_announced = False

                previous_spend = spent
        except Exception as exc:  # pragma: no cover
            logger.exception("cost-controller poll error: %s", exc)

        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
