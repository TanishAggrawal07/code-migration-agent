"""
Custom exception hierarchy for Code Migration Agent.

All domain exceptions inherit from :class:`MigrationAgentError` so
callers can catch the base class when they don't care which layer failed.

Hierarchy:
    MigrationAgentError
    ├── AgentException      — individual agent failures
    ├── WorkflowException   — LangGraph / orchestration failures
    ├── ServiceException    — service layer (MigrationService) failures
    └── ValidationException — request / input validation failures
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Optional


class MigrationAgentError(Exception):
    """Root exception for all Code Migration Agent errors."""

    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Any] = None,
        migration_id: Optional[str] = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        self.migration_id = migration_id
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict for HTTP error responses."""
        payload: dict[str, Any] = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.details is not None:
            payload["details"] = self.details
        if self.migration_id is not None:
            payload["migration_id"] = self.migration_id
        return payload


# ── Agent-level exceptions ────────────────────────────────────────────────


class AgentException(MigrationAgentError):
    """Raised when a pipeline agent fails in an unrecoverable way."""

    http_status = HTTPStatus.UNPROCESSABLE_ENTITY
    default_message = "Agent execution failed"

    def __init__(
        self,
        message: Optional[str] = None,
        agent_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.agent_name = agent_name

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        if self.agent_name:
            payload["agent"] = self.agent_name
        return payload


# ── Workflow-level exceptions ─────────────────────────────────────────────


class WorkflowException(MigrationAgentError):
    """Raised when the LangGraph workflow fails to execute."""

    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message = "Workflow execution failed"

    def __init__(
        self,
        message: Optional[str] = None,
        stage: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.stage = stage

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        if self.stage:
            payload["stage"] = self.stage
        return payload


# ── Service-level exceptions ──────────────────────────────────────────────


class ServiceException(MigrationAgentError):
    """Raised by the service layer (MigrationService) for logic errors."""

    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    default_message = "Service operation failed"


class MigrationNotFoundException(ServiceException):
    """Raised when a migration_id is not found in the store."""

    http_status = HTTPStatus.NOT_FOUND
    default_message = "Migration not found"

    def __init__(self, migration_id: str) -> None:
        super().__init__(
            message=f"Migration {migration_id!r} not found",
            migration_id=migration_id,
        )


class MigrationAlreadyRunningException(ServiceException):
    """Raised when a workflow run is requested while one is already active."""

    http_status = HTTPStatus.CONFLICT
    default_message = "Migration is already running"


# ── Validation exceptions ─────────────────────────────────────────────────


class ValidationException(MigrationAgentError):
    """Raised for invalid user input or request payloads."""

    http_status = HTTPStatus.UNPROCESSABLE_ENTITY
    default_message = "Validation failed"
