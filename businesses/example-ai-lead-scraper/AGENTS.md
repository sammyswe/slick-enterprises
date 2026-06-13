# Agents — Example AI Lead Scraper

Agents communicate **through** the Business Manager. Sheriff S talks to the Business
Manager, not to every sub-agent.

| Agent | Role | Status | Notes |
|-------|------|--------|-------|
| Business Manager | business-manager | sleeping | Routing point for the compartment |
| Researcher | researcher | sleeping | Finds + vets lead sources |
| Coder | coder | sleeping | Builds the scraper + digest job |
| Tester | tester | sleeping | Verifies scraping + digest output |
| Reviewer | reviewer | sleeping | Reviews changes before merge |
| Scraper | scraper | sleeping | Collects leads from approved sources |
| Notifier | notifier | sleeping | Delivers the daily digest (approval needed for email) |

Role templates: `agents/templates/`.
