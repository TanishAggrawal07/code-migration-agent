"""
Tests for custom exception hierarchy.
"""

from app.core.exceptions import (
    AgentException,
    MigrationAgentError,
    MigrationAlreadyRunningException,
    MigrationNotFoundException,
    ServiceException,
    ValidationException,
    WorkflowException,
)


def test_migration_agent_error_is_base() -> None:
    e = MigrationAgentError("base error")
    assert isinstance(e, Exception)
    assert e.message == "base error"


def test_to_dict_has_required_keys() -> None:
    e = MigrationAgentError("oops", details={"x": 1}, migration_id="abc")
    d = e.to_dict()
    assert d["error"] == "MigrationAgentError"
    assert d["message"] == "oops"
    assert d["details"] == {"x": 1}
    assert d["migration_id"] == "abc"


def test_agent_exception_inherits_base() -> None:
    e = AgentException("agent failed", agent_name="parser_agent")
    assert isinstance(e, MigrationAgentError)
    assert e.agent_name == "parser_agent"
    assert e.to_dict()["agent"] == "parser_agent"


def test_workflow_exception_has_stage() -> None:
    e = WorkflowException("wf failed", stage="parsed")
    assert e.stage == "parsed"
    assert e.to_dict()["stage"] == "parsed"


def test_migration_not_found_sets_id() -> None:
    e = MigrationNotFoundException("abc-123")
    assert e.migration_id == "abc-123"
    assert "abc-123" in e.message
    assert e.http_status == 404


def test_already_running_http_status() -> None:
    e = MigrationAlreadyRunningException(migration_id="xyz")
    assert e.http_status == 409


def test_service_exception_inherits_base() -> None:
    e = ServiceException("svc error")
    assert isinstance(e, MigrationAgentError)


def test_validation_exception_http_status() -> None:
    e = ValidationException("bad input")
    assert e.http_status == 422


def test_default_messages_are_strings() -> None:
    for cls in (
        MigrationAgentError,
        AgentException,
        WorkflowException,
        ServiceException,
        ValidationException,
    ):
        e = cls()
        assert isinstance(e.message, str)
        assert len(e.message) > 0
