# slick-discord-bot

The first command interface, with the **Sheriff S** persona.

- Ensures channels exist: `#slick-control`, `#sheriff-s`, `#agent-updates`,
  `#approvals`, `#costs`, `#github-prs`, `#system-alerts`, `#business-ideas`.
- Forwards messages in idea/sheriff channels to the gateway `POST /sheriff/message`
  and posts replies back.
- Treats natural-language approvals (e.g. "approved", "go ahead") in `#approvals`.
- Relays Redis events (cost alerts, hard-cap, task finished, skills synced).

## Setup

1. Create an app + bot at https://discord.com/developers/applications
2. Enable the **Message Content Intent**.
3. Put the token in `.env` → `DISCORD_BOT_TOKEN`, set `DISCORD_GUILD_ID`.
4. Invite the bot with `bot` scope + send/manage-channels permissions.

If `DISCORD_BOT_TOKEN` is empty the bot idles cleanly so the rest of the stack still
runs. See `docs/15-discord-interface.md`.
