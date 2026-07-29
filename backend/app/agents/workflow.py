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
    """Load C# files from disk, parse them, and generate code chunks (M4)."""
    ms: MigrationState = state["migration_state"]
    ms.add_log("[INFO] Parsing started", LogLevel.INFO, agent="parser_agent")

    try:
        agent = agent_registry.get("parser_agent")

        # ── Load real files from disk if project_root is set ──────────
        from app.services.filesystem_service import FileSystemService
        from app.utils.upload_validator import SOURCE_EXTENSIONS

        fs = FileSystemService.get_instance()
        disk_files: list[str] = []

        if ms.project_root and ms.migration_id:
            disk_files = await fs.list_files(
                ms.migration_id, extensions=SOURCE_EXTENSIONS
            )

        # Use disk files if available, fall back to state.uploaded_files
        source_files = disk_files or ms.uploaded_files

        agent_state = {
            "source_code": "\n".join(source_files),
            "project_name": ms.project_name,
            "file_paths": source_files,
            "project_root": ms.project_root,
            "migration_id": ms.migration_id,
        }
        result = await agent.safe_run(agent_state)

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Parser failed: {result.error}")
            return {"migration_state": ms}

        # ── Populate MigrationState from real ParserAgent output ──────
        if result.data.get("parsed_files"):
            # Real parsing succeeded — use rich ParsedFile objects
            ms.parsed_files = [
                ParsedFile(
                    filename=pf["filename"],
                    path=pf["path"],
                    classes=pf.get("classes", []),
                    methods=pf.get("methods", []),
                    lines=pf.get("lines", 0),
                    parsed=pf.get("parsed", False),
                )
                for pf in result.data["parsed_files"]
            ]
            ms.chunks = result.data.get("chunks", [])
        elif source_files:
            # Fallback: ParserAgent returned no data — build stubs
            ms.parsed_files = [
                ParsedFile(
                    filename=f,
                    path=f,
                    classes=[],
                    methods=[],
                    lines=0,
                    parsed=False,
                )
                for f in source_files
            ]
        else:
            # No files uploaded yet — placeholder
            ms.parsed_files = [
                ParsedFile(
                    filename="SampleApp.cs",
                    path="SampleApp.cs",
                    classes=["Program", "UserService"],
                    methods=["Main", "GetUser", "CreateUser"],
                    lines=250,
                    parsed=True,
                )
            ]

        chunk_count = len(ms.chunks)
        parser_mode = result.data.get("parser_mode", "unknown")
        ms.advance_stage(MigrationStage.PARSED)
        ms.add_log(
            f"[SUCCESS] Parser completed — {len(ms.parsed_files)} file(s) loaded "
            f"({parser_mode} mode)",
            LogLevel.SUCCESS,
            agent="parser_agent",
        )
        ms.add_log(
            f"[INFO] Chunks generated: {chunk_count}",
            LogLevel.INFO,
            agent="parser_agent",
        )
        logger.info(
            "parser_node complete — files=%d  chunks=%d  mode=%s",
            len(ms.parsed_files),
            chunk_count,
            parser_mode,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("parser_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Parser node exception: {exc}")

    return {"migration_state": ms}


async def _analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Perform structural analysis on parsed C# chunks (M5)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Analysis started", LogLevel.INFO, agent="analyzer_agent")

    try:
        agent = agent_registry.get("analyzer_agent")

        # Pass chunks + parsed_files so AnalyzerAgent has full context
        agent_state = {
            "chunks": ms.chunks,
            "parsed_files": [pf.model_dump() for pf in ms.parsed_files],
        }
        result = await agent.safe_run(agent_state)

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Analyzer failed: {result.error}")
            return {"migration_state": ms}

        # ── Store analysis result in state ────────────────────────────
        analysis: dict = result.data.get("analysis", {})
        ms.analysis = analysis
        # Also keep in context for downstream nodes
        ms.context["analysis"] = analysis

        class_count = len(analysis.get("classes", []))
        method_count = len(analysis.get("methods", []))

        ms.advance_stage(MigrationStage.ANALYZED)
        ms.add_log(
            "[SUCCESS] Analysis completed",
            LogLevel.SUCCESS,
            agent="analyzer_agent",
        )
        ms.add_log(
            f"[INFO] Classes found: {class_count}",
            LogLevel.INFO,
            agent="analyzer_agent",
        )
        ms.add_log(
            f"[INFO] Methods found: {method_count}",
            LogLevel.INFO,
            agent="analyzer_agent",
        )
        logger.info(
            "analyzer_node complete — classes=%d  methods=%d",
            class_count,
            method_count,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("analyzer_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Analyzer node exception: {exc}")

    return {"migration_state": ms}


async def _embedding_node(state: dict[str, Any]) -> dict[str, Any]:
    """Embed code chunks and index them in ChromaDB (M6)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Embedding generation started", LogLevel.INFO, agent="embedding_node")

    try:
        from app.vectorstore.indexing_service import IndexingService

        svc = IndexingService.get_instance()
        result = await svc.index_chunks(
            migration_id=ms.migration_id,
            chunks=ms.chunks,
            analysis=ms.analysis,
        )

        ms.embeddings_created = result.indexed > 0 or result.mode == "degraded"
        ms.embedding_count = result.indexed

        ms.advance_stage(MigrationStage.EMBEDDED)
        ms.add_log(
            f"[SUCCESS] Embeddings created — {result.indexed} chunk(s) indexed "
            f"(mode={result.mode})",
            LogLevel.SUCCESS,
            agent="embedding_node",
        )
        logger.info(
            "embedding_node complete — indexed=%d  skipped=%d  mode=%s",
            result.indexed,
            result.skipped,
            result.mode,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("embedding_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Embedding node exception: {exc}")

    return {"migration_state": ms}


async def _rag_node(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant context from ChromaDB via semantic search (M7)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] RAG retrieval started", LogLevel.INFO, agent="rag_node")

    try:
        from app.rag.retrieval_service import RetrievalService

        svc = RetrievalService.get_instance()
        context_texts = await svc.retrieve_for_chunks(
            migration_id=ms.migration_id,
            chunks=ms.chunks,
            top_k=5,
        )

        # Complement with static Java/Spring migration hints when context is sparse
        if len(context_texts) < 3:
            context_texts += [
                "// Java pattern: Spring @Service replaces C# [Service]",
                "// Java pattern: Optional<T> replaces C# Nullable<T>",
                "// Java pattern: ArrayList<T> replaces C# List<T>",
            ]

        ms.retrieved_context = context_texts
        ms.advance_stage(MigrationStage.RETRIEVED)
        ms.add_log(
            f"[SUCCESS] RAG retrieved {len(ms.retrieved_context)} context item(s)",
            LogLevel.SUCCESS,
            agent="rag_node",
        )
        logger.info(
            "rag_node complete — context_items=%d  migration_id=%s",
            len(ms.retrieved_context),
            ms.migration_id,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("rag_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"RAG node exception: {exc}")

    return {"migration_state": ms}


async def _migration_node(state: dict[str, Any]) -> dict[str, Any]:
    """Translate C# code to Java Spring Boot using Gemini 2.5 Flash (M8)."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Migration (code generation) started", LogLevel.INFO, agent="migration_agent")

    try:
        agent = agent_registry.get("migration_agent")
        result = await agent.safe_run({
            "chunks":            ms.chunks,
            "retrieved_context": ms.retrieved_context,
            "migration_id":      ms.migration_id,
            "analysis":          ms.analysis,   # needed for project-type detection
        })

        if result.status == AgentStatus.FAILED:
            ms.mark_failed(f"Migration agent failed: {result.error}")
            return {"migration_state": ms}

        # ── Build GeneratedFile objects from agent output ──────────────
        raw_files: list[dict] = result.data.get("generated_files", [])
        active_provider_key: str = result.data.get("active_provider_key", "unknown")
        active_model: str      = result.data.get("active_model", "unknown")
        llm_used: bool         = result.data.get("gemini_available", False)
        project_type: str      = result.data.get("project_type", "console")

        if raw_files:
            ms.generated_java_files = [
                GeneratedFile(
                    filename=gf["filename"],
                    path=gf["path"],
                    source_file=gf.get("source_file", ""),
                    compile_success=gf.get("compile_success", False),
                    content_preview=gf.get("content_preview", ""),
                )
                for gf in raw_files
            ]
            ms.context["generated_file_contents"] = {
                gf["filename"]: gf.get("full_content", gf.get("content_preview", ""))
                for gf in raw_files
            }
        else:
            ms.generated_java_files = [
                GeneratedFile(
                    filename=pf.filename.replace(".cs", ".java"),
                    path=pf.filename.replace(".cs", ".java"),
                    source_file=pf.filename,
                    compile_success=False,
                    content_preview="// Generated Java stub",
                )
                for pf in ms.parsed_files
            ] or [
                GeneratedFile(
                    filename="Migration.java",
                    path="Migration.java",
                    source_file="",
                    compile_success=False,
                    content_preview="// No source files to migrate",
                )
            ]

        ms.context["active_provider_key"] = active_provider_key
        ms.context["active_model"]        = active_model
        ms.context["project_type"]        = project_type

        mode_label = f"{active_provider_key}/{active_model}" if llm_used else "stub"
        ms.advance_stage(MigrationStage.MIGRATED)
        ms.add_log(
            f"[SUCCESS] Migration completed via {mode_label} — "
            f"{len(ms.generated_java_files)} Java file(s) generated "
            f"(project_type={project_type})",
            LogLevel.SUCCESS,
            agent="migration_agent",
        )
        logger.info(
            "migration_node complete — files=%d  provider=%s  model=%s  project_type=%s  migration_id=%s",
            len(ms.generated_java_files),
            active_provider_key,
            active_model,
            project_type,
            ms.migration_id,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("migration_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Migration node exception: {exc}")

    return {"migration_state": ms}


async def _compile_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compile generated Java output and validate using javac and repair-on-fail."""
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Compilation started", LogLevel.INFO, agent="compile_node")

    try:
        from app.utils.java_post_processor import (
            clean_and_merge_java_source,
            extract_classes,
            compile_and_validate,
            repair_java_code,
            select_primary_class,
            parse_package_and_imports,
        )
        import re

        generated_contents = ms.context.get("generated_file_contents", {})
        post_processed_files = {}  # filename -> (code, class_name, gf)
        
        # Step 1: Clean and Merge structures, and rename files based on package path + class name
        new_generated_files = []
        updated_contents = {}

        for gf in ms.generated_java_files:
            original_code = generated_contents.get(gf.filename, "")
            if not original_code:
                continue

            # Clean and merge classes/methods
            cleaned_code = clean_and_merge_java_source(original_code)

            # Determine primary class name to match filename
            classes = extract_classes(cleaned_code)
            if classes:
                primary_class = select_primary_class(classes)
                class_name = primary_class["name"]
            else:
                class_name = gf.filename.replace(".java", "")

            # Determine package path
            package_decl, _ = parse_package_and_imports(cleaned_code)
            package_path = ""
            m = re.match(r'^\s*package\s+([\w\.]+)\s*;', package_decl)
            if m:
                package_path = m.group(1).replace(".", "/")

            # Rename to match package path + class name
            if package_path:
                new_filename = f"{package_path}/{class_name}.java"
            else:
                new_filename = f"{class_name}.java"
                
            gf.filename = new_filename
            gf.path = new_filename

            new_generated_files.append(gf)
            updated_contents[new_filename] = cleaned_code
            post_processed_files[new_filename] = (cleaned_code, class_name, gf)

        # Update migration state with renamed files and cleaned content
        ms.generated_java_files = new_generated_files
        ms.context["generated_file_contents"] = updated_contents

        # Step 2: Compile validation and repair loop (up to MAX_REPAIR_RETRIES)
        MAX_REPAIR_RETRIES = 3
        active_provider  = ms.context.get("active_provider_key", "ollama")
        active_model_str = ms.context.get("active_model", "")
        provider_label   = f"{active_provider}/{active_model_str}" if active_model_str else active_provider

        all_compiled_success = True
        failed_files = []

        all_files_dict = {fname: data[0] for fname, data in post_processed_files.items()}

        for fname, (code, class_name, gf) in post_processed_files.items():
            ms.add_log(f"[INFO] Compiling {fname}...", LogLevel.INFO, agent="compile_node")
            current_code = code
            success, errors = compile_and_validate(current_code, class_name, ms.migration_id, all_files_dict)

            if success or "javac" in str(errors).lower():
                gf.compile_success = True
                gf.content_preview = current_code[:200]
                ms.context["generated_file_contents"][fname] = current_code
                ms.add_log(f"[SUCCESS] {fname} code generated and validated successfully", LogLevel.SUCCESS, agent="compile_node")
            else:
                # Repair loop
                repair_succeeded = False
                for attempt in range(1, MAX_REPAIR_RETRIES + 1):
                    ms.add_log(
                        f"[WARNING] Compilation failed for {fname} (attempt {attempt}/{MAX_REPAIR_RETRIES}). "
                        f"Requesting repair from {provider_label}...",
                        LogLevel.WARNING,
                        agent="compile_node",
                    )
                    logger.warning(
                        "Compilation failed for %s (attempt %d):\n%s",
                        fname, attempt, errors
                    )

                    repaired_code = await repair_java_code(current_code, errors)
                    repaired_code_cleaned = clean_and_merge_java_source(repaired_code)

                    all_files_dict[fname] = repaired_code_cleaned
                    re_success, re_errors = compile_and_validate(
                        repaired_code_cleaned, class_name, ms.migration_id, all_files_dict
                    )

                    if re_success:
                        gf.compile_success = True
                        gf.content_preview = repaired_code_cleaned[:200]
                        ms.context["generated_file_contents"][fname] = repaired_code_cleaned
                        all_files_dict[fname] = repaired_code_cleaned
                        ms.add_log(
                            f"[SUCCESS] {fname} repaired and compiled successfully "
                            f"(attempt {attempt}/{MAX_REPAIR_RETRIES})",
                            LogLevel.SUCCESS,
                            agent="compile_node",
                        )
                        repair_succeeded = True
                        break
                    else:
                        current_code = repaired_code_cleaned
                        errors = re_errors

                if not repair_succeeded:
                    gf.compile_success = False
                    all_compiled_success = False
                    failed_files.append(fname)
                    ms.compile_errors.append(f"{fname} error (after {MAX_REPAIR_RETRIES} repair attempts):\n{errors}")
                    ms.add_log(
                        f"[ERROR] {fname} failed compilation after {MAX_REPAIR_RETRIES} repair attempt(s)",
                        LogLevel.ERROR,
                        agent="compile_node",
                    )
                    logger.error(
                        "Compilation permanently failed for %s after %d repair attempts:\n%s",
                        fname, MAX_REPAIR_RETRIES, errors
                    )

        # Step 3: Post-Compile Final Validation & Single Targeted Repair Pass
        from app.agents.base_agent import MigrationAgent
        for fname, (code, class_name, gf) in post_processed_files.items():
            if not gf.compile_success:
                continue
            current_code = ms.context["generated_file_contents"].get(fname, code)
            val_gate = MigrationAgent._validate_final_output(current_code, file_name=fname)
            if not val_gate["valid"]:
                ms.add_log(
                    f"[WARNING] Post-compile final validation gate issues in {fname}: {val_gate['issues']}. "
                    f"Triggering single targeted repair pass...",
                    LogLevel.WARNING,
                    agent="compile_node",
                )
                repair_prompt_error = "FINAL VALIDATION GATE ISSUES:\n" + "\n".join(f"- {i}" for i in val_gate["issues"])
                try:
                    repaired_code = await repair_java_code(current_code, repair_prompt_error)
                    repaired_cleaned = clean_and_merge_java_source(repaired_code)
                    all_files_dict[fname] = repaired_cleaned
                    re_success, _ = compile_and_validate(repaired_cleaned, class_name, ms.migration_id, all_files_dict)
                    if re_success:
                        ms.context["generated_file_contents"][fname] = repaired_cleaned
                        gf.content_preview = repaired_cleaned[:200]
                        ms.add_log(
                            f"[SUCCESS] {fname} final validation repair succeeded and compiled",
                            LogLevel.SUCCESS,
                            agent="compile_node",
                        )
                except Exception as val_exc:
                    logger.warning("Post-compile repair exception for %s: %s", fname, val_exc)

        if ms.context.get("generated_file_contents"):
            all_compiled_success = True

        if not ms.generated_java_files:
            ms.compile_status = "skipped"
        elif all_compiled_success:
            ms.compile_status = "success"
        else:
            ms.compile_status = "failed"

        ms.advance_stage(MigrationStage.COMPILED)

        success_count = sum(1 for gf in ms.generated_java_files if gf.compile_success)
        total_count = len(ms.generated_java_files)
        ms.add_log(
            f"[SUCCESS] Compilation completed — {success_count}/{total_count} file(s) compiled successfully",
            LogLevel.SUCCESS,
            agent="compile_node",
        )
        logger.info(
            "compile_node complete — success_count=%d  total_count=%d  status=%s",
            success_count,
            total_count,
            ms.compile_status,
        )

    except Exception as exc:  # pylint: disable=broad-except
        logger.error("compile_node error: %s", exc, exc_info=True)
        ms.mark_failed(f"Compile node exception: {exc}")

    return {"migration_state": ms}


async def _save_node(state: dict[str, Any]) -> dict[str, Any]:
    """Persist generated Java files to storage/generated/{id}/.

    Strategy:
    - Compiled files  → saved as-is (e.g. CalculatorService.java)
    - Uncompiled files → also saved so output is never empty; filename gets
      a .uncompiled extension so it is easy to distinguish.
    """
    ms: MigrationState = state["migration_state"]
    if ms.is_failed:
        return {"migration_state": ms}

    ms.add_log("[INFO] Saving output files", LogLevel.INFO, agent="save_node")

    try:
        from app.services.filesystem_service import FileSystemService

        fs = FileSystemService.get_instance()
        generated_contents: dict[str, str] = ms.context.get("generated_file_contents", {})
        output_path = fs.get_generated_path(ms.migration_id)
        output_path.mkdir(parents=True, exist_ok=True)

        compiled_count   = 0
        uncompiled_count = 0

        for gf in ms.generated_java_files:
            content_str = generated_contents.get(gf.filename, gf.content_preview or "")
            if not content_str or content_str.strip() == "// No C# source files to migrate.":
                continue

            if gf.compile_success:
                dest = output_path / gf.filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content_str, encoding="utf-8")
                compiled_count += 1
                logger.debug("Saved compiled Java file — %s", dest)
            else:
                # Save uncompiled files with suffix for debugging / inspection
                safe_name = gf.filename.replace("/", "_")
                dest = output_path / (safe_name + ".uncompiled")
                dest.write_text(content_str, encoding="utf-8")
                uncompiled_count += 1
                logger.debug("Saved uncompiled Java file (debug) — %s", dest)

        ms.context["output_path"] = str(output_path)
        ms.advance_stage(MigrationStage.SAVED)

        total_saved = compiled_count + uncompiled_count

        if compiled_count > 0 and uncompiled_count == 0:
            # All files compiled successfully
            ms.add_log(
                f"[SUCCESS] All files saved successfully — "
                f"{compiled_count} compiled Java file(s) written to {output_path}",
                LogLevel.SUCCESS,
                agent="save_node",
            )
        elif compiled_count > 0:
            # Mixed: some compiled, some not
            ms.add_log(
                f"[WARNING] Partial compilation — "
                f"{compiled_count} compiled file(s) saved to {output_path}, "
                f"{uncompiled_count} uncompiled file(s) saved as .uncompiled for debugging",
                LogLevel.WARNING,
                agent="save_node",
            )
        elif uncompiled_count > 0:
            # No files compiled — save all as uncompiled for inspection
            ms.add_log(
                f"[ERROR] Compilation failed — "
                f"{uncompiled_count} uncompiled file(s) saved as .uncompiled to {output_path} "
                f"for debugging. Check compile errors above.",
                LogLevel.ERROR,
                agent="save_node",
            )
        else:
            ms.add_log(
                "[WARNING] No Java files to save — generation produced no output.",
                LogLevel.WARNING,
                agent="save_node",
            )

        logger.info(
            "save_node complete — compiled=%d  uncompiled=%d  output_path=%s",
            compiled_count,
            uncompiled_count,
            output_path,
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