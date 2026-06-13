"""Sheriff S Discord bot.

- Logs in as DISCORD_BOT_NAME ("Sheriff S").
- Ensures the configured channels exist.
- Forwards owner messages in idea/sheriff channels to the gateway `POST /sheriff/message`
  and posts the reply back.
- Treats natural-language approvals in #approvals as approval intent.
- Subscribes to the Redis events channel to relay cost/system alerts.

If DISCORD_BOT_TOKEN is empty, the bot logs a notice and exits cleanly so the rest of
the stack still runs.
"""

from __future__ import annotations

import asyncio
import json

import httpx

from slick_shared.config import get_settings
from slick_shared.logging import setup_logging
from slick_shared.queue import EVENTS_CHANNEL, get_redis

logger = setup_logging("discord-bot")
settings = get_settings()

IDEA_CHANNELS = {"business-ideas", "sheriff-s", "slick-control"}
APPROVAL_CHANNEL = "approvals"
# Map event types -> channel name to relay into.
EVENT_CHANNEL_MAP = {
    "cost_alert": "costs",
    "budget_hard_cap": "system-alerts",
    "task_finished": "agent-updates",
    "skills_synced": "github-prs",
}


async def _post_sheriff(channel: str, author: str, content: str) -> dict:
    url = f"{settings.gateway_public_url}/sheriff/message"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url, json={"channel": channel, "author": author, "content": content}
        )
        resp.raise_for_status()
        return resp.json()


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
            channel_name = EVENT_CHANNEL_MAP.get(event.get("type"), "system-alerts")
            text = event.get("message") or f"{event.get('type')}: {json.dumps(event)}"
            for guild in client.guilds:
                ch = await channel_by_name(guild, channel_name)
                if ch:
                    await ch.send(text)

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
        if channel_name in IDEA_CHANNELS or channel_name == APPROVAL_CHANNEL:
            try:
                data = await _post_sheriff(channel_name, str(message.author), message.content)
                reply = data.get("reply", "🤠 (no reply)")
                await message.channel.send(reply[:1900])
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
        # Idle so the container stays up without crashing the stack.
        asyncio.run(_idle())
        return
    client = build_bot()
    client.run(settings.discord_bot_token)


async def _idle() -> None:
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    main()
