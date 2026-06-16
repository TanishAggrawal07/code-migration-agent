"""
Global FastAPI exception handlers.

Registers handlers for:
  - :class:`~app.core.exceptions.MigrationAgentError` subclasses
  - FastAPI's built-in :class:`~fastapi.exceptions.RequestValidationError`
  - Unhandled :class:`Exception` (500 fallback)

Usage (in app factory):
    from app.api.error_handlers import register_exception_handlers
    register_exception_handlers(app)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import MigrationAgentError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to *app*."""

    # ── Domain exceptions ─────────────────────────────────────────────

    @app.exception_handler(MigrationAgentError)
    async def migration_agent_error_handler(
        request: Request, exc: MigrationAgentError
    ) -> JSONResponse:
        logger.warning(
            "Domain error [%s] %s — path=%s",
            type(exc).__name__,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    # ── Request validation errors (422) ───────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })

        logger.info(
            "Validation error — path=%s  errors=%d",
            request.url.path,
            len(errors),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": errors,
            },
        )

    # ── Catch-all 500 handler ─────────────────────────────────────────

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception — path=%s  error=%s",
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )
