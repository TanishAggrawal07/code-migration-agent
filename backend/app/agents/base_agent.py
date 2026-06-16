"""
LangGraph agent base class and stub implementations.

Defines the BaseAgent interface that all migration agents implement.
Concrete stub agents (Parser, Analyzer, Migration) are scaffolded here;
business logic will be added in later modules.

Usage:
    from app.agents.base_agent import ParserAgent
    agent = ParserAgent()
    result = await agent.run({"source_code": "..."})
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Agent status / result ─────────────────────────────────────────────────

class AgentStatus(str, Enum):
    """Lifecycle state of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentResult:
    """Structured result returned by every agent."""

    status: AgentStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    agent_name: str = ""

    @property
    def success(self) -> bool:
        """True when the agent completed without errors."""
        return self.status == AgentStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result to a plain dict."""
        return {
            "status": self.status.value,
            "agent_name": self.agent_name,
            "data": self.data,
            "error": self.error,
        }


# ── Base agent ────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Abstract base class for all migration pipeline agents.

    Each concrete agent must implement :meth:`run` and :meth:`validate`.
    The ``name`` and ``description`` class attributes identify the agent
    in logs and API responses.
    """

    #: Human-readable agent name (override in subclasses)
    name: str = "base_agent"

    #: Short description of what this agent does
    description: str = "Base agent — no business logic"

    def __init__(self) -> None:
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    @abstractmethod
    async def run(self, state: dict[str, Any]) -> AgentResult:
        """
        Execute the agent's primary task.

        Args:
            state: LangGraph state dict passed between agents.

        Returns:
            :class:`AgentResult` with status and output data.
        """

    @abstractmethod
    async def validate(self, state: dict[str, Any]) -> bool:
        """
        Validate that the state contains everything this agent needs.

        Args:
            state: Current pipeline state.

        Returns:
            ``True`` if preconditions are met, ``False`` otherwise.
        """

    async def safe_run(self, state: dict[str, Any]) -> AgentResult:
        """
        Run the agent with top-level exception handling.

        Wraps :meth:`run` so unhandled exceptions produce a FAILED result
        rather than crashing the pipeline.

        Args:
            state: LangGraph state dict.

        Returns:
            :class:`AgentResult` — always returns, never raises.
        """
        self._logger.info("Agent starting — %s", self.name)
        try:
            valid = await self.validate(state)
            if not valid:
                return AgentResult(
                    status=AgentStatus.SKIPPED,
                    agent_name=self.name,
                    error="Validation failed — required state keys missing",
                )
            result = await self.run(state)
            result.agent_name = self.name
            self._logger.info(
                "Agent finished — %s  status=%s", self.name, result.status.value
            )
            return result
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.error("Agent %s failed: %s", self.name, exc, exc_info=True)
            return AgentResult(
                status=AgentStatus.FAILED,
                agent_name=self.name,
                error=str(exc),
            )


# ── Concrete stub agents ──────────────────────────────────────────────────

class ParserAgent(BaseAgent):
    """
    Agent responsible for parsing .NET source files into ASTs.

    Stub implementation — business logic in Module 1.
    """

    name = "parser_agent"
    description = "Parses .NET C# source files using Tree-sitter to produce ASTs"

    async def validate(self, state: dict[str, Any]) -> bool:
        """Requires 'source_code' or 'project_path' in state."""
        return "source_code" in state or "project_path" in state

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """Stub: returns a placeholder parse result."""
        self._logger.info("ParserAgent.run — stub implementation")
        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={
                "parsed": True,
                "message": "Parser stub — implement in Module 1",
                "source_keys": list(state.keys()),
            },
        )


class AnalyzerAgent(BaseAgent):
    """
    Agent responsible for semantic analysis of the parsed AST.

    Stub implementation — business logic in Module 2.
    """

    name = "analyzer_agent"
    description = "Performs semantic analysis: types, dependencies, namespace mapping"

    async def validate(self, state: dict[str, Any]) -> bool:
        """Requires 'parsed_ast' in state (produced by ParserAgent)."""
        return "parsed_ast" in state or True  # relaxed for stub

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """Stub: returns a placeholder analysis result."""
        self._logger.info("AnalyzerAgent.run — stub implementation")
        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={
                "analyzed": True,
                "message": "Analyzer stub — implement in Module 2",
            },
        )


class MigrationAgent(BaseAgent):
    """
    Agent responsible for translating C# constructs to Java.

    Stub implementation — business logic in Module 3.
    """

    name = "migration_agent"
    description = "Translates .NET code to Java using Gemini 2.5 Flash and RAG"

    async def validate(self, state: dict[str, Any]) -> bool:
        """Requires 'analysis_result' in state (produced by AnalyzerAgent)."""
        return "analysis_result" in state or True  # relaxed for stub

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """Stub: returns a placeholder migration result."""
        self._logger.info("MigrationAgent.run — stub implementation")
        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={
                "migrated": True,
                "message": "Migration stub — implement in Module 3",
            },
        )


# ── Agent registry ────────────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    ParserAgent.name:    ParserAgent,
    AnalyzerAgent.name:  AnalyzerAgent,
    MigrationAgent.name: MigrationAgent,
}


def get_agent(name: str) -> BaseAgent:
    """
    Instantiate and return a registered agent by name.

    Args:
        name: Agent name (e.g. ``"parser_agent"``).

    Returns:
        A new :class:`BaseAgent` instance.

    Raises:
        KeyError: If the name is not in the registry.
    """
    cls = AGENT_REGISTRY[name]
    return cls()
