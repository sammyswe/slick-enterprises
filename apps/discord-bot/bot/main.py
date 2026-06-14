"""Sheriff S Discord bot.

- Logs in as DISCORD_BOT_NAME ("Sheriff S").
- Ensures the configured channels exist.
- Forwards owner messages in idea/sheriff channels to the gateway `POST /sheriff/message`
  and posts the reply back.
- Routes ``#biz-<slug>`` channels to ``POST /businesses/{slug}/message`` (Business Manager).
- Creates per-business channels when ``business_channel_needed`` events arrive.
- Treats natural-language approvals in #approvals as approval intent.
- Subscribes to the Redis events channel to relay cost/system alerts and command results.
"""

from __future__ import annotations

import asyncio
import json

import httpx

from slick_shared.config import get_settings
from slick_shared.discord_channels import BIZ_CATEGORY_NAME, BIZ_CHANNEL_PREFIX, slug_from_channel_name
from slick_shared.logging import setup_logging
from slick_shared.queue import EVENTS_CHANNEL, get_redis

logger = setup_logging("discord-bot")
settings = get_settings()

IDEA_CHANNELS = {"business-ideas", "sheriff-s", "slick-control"}
APPROVAL_CHANNEL = "approvals"
# Map event types -> channel name to relay into (HQ channels).
EVENT_CHANNEL_MAP = {
    "cost_alert": "costs",
    "budget_hard_cap": "system-alerts",
    "build_plan": "approvals",
    "task_started": "agent-updates",
    "task_progress": "agent-updates",
    "wave_started": "agent-updates",
    "agent_task": "agent-updates",
    "evaluation": "agent-updates",
    "milestone_done": "agent-updates",
    "build_report": "agent-updates",
    "task_finished": "agent-updates",
    "skills_synced": "github-prs",
    "business_channel_needed": "agent-updates",
}
# Events that route to the business's #biz-<slug> channel when business_slug is set.
# command_result always; agent_task only for operate runs (run_id present).

DISCORD_MESSAGE_LIMIT = 1900


def chunk_discord_message(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Split long replies so Discord doesn't truncate mid-question."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.rstrip())
    return chunks or [text[:limit]]


async def _post_sheriff(channel: str, author: str, content: str) -> dict:
    url = f"{settings.gateway_public_url}/sheriff/message"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url, json={"channel": channel, "author": author, "content": content}
        )
        resp.raise_for_status()
        return resp.json()


async def _post_business_ops(slug: str, channel: str, author: str, content: str, *, channel_id: str, message_id: str) -> dict:
    url = f"{settings.gateway_public_url}/businesses/{slug}/message"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            json={
                "channel": channel,
                "author": author,
                "content": content,
                "discord_channel_id": channel_id,
                "discord_message_id": message_id,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _patch_business_discord(slug: str, channel_id: str, channel_name: str) -> None:
    url = f"{settings.gateway_public_url}/businesses/{slug}/discord"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            url,
            json={"channel_id": str(channel_id), "channel_name": channel_name},
        )
        resp.raise_for_status()


