"""Central configuration loader.

Every service reads configuration through `get_settings()`. No module should open
`.env` or read secret files directly (see .cursor/rules/01-no-secrets.mdc).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings sourced from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Core ----
    env: str = "development"
    log_level: str = "INFO"
    tz: str = "Europe/London"
    # Repo root inside the container; the repo is mounted here so services can read
    # docs/, skills/, and businesses/. Set via SLICK_REPO_ROOT in compose.
    slick_repo_root: str = "/workspace"

    # ---- UI auth ----
    ui_admin_password: str = "change-me-please"
    gateway_api_token: str = "dev-gateway-token-change-me"

    # ---- Gateway ----
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    gateway_public_url: str = "http://localhost:8000"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://slick:change-me-postgres@slick-postgres:5432/slick_hq"
    database_url_sync: str = (
        "postgresql+psycopg://slick:change-me-postgres@slick-postgres:5432/slick_hq"
    )

    # ---- Redis ----
    redis_url: str = "redis://slick-redis:6379/0"

    # ---- Model provider ----
    # "cursor"  -> Cursor SDK (Composer); billed against your Cursor subscription.
    # "anthropic" -> direct Anthropic API (pay-per-token).
    # "mock"    -> deterministic, zero-cost responses (also forced by model_mock_mode).
    model_provider: str = "anthropic"
    anthropic_api_key: str = ""
    model_cheap: str = "claude-haiku-4"
    model_smart: str = "claude-sonnet-4"
    model_mock_mode: bool = True

    # ---- Cursor SDK (Composer) ----
    # Key minted at https://cursor.com/dashboard/integrations (prefix `crsr_`).
    # SDK runs bill against the same plan/request pool as the IDE; spend appears
    # in the Cursor usage dashboard under the "SDK" tag (no per-call $ is returned).
    cursor_api_key: str = ""
    # "local" runs Composer on this machine against cursor_workspace_dir.
    # "cloud" runs on a Cursor-hosted VM against a cloned GitHub repo (PRs).
    cursor_runtime: str = "local"
    cursor_workspace_dir: str = "/workspace"
    # Model used for routine/cheap work vs. high-quality coding/review work.
    cursor_model_cheap: str = "auto"
    cursor_model_smart: str = "composer-2.5"
    # Dashboard usage sync (Individual Max/Pro — see docs/08-cost-control.md).
    # JWT bearer or WorkosCursorSessionToken cookie value from cursor.com.
    cursor_access_token: str = ""
    cursor_workos_session_token: str = ""
    cursor_refresh_token: str = ""
    # How often cost-controller polls Cursor dashboard usage (seconds).
    cursor_usage_sync_interval_sec: int = 900

    # ---- Cost control ----
    cost_budget_usd: float = 200.0
    cost_alert_step_usd: float = 20.0
    cost_hard_cap_usd: float = 200.0

    # ---- Self-building engine (autonomous build bounds) ----
    # Max specialised-agent tasks running concurrently within one build.
    build_max_concurrency: int = 3
    # Hard ceiling on Composer runs for a single build (planner + builders + evaluators).
    build_max_composer_runs: int = 40
    # Wall-clock timeout for a single build, in minutes.
    build_timeout_min: int = 60
    # How many times a failing task may be reworked before it is marked blocked.
    build_max_rework_attempts: int = 3

    # ---- Discord ----
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_bot_name: str = "Sheriff S"
    discord_channels: str = (
        "slick-control,sheriff-s,agent-updates,approvals,costs,github-prs,system-alerts,business-ideas"
    )

    # ---- GitHub ----
    github_pat: str = ""
    github_owner: str = ""
    github_repo: str = "slick-enterprises"
    github_default_branch: str = "main"
    github_allow_direct_push_to_main: bool = False

    # ---- OpenClaw bridge ----
    openclaw_mode: str = "mock"
    openclaw_base_url: str = "http://slick-openclaw-bridge:8100"
    openclaw_api_key: str = ""

    # ---- Hermes / coding-engine bridge ----
    # cursor = Composer-backed (default), mock = canned, live = real Hermes deployment.
    hermes_mode: str = "cursor"
    hermes_base_url: str = "http://slick-hermes-bridge:8200"
    hermes_api_key: str = ""
    hermes_data_dir: str = "/data/hermes"

    # ---- Sandbox runner ----
    sandbox_base_url: str = "http://slick-sandbox-runner:8300"
    sandbox_require_approval_for_dangerous: bool = True

    @property
    def discord_channel_list(self) -> list[str]:
        return [c.strip() for c in self.discord_channels.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
