from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource


def _resolve_business_env_file() -> Path | None:
    for base in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1]):
        candidate = base / ".env"
        if candidate.is_file():
            return candidate
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str = "redis://localhost:6380/0"
    api_base_url: str = "http://localhost:8000"
    job_queue_key: str = "price-pulse:jobs"
    schedule_interval_seconds: int = 3600
    heartbeat_key: str = "price-pulse:scheduler:heartbeat"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
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
