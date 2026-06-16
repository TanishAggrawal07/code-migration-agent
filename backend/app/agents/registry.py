"""
Agent registry — central catalogue of all pipeline agents.

New agents are registered at module import time via
:meth:`AgentRegistry.register`.  The registry is a process-wide
singleton so any module can look up an agent by name.

Usage:
    from app.agents.registry import agent_registry
    agent = agent_registry.get("parser_agent")
    result = await agent.safe_run(state)
"""

from __future__ import annotations

import logging
from typing import Optional, Type

from app.agents.base_agent import (
    AgentResult,
    BaseAgent,
    ParserAgent,
    AnalyzerAgent,
    MigrationAgent,
)

logger = logging.getLogger(__name__)


class AgentRegistryError(Exception):
    """Raised when an agent lookup or registration fails."""


class AgentRegistry:
    """
    Thread-safe (GIL-protected) registry mapping agent names to classes.

    Agents are registered as *classes*, not instances, so each call to
    :meth:`get` creates a fresh instance — avoiding shared mutable state
    across concurrent workflow runs.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Type[BaseAgent]] = {}

    # ── Registration ──────────────────────────────────────────────────

    def register(self, agent_cls: Type[BaseAgent]) -> Type[BaseAgent]:
        """
        Register an agent class under its ``name`` class attribute.

        Can be used as a decorator::

            @agent_registry.register
            class MyAgent(BaseAgent):
                name = "my_agent"

        Args:
            agent_cls: A :class:`BaseAgent` subclass.

        Returns:
            The same class (allows decorator use).

        Raises:
            AgentRegistryError: If the agent name is already taken.
        """
        agent_name = agent_cls.name
        if agent_name in self._registry:
            raise AgentRegistryError(
                f"Agent {agent_name!r} is already registered. "
                "Use replace=True to override."
            )
        self._registry[agent_name] = agent_cls
        logger.debug("Agent registered — name=%s class=%s", agent_name, agent_cls.__name__)
        return agent_cls

    def register_or_replace(self, agent_cls: Type[BaseAgent]) -> Type[BaseAgent]:
        """Register or silently replace an existing agent."""
        self._registry[agent_cls.name] = agent_cls
        return agent_cls

    # ── Lookup ────────────────────────────────────────────────────────

    def get(self, name: str) -> BaseAgent:
        """
        Instantiate and return a registered agent by name.

        Args:
            name: Agent name as registered.

        Returns:
            A fresh :class:`BaseAgent` instance.

        Raises:
            AgentRegistryError: If *name* is not in the registry.
        """
        cls = self._registry.get(name)
        if cls is None:
            available = ", ".join(self._registry.keys())
            raise AgentRegistryError(
                f"Agent {name!r} not found. Available: {available}"
            )
        return cls()

    def get_class(self, name: str) -> Type[BaseAgent]:
        """Return the agent *class* (not an instance) for *name*."""
        cls = self._registry.get(name)
        if cls is None:
            raise AgentRegistryError(f"Agent {name!r} not found.")
        return cls

    # ── Introspection ─────────────────────────────────────────────────

    def list_agents(self) -> list[dict[str, str]]:
        """
        Return a sorted list of registered agent descriptors.

        Returns:
            List of dicts with ``name`` and ``description`` keys.
        """
        return sorted(
            [
                {"name": name, "description": cls.description}
                for name, cls in self._registry.items()
            ],
            key=lambda d: d["name"],
        )

    def is_registered(self, name: str) -> bool:
        """Return True if *name* maps to a registered agent."""
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: object) -> bool:
        return name in self._registry

    def __repr__(self) -> str:
        names = list(self._registry.keys())
        return f"AgentRegistry(agents={names})"


# ── Process-wide singleton ────────────────────────────────────────────────

agent_registry = AgentRegistry()

# Auto-register all built-in agents at import time
for _cls in (ParserAgent, AnalyzerAgent, MigrationAgent):
    agent_registry.register(_cls)

logger.debug("AgentRegistry initialised — %d agents loaded", len(agent_registry))
