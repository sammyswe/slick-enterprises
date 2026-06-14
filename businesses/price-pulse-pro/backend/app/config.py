from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource


def _resolve_business_env_file() -> Path | None:
    """Locate the monorepo `.env` from local checkout or Docker (/app) layout."""
    for base in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        candidate = base / ".env"
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://pricepulse:pricepulse@localhost:5433/pricepulse"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://pricepulse:pricepulse@localhost:5433/pricepulse"
    )
    redis_url: str = "redis://localhost:6380/0"
    slack_webhook_url: str = ""
    api_base_url: str = "http://localhost:8000"
    demo_pricing_base_url: str = "http://localhost:8000/demo/pricing"
    backend_port: int = 8000
    log_level: str = "INFO"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority (highest first): init → business .env → process env → secrets.

        The business `.env` wins over ambient HQ environment variables during local
        development. In Docker the `.env` file is absent on disk, so compose
        `environment:` values are picked up via ``env_settings``.
        """
        business_env_file = _resolve_business_env_file()
        sources: list[PydanticBaseSettingsSource] = [init_settings]
        if business_env_file is not None:
            sources.append(
                DotEnvSettingsSource(
                    settings_cls,
                    env_file=business_env_file,
                    env_file_encoding="utf-8",
                )
            )
        sources.extend([env_settings, file_secret_settings])
        return tuple(sources)


@lru_cache
def get_settings() -> Settings:
    return Settings()
