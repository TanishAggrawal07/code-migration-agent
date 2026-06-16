"""
Tree-sitter parsing service for C# source code.

Provides AST generation, class extraction, and method extraction.
Migration logic is deliberately absent — this is infrastructure only.

Usage:
    from app.parser.tree_sitter_service import TreeSitterService
    svc = TreeSitterService.get_instance()
    await svc.initialize()
    tree = await svc.parse_code(csharp_source)
    classes = await svc.extract_classes(csharp_source)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import tree_sitter  # type: ignore[import]
    from tree_sitter import Language, Parser  # type: ignore[import]
    _TS_AVAILABLE = True
except ImportError:
    tree_sitter = None   # type: ignore[assignment]
    Language = None      # type: ignore[assignment,misc]
    Parser = None        # type: ignore[assignment,misc]
    _TS_AVAILABLE = False
    logger.warning("tree-sitter not installed — TreeSitterService will be unavailable")


# ── Data transfer objects ─────────────────────────────────────────────────

@dataclass
class ParsedNode:
    """Represents a generic AST node extracted from source code."""

    node_type: str
    text: str
    start_line: int
    end_line: int
    children: list["ParsedNode"] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information extracted from a C# class declaration."""

    name: str
    start_line: int
    end_line: int
    methods: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class MethodInfo:
    """Information extracted from a C# method declaration."""

    name: str
    return_type: str
    parameters: list[str]
    start_line: int
    end_line: int
    class_name: Optional[str] = None
    raw_text: str = ""


# ── Service ───────────────────────────────────────────────────────────────

class TreeSitterServiceError(Exception):
    """Raised when Tree-sitter operations fail."""


