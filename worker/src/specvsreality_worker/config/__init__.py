"""Application settings: packaged YAML defaults with environment overrides."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import AliasChoices, Field, field_validator
from pydantic_ai.usage import UsageLimits
from pydantic_settings import BaseSettings, InitSettingsSource, SettingsConfigDict

from specvsreality_worker.model_token_cost import ModelTokenCost, parse_model_token_costs

if TYPE_CHECKING:
    from pydantic_settings.sources import PydanticBaseSettingsSource


def _load_yaml_defaults() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "defaults.yaml"
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        return {}
    return data


def _parse_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class WorkerSettings(BaseSettings):
    """Worker configuration from packaged YAML, `.env`, and process environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- RabbitMQ (field names match `defaults.yaml`; env uses RABBITMQ_* aliases) ---
    host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("RABBITMQ_HOST", "host"),
        description="AMQP host",
    )
    port: int = Field(
        default=5672,
        validation_alias=AliasChoices("RABBITMQ_PORT", "port"),
        description="AMQP port",
    )
    virtual_host: str = Field(
        default="/",
        validation_alias=AliasChoices("RABBITMQ_VIRTUAL_HOST", "virtual_host"),
        description="AMQP vhost",
    )
    queue_name: str = Field(
        default="messages",
        validation_alias=AliasChoices("RABBITMQ_QUEUE_NAME", "queue_name"),
        description="Queue to consume",
    )
    prefetch_count: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("RABBITMQ_PREFETCH_COUNT", "prefetch_count"),
        description="Consumer prefetch (QoS)",
    )
    heartbeat: int = Field(
        default=1800,
        ge=0,
        validation_alias=AliasChoices("RABBITMQ_HEARTBEAT", "heartbeat"),
        description="AMQP heartbeat interval in seconds",
    )
    blocked_connection_timeout: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices(
            "RABBITMQ_BLOCKED_CONNECTION_TIMEOUT",
            "blocked_connection_timeout",
        ),
        description="Seconds before a broker-blocked connection is closed (0 = disabled)",
    )
    reconnect_delay_seconds: float = Field(
        default=5.0,
        ge=0,
        validation_alias=AliasChoices(
            "RABBITMQ_RECONNECT_DELAY_SECONDS",
            "reconnect_delay_seconds",
        ),
        description="Pause before reconnecting after the AMQP connection is lost",
    )
    username: str = Field(
        default="guest",
        validation_alias=AliasChoices("RABBITMQ_USERNAME", "username"),
        description="AMQP username",
    )
    password: str = Field(
        default="guest",
        validation_alias=AliasChoices("RABBITMQ_PASSWORD", "password"),
        description="AMQP password",
    )

    # --- Process / infrastructure ---
    worker_log_level: str = Field(
        default="INFO",
        validation_alias="WORKER_LOG_LEVEL",
        description="Root log level for the worker process",
    )
    database_url: str = Field(
        default="",
        validation_alias="DATABASE_URL",
        description="SQLAlchemy database URL (required for repo handlers)",
    )
    repo_clone_root: str = Field(
        default="/repos",
        validation_alias="REPO_CLONE_ROOT",
        description="Directory where repositories are cloned for scanning",
    )
    git_clone_token: str = Field(
        default="",
        validation_alias="GIT_CLONE_TOKEN",
        description="Optional HTTPS clone token for private repositories",
    )
    git_clone_username: str = Field(
        default="x-access-token",
        validation_alias="GIT_CLONE_USERNAME",
        description="Username paired with GIT_CLONE_TOKEN for HTTPS clone URLs",
    )

    # --- Observability ---
    logfire_token: str = Field(default="", validation_alias="LOGFIRE_TOKEN")
    logfire_service_name: str = Field(
        default="specvsreality-worker",
        validation_alias="LOGFIRE_SERVICE_NAME",
    )
    logfire_environment: str = Field(default="", validation_alias="LOGFIRE_ENVIRONMENT")
    opik_url_override: str = Field(default="", validation_alias="OPIK_URL_OVERRIDE")
    otel_exporter_otlp_headers: str = Field(
        default="",
        validation_alias="OTEL_EXPORTER_OTLP_HEADERS",
    )
    pydantic_ai_verbose: bool = Field(default=False, validation_alias="PYDANTIC_AI_VERBOSE")
    logfire_console_verbose: bool = Field(
        default=False,
        validation_alias="LOGFIRE_CONSOLE_VERBOSE",
    )

    # --- Agent models ---
    spec_extraction_model: str = Field(
        default="openai:gpt-4o-mini",
        validation_alias="SPEC_EXTRACTION_MODEL",
    )
    artifact_candidate_agent_model: str = Field(
        default="openai:gpt-4o-mini",
        validation_alias="ARTIFACT_CANDIDATE_AGENT_MODEL",
    )
    implements_agent_model: str = Field(
        default="openai:gpt-4o-mini",
        validation_alias="IMPLEMENTS_AGENT_MODEL",
    )

    # --- Implements agent limits ---
    implements_agent_batch_size: int = Field(
        default=5,
        validation_alias="IMPLEMENTS_AGENT_BATCH_SIZE",
    )
    implements_agent_timeout_seconds: float = Field(
        default=600.0,
        validation_alias="IMPLEMENTS_AGENT_TIMEOUT_SECONDS",
    )
    implements_agent_request_limit: int = Field(
        default=10,
        validation_alias="IMPLEMENTS_AGENT_REQUEST_LIMIT",
    )
    implements_agent_max_artifact_chars: int = Field(
        default=20_000,
        validation_alias="IMPLEMENTS_AGENT_MAX_ARTIFACT_CHARS",
    )

    # --- Artifact candidate agent limits ---
    artifact_candidate_agent_timeout_seconds: float = Field(
        default=600.0,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_TIMEOUT_SECONDS",
    )
    artifact_candidate_agent_request_limit: int = Field(
        default=30,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_REQUEST_LIMIT",
    )
    artifact_candidate_agent_tool_calls_limit: int = Field(
        default=40,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_TOOL_CALLS_LIMIT",
    )
    artifact_candidate_agent_search_max_files: int = Field(
        default=60,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_SEARCH_MAX_FILES",
    )
    artifact_candidate_agent_search_max_matches: int = Field(
        default=50,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_SEARCH_MAX_MATCHES",
    )
    artifact_candidate_agent_find_files_max: int = Field(
        default=200,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_FIND_FILES_MAX",
    )
    artifact_candidate_agent_read_max_bytes: int = Field(
        default=256_000,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_READ_MAX_BYTES",
    )
    artifact_candidate_agent_read_max_lines: int = Field(
        default=400,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_READ_MAX_LINES",
    )
    artifact_candidate_agent_read_max_line_span: int = Field(
        default=120,
        validation_alias="ARTIFACT_CANDIDATE_AGENT_READ_MAX_LINE_SPAN",
    )

    model_token_costs: dict[str, ModelTokenCost] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("MODEL_TOKEN_COSTS", "model_token_costs"),
        description="USD cost per million input/output tokens keyed by model id",
    )

    @field_validator("model_token_costs", mode="before")
    @classmethod
    def _parse_model_token_costs(cls, value: object) -> dict[str, ModelTokenCost]:
        return parse_model_token_costs(value)

    @field_validator("pydantic_ai_verbose", "logfire_console_verbose", mode="before")
    @classmethod
    def _parse_bool_flags(cls, value: object) -> bool:
        return _parse_truthy(value)

    @field_validator("implements_agent_batch_size")
    @classmethod
    def _clamp_batch_size(cls, value: int) -> int:
        return max(1, value)

    @property
    def pydantic_ai_verbose_enabled(self) -> bool:
        return self.pydantic_ai_verbose or self.logfire_console_verbose

    @property
    def logfire_environment_or_none(self) -> str | None:
        value = self.logfire_environment.strip()
        return value or None

    @property
    def opik_base_url(self) -> str:
        return self.opik_url_override.strip().rstrip("/")

    def sync_database_url(self) -> str:
        """Normalize common Postgres URL schemes for sync SQLAlchemy."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    def implements_usage_limits(self) -> UsageLimits:
        return UsageLimits(request_limit=self.implements_agent_request_limit)

    def artifact_candidate_usage_limits(self) -> UsageLimits:
        return UsageLimits(
            request_limit=self.artifact_candidate_agent_request_limit,
            tool_calls_limit=self.artifact_candidate_agent_tool_calls_limit,
        )

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


@lru_cache
def get_settings() -> WorkerSettings:
    """Cached settings for the worker process entrypoint."""
    return load_settings()
