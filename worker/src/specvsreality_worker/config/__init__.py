"""Application settings: packaged YAML defaults with environment overrides."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, InitSettingsSource, SettingsConfigDict

if TYPE_CHECKING:
    from pydantic_settings.sources import PydanticBaseSettingsSource


def _load_yaml_defaults() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "defaults.yaml"
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        return {}
    return data


class WorkerSettings(BaseSettings):
    """RabbitMQ and worker tuning. YAML defaults; `RABBITMQ_*` env vars override (later wins)."""

    model_config = SettingsConfigDict(
        env_prefix="RABBITMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Defaults match `defaults.yaml`; YAML/env still merge via settings sources.
    host: str = Field(default="localhost", description="AMQP host")
    port: int = Field(default=5672, description="AMQP port")
    virtual_host: str = Field(default="/", description="AMQP vhost")
    queue_name: str = Field(default="messages", description="Queue to consume")
    prefetch_count: int = Field(default=1, ge=1, description="Consumer prefetch (QoS)")
    username: str = Field(default="guest", description="AMQP username")
    password: str = Field(default="", description="AMQP password (prefer env in production)")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Order: earlier sources win on key conflicts. YAML last => lowest priority; env beats YAML.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            InitSettingsSource(settings_cls, _load_yaml_defaults()),
        )


def load_settings() -> WorkerSettings:
    """Load settings from packaged defaults, `.env`, and process environment."""
    return WorkerSettings()