def build_bot():
    try:
        import discord
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("discord.py not installed") from exc

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    async def ensure_channels(guild) -> None:
        existing = {c.name for c in guild.text_channels}
        for name in settings.discord_channel_list:
            if name not in existing:
                try:
                    await guild.create_text_channel(name)
                    logger.info("Created channel #%s", name)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Could not create #%s: %s", name, exc)

    async def channel_by_name(guild, name: str):
        for c in guild.text_channels:
            if c.name == name:
                return c
        return None

    async def category_by_name(guild, name: str):
        for cat in guild.categories:
            if cat.name == name:
                return cat
        return None

    async def ensure_business_channel(guild, *, slug: str, channel_name: str, business_name: str):
        existing = await channel_by_name(guild, channel_name)
        if existing:
            await _patch_business_discord(slug, str(existing.id), channel_name)
            return existing

        category = await category_by_name(guild, BIZ_CATEGORY_NAME)
        if category is None:
            try:
                category = await guild.create_category(BIZ_CATEGORY_NAME)
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not create category %s: %s", BIZ_CATEGORY_NAME, exc)
                category = None

        try:
            ch = await guild.create_text_channel(
                channel_name,
                category=category,
                topic=f"Operations channel for {business_name} — talk to the Business Manager.",
            )
            await _patch_business_discord(slug, str(ch.id), channel_name)
            welcome = (
                f"🧭 Welcome to **{business_name}** (`#{channel_name}`).\n"
                "I'm the Business Manager for this compartment. "
                "Send operational goals here and I'll elicit requirements, "
                "delegate to specialists, and report results.\n"
                "_(New business ideas go in #business-ideas with Sheriff S.)_"
            )
            await ch.send(welcome)
            logger.info("Created business channel #%s for %s", channel_name, slug)
            return ch
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not create #%s: %s", channel_name, exc)
            return None

    async def relay_events() -> None:
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(EVENTS_CHANNEL)
        logger.info("Subscribed to %s for alerts", EVENTS_CHANNEL)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                event = json.loads(message["data"])
            except (ValueError, TypeError):
                continue

            event_type = event.get("type", "")
            business_slug = event.get("business_slug", "")
            text = event.get("message") or f"{event_type}: {json.dumps(event)}"

            # Route operate results to the business channel (not build progress).
            if event_type == "command_result" and business_slug:
                channel_name = f"{BIZ_CHANNEL_PREFIX}{business_slug}"
                for guild in client.guilds:
                    ch = await channel_by_name(guild, channel_name)
                    if ch:
                        for chunk in chunk_discord_message(text):
                            await ch.send(chunk)
                continue
            if event_type == "agent_task" and business_slug and event.get("run_id"):
                channel_name = f"{BIZ_CHANNEL_PREFIX}{business_slug}"
                for guild in client.guilds:
                    ch = await channel_by_name(guild, channel_name)
                    if ch:
                        for chunk in chunk_discord_message(text):
                            await ch.send(chunk)
                continue

            if event_type == "business_channel_needed":
                channel_name = event.get("channel_name") or f"{BIZ_CHANNEL_PREFIX}{business_slug}"
                for guild in client.guilds:
                    await ensure_business_channel(
                        guild,
                        slug=business_slug,
                        channel_name=channel_name,
                        business_name=event.get("business_name", business_slug),
                    )
                # Also announce in agent-updates.
                channel_name = EVENT_CHANNEL_MAP.get(event_type, "agent-updates")
                for guild in client.guilds:
                    ch = await channel_by_name(guild, channel_name)
                    if ch:
                        for chunk in chunk_discord_message(text):
                            await ch.send(chunk)
                continue

            channel_name = EVENT_CHANNEL_MAP.get(event_type, "system-alerts")
            for guild in client.guilds:
                ch = await channel_by_name(guild, channel_name)
                if ch:
                    for chunk in chunk_discord_message(text):
                        await ch.send(chunk)

    @client.event
    async def on_ready():
        logger.info("Logged in as %s", client.user)
        for guild in client.guilds:
            await ensure_channels(guild)
        client.loop.create_task(relay_events())

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        channel_name = getattr(message.channel, "name", "")

        # Per-business operations channel.
        if channel_name.startswith(BIZ_CHANNEL_PREFIX):
            slug = slug_from_channel_name(channel_name)
            if not slug:
                return
            try:
                data = await _post_business_ops(
                    slug,
                    channel_name,
                    str(message.author),
                    message.content,
                    channel_id=str(message.channel.id),
                    message_id=str(message.id),
                )
                reply = data.get("reply", "🧭 (no reply)")
                for chunk in chunk_discord_message(reply):
                    await message.channel.send(chunk)
            except Exception as exc:  # pragma: no cover
                logger.warning("Business ops call failed: %s", exc)
                await message.channel.send(
                    "🧭 I hit a snag reaching the gateway. Check the logs."
                )
            return

        if channel_name in IDEA_CHANNELS or channel_name == APPROVAL_CHANNEL:
            try:
                data = await _post_sheriff(channel_name, str(message.author), message.content)
                reply = data.get("reply", "🤠 (no reply)")
                for chunk in chunk_discord_message(reply):
                    await message.channel.send(chunk)
            except Exception as exc:  # pragma: no cover
                logger.warning("Sheriff call failed: %s", exc)
                await message.channel.send("🤠 I hit a snag reaching the gateway. Check the logs.")

    return client


def main() -> None:
    if not settings.discord_bot_token:
        logger.warning(
            "DISCORD_BOT_TOKEN is empty. The bot will idle. "
            "Set the token in .env and enable the Message Content Intent to go live."
        )
        asyncio.run(_idle())
        return
    client = build_bot()
    client.run(settings.discord_bot_token)


async def _idle() -> None:
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    main()
