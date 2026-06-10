"""ASGI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from specvsreality_api.config import get_settings
from specvsreality_api.routes import (
    health,
    hello_world,
    metrics_dashboard,
    repo_catalog,
    repo_dashboard,
    repo_logs,
    repos,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Spec vs Reality API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(hello_world.router)
    app.include_router(repos.router)
    app.include_router(repo_catalog.router)
    app.include_router(repo_dashboard.router)
    app.include_router(repo_logs.router)
    app.include_router(metrics_dashboard.router)
    app.include_router(health.router)
    return app


app = create_app()
