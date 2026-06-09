"""API settings: CORS and RabbitMQ (env-aligned with worker)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5180",
            "http://127.0.0.1:5180",
            "http://localhost:9080",
            "http://127.0.0.1:9080",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:3000",
        ],
        description="Allowed browser origins (JSON array or comma-separated via env).",
    )

    rabbitmq_host: str = Field(default="localhost", validation_alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, validation_alias="RABBITMQ_PORT")
    rabbitmq_virtual_host: str = Field(default="/", validation_alias="RABBITMQ_VIRTUAL_HOST")
    rabbitmq_username: str = Field(default="guest", validation_alias="RABBITMQ_USERNAME")
    rabbitmq_password: str = Field(default="guest", validation_alias="RABBITMQ_PASSWORD")
    rabbitmq_queue_name: str = Field(default="messages", validation_alias="RABBITMQ_QUEUE_NAME")

    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: object) -> list[str]:
        if v is None or v == "":
            return [
                "http://localhost:5180",
                "http://127.0.0.1:5180",
                "http://localhost:9080",
                "http://127.0.0.1:9080",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
            ]
        if isinstance(v, list):
            return [str(x) for x in v]
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json

                data = json.loads(s)
                if isinstance(data, list):
                    return [str(x) for x in data]
            return [p.strip() for p in s.split(",") if p.strip()]
        return [str(v)]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
