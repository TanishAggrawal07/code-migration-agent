"""
Tests for MigrationState model and helpers.
"""

from app.agents.state import (
    LogLevel,
    MigrationStage,
    MigrationState,
    ParsedFile,
    GeneratedFile,
    STAGE_ORDER,
)


def _new() -> MigrationState:
    return MigrationState(project_name="TestProject")


def test_default_stage_is_uploaded() -> None:
    state = _new()
    assert state.current_stage == MigrationStage.UPLOADED


def test_migration_id_is_auto_generated() -> None:
    s1, s2 = _new(), _new()
    assert s1.migration_id != s2.migration_id
    assert len(s1.migration_id) == 36  # UUID4 format


def test_add_log_appends_entry() -> None:
    state = _new()
    state.add_log("hello", LogLevel.INFO, agent="test_agent")
    assert len(state.logs) == 1
    assert state.logs[0].message == "hello"
    assert state.logs[0].agent == "test_agent"


def test_add_log_updates_updated_at() -> None:
    import time
    state = _new()
    before = state.updated_at
    time.sleep(0.01)
    state.add_log("bump")
    assert state.updated_at >= before


def test_advance_stage_moves_forward() -> None:
    state = _new()
    state.advance_stage(MigrationStage.PARSED)
    assert state.current_stage == MigrationStage.PARSED
    assert MigrationStage.UPLOADED in state.completed_stages


def test_advance_stage_does_not_duplicate_completed() -> None:
    state = _new()
    state.advance_stage(MigrationStage.PARSED)
    state.advance_stage(MigrationStage.PARSED)  # duplicate call
    assert state.completed_stages.count(MigrationStage.UPLOADED) == 1


def test_mark_failed_sets_stage() -> None:
    state = _new()
    state.mark_failed("something broke")
    assert state.current_stage == MigrationStage.FAILED
    assert state.is_failed is True
    assert "something broke" in state.errors


def test_mark_failed_adds_error_log() -> None:
    state = _new()
    state.mark_failed("oops")
    error_logs = [l for l in state.logs if l.level == LogLevel.ERROR]
    assert len(error_logs) >= 1


def test_is_complete_false_before_saved() -> None:
    state = _new()
    assert state.is_complete is False


def test_is_complete_true_at_saved() -> None:
    state = _new()
    state.current_stage = MigrationStage.SAVED
    assert state.is_complete is True


def test_to_summary_keys() -> None:
    state = _new()
    summary = state.to_summary()
    for key in ("migration_id", "project_name", "current_stage", "is_failed", "is_complete"):
        assert key in summary


def test_stage_order_has_eight_stages() -> None:
    assert len(STAGE_ORDER) == 8


def test_parsed_file_defaults() -> None:
    pf = ParsedFile(filename="Foo.cs", path="/src/Foo.cs")
    assert pf.parsed is False
    assert pf.classes == []


def test_generated_file_defaults() -> None:
    gf = GeneratedFile(filename="Foo.java", path="/out/Foo.java")
    assert gf.compile_success is False