class TreeSitterService:
    """
    Singleton Tree-sitter service for C# source parsing.

    tree-sitter >= 0.23 ships language grammars as separate packages
    (``tree-sitter-c-sharp``).  If that grammar is unavailable the service
    falls back to a pure-Python regex-based stub so other modules are
    unaffected during development.
    """

    _instance: Optional["TreeSitterService"] = None
    _parser: Any = None     # tree_sitter.Parser
    _language: Any = None   # tree_sitter.Language
    _initialized: bool = False
    _using_stub: bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    def __new__(cls) -> "TreeSitterService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "TreeSitterService":
        """Return the application-wide TreeSitterService singleton."""
        return cls()

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """
        Load the Tree-sitter C# grammar and create the parser.

        Falls back to a regex stub if the grammar package is absent,
        so downstream services always have something to call.

        Returns:
            ``True`` on success (real or stub), ``False`` on fatal error.
        """
        if self._initialized:
            return True

        if not _TS_AVAILABLE:
            logger.warning(
                "tree-sitter not installed — using regex stub parser"
            )
            self._using_stub = True
            self._initialized = True
            return True

        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._load_grammar)
            if success:
                logger.info("TreeSitterService initialized with C# grammar")
                self._initialized = True
                return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Tree-sitter grammar load failed (%s) — using stub", exc)

        # Fall back to stub
        self._using_stub = True
        self._initialized = True
        return True

    def _load_grammar(self) -> bool:
        """
        Try to load the tree-sitter-c-sharp grammar.

        Returns ``True`` on success, raises on failure so the caller
        can catch and fall back to the stub.
        """
        try:
            # tree-sitter-c-sharp >= 0.23 style
            from tree_sitter_languages import get_language, get_parser  # type: ignore[import]
            self._language = get_language("c_sharp")
            self._parser = get_parser("c_sharp")
            return True
        except ImportError:
            pass

        try:
            # Alternative: tree-sitter-c-sharp package
            import tree_sitter_c_sharp as ts_csharp  # type: ignore[import]
            self._language = Language(ts_csharp.language())
            self._parser = Parser(self._language)
            return True
        except (ImportError, Exception):
            pass

        raise ImportError("No C# Tree-sitter grammar package found")

    # ── Parsing ───────────────────────────────────────────────────────

    async def parse_code(self, source_code: str) -> dict[str, Any]:
        """
        Parse C# source code and return a serialisable AST summary.

        Args:
            source_code: C# source code string.

        Returns:
            Dict with keys ``root_type``, ``node_count``, ``source_lines``,
            and ``using_stub``.

        Raises:
            TreeSitterServiceError: If parsing fails fatally.
        """
        if not self._initialized:
            raise TreeSitterServiceError("TreeSitterService not initialized.")

        if self._using_stub:
            return self._stub_parse(source_code)

        try:
            loop = asyncio.get_event_loop()
            tree = await loop.run_in_executor(
                None,
                lambda: self._parser.parse(source_code.encode("utf-8")),
            )
            root = tree.root_node
            return {
                "root_type": root.type,
                "node_count": self._count_nodes(root),
                "source_lines": source_code.count("\n") + 1,
                "using_stub": False,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Tree-sitter parse failed: %s", exc)
            raise TreeSitterServiceError(f"Parse failed: {exc}") from exc

    async def extract_classes(self, source_code: str) -> list[ClassInfo]:
        """
        Extract class declarations from C# source code.

        Args:
            source_code: C# source code string.

        Returns:
            List of :class:`ClassInfo` data objects.
        """
        if not self._initialized:
            raise TreeSitterServiceError("TreeSitterService not initialized.")

        if self._using_stub:
            return self._stub_extract_classes(source_code)

        try:
            loop = asyncio.get_event_loop()
            classes = await loop.run_in_executor(
                None,
                lambda: self._ts_extract_classes(source_code),
            )
            logger.debug("Extracted %d classes", len(classes))
            return classes
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Class extraction failed: %s", exc)
            return self._stub_extract_classes(source_code)

    async def extract_methods(self, source_code: str) -> list[MethodInfo]:
        """
        Extract method declarations from C# source code.

        Args:
            source_code: C# source code string.

        Returns:
            List of :class:`MethodInfo` data objects.
        """
        if not self._initialized:
            raise TreeSitterServiceError("TreeSitterService not initialized.")

        if self._using_stub:
            return self._stub_extract_methods(source_code)

        try:
            loop = asyncio.get_event_loop()
            methods = await loop.run_in_executor(
                None,
                lambda: self._ts_extract_methods(source_code),
            )
            logger.debug("Extracted %d methods", len(methods))
            return methods
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Method extraction failed: %s", exc)
            return self._stub_extract_methods(source_code)

    # ── Tree-sitter helpers ───────────────────────────────────────────

    def _count_nodes(self, node: Any) -> int:
        """Recursively count AST nodes."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _ts_extract_classes(self, source_code: str) -> list[ClassInfo]:
        """Extract classes using Tree-sitter queries."""
        lines = source_code.splitlines()
        tree = self._parser.parse(source_code.encode("utf-8"))
        classes: list[ClassInfo] = []

        def visit(node: Any) -> None:
            if node.type == "class_declaration":
                name = ""
                for child in node.children:
                    if child.type == "identifier":
                        name = child.text.decode("utf-8") if isinstance(child.text, bytes) else child.text
                        break
                classes.append(ClassInfo(
                    name=name,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    raw_text="\n".join(lines[node.start_point[0]: node.end_point[0] + 1]),
                ))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return classes

    def _ts_extract_methods(self, source_code: str) -> list[MethodInfo]:
        """Extract methods using Tree-sitter node traversal."""
        lines = source_code.splitlines()
        tree = self._parser.parse(source_code.encode("utf-8"))
        methods: list[MethodInfo] = []

        def get_text(node: Any) -> str:
            t = node.text
            return t.decode("utf-8") if isinstance(t, bytes) else (t or "")

        def visit(node: Any) -> None:
            if node.type == "method_declaration":
                name = ""
                return_type = ""
                params: list[str] = []
                for child in node.children:
                    if child.type == "identifier":
                        name = get_text(child)
                    elif child.type in {"predefined_type", "identifier", "void_keyword",
                                        "nullable_type", "generic_name", "array_type"}:
                        if not return_type:
                            return_type = get_text(child)
                    elif child.type == "parameter_list":
                        for p in child.children:
                            if p.type == "parameter":
                                params.append(get_text(p))
                methods.append(MethodInfo(
                    name=name,
                    return_type=return_type,
                    parameters=params,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    raw_text="\n".join(lines[node.start_point[0]: node.end_point[0] + 1]),
                ))
            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return methods

    # ── Regex stub (fallback) ─────────────────────────────────────────

    @staticmethod
    def _stub_parse(source_code: str) -> dict[str, Any]:
        """Minimal regex-based parse summary."""
        return {
            "root_type": "compilation_unit",
            "node_count": source_code.count("\n") + 1,
            "source_lines": source_code.count("\n") + 1,
            "using_stub": True,
        }

    @staticmethod
    def _stub_extract_classes(source_code: str) -> list[ClassInfo]:
        """Regex-based class extraction fallback."""
        import re
        classes: list[ClassInfo] = []
        pattern = re.compile(r"(?:public|private|protected|internal)?\s+(?:static\s+)?class\s+(\w+)")
        lines = source_code.splitlines()
        for i, line in enumerate(lines):
            m = pattern.search(line)
            if m:
                classes.append(ClassInfo(
                    name=m.group(1),
                    start_line=i + 1,
                    end_line=i + 1,
                    raw_text=line.strip(),
                ))
        return classes

    @staticmethod
    def _stub_extract_methods(source_code: str) -> list[MethodInfo]:
        """Regex-based method extraction fallback."""
        import re
        methods: list[MethodInfo] = []
        pattern = re.compile(
            r"(?:public|private|protected|internal|static|async|virtual|override)+"
            r"\s+([\w<>\[\]?]+)\s+(\w+)\s*\(([^)]*)\)"
        )
        lines = source_code.splitlines()
        for i, line in enumerate(lines):
            m = pattern.search(line)
            if m:
                params = [p.strip() for p in m.group(3).split(",") if p.strip()]
                methods.append(MethodInfo(
                    name=m.group(2),
                    return_type=m.group(1),
                    parameters=params,
                    start_line=i + 1,
                    end_line=i + 1,
                    raw_text=line.strip(),
                ))
        return methods

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        """Whether the service has been initialized."""
        return self._initialized

    @property
    def using_stub(self) -> bool:
        """True if the regex-stub fallback is active."""
        return self._using_stub

    @property
    def is_available(self) -> bool:
        """Whether tree-sitter is installed."""
        return _TS_AVAILABLE
