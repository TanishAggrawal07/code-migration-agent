"""
Tests for WorkflowEngine and pipeline status helpers.
"""

import asyncio
import pytest

from app.agents.state import MigrationStage, MigrationState
from app.agents.workflow import WorkflowEngine, get_workflow_engine


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture
def engine() -> WorkflowEngine:
    return get_workflow_engine()


@pytest.fixture
def initial_state() -> MigrationState:
    return MigrationState(
        project_name="WorkflowTest",
        uploaded_files=["App.cs", "Service.cs"],
    )


# ── Engine construction ───────────────────────────────────────────────────

def test_get_workflow_engine_returns_singleton() -> None:
    e1 = get_workflow_engine()
    e2 = get_workflow_engine()
    assert e1 is e2


def test_engine_has_graph() -> None:
    engine = get_workflow_engine()
    assert engine._graph is not None


# ── run_workflow ──────────────────────────────────────────────────────────

def test_workflow_returns_migration_state(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert isinstance(result, MigrationState)


def test_workflow_completes_to_saved(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert result.current_stage == MigrationStage.SAVED
    assert result.is_complete is True
    assert result.is_failed is False


def test_workflow_preserves_migration_id(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    original_id = initial_state.migration_id
    result = run(engine.run_workflow(initial_state))
    assert result.migration_id == original_id


def test_workflow_populates_parsed_files(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert len(result.parsed_files) > 0


def test_workflow_creates_embeddings(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    # Embedding stage must complete (EMBEDDED in completed_stages) even when
    # no real C# files are on disk — IndexingService degrades gracefully.
    assert MigrationStage.EMBEDDED in result.completed_stages


def test_workflow_retrieves_context(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert len(result.retrieved_context) > 0


def test_workflow_generates_java_files(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert len(result.generated_java_files) > 0


def test_workflow_all_java_files_compiled(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    for jf in result.generated_java_files:
        assert jf.compile_success is True


def test_workflow_compile_status_success(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert result.compile_status == "success"


def test_workflow_has_logs(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert len(result.logs) > 0


def test_workflow_no_errors_on_success(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    assert result.errors == []


def test_workflow_all_stages_completed(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    # UPLOADED through COMPILED should all be in completed_stages
    expected = [
        MigrationStage.UPLOADED,
        MigrationStage.PARSED,
        MigrationStage.ANALYZED,
        MigrationStage.EMBEDDED,
        MigrationStage.RETRIEVED,
        MigrationStage.MIGRATED,
        MigrationStage.COMPILED,
    ]
    for stage in expected:
        assert stage in result.completed_stages, f"{stage} not in completed_stages"


def test_workflow_empty_files_still_completes(engine: WorkflowEngine) -> None:
    """Workflow must handle a migration with no uploaded files."""
    state = MigrationState(project_name="EmptyProject")
    result = run(engine.run_workflow(state))
    assert result.is_complete is True


# ── get_pipeline_status ───────────────────────────────────────────────────

def test_pipeline_status_keys(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    status = engine.get_pipeline_status(result)
    for key in ("migration_id", "current_stage", "completed", "remaining", "progress_pct", "is_failed", "is_complete"):
        assert key in status, f"Missing key: {key}"


def test_pipeline_status_100_pct_when_complete(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    status = engine.get_pipeline_status(result)
    assert status["progress_pct"] == 100
    assert status["remaining"] == []
    assert status["is_complete"] is True


def test_pipeline_status_zero_pct_on_fresh_state(engine: WorkflowEngine) -> None:
    state = MigrationState(project_name="Fresh")
    status = engine.get_pipeline_status(state)
    assert status["progress_pct"] == 0
    assert status["completed"] == []


def test_pipeline_status_not_failed_on_success(engine: WorkflowEngine, initial_state: MigrationState) -> None:
    result = run(engine.run_workflow(initial_state))
    status = engine.get_pipeline_status(result)
    assert status["is_failed"] is False
