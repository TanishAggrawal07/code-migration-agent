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
import re as _re
from abc import ABC, abstractmethod
from collections import defaultdict
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
    Agent responsible for parsing .NET source files into ASTs and chunks.

    M4 implementation — delegates to ParserService which uses Tree-sitter
    (with a regex fallback) to produce structured CodeChunk objects.
    """

    name = "parser_agent"
    description = "Parses .NET C# source files using Tree-sitter to produce ASTs"

    async def validate(self, state: dict[str, Any]) -> bool:
        """Requires 'source_code' or 'project_path' or 'file_paths' in state."""
        return (
            "source_code" in state
            or "project_path" in state
            or "file_paths" in state
        )

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """Parse uploaded .cs files and produce code chunks."""
        from app.parser.parser_service import ParserService

        migration_id: str = state.get("migration_id", "")
        uploaded_files: list[str] = state.get("file_paths", [])
        project_root: str = state.get("project_root", "")

        self._logger.info(
            "ParserAgent.run — migration_id=%s  files=%d",
            migration_id,
            len(uploaded_files),
        )

        svc = ParserService.get_instance()
        result = await svc.parse_migration(
            migration_id=migration_id,
            uploaded_files=uploaded_files,
            project_root=project_root,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={
                "parsed_files": result.parsed_files,
                "chunks": result.chunks,
                "parser_mode": result.parser_mode,
                "total_files": result.total_files,
                "total_chunks": result.total_chunks,
                "errors": result.errors,
            },
        )


class AnalyzerAgent(BaseAgent):
    """
    Agent responsible for semantic analysis of parsed C# code chunks.

    M5 implementation — delegates to AnalyzerService which extracts
    namespaces, imports, classes, interfaces, methods, and dependencies.
    """

    name = "analyzer_agent"
    description = "Performs semantic analysis: types, dependencies, namespace mapping"

    async def validate(self, state: dict[str, Any]) -> bool:
        """Accepts any state — chunks or parsed_files may be empty at start."""
        return True

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """Analyze code chunks and return structural metadata."""
        from app.analyzer.analyzer_service import AnalyzerService

        chunks: list[dict[str, Any]] = state.get("chunks", [])
        parsed_files: list[dict[str, Any]] = state.get("parsed_files", [])

        self._logger.info(
            "AnalyzerAgent.run — chunks=%d  parsed_files=%d",
            len(chunks),
            len(parsed_files),
        )

        svc = AnalyzerService.get_instance()
        analysis = await svc.analyze_chunks(
            chunks=chunks,
            parsed_files=parsed_files,
        )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={"analysis": analysis},
        )


class MigrationAgent(BaseAgent):
    """
    Agent responsible for translating C# constructs to Java.

    Detects the project type (console, web API, library, etc.) from the
    analysis result and builds a context-aware system prompt so the LLM
    produces idiomatic Java without hallucinating Spring Boot annotations
    for plain console applications.

    Improvements (accuracy pass):
      - Change 1: All prompts include CRITICAL CONSTRAINTS forbidding placeholders/omissions
      - Change 2: _build_prompt injects full per-file structural inventory as checklist
      - Change 3: _verify_and_complete checks generated Java against per-file inventory
      - Change 4: analysis dict threaded through entire call chain
      - Change 5: _extract_per_file_inventory produces per-file class/method/property inventory
      - Change 6: _semantic_verify compares C# source vs Java for behaviour correctness
    """

    name = "migration_agent"
    description = "Translates .NET code to Java using the active LLM provider and RAG"

    # ── Project-type detection ─────────────────────────────────────────
    @staticmethod
    def _detect_project_type(analysis: dict, chunks: list[dict]) -> str:
        """
        Classify the uploaded project so the prompt can be tailored.

        Returns one of: 'console', 'webapi', 'mvc', 'library'
        """
        all_text = " ".join(
            c.get("content", "") for c in chunks
        ).lower()
        dependencies: list[str] = [
            d.lower() for d in analysis.get("dependencies", [])
        ]

        # Web API indicators
        web_api_signals = [
            "controller", "apicontroller", "[httpget]", "[httppost]",
            "iactionresult", "actionresult", "microsoft.aspnetcore",
            "[route", "[api",
        ]
        mvc_signals = [
            "viewresult", "iview", "razor", "html.", "model.",
            "@html", "viewbag", "viewdata",
        ]
        library_signals = [
            "class library", ".netstandard", "nuget", "packagereference",
        ]

        # Score each type
        def _score(signals: list[str]) -> int:
            return sum(1 for s in signals if s in all_text or any(s in d for d in dependencies))

        if _score(mvc_signals) >= 2:
            return "mvc"
        if _score(web_api_signals) >= 2:
            return "webapi"
        if _score(library_signals) >= 2:
            return "library"
        # Default: console (most conservative choice — never adds Spring)
        return "console"

    # ── Per-project system prompts ──────────────────────────────────────
    # Change 1: CRITICAL CONSTRAINTS block added at the top of every prompt.
    # This explicitly forbids placeholders, omissions, and creative rewrites.

    _CONSOLE_PROMPT = (
        "You are a DETERMINISTIC SOURCE-TO-SOURCE MIGRATION TOOL, not a code generator.\n"
        "Your ONLY task: convert the given C# code into equivalent Java code, line by line.\n\n"
        "CRITICAL CONSTRAINTS — violation of ANY rule below is UNACCEPTABLE:\n"
        "  ✗ NEVER write placeholder comments: '// Other methods...', '// TODO',\n"
        "    '// Implement later', '// Remaining code...', '// ...rest of methods', or any similar shorthand.\n"
        "  ✗ NEVER omit any class, constructor, field, property, method, enum, or statement.\n"
        "  ✗ NEVER merge two separate classes into one.\n"
        "  ✗ NEVER change the algorithm, control flow, loop logic, or conditions.\n"
        "  ✗ NEVER add code that does not exist in the C# source.\n"
        "  ✗ NEVER rewrite or simplify business logic.\n"
        "  ✓ ALWAYS output the COMPLETE Java file with EVERY member fully implemented.\n"
        "  ✓ If the source has 10 methods, the output MUST have 10 methods.\n"
        "  ✓ If the source has 3 classes, the output MUST have 3 classes.\n"
        "  ✓ Preserve the original program behaviour exactly — correctness is more important than style.\n\n"
        "TASK: Convert the given C# code to plain Java.\n\n"
        "STRICT RULES:\n"
        "- Do NOT add @SpringBootApplication, @Service, @Component, @Autowired, "
        "  @Repository, CommandLineRunner, SpringApplication, or ANY Spring annotations "
        "  UNLESS the source code clearly uses ASP.NET Web API or MVC patterns.\n"
        "- Do NOT import org.springframework.* packages.\n"
        "NAMESPACE MAPPING:\n"
        "- Map C# namespace MyApp.Services -> package com.myapp.services;\n"
        "- Map C# using statements -> Java import statements.\n"
        "- Always include a package declaration at the top of the file.\n"
        "CONSOLE I/O:\n"
        "- Map Console.WriteLine() -> System.out.println().\n"
        "- Map Console.Write() -> System.out.print().\n"
        "- Map Console.ReadLine() -> new java.util.Scanner(System.in).nextLine().\n"
        "AUTO-PROPERTIES & CONSTRUCTORS:\n"
        "- Replace C# auto-properties with private fields + public getters and setters.\n"
        "- Preserve all constructors exactly, renaming them to match the Java class name.\n"
        "COLLECTIONS & LINQ:\n"
        "- Map C# List<T> -> java.util.List<T> (implement with new java.util.ArrayList<T>()).\n"
        "- Map C# Dictionary<K,V> -> java.util.Map<K,V> (implement with new java.util.HashMap<K,V>()).\n"
        "- Map C# HashSet<T> -> java.util.Set<T> (implement with new java.util.HashSet<T>()).\n"
        "- Map LINQ .Where() -> stream().filter().\n"
        "- Map LINQ .Select() -> stream().map().\n"
        "- Map LINQ .FirstOrDefault() -> stream().findFirst().orElse(null).\n"
        "- Map LINQ .Any() -> stream().anyMatch().\n"
        "- Map LINQ .Count() -> stream().count() or .size().\n"
        "- Map LINQ .OrderBy() -> stream().sorted().\n"
        "- Map LINQ .OrderByDescending() -> stream().sorted(java.util.Comparator.reverseOrder()).\n"
        "- Map LINQ .ToList() -> .collect(java.util.stream.Collectors.toList()).\n"
        "EXCEPTIONS:\n"
        "- Map C# Exception -> java.lang.Exception.\n"
        "- Map C# ArgumentException -> java.lang.IllegalArgumentException.\n"
        "- Map C# InvalidOperationException -> java.lang.IllegalStateException.\n"
        "- Map C# NotImplementedException -> java.lang.UnsupportedOperationException.\n"
        "STRING & MATH:\n"
        "- Map string.Format(\"...\", x) -> String.format(\"...\", x).\n"
        "- Map $\"Hello {name}\" -> \"Hello \" + name (or String.format).\n"
        "- Map Math.Max/Min/Abs -> Math.max/min/abs.\n"
        "TYPES:\n"
        "- Map C# int -> int (or Integer for generics).\n"
        "- Map C# string -> String.\n"
        "- Map C# bool -> boolean.\n"
        "- Map C# double/float/long -> double/float/long.\n"
        "- Map C# object -> Object.\n"
        "- Map C# var -> use explicit type or var (Java 10+).\n"
        "MULTI-CLASS FILES:\n"
        "- If the source has multiple classes, output ALL of them in the same .java file.\n"
        "- Only one public class per file; make inner classes package-private or static nested.\n"
        "STATIC METHODS:\n"
        "- Preserve ALL static methods as static.\n"
        "- Map C# Main(string[] args) -> public static void main(String[] args).\n"
        "OUTPUT:\n"
        "- Preserve ALL business logic exactly as-is.\n"
        "- Return ONLY valid, COMPLETE Java source code. No explanations. No markdown fences.\n"
        "- No placeholder comments. Every method body must be fully implemented.\n"
    )

    _WEBAPI_PROMPT = (
        "You are a DETERMINISTIC SOURCE-TO-SOURCE MIGRATION TOOL, not a code generator.\n"
        "Your ONLY task: convert the given C# ASP.NET Web API code into equivalent Java Spring Boot 3, line by line.\n\n"
        "CRITICAL CONSTRAINTS — violation of ANY rule below is UNACCEPTABLE:\n"
        "  ✗ NEVER write placeholder comments: '// Other methods...', '// TODO',\n"
        "    '// Implement later', '// Remaining code...', or any similar shorthand.\n"
        "  ✗ NEVER omit any class, constructor, field, property, method, enum, or statement.\n"
        "  ✗ NEVER change the algorithm, control flow, loop logic, or conditions.\n"
        "  ✗ NEVER add code that does not exist in the C# source.\n"
        "  ✓ ALWAYS output the COMPLETE Java file with EVERY member fully implemented.\n"
        "  ✓ Preserve the original program behaviour exactly.\n\n"
        "TASK: Convert the given C# ASP.NET Web API code to Java Spring Boot 3.\n\n"
        "RULES:\n"
        "- Use Spring Boot 3 / Spring MVC annotations.\n"
        "- Map [ApiController] -> @RestController.\n"
        "- Map [Controller] -> @Controller.\n"
        "- Map [Route(\"api/[controller]\")] -> @RequestMapping(\"/api/...\").\n"
        "- Map [HttpGet] -> @GetMapping, [HttpPost] -> @PostMapping, "
        "  [HttpPut] -> @PutMapping, [HttpDelete] -> @DeleteMapping.\n"
        "- Map IActionResult/ActionResult<T> -> ResponseEntity<T>.\n"
        "- Map [FromBody] -> @RequestBody, [FromQuery] -> @RequestParam, [FromRoute] -> @PathVariable.\n"
        "- Add @Service for service classes, @Repository for data-access classes.\n"
        "- Use constructor injection (no @Autowired on fields).\n"
        "NAMESPACE MAPPING:\n"
        "- Map C# namespace -> Java package declaration.\n"
        "- Map C# using -> Java import.\n"
        "- Always include a package declaration at the top of the file.\n"
        "AUTO-PROPERTIES:\n"
        "- Replace C# auto-properties with private fields + public getters and setters.\n"
        "- Preserve all constructors exactly.\n"
        "COLLECTIONS:\n"
        "- Map C# List<T> -> java.util.List<T> (ArrayList).\n"
        "- Map C# Dictionary<K,V> -> java.util.Map<K,V> (HashMap).\n"
        "TYPES:\n"
        "- Map C# string -> String, int -> int, bool -> boolean.\n"
        "OUTPUT:\n"
        "- Preserve ALL business logic exactly.\n"
        "- Use Java 17 syntax.\n"
        "- Return ONLY valid, COMPLETE Java source code. No explanations. No markdown fences.\n"
        "- No placeholder comments. Every method body must be fully implemented.\n"
    )

    _MVC_PROMPT = (
        "You are a DETERMINISTIC SOURCE-TO-SOURCE MIGRATION TOOL, not a code generator.\n"
        "Your ONLY task: convert the given C# ASP.NET MVC code into equivalent Java Spring MVC, line by line.\n\n"
        "CRITICAL CONSTRAINTS — violation of ANY rule below is UNACCEPTABLE:\n"
        "  ✗ NEVER write placeholder comments: '// Other methods...', '// TODO',\n"
        "    '// Implement later', '// Remaining code...', or any similar shorthand.\n"
        "  ✗ NEVER omit any class, constructor, field, property, method, or statement.\n"
        "  ✗ NEVER change the algorithm, control flow, loop logic, or conditions.\n"
        "  ✗ NEVER add code that does not exist in the C# source.\n"
        "  ✓ ALWAYS output the COMPLETE Java file with EVERY member fully implemented.\n"
        "  ✓ Preserve the original program behaviour exactly.\n\n"
        "TASK: Convert the given C# ASP.NET MVC code to Java Spring MVC.\n\n"
        "RULES:\n"
        "- Use Spring MVC with @Controller (not @RestController for view-returning actions).\n"
        "- Map [HttpGet] -> @GetMapping, [HttpPost] -> @PostMapping.\n"
        "- Map ViewResult -> String (return view name) or ModelAndView.\n"
        "- Map ViewBag/ViewData -> Model (pass model attributes via method parameters or ModelMap).\n"
        "- Add @Service for service classes.\n"
        "- Use constructor injection.\n"
        "NAMESPACE MAPPING:\n"
        "- Map C# namespace -> Java package declaration.\n"
        "- Map C# using -> Java import.\n"
        "- Always include a package declaration at the top of the file.\n"
        "AUTO-PROPERTIES:\n"
        "- Replace C# auto-properties with private fields + public getters and setters.\n"
        "- Preserve all constructors exactly.\n"
        "OUTPUT:\n"
        "- Preserve ALL business logic exactly.\n"
        "- Use Java 17 syntax.\n"
        "- Return ONLY valid, COMPLETE Java source code. No explanations. No markdown fences.\n"
        "- No placeholder comments. Every method body must be fully implemented.\n"
    )

    _LIBRARY_PROMPT = (
        "You are a DETERMINISTIC SOURCE-TO-SOURCE MIGRATION TOOL, not a code generator.\n"
        "Your ONLY task: convert the given C# class library code into equivalent plain Java, line by line.\n\n"
        "CRITICAL CONSTRAINTS — violation of ANY rule below is UNACCEPTABLE:\n"
        "  ✗ NEVER write placeholder comments: '// Other methods...', '// TODO',\n"
        "    '// Implement later', '// Remaining code...', or any similar shorthand.\n"
        "  ✗ NEVER omit any class, constructor, field, property, method, enum, or interface.\n"
        "  ✗ NEVER change the algorithm, control flow, loop logic, or conditions.\n"
        "  ✗ NEVER add code that does not exist in the C# source.\n"
        "  ✓ ALWAYS output the COMPLETE Java file with EVERY member fully implemented.\n"
        "  ✓ Preserve the original public API surface and behaviour exactly.\n\n"
        "TASK: Convert the given C# class library to a plain Java library.\n\n"
        "RULES:\n"
        "- This is a plain Java library — do NOT add Spring annotations.\n"
        "- Map C# interfaces to Java interfaces exactly (same method signatures).\n"
        "- Map C# abstract classes to Java abstract classes.\n"
        "- Replace C# auto-properties with Java getters/setters.\n"
        "- Map C# const -> public static final.\n"
        "- Map C# readonly -> final.\n"
        "- Map C# generics <T> -> Java generics <T>.\n"
        "NAMESPACE MAPPING:\n"
        "- Map C# namespace -> Java package declaration.\n"
        "- Map C# using -> Java import.\n"
        "- Always include a package declaration at the top of the file.\n"
        "COLLECTIONS:\n"
        "- Map C# List<T> -> java.util.List<T> (ArrayList).\n"
        "- Map C# Dictionary<K,V> -> java.util.Map<K,V> (HashMap).\n"
        "OUTPUT:\n"
        "- Preserve ALL public API surface exactly.\n"
        "- Use Java 17 syntax.\n"
        "- Return ONLY valid, COMPLETE Java source code. No explanations. No markdown fences.\n"
        "- No placeholder comments. Every method body must be fully implemented.\n"
    )

    def _get_system_prompt(self, project_type: str) -> str:
        return {
            "console": self._CONSOLE_PROMPT,
            "webapi":  self._WEBAPI_PROMPT,
            "mvc":     self._MVC_PROMPT,
            "library": self._LIBRARY_PROMPT,
        }.get(project_type, self._CONSOLE_PROMPT)

    async def validate(self, state: dict[str, Any]) -> bool:
        """Accepts any state — chunks may be empty when running without uploads."""
        return True

    async def run(self, state: dict[str, Any]) -> AgentResult:
        """
        Translate C# code chunks to Java using the active LLM provider.

        Per-file processing order (accuracy pass):
          1. Extract per-file structural inventory   (Change 5)
          2. Build enriched prompt with inventory    (Changes 2, 4)
          3. Translate with LLM                      (existing)
          4. Structural verification + fix           (Change 3)
          5. Semantic verification + fix             (Change 6)
          6. Pass merged output to compile stage     (unchanged)

        State keys consumed:
            chunks            — list[dict] CodeChunk dicts
            retrieved_context  — list[str] RAG context strings
            migration_id      — str
            analysis          — dict (optional, for project-type detection)
        """
        from app.core.gemini_client import GeminiClient

        chunks: list[dict[str, Any]] = state.get("chunks", [])
        retrieved_context: list[str] = state.get("retrieved_context", [])
        migration_id: str = state.get("migration_id", "")
        analysis: dict = state.get("analysis", {})

        self._logger.info(
            "MigrationAgent.run — migration_id=%s  chunks=%d  context_items=%d",
            migration_id,
            len(chunks),
            len(retrieved_context),
        )

        gemini = GeminiClient.get_instance()
        gemini_available = gemini.is_initialized
        active_provider_key = gemini.active_provider_key if gemini_available else "none"
        active_model = gemini.active_model if gemini_available else "none"

        # Detect project type for context-aware prompt selection
        project_type = self._detect_project_type(analysis, chunks)
        system_prompt = self._get_system_prompt(project_type)
        self._logger.info(
            "MigrationAgent — project_type=%s  provider=%s  model=%s",
            project_type, active_provider_key, active_model,
        )

        # retrieved_context may be a list[str] OR list[dict] depending on caller
        def _ctx_to_str(item: Any) -> str:
            if isinstance(item, str):
                return item
            if isinstance(item, dict):
                return (
                    item.get("content")
                    or item.get("text")
                    or item.get("chunk_content")
                    or str(item)
                )
            return str(item)

        context_block = "\n\n".join(_ctx_to_str(c) for c in retrieved_context) if retrieved_context else ""

        # All source file names for the prompt (so LLM knows what classes exist)
        source_file_names = sorted(set(
            c.get("file_name", "") for c in chunks if c.get("file_name", "").endswith(".cs")
        ))

        # Filter to only .cs chunks (skip file-level non-C# entries)
        cs_chunks = [c for c in chunks if c.get("file_name", "").endswith(".cs")]
        if not cs_chunks:
            cs_chunks = chunks[:1] if chunks else []

        migration_results: list[dict[str, Any]] = []
        generated_files: list[dict[str, Any]] = []

        # ── Group chunks by source file for per-file processing ────────────
        # Change 5 / Change 3 / Change 6: process each file as a unit so that
        # verification is scoped to the correct file, not the whole project.
        chunks_by_file: dict[str, list[dict]] = defaultdict(list)
        for chunk in cs_chunks:
            fname = chunk.get("file_name", "Unknown.cs")
            chunks_by_file[fname].append(chunk)

        for file_name, file_chunks in chunks_by_file.items():
            # ── Extract per-file structural inventory ──────────────────────
            per_file_inv = self._extract_per_file_inventory(file_chunks)
            self._logger.debug(
                "Per-file inventory for %s — classes=%s  methods=%d  constructors=%s",
                file_name,
                per_file_inv.get("classes", []),
                len(per_file_inv.get("methods", [])),
                per_file_inv.get("constructors", []),
            )

            full_source = "\n\n".join(
                c.get("content", "") for c in file_chunks if c.get("content", "").strip()
            )

            # ── Adaptive Strategy Selection (Full-File vs Chunking) ────────
            caps = gemini.get_capabilities() if gemini_available and hasattr(gemini, "get_capabilities") else None
            context_window = getattr(caps, "context_window", 8192) if caps else 8192
            if not isinstance(context_window, int):
                context_window = 8192
            req_tokens = self._estimate_prompt_tokens(
                full_source, context_block, project_type, system_prompt,
                source_file_names, per_file_inv, analysis
            )

            if req_tokens <= context_window or len(file_chunks) == 1:
                # FULL-FILE TRANSLATION (Default) — 1 prompt pass → 1 Java file
                self._logger.info(
                    "Adaptive Migration — Translating entire file %s in ONE prompt pass (~%d tokens vs max %d context)",
                    file_name, req_tokens, context_window
                )
                java_code, model_name, tokens_used = await self._translate_chunk(
                    gemini=gemini,
                    gemini_available=gemini_available,
                    source_chunk=full_source,
                    context_block=context_block,
                    file_name=file_name,
                    project_type=project_type,
                    system_prompt=system_prompt,
                    source_file_names=source_file_names,
                    per_file_inventory=per_file_inv,
                    analysis=analysis,
                )
                migration_results.append({
                    "source_chunk_id": f"{file_name}_full",
                    "java_code":       java_code,
                    "model":           model_name,
                    "tokens_used":     tokens_used,
                    "source_file":     file_name,
                })
                merged = java_code
            else:
                # INTELLIGENT CHUNKING FALLBACK — for massive files exceeding context
                self._logger.info(
                    "Adaptive Migration — File %s exceeds context (~%d > %d tokens), using chunking fallback",
                    file_name, req_tokens, context_window
                )
                java_blocks: list[str] = []
                for chunk in file_chunks:
                    chunk_id = chunk.get("chunk_id", "")
                    content = chunk.get("content", "")
                    if not content.strip():
                        continue

                    java_code, model_name, tokens_used = await self._translate_chunk(
                        gemini=gemini,
                        gemini_available=gemini_available,
                        source_chunk=content,
                        context_block=context_block,
                        file_name=file_name,
                        project_type=project_type,
                        system_prompt=system_prompt,
                        source_file_names=source_file_names,
                        per_file_inventory=per_file_inv,
                        analysis=analysis,
                    )

                    migration_results.append({
                        "source_chunk_id": chunk_id,
                        "java_code":       java_code,
                        "model":           model_name,
                        "tokens_used":     tokens_used,
                        "source_file":     file_name,
                    })
                    java_blocks.append(java_code)

                merged = "\n\n".join(java_blocks)

            if not merged.strip():
                continue

            # ── Change 3: per-file structural completeness check ───────────
            # Done on the MERGED output so the full class picture is visible.
            if gemini_available and per_file_inv.get("classes"):
                merged = await self._verify_and_complete(
                    java_code=merged,
                    per_file_inventory=per_file_inv,
                    source_chunk=full_source,
                    file_name=file_name,
                    gemini=gemini,
                    project_type=project_type,
                    system_prompt=system_prompt,
                    context_block=context_block,
                    analysis=analysis,
                )

            # ── Change 6: semantic verification before compilation ─────────
            if gemini_available:
                merged = await self._semantic_verify(
                    source_chunk=full_source,
                    java_code=merged,
                    file_name=file_name,
                    gemini=gemini,
                    project_type=project_type,
                )

            java_filename = file_name.replace(".cs", ".java")
            generated_files.append({
                "filename":        java_filename,
                "path":            java_filename,
                "source_file":     file_name,
                "compile_success": False,
                "content_preview": merged[:300],
                "full_content":    merged,
            })

        # Fallback: if still empty, produce one stub
        if not generated_files:
            generated_files.append({
                "filename":        "Migration.java",
                "path":            "Migration.java",
                "source_file":     "",
                "compile_success": False,
                "content_preview": "// No C# source files to migrate.",
                "full_content":    "// No C# source files to migrate.",
            })

        return AgentResult(
            status=AgentStatus.SUCCESS,
            agent_name=self.name,
            data={
                "migration_results":   migration_results,
                "generated_files":     generated_files,
                "gemini_available":    gemini_available,
                "active_provider_key": active_provider_key,
                "active_model":        active_model,
                "project_type":        project_type,
            },
        )

    async def _translate_chunk(
        self,
        gemini: Any,
        gemini_available: bool,
        source_chunk: str,
        context_block: str,
        file_name: str,
        project_type: str = "console",
        system_prompt: str = "",
        source_file_names: list[str] | None = None,
        per_file_inventory: dict | None = None,  # Change 4
        analysis: dict | None = None,             # Change 4
    ) -> tuple[str, str, int]:
        """
        Call the active LLM provider to translate one chunk.
        Returns (java_code, model, tokens).

        Falls back to an annotated stub when no provider is available.
        Verification (structural + semantic) is performed in run() on the
        merged per-file output, not here.
        """
        if not gemini_available:
            stub = self._make_stub(source_chunk, file_name, project_type)
            return stub, "stub", 0

        # Changes 2, 4: per_file_inventory and analysis injected into prompt
        prompt = self._build_prompt(
            source_chunk, context_block, project_type,
            system_prompt or self._get_system_prompt(project_type),
            source_file_names or [],
            per_file_inventory=per_file_inventory,
            analysis=analysis,
        )
        provider_key = gemini.active_provider_key
        model_name   = gemini.active_model

        try:
            java_code = await gemini.generate_text(prompt)
            java_code = _clean_java_output(java_code)
            tokens = len(prompt.split()) + len(java_code.split())
            self._logger.debug(
                "[%s/%s] translated chunk from %s — ~%d tokens",
                provider_key, model_name, file_name, tokens
            )
            return java_code, model_name, tokens

        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning(
                "[%s/%s] translation failed for chunk in %s: %s — using stub fallback",
                provider_key, model_name, file_name, exc,
            )
            stub = self._make_stub(source_chunk, file_name, project_type)
            return stub, "stub-fallback", 0

    def _estimate_prompt_tokens(
        self,
        source_chunk: str,
        context_block: str,
        project_type: str = "console",
        system_prompt: str = "",
        source_file_names: list[str] | None = None,
        per_file_inventory: dict | None = None,
        analysis: dict | None = None,
    ) -> int:
        """
        Estimate total input + output tokens required to translate source_chunk.
        Used by the Adaptive Strategy Selection engine to determine if full-file
        translation can fit comfortably within the model's context_window.
        """
        prompt = self._build_prompt(
            source_chunk=source_chunk,
            context_block=context_block,
            project_type=project_type,
            system_prompt=system_prompt or self._get_system_prompt(project_type),
            source_file_names=source_file_names or [],
            per_file_inventory=per_file_inventory,
            analysis=analysis,
        )
        input_tokens = int(len(prompt) / 3.8)
        output_buffer = max(1024, int(len(source_chunk) / 3.2))
        return input_tokens + output_buffer

    @staticmethod
    def _validate_final_output(
        java_code: str,
        per_file_inventory: dict | None = None,
        file_name: str = "",
    ) -> dict[str, Any]:
        """
        Lightweight Final Validation Gate (non-modifying quality checkpoint).
        Verifies non-empty output, package declaration, expected classes/methods,
        and absence of placeholder comments or TODO blocks.
        """
        issues: list[str] = []
        if not java_code or not java_code.strip():
            issues.append("Generated Java output is empty.")
            return {"file_name": file_name, "valid": False, "issues": issues}

        if not _re.search(r"^\s*package\s+[\w.]+\s*;", java_code, _re.MULTILINE):
            issues.append("Missing package declaration.")

        if _re.search(r"//\s*(?:TODO|Other methods|Remaining|Implement later|\.\.\.rest|more methods)", java_code, _re.IGNORECASE):
            issues.append("Placeholder comment or TODO block detected.")

        if per_file_inventory:
            expected_classes = per_file_inventory.get("classes", [])
            java_classes = set(_re.findall(r"\b(?:class|interface|enum)\s+(\w+)", java_code))
            for cls in expected_classes:
                if cls not in java_classes:
                    issues.append(f"Expected class '{cls}' is missing from output.")

        return {
            "file_name": file_name,
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def _build_prompt(
        self,
        source_chunk: str,
        context_block: str,
        project_type: str = "console",
        system_prompt: str = "",
        source_file_names: list[str] | None = None,
        per_file_inventory: dict | None = None,  # Change 2
        analysis: dict | None = None,             # Change 2
    ) -> str:
        """
        Compose the full prompt sent to the LLM.

        Change 2: Injects a REQUIRED STRUCTURE checklist from per_file_inventory
        so the LLM knows exactly which classes, methods, constructors, properties,
        enums, LINQ operators and collections to produce.
        """
        parts = [system_prompt or self._get_system_prompt(project_type)]

        if source_file_names:
            parts.append(
                f"Project type: {project_type}\n"
                f"Source files in project: {', '.join(source_file_names)}\n"
            )

        # ── Change 2: inject per-file structural inventory as checklist ────
        if per_file_inventory:
            inv = per_file_inventory
            checklist: list[str] = [
                "REQUIRED STRUCTURE — ALL items listed below MUST appear in your Java output.",
                "Every class, constructor, method, property, enum and interface must be present and fully implemented.\n",
            ]
            if inv.get("namespace"):
                checklist.append(f"  Namespace → Java package: '{inv['namespace']}'")
            if inv.get("classes"):
                checklist.append(f"  Classes       : {', '.join(inv['classes'])}")
            if inv.get("interfaces"):
                checklist.append(f"  Interfaces    : {', '.join(inv['interfaces'])}")
            if inv.get("enums"):
                checklist.append(f"  Enums         : {', '.join(inv['enums'])}")
            if inv.get("base_classes"):
                checklist.append(f"  Base classes  : {', '.join(inv['base_classes'])}")
            if inv.get("constructors"):
                checklist.append(f"  Constructors  : {', '.join(inv['constructors'])}")
            if inv.get("methods"):
                checklist.append(f"  Methods       : {', '.join(inv['methods'])}")
            if inv.get("properties"):
                checklist.append(
                    f"  Properties (→ Java getters/setters): {', '.join(inv['properties'])}"
                )
            if inv.get("static_members"):
                checklist.append(f"  Static members: {', '.join(inv['static_members'])}")
            if inv.get("collection_types"):
                checklist.append(
                    f"  Collections used: {', '.join(inv['collection_types'])}"
                )
            if inv.get("linq_operators"):
                checklist.append(
                    f"  LINQ operators (→ Java streams): {', '.join(inv['linq_operators'])}"
                )
            if inv.get("imports"):
                checklist.append(
                    f"  Using statements: {', '.join(inv['imports'][:12])}"
                )
            checklist.append(
                "\n  Do NOT produce output that is missing any of the above.\n"
                "  Do NOT write placeholder comments instead of real implementations."
            )
            parts.append("\n".join(checklist))

        elif analysis:
            # Fall back to project-level context when no per-file inventory exists
            fb: list[str] = ["PROJECT CONTEXT (for reference):"]
            if analysis.get("classes"):
                fb.append(f"  Classes in project : {', '.join(analysis['classes'])}")
            if analysis.get("methods"):
                fb.append(f"  Methods in project : {', '.join(analysis['methods'][:20])}")
            if analysis.get("interfaces"):
                fb.append(f"  Interfaces         : {', '.join(analysis['interfaces'])}")
            if analysis.get("namespace"):
                fb.append(f"  Primary namespace  : {analysis['namespace']}")
            parts.append("\n".join(fb))

        if context_block:
            parts.append(
                "Reference Java patterns from similar migrations:\n"
                f"{context_block}\n"
            )

        parts.append(
            "C# source code to convert:\n"
            f"{source_chunk}\n\n"
            "Output ONLY the complete equivalent Java code "
            "(no markdown fences, no explanations, no placeholders — every method fully implemented):"
        )
        return "\n\n".join(parts)

    # ── Change 5: per-file structural inventory extraction ─────────────────

    @staticmethod
    def _extract_per_file_inventory(chunks_for_file: list[dict]) -> dict:
        """
        Extract a comprehensive structural inventory for a single .cs source file.

        Applies the same regex patterns used by AnalyzerService (without importing
        or modifying it) plus additional patterns for constructors, properties,
        enums, LINQ operators, collection types, and static members.

        Returns a dict with keys:
            classes, interfaces, enums, base_classes, namespace, imports,
            constructors, properties, methods, static_members,
            linq_operators, collection_types
        """
        source = "\n".join(c.get("content", "") for c in chunks_for_file)

        # ── Class names ────────────────────────────────────────────────────
        classes = _re.findall(
            r"^\s*(?:public|internal|private|protected)?\s*"
            r"(?:static\s+|abstract\s+|sealed\s+|partial\s+)*"
            r"class\s+(\w+)",
            source, _re.MULTILINE,
        )

        # ── Interfaces ─────────────────────────────────────────────────────
        interfaces = _re.findall(
            r"^\s*(?:public|internal|private|protected)?\s*interface\s+(\w+)",
            source, _re.MULTILINE,
        )

        # ── Enums ──────────────────────────────────────────────────────────
        enums = _re.findall(
            r"^\s*(?:public|internal|private|protected)?\s*enum\s+(\w+)",
            source, _re.MULTILINE,
        )

        # ── Base classes from : declarations ───────────────────────────────
        base_classes: list[str] = []
        for m in _re.finditer(
            r"class\s+\w+(?:\s*<[^>]*>)?\s*:\s*([\w,\s<>.]+?)(?:\s*\{|\s*where|\n)",
            source, _re.MULTILINE,
        ):
            for token in _re.split(r"[,<>]", m.group(1)):
                token = token.strip()
                if token and _re.match(r"^\w+$", token):
                    base_classes.append(token)

        # ── Namespace ──────────────────────────────────────────────────────
        ns_m = _re.search(r"^\s*namespace\s+([\w.]+)", source, _re.MULTILINE)
        namespace = ns_m.group(1) if ns_m else ""

        # ── Using statements ───────────────────────────────────────────────
        imports = _re.findall(
            r"^\s*using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;",
            source, _re.MULTILINE,
        )

        # ── Constructors: public/private/protected ClassName(…) ────────────
        constructors: list[str] = []
        for cls in classes:
            ctor_hits = _re.findall(
                rf"^\s*(?:public|private|protected|internal)\s+{_re.escape(cls)}\s*\(",
                source, _re.MULTILINE,
            )
            if ctor_hits:
                constructors.append(f"{cls}(...)")
        constructors = list(dict.fromkeys(constructors))

        # ── Properties: public Type Name { get; … } ────────────────────────
        properties = _re.findall(
            r"^\s*(?:public|protected|internal)\s+"
            r"(?:virtual\s+|abstract\s+|override\s+|static\s+)?"
            r"[\w<>\[\]?]+\s+(\w+)\s*\{\s*get",
            source, _re.MULTILINE,
        )

        # ── Methods (filter out class names = constructors) ────────────────
        methods = _re.findall(
            r"^\s*(?:public|private|protected|internal|static|async|virtual|"
            r"override|abstract|sealed|new)"
            r"(?:\s+(?:public|private|protected|internal|static|async|virtual|"
            r"override|abstract|sealed|new))*"
            r"\s+[\w<>\[\]?]+\s+(\w+)\s*\(",
            source, _re.MULTILINE,
        )
        class_set = set(classes)
        methods = [m for m in methods if m not in class_set]

        # ── Static members ─────────────────────────────────────────────────
        static_members = _re.findall(
            r"^\s*(?:public|private|protected|internal)\s+static\s+[\w<>\[\]?]+\s+(\w+)",
            source, _re.MULTILINE,
        )

        # ── LINQ operators ─────────────────────────────────────────────────
        _LINQ_OPS = [
            "Where", "Select", "FirstOrDefault", "First", "LastOrDefault", "Last",
            "Any", "All", "Count", "Sum", "Average", "Min", "Max",
            "OrderBy", "OrderByDescending", "ThenBy", "GroupBy",
            "Join", "SelectMany", "Distinct", "Skip", "Take",
            "ToList", "ToArray", "ToDictionary", "ToHashSet", "Aggregate",
        ]
        linq_operators = [op for op in _LINQ_OPS if f".{op}(" in source]

        # ── Collection types ───────────────────────────────────────────────
        _COLL_MARKERS = [
            ("List<",            "List"),
            ("Dictionary<",      "Dictionary"),
            ("HashSet<",         "HashSet"),
            ("IEnumerable<",     "IEnumerable"),
            ("IList<",           "IList"),
            ("ICollection<",     "ICollection"),
            ("IReadOnlyList<",   "IReadOnlyList"),
            ("Queue<",           "Queue"),
            ("Stack<",           "Stack"),
            ("SortedDictionary<","SortedDictionary"),
        ]
        collection_types = [name for marker, name in _COLL_MARKERS if marker in source]

        def _dedup(lst: list[str]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for x in lst:
                x = x.strip()
                if x and x not in seen:
                    seen.add(x)
                    result.append(x)
            return result

        return {
            "classes":          _dedup(classes),
            "interfaces":       _dedup(interfaces),
            "enums":            _dedup(enums),
            "base_classes":     _dedup(base_classes),
            "namespace":        namespace,
            "imports":          _dedup(imports),
            "constructors":     _dedup(constructors),
            "properties":       _dedup(properties),
            "methods":          _dedup(methods),
            "static_members":   _dedup(static_members),
            "linq_operators":   _dedup(linq_operators),
            "collection_types": _dedup(collection_types),
        }

    # ── Change 3: per-file structural completeness check ──────────────────

    async def _verify_and_complete(
        self,
        java_code: str,
        per_file_inventory: dict,
        source_chunk: str,
        file_name: str,
        gemini: Any,
        project_type: str,
        system_prompt: str,
        context_block: str,
        analysis: dict,
    ) -> str:
        """
        Per-file structural completeness check.

        Scans the generated Java for class and method names, compares against the
        per-file inventory, and issues one targeted regeneration prompt if anything
        is missing. Operates on the MERGED per-file output.

        Returns the (possibly regenerated) Java code.
        """
        # Extract names from generated Java
        java_classes = set(_re.findall(
            r"\b(?:class|interface|enum)\s+(\w+)", java_code
        ))
        java_methods = set(_re.findall(
            r"(?:public|private|protected|static)\s+[\w<>\[\]]+\s+(\w+)\s*\(",
            java_code,
        ))

        expected_types = (
            set(per_file_inventory.get("classes", []))
            | set(per_file_inventory.get("interfaces", []))
            | set(per_file_inventory.get("enums", []))
        )
        expected_methods = set(per_file_inventory.get("methods", []))

        missing_types   = expected_types   - java_classes
        missing_methods = expected_methods - java_methods

        if not missing_types and not missing_methods:
            self._logger.debug(
                "Structural check PASSED for %s — all expected members present", file_name
            )
            return java_code

        # Build concise missing-member description
        missing_parts: list[str] = []
        if missing_types:
            missing_parts.append(
                f"Missing classes/interfaces/enums: {', '.join(sorted(missing_types))}"
            )
        if missing_methods:
            m_sample = sorted(missing_methods)[:15]
            suffix = f" (and {len(missing_methods) - 15} more)" if len(missing_methods) > 15 else ""
            missing_parts.append(
                f"Missing methods: {', '.join(m_sample)}{suffix}"
            )

        missing_desc = "\n".join(missing_parts)
        self._logger.warning(
            "Structural check FAILED for %s — triggering targeted regeneration:\n%s",
            file_name, missing_desc,
        )

        fix_prompt = (
            f"{system_prompt}\n\n"
            f"STRUCTURAL COMPLETENESS FIX REQUIRED for '{file_name}':\n"
            f"Your previous Java output was INCOMPLETE. The following members from the\n"
            f"C# source file were MISSING:\n{missing_desc}\n\n"
            f"You MUST include ALL of them in the corrected output. Do NOT use placeholder\n"
            f"comments. Every method body must be fully implemented.\n\n"
            f"Return the COMPLETE corrected Java file — not just the missing parts.\n\n"
            f"=== Original C# source ===\n{source_chunk}\n\n"
            f"=== Your previous (incomplete) Java output ===\n{java_code}\n\n"
            f"Output ONLY the corrected complete Java code (no markdown, no explanations):"
        )

        try:
            regenerated = await gemini.generate_text(fix_prompt)
            regenerated = _clean_java_output(regenerated)
            self._logger.info(
                "Structural fix applied for %s — regeneration complete", file_name
            )
            return regenerated
        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning(
                "Structural fix regeneration failed for %s: %s — keeping original",
                file_name, exc,
            )
            return java_code

    # ── Change 6: semantic verification before compilation ────────────────

    async def _semantic_verify(
        self,
        source_chunk: str,
        java_code: str,
        file_name: str,
        gemini: Any,
        project_type: str,
    ) -> str:
        """
        Semantic verification: compare C# source vs generated Java for behaviour correctness.

        Issues one review call per file. If semantic issues are found, issues one
        targeted fix call. Does NOT loop. Does NOT replace the compile→repair stage.

        Returns the (possibly corrected) Java code.
        """
        review_prompt = (
            "You are a .NET-to-Java migration reviewer performing a SEMANTIC CORRECTNESS CHECK.\n\n"
            "Compare the C# source and its Java translation below. Verify ALL of the following:\n"
            "  ✓ Business logic preserved (no altered formulas, constants, or algorithms)\n"
            "  ✓ Control flow preserved (loops, break/continue, if/else/switch — identical)\n"
            "  ✓ Method behaviour preserved (same inputs produce same outputs)\n"
            "  ✓ Constructor behaviour preserved (fields initialised correctly)\n"
            "  ✓ Collection mapping correct (List→ArrayList, Dictionary→HashMap, etc.)\n"
            "  ✓ LINQ mapping correct (.Where()→filter(), .Select()→map(), etc.)\n"
            "  ✓ Exception handling preserved (same exceptions thrown in same conditions)\n"
            "  ✓ No hallucinated code (no implementations absent from C# source)\n"
            "  ✓ No omitted statements (every statement in C# has an equivalent in Java)\n\n"
            f"=== C# SOURCE ({file_name}) ===\n{source_chunk}\n\n"
            f"=== GENERATED JAVA ===\n{java_code}\n\n"
            "RESPONSE FORMAT:\n"
            "  • If semantically correct: respond with exactly the word  OK\n"
            "  • If issues exist: list ONLY the specific problems, one per line.\n"
            "    Be concise. Do NOT rewrite the code — only describe what is wrong."
        )

        try:
            review = await gemini.generate_text(review_prompt)
            review = review.strip()

            # Accept "OK", "ok", "OK.", "Translation is OK.", etc.
            if _re.match(r"^ok[.\s]*$", review, _re.IGNORECASE) or review.upper().startswith("OK"):
                self._logger.debug("Semantic review PASSED for %s", file_name)
                return java_code

            # Semantic issues found — one targeted fix
            self._logger.warning(
                "Semantic issues found in %s — triggering fix:\n%s",
                file_name, review[:600],
            )

            fix_prompt = (
                "You are a .NET-to-Java migration engineer correcting SEMANTIC ERRORS.\n\n"
                f"The Java translation of '{file_name}' has the following semantic issues:\n"
                f"{review}\n\n"
                "Fix ONLY these specific issues. Do NOT change anything else.\n"
                "Do NOT add placeholder comments. Every method body must be fully implemented.\n"
                "Return the COMPLETE corrected Java file.\n\n"
                f"=== C# SOURCE (reference) ===\n{source_chunk}\n\n"
                f"=== JAVA TO FIX ===\n{java_code}\n\n"
                "Output ONLY the corrected complete Java code (no markdown, no explanations):"
            )

            fixed = await gemini.generate_text(fix_prompt)
            fixed = _clean_java_output(fixed)
            self._logger.info("Semantic fix applied for %s", file_name)
            return fixed

        except Exception as exc:  # pylint: disable=broad-except
            self._logger.warning(
                "Semantic verification failed for %s: %s — keeping original",
                file_name, exc,
            )
            return java_code

    @staticmethod
    def _make_stub(source_chunk: str, file_name: str, project_type: str = "console") -> str:
        """Generate an annotated Java stub when the LLM is unavailable."""
        import re

        m = re.search(r"\bclass\s+(\w+)", source_chunk)
        class_name = m.group(1) if m else file_name.replace(".cs", "").replace(".java", "")

        if project_type in ("webapi", "mvc"):
            header = (
                "import org.springframework.stereotype.Service;\n\n"
                "@Service\n"
            )
        else:
            header = ""

        return (
            "// AUTO-GENERATED STUB — LLM unavailable\n"
            "// Original C# source preserved in comments below.\n"
            + header
            + f"public class {class_name} {{\n\n"
            "    // TODO: implement migration\n\n"
            "    /*\n"
            + "\n".join(f"     * {line}" for line in source_chunk.splitlines())
            + "\n     */\n"
            "}\n"
        )



# ── Module helpers ────────────────────────────────────────────────────────


def _clean_java_output(text: str) -> str:
    """
    Strip markdown fences and leading/trailing whitespace from LLM output.

    LLMs sometimes wrap code in ```java ... ``` blocks even when instructed
    not to. This function removes such wrappers defensively.
    """
    import re

    # Remove ```java ... ``` or ``` ... ``` fences
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


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
