# Agents

Markdown agent **profiles**. The live registry (DB `agents` table) tracks runtime state;
these files define identity, mission, scope, tools, permissions, risk, skills, and
operating rules. See `docs/04-agent-system.md`.

- `global/` — reusable agents shared across all businesses.
- `templates/` — role templates instantiated per business by the Agent Designer.

## Profile format

Every `AGENT.md` follows this structure:

```
# Agent: <Name>
- Role / Scope / Risk
## Mission
## Inputs / Outputs
## Tools & MCP servers
## Permissions
## Skills
## Operating rules
```
