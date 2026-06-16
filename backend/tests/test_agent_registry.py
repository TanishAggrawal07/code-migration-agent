"""
Tests for AgentRegistry.
"""

import pytest

from app.agents.base_agent import BaseAgent, AgentResult, AgentStatus
from app.agents.registry import AgentRegistry, AgentRegistryError, agent_registry


# ── Helpers ───────────────────────────────────────────────────────────────

class _DummyAgent(BaseAgent):
    name = "dummy_test_agent"
    description = "Dummy agent for tests"

    async def validate(self, state: dict) -> bool:  # type: ignore[override]
        return True

    async def run(self, state: dict) -> AgentResult:  # type: ignore[override]
        return AgentResult(status=AgentStatus.SUCCESS, agent_name=self.name)


# ── Tests ─────────────────────────────────────────────────────────────────

def test_registry_has_builtin_agents() -> None:
    """All three built-in agents must be registered at import time."""
    for name in ("parser_agent", "analyzer_agent", "migration_agent"):
        assert name in agent_registry


def test_registry_len_at_least_three() -> None:
    assert len(agent_registry) >= 3


def test_get_returns_fresh_instance() -> None:
    """Each call to get() must return a distinct object."""
    a = agent_registry.get("parser_agent")
    b = agent_registry.get("parser_agent")
    assert a is not b


def test_get_unknown_raises() -> None:
    with pytest.raises(AgentRegistryError):
        agent_registry.get("no_such_agent")


def test_list_agents_returns_dicts() -> None:
    agents = agent_registry.list_agents()
    assert isinstance(agents, list)
    for entry in agents:
        assert "name" in entry
        assert "description" in entry


def test_list_agents_is_sorted() -> None:
    names = [a["name"] for a in agent_registry.list_agents()]
    assert names == sorted(names)


def test_register_new_agent() -> None:
    """A custom agent can be registered in a fresh registry."""
    reg = AgentRegistry()

    class _Local(BaseAgent):
        name = "local_agent"
        description = "local"
        async def validate(self, state: dict) -> bool:  # type: ignore[override]
            return True
        async def run(self, state: dict) -> AgentResult:  # type: ignore[override]
            return AgentResult(status=AgentStatus.SUCCESS)

    reg.register(_Local)
    assert reg.is_registered("local_agent")
    assert isinstance(reg.get("local_agent"), _Local)


def test_register_duplicate_raises() -> None:
    """Registering the same name twice must raise AgentRegistryError."""
    reg = AgentRegistry()

    class _A(BaseAgent):
        name = "dup_agent"
        description = "dup"
        async def validate(self, state: dict) -> bool:  # type: ignore[override]
            return True
        async def run(self, state: dict) -> AgentResult:  # type: ignore[override]
            return AgentResult(status=AgentStatus.SUCCESS)

    class _B(_A):
        pass

    reg.register(_A)
    with pytest.raises(AgentRegistryError, match="already registered"):
        reg.register(_B)


def test_register_or_replace_silently_replaces() -> None:
    reg = AgentRegistry()

    class _V1(BaseAgent):
        name = "replaceable"
        description = "v1"
        async def validate(self, state: dict) -> bool:  # type: ignore[override]
            return True
        async def run(self, state: dict) -> AgentResult:  # type: ignore[override]
            return AgentResult(status=AgentStatus.SUCCESS)

    class _V2(_V1):
        description = "v2"

    reg.register(_V1)
    reg.register_or_replace(_V2)
    assert reg.get_class("replaceable") is _V2


def test_is_registered_true_for_parser() -> None:
    assert agent_registry.is_registered("parser_agent") is True


def test_is_registered_false_for_unknown() -> None:
    assert agent_registry.is_registered("ghost_agent") is False
