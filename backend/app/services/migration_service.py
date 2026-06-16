"""
MigrationService — in-memory CRUD store for MigrationState objects.

This module is deliberately storage-agnostic: the public interface will
remain unchanged when the backing store is switched to a database in a
later module.  All methods are async-safe and designed for concurrent
FastAPI request handling.

Usage:
    from app.services.migration_service import MigrationService
    svc = MigrationService.get_instance()
    state = await svc.create_migration("MyProject")
    await svc.add_log(state.migration_id, "Upload complete")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.agents.state import LogEntry, LogLevel, MigrationStage, MigrationState
from app.core.exceptions import (
    MigrationAlreadyRunningException,
    MigrationNotFoundException,
)

logger = logging.getLogger(__name__)


class MigrationService:
    """
    In-memory store and business-logic facade for :class:`MigrationState`.

    Pattern:
    - All mutations go through this service (no direct dict writes).
    - Methods are async so the interface is compatible with a future
      async database driver (SQLAlchemy async, Motor, etc.).
    - A :class:`asyncio.Lock` serialises writes per migration_id.
    """

    _instance: Optional["MigrationService"] = None

    def __new__(cls) -> "MigrationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store: dict[str, MigrationState] = {}
            cls._instance._locks: dict[str, asyncio.Lock] = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "MigrationService":
        """Return the process-wide MigrationService singleton."""
        return cls()

    # ── Internal helpers ──────────────────────────────────────────────

    def _lock_for(self, migration_id: str) -> asyncio.Lock:
        """Return (creating if necessary) a per-migration write lock."""
        if migration_id not in self._locks:
            self._locks[migration_id] = asyncio.Lock()
        return self._locks[migration_id]

    def _require(self, migration_id: str) -> MigrationState:
        """Fetch a state or raise :class:`MigrationNotFoundException`."""
        state = self._store.get(migration_id)
        if state is None:
            raise MigrationNotFoundException(migration_id)
        return state

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create_migration(
        self,
        project_name: str,
        uploaded_files: Optional[list[str]] = None,
    ) -> MigrationState:
        """
        Create and persist a new :class:`MigrationState`.

        Args:
            project_name:    Human-readable name for the project.
            uploaded_files:  Optional list of uploaded file paths/names.

        Returns:
            The newly created :class:`MigrationState`.
        """
        state = MigrationState(
            project_name=project_name,
            uploaded_files=uploaded_files or [],
        )
        state.add_log(
            f"[INFO] Migration created for project '{project_name}'",
            level=LogLevel.INFO,
        )

        async with self._lock_for(state.migration_id):
            self._store[state.migration_id] = state

        logger.info(
            "Migration created — id=%s  project=%s",
            state.migration_id,
            project_name,
        )
        return state

    async def get_migration(self, migration_id: str) -> MigrationState:
        """
        Retrieve a :class:`MigrationState` by ID.

        Args:
            migration_id: UUID string of the migration.

        Returns:
            The current :class:`MigrationState`.

        Raises:
            :class:`MigrationNotFoundException`: If not found.
        """
        return self._require(migration_id)

    async def list_migrations(self) -> list[MigrationState]:
        """Return all migrations sorted by creation time (newest first), stable."""
        items = list(self._store.values())
        # Reverse insertion order as tiebreaker — newer items were appended later
        items_with_idx = list(enumerate(items))
        return [
            state
            for _, state in sorted(
                items_with_idx,
                key=lambda x: (x[1].created_at, x[0]),
                reverse=True,
            )
        ]

    async def update_state(
        self, migration_id: str, updated: MigrationState
    ) -> MigrationState:
        """
        Persist an updated :class:`MigrationState`.

        Args:
            migration_id: ID of the migration to update.
            updated:      The new state to store.

        Returns:
            The stored state (same object).

        Raises:
            :class:`MigrationNotFoundException`: If the ID is unknown.
        """
        self._require(migration_id)   # raises if not found
        updated.updated_at = datetime.now(timezone.utc)

        async with self._lock_for(migration_id):
            self._store[migration_id] = updated

        logger.debug(
            "Migration updated — id=%s  stage=%s",
            migration_id,
            updated.current_stage.value,
        )
        return updated

    async def delete_migration(self, migration_id: str) -> bool:
        """
        Remove a migration from the store.

        Args:
            migration_id: UUID of the migration.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        async with self._lock_for(migration_id):
            existed = migration_id in self._store
            self._store.pop(migration_id, None)
            self._locks.pop(migration_id, None)

        if existed:
            logger.info("Migration deleted — id=%s", migration_id)
        return existed

    # ── Mutation helpers ──────────────────────────────────────────────

    async def add_log(
        self,
        migration_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        agent: Optional[str] = None,
    ) -> None:
        """
        Append a log entry to the migration's log list.

        Args:
            migration_id: Target migration UUID.
            message:      Human-readable log message.
            level:        :class:`LogLevel` severity.
            agent:        Optional agent name for attribution.

        Raises:
            :class:`MigrationNotFoundException`: If the ID is unknown.
        """
        async with self._lock_for(migration_id):
            state = self._require(migration_id)
            state.add_log(message, level=level, agent=agent)

    async def advance_stage(
        self, migration_id: str, stage: MigrationStage
    ) -> MigrationState:
        """
        Advance the migration to *stage* and persist.

        Args:
            migration_id: Target migration UUID.
            stage:        The next :class:`MigrationStage` to enter.

        Returns:
            Updated :class:`MigrationState`.
        """
        async with self._lock_for(migration_id):
            state = self._require(migration_id)
            state.advance_stage(stage)

        logger.info(
            "Stage advanced — id=%s  stage=%s",
            migration_id,
            stage.value,
        )
        return state

    async def mark_failed(
        self, migration_id: str, reason: str
    ) -> MigrationState:
        """
        Transition migration to FAILED state.

        Args:
            migration_id: Target migration UUID.
            reason:       Human-readable failure reason.

        Returns:
            Updated :class:`MigrationState`.
        """
        async with self._lock_for(migration_id):
            state = self._require(migration_id)
            state.mark_failed(reason)

        logger.error(
            "Migration failed — id=%s  reason=%s",
            migration_id,
            reason,
        )
        return state

    async def guard_not_running(self, migration_id: str) -> None:
        """
        Raise :class:`MigrationAlreadyRunningException` if a workflow
        for *migration_id* is currently in-flight.

        Uses a sentinel context key ``"_workflow_running"`` written by the
        workflow runner.
        """
        state = self._require(migration_id)
        if state.context.get("_workflow_running"):
            raise MigrationAlreadyRunningException(
                migration_id=migration_id,
                message=f"Migration {migration_id!r} is already running a workflow",
            )

    async def set_workflow_running(
        self, migration_id: str, running: bool
    ) -> None:
        """Toggle the ``_workflow_running`` sentinel on the state context."""
        async with self._lock_for(migration_id):
            state = self._require(migration_id)
            state.context["_workflow_running"] = running

    # ── Statistics ────────────────────────────────────────────────────

    async def stats(self) -> dict[str, int]:
        """Return a quick summary count of migrations by stage."""
        counts: dict[str, int] = {"total": len(self._store)}
        for state in self._store.values():
            key = state.current_stage.value
            counts[key] = counts.get(key, 0) + 1
        return counts
