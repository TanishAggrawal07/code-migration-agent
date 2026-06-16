"""
LangGraph workflow engine — orchestrates the migration pipeline.

Each pipeline stage is a LangGraph node that receives a MigrationState,
calls the corresponding agent, updates state, and returns.  Nodes return
mock data in this module; real logic arrives in Modules 2–5.

Topology (linear for now):
    START → parser → analyzer → embedding → rag → migration → compile → save → END

Usage:
    from app.agents.workflow import WorkflowEngine
    engine = WorkflowEngine()
    state = await engine.run_workflow(initial_state)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph  # type: ignore[import]

from app.agents.base_agent import AgentStatus
from app.agents.registry import agent_registry
from app.agents.state import (
    GeneratedFile,
    LogLevel,
    MigrationStage,
    MigrationState,
    ParsedFile,
)
from app.core.exceptions import WorkflowException

logger = logging.getLogger(__name__)


# ── Pipeline stage ordering (mirrors STAGE_ORDER) ─────────────────────────

_PIPELINE_NODES = [
    "parser_node",
    "analyzer_node",
    "embedding_node",
    "rag_node",
    "migration_node",
    "compile_node",
    "save_node",
]


# ── Node implementations ──────────────────────────────────────────────────
#
# Each node receives the raw state dict (LangGraph convention), extracts
# the MigrationState, does its work, and returns a *partial* dict that
# LangGraph merges back into state.  Nodes never raise — they log errors
# and transition state to FAILED so the graph can route accordingly.
# --------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _parser_node(state: dict[str, Any]) -> dict[str, Any]:
    """Parse uploaded .NET files into structured metadata (stub)."""
    ms: MigrationState = state["migration_state"]
    ms.add_log("[INFO] Parser started", LogLevel.INFO, agent="parser_agent")

    try:
        agent = agent_registry.get("parser_agent")
        agent_state = {
            "source_code": "\n".join(ms.uploaded_files),
            "project_name": ms.project_name,
        }
        result = await agent.safe_run(agent_state)

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Parser failed: {result.error}")
            return {"migration_state": ms}

        # Mock parsed files — real implementation in Module 2
        ms.parsed_files = [
            ParsedFile(
                filename=f,
                path=f,
                classes=["MockClass"],
                methods=["mockMethod"],
                lines=100,
                parsed=True,
            )
            for f in ms.uploaded_files
        ] or [
            ParsedFile(
                filename="SampleApp.cs",
                path="SampleApp.cs",
                classes=["Program", "UserService"],
                methods=["Main", "GetUser", "CreateUser"],
                lines=250,
                parsed=True,
            )
        ]

        ms.advance_stage(MigrationStage.PARSED)
        ms.add_log(
            f"[SUCCESS] Parser completed — {len(ms.parsed_files)} file(s) parsed",
            LogLevel.SUCCESS,
            agent="parser_agent",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("parser_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Parser node exception: {exc}")

    return {"migration_state": ms}


async def _analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Perform semantic analysis on parsed files (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Analyzer started", LogLevel.INFO, agent="analyzer_agent")

    try:
        agent = agent_registry.get("analyzer_agent")
        result = await agent.safe_run({"parsed_files": [f.model_dump() for f in ms.parsed_files]})

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Analyzer failed: {result.error}")
            return {"migration_state": ms}

        # Store analysis result in context for downstream nodes
        ms.context["analysis"] = result.data
        ms.advance_stage(MigrationStage.ANALYZED)
        ms.add_log("[SUCCESS] Analyzer completed", LogLevel.SUCCESS, agent="analyzer_agent")

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("analyzer_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Analyzer node exception: {exc}")

    return {"migration_state": ms}


async def _embedding_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate and store embeddings for code chunks (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Embedding generation started", LogLevel.INFO, agent="embedding_node")

    try:
        # Mock: create one chunk per parsed file
        ms.chunks = [
            f"// {pf.filename}\npublic class {cls} {{}}"
            for pf in ms.parsed_files
            for cls in (pf.classes or ["MockClass"])
        ] or ["// placeholder chunk"]

        ms.embeddings_created = True
        ms.embedding_count = len(ms.chunks)
        ms.advance_stage(MigrationStage.EMBEDDED)
        ms.add_log(
            f"[SUCCESS] Embeddings created — {ms.embedding_count} chunk(s)",
            LogLevel.SUCCESS,
            agent="embedding_node",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("embedding_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Embedding node exception: {exc}")

    return {"migration_state": ms}


async def _rag_node(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant Java migration patterns from ChromaDB (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] RAG retrieval started", LogLevel.INFO, agent="rag_node")

    try:
        # Mock context — real retrieval in Module 3
        ms.retrieved_context = [
            "// Java pattern: Spring @Service replaces C# [Service]",
            "// Java pattern: Optional<T> replaces C# Nullable<T>",
            "// Java pattern: ArrayList<T> replaces C# List<T>",
        ]
        ms.advance_stage(MigrationStage.RETRIEVED)
        ms.add_log(
            f"[SUCCESS] RAG retrieved {len(ms.retrieved_context)} pattern(s)",
            LogLevel.SUCCESS,
            agent="rag_node",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("rag_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"RAG node exception: {exc}")

    return {"migration_state": ms}


async def _migration_node(state: dict[str, Any]) -> dict[str, Any]:
    """Translate C# code to Java using Gemini 2.5 Flash (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Migration (code generation) started", LogLevel.INFO, agent="migration_agent")

    try:
        agent = agent_registry.get("migration_agent")
        result = await agent.safe_run({
            "chunks": ms.chunks,
            "retrieved_context": ms.retrieved_context,
        })

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Migration agent failed: {result.error}")
            return {"migration_state": ms}

        # Mock generated Java files — real generation in Module 3
        ms.generated_java_files = [
            GeneratedFile(
                filename=pf.filename.replace(".cs", ".java"),
                path=pf.filename.replace(".cs", ".java"),
                source_file=pf.filename,
                compile_success=False,
                content_preview="// Generated Java stub\npublic class {} {}".format(
                    (pf.classes[0] if pf.classes else "GeneratedClass"), "{}"
                ),
            )
            for pf in ms.parsed_files
        ] or [
            GeneratedFile(
                filename="SampleApp.java",
                path="SampleApp.java",
                source_file="SampleApp.cs",
                compile_success=False,
                content_preview="// Generated Java stub\npublic class SampleApp {}",
            )
        ]

        ms.advance_stage(MigrationStage.MIGRATED)
        ms.add_log(
            f"[SUCCESS] Migration completed — {len(ms.generated_java_files)} Java file(s) generated",
            LogLevel.SUCCESS,
            agent="migration_agent",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("migration_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Migration node exception: {exc}")

    return {"migration_state": ms}


async def _compile_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compile generated Java output and validate (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Compilation started", LogLevel.INFO, agent="compile_node")

    try:
        # Mock: all files compile successfully in stub mode
        for gf in ms.generated_java_files:
            gf.compile_success = True

        ms.compile_status = "success"
        ms.advance_stage(MigrationStage.COMPILED)
        ms.add_log(
            f"[SUCCESS] Compilation completed — {len(ms.generated_java_files)} file(s) OK",
            LogLevel.SUCCESS,
            agent="compile_node",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("compile_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Compile node exception: {exc}")

    return {"migration_state": ms}


async def _save_node(state: dict[str, Any]) -> dict[str, Any]:
    """Persist generated Java files to the output directory (stub)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Saving output files", LogLevel.INFO, agent="save_node")

    try:
        # Mock: just mark as saved — real file I/O in Module 4
        ms.context["output_path"] = f"./outputs/{ms.migration_id}/"
        ms.advance_stage(MigrationStage.SAVED)
        ms.add_log(
            "[SUCCESS] All files saved successfully",
            LogLevel.SUCCESS,
            agent="save_node",
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("save_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Save node exception: {exc}")

    return {"migration_state": ms}


# ── Routing ───────────────────────────────────────────────────────────────


def _should_continue(state: dict[str, Any]) -> str:
    """Route to END immediately if state is FAILED."""
    ms: MigrationState = state["migration_state"]
    return END if ms.is_failed else "continue"


# ── Workflow engine ───────────────────────────────────────────────────────


class WorkflowEngine:
    """
    LangGraph-based orchestrator for the migration pipeline.

    Builds a compiled StateGraph once and reuses it for every run.
    The graph is linear with a failure short-circuit at each node.
    """

    def __init__(self) -> None:
        self._graph = self._build_graph()
        logger.info("WorkflowEngine initialised — %d nodes", len(_PIPELINE_NODES))

    def _build_graph(self) -> Any:
        """Construct and compile the LangGraph StateGraph."""
        builder: StateGraph = StateGraph(dict)  # type: ignore[arg-type]

        # Add nodes
        builder.add_node("parser_node",    _parser_node)
        builder.add_node("analyzer_node",  _analyzer_node)
        builder.add_node("embedding_node", _embedding_node)
        builder.add_node("rag_node",       _rag_node)
        builder.add_node("migration_node", _migration_node)
        builder.add_node("compile_node",   _compile_node)
        builder.add_node("save_node",      _save_node)

        # Linear edges: START → parser → analyzer → … → save → END
        builder.add_edge(START, "parser_node")
        builder.add_edge("parser_node",    "analyzer_node")
        builder.add_edge("analyzer_node",  "embedding_node")
        builder.add_edge("embedding_node", "rag_node")
        builder.add_edge("rag_node",       "migration_node")
        builder.add_edge("migration_node", "compile_node")
        builder.add_edge("compile_node",   "save_node")
        builder.add_edge("save_node",      END)

        return builder.compile()

    async def run_workflow(self, initial_state: MigrationState) -> MigrationState:
        """
        Execute the full migration pipeline for *initial_state*.

        Args:
            initial_state: The starting :class:`MigrationState`.

        Returns:
            The updated :class:`MigrationState` after all nodes have run.

        Raises:
            WorkflowException: If the graph raises an unhandled exception.
        """
        logger.info(
            "Workflow starting — migration_id=%s project=%s",
            initial_state.migration_id,
            initial_state.project_name,
        )

        initial_state.add_log("[INFO] Workflow started", LogLevel.INFO)

        try:
            graph_input = {"migration_state": initial_state}

            # Use ainvoke so LangGraph runs async nodes natively
            final_state_dict = await self._graph.ainvoke(graph_input)

            result: MigrationState = final_state_dict["migration_state"]
            logger.info(
                "Workflow finished — migration_id=%s  stage=%s",
                result.migration_id,
                result.current_stage.value,
            )
            return result

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Workflow raised unhandled exception for %s: %s",
                initial_state.migration_id,
                exc,
                exc_info=True,
            )
            initial_state.mark_failed(f"Workflow engine exception: {exc}")
            raise WorkflowException(
                message=str(exc),
                migration_id=initial_state.migration_id,
            ) from exc

    def get_pipeline_status(self, state: MigrationState) -> dict[str, Any]:
        """
        Return a human-readable pipeline visualisation for *state*.

        Args:
            state: Current :class:`MigrationState`.

        Returns:
            Dict with keys ``current_stage``, ``completed``, ``remaining``,
            ``progress_pct``, and ``is_failed``.
        """
        from app.agents.state import STAGE_ORDER

        completed = [s.value for s in state.completed_stages if s != MigrationStage.FAILED]
        # If the migration is complete (SAVED), include the current stage in completed
        if state.is_complete and state.current_stage not in state.completed_stages:
            completed.append(state.current_stage.value)

        remaining = [
            s.value
            for s in STAGE_ORDER
            if s not in state.completed_stages and s != state.current_stage
        ]

        total = len(STAGE_ORDER)
        done_count = len(completed)
        progress_pct = round((done_count / total) * 100) if total else 0

        return {
            "migration_id": state.migration_id,
            "current_stage": state.current_stage.value,
            "completed": completed,
            "remaining": remaining,
            "progress_pct": progress_pct,
            "is_failed": state.is_failed,
            "is_complete": state.is_complete,
            "file_count": len(state.uploaded_files),
            "generated_count": len(state.generated_java_files),
            "log_count": len(state.logs),
        }


# ── Module-level singleton ────────────────────────────────────────────────

_engine_instance: WorkflowEngine | None = None


def get_workflow_engine() -> WorkflowEngine:
    """Return the process-wide WorkflowEngine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WorkflowEngine()
    return _engine_instance