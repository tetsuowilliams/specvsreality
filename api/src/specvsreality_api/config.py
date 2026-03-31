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
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:3000",
        ],
        description="Allowed browser origins (JSON array or comma-separated via env).",
    )

    rabbitmq_host: str = Field(default="localhost", validation_alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, validation_alias="RABBITMQ_PORT")
    rabbitmq_virtual_host: str = Field(default="/", validation_alias="RABBITMQ_VIRTUAL_HOST")
    rabbitmq_username: str = Field(default="guest", validation_alias="RABBITMQ_USERNAME")
    rabbitmq_password: str = Field(default="", validation_alias="RABBITMQ_PASSWORD")
    rabbitmq_queue_name: str = Field(default="messages", validation_alias="RABBITMQ_QUEUE_NAME")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: object) -> list[str]:
        if v is None or v == "":
            return [
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
