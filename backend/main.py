"""
Code Migration Agent — FastAPI application entry point.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.ai_status import router as ai_status_router
from app.core.config import get_settings
from app.core.logger import configure_logging, get_logger
from app.core.startup import initialize_services, shutdown_services


# ── Logging is configured before any other module writes a log line ────────
_settings = get_settings()
configure_logging(
    level=_settings.log_level,
    log_dir=_settings.log_dir,
    max_bytes=_settings.log_max_bytes,
    backup_count=_settings.log_backup_count,
    is_production=_settings.is_production,
)
logger = get_logger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan — startup and shutdown hooks."""
    settings = get_settings()
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    # Ensure storage directories exist
    for directory in (
        settings.upload_dir,
        settings.output_dir,
        settings.chroma_db_path,
        settings.log_dir,
    ):
        os.makedirs(directory, exist_ok=True)
    logger.info("Storage directories verified")

    # Initialise AI services (each fails gracefully)
    await initialize_services()

    yield  # ── application runs ──────────────────────────────────────────

    await shutdown_services()
    logger.info("Shutdown complete — goodbye")


# ── Application factory ────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-powered .NET → Java code migration agent using "
            "Gemini 2.5 Flash, RAG, LangGraph, ChromaDB, and MCP."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(ai_status_router)

    return app


app = create_app()
