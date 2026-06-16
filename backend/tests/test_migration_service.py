"""
Tests for MigrationService (in-memory store).
"""

import asyncio
import pytest

from app.agents.state import LogLevel, MigrationStage, MigrationState
from app.core.exceptions import (
    MigrationAlreadyRunningException,
    MigrationNotFoundException,
)
from app.services.migration_service import MigrationService


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def fresh_service() -> None:
    """Reset the singleton store before each test."""
    svc = MigrationService.get_instance()
    svc._store.clear()
    svc._locks.clear()


# ── Creation ──────────────────────────────────────────────────────────────

def test_create_returns_migration_state() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("TestProject"))
    assert isinstance(state, MigrationState)
    assert state.project_name == "TestProject"


def test_create_assigns_unique_ids() -> None:
    svc = MigrationService.get_instance()
    s1 = run(svc.create_migration("P1"))
    s2 = run(svc.create_migration("P2"))
    assert s1.migration_id != s2.migration_id


def test_create_with_uploaded_files() -> None:
    svc = MigrationService.get_instance()
    files = ["Foo.cs", "Bar.cs"]
    state = run(svc.create_migration("P", uploaded_files=files))
    assert state.uploaded_files == files


def test_create_adds_initial_log() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("P"))
    assert len(state.logs) >= 1


# ── Retrieval ─────────────────────────────────────────────────────────────

def test_get_returns_correct_state() -> None:
    svc = MigrationService.get_instance()
    created = run(svc.create_migration("GetTest"))
    fetched = run(svc.get_migration(created.migration_id))
    assert fetched.migration_id == created.migration_id


def test_get_unknown_raises_not_found() -> None:
    svc = MigrationService.get_instance()
    with pytest.raises(MigrationNotFoundException):
        run(svc.get_migration("00000000-0000-0000-0000-000000000000"))


def test_list_returns_all() -> None:
    svc = MigrationService.get_instance()
    run(svc.create_migration("A"))
    run(svc.create_migration("B"))
    run(svc.create_migration("C"))
    lst = run(svc.list_migrations())
    assert len(lst) == 3


def test_list_sorted_newest_first() -> None:
    svc = MigrationService.get_instance()
    run(svc.create_migration("First"))
    run(svc.create_migration("Second"))
    lst = run(svc.list_migrations())
    assert lst[0].project_name == "Second"


# ── Mutation helpers ──────────────────────────────────────────────────────

def test_add_log_appends_entry() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("LogTest"))
    run(svc.add_log(state.migration_id, "test message", LogLevel.INFO, "my_agent"))
    fetched = run(svc.get_migration(state.migration_id))
    messages = [l.message for l in fetched.logs]
    assert "test message" in messages


def test_advance_stage_persists() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("StageTest"))
    run(svc.advance_stage(state.migration_id, MigrationStage.PARSED))
    fetched = run(svc.get_migration(state.migration_id))
    assert fetched.current_stage == MigrationStage.PARSED


def test_mark_failed_persists() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("FailTest"))
    run(svc.mark_failed(state.migration_id, "something went wrong"))
    fetched = run(svc.get_migration(state.migration_id))
    assert fetched.is_failed is True
    assert "something went wrong" in fetched.errors


def test_update_state_persists_changes() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("UpdateTest"))
    state.project_name = "RenamedProject"
    run(svc.update_state(state.migration_id, state))
    fetched = run(svc.get_migration(state.migration_id))
    assert fetched.project_name == "RenamedProject"


# ── Deletion ──────────────────────────────────────────────────────────────

def test_delete_removes_migration() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("DeleteMe"))
    deleted = run(svc.delete_migration(state.migration_id))
    assert deleted is True
    with pytest.raises(MigrationNotFoundException):
        run(svc.get_migration(state.migration_id))


def test_delete_unknown_returns_false() -> None:
    svc = MigrationService.get_instance()
    result = run(svc.delete_migration("nonexistent-id"))
    assert result is False


# ── Concurrency guard ─────────────────────────────────────────────────────

def test_guard_not_running_passes_when_idle() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("GuardTest"))
    # Should not raise
    run(svc.guard_not_running(state.migration_id))


def test_guard_not_running_raises_when_running() -> None:
    svc = MigrationService.get_instance()
    state = run(svc.create_migration("RunningTest"))
    run(svc.set_workflow_running(state.migration_id, True))
    with pytest.raises(MigrationAlreadyRunningException):
        run(svc.guard_not_running(state.migration_id))


# ── Statistics ────────────────────────────────────────────────────────────

def test_stats_total_matches_store() -> None:
    svc = MigrationService.get_instance()
    run(svc.create_migration("S1"))
    run(svc.create_migration("S2"))
    stats = run(svc.stats())
    assert stats["total"] == 2
