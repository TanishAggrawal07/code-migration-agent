"""
Analyzer service — extracts structural metadata from C# code chunks.

Responsibilities:
- Accept code chunks (produced by ParserService) and raw source text
- Extract namespaces, using-statements, classes, interfaces, methods,
  inheritance hierarchies, and external dependencies
- Merge per-file analyses into one consolidated MigrationAnalysis dict

Analysis schema returned:
    {
        "classes":      list[str],
        "methods":      list[str],
        "imports":      list[str],
        "interfaces":   list[str],
        "dependencies": list[str],
        "namespace":    str,
        "file_count":   int,
        "total_lines":  int,
    }

Usage:
    from app.analyzer.analyzer_service import AnalyzerService
    svc = AnalyzerService.get_instance()
    analysis = await svc.analyze_chunks(chunks, parsed_files)
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Regex patterns ────────────────────────────────────────────────────────

# namespace MyApp.Services { ... }  or  namespace MyApp.Services;  (file-scoped)
_NS_PATTERN = re.compile(
    r"^\s*namespace\s+([\w.]+)",
    re.MULTILINE,
)

# using System;  /  using System.Collections.Generic;
# using static System.Math;  /  using Alias = Some.Type;
_USING_PATTERN = re.compile(
    r"^\s*using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;",
    re.MULTILINE,
)

# public class Foo : Bar, IBaz { ...
_CLASS_PATTERN = re.compile(
    r"^\s*(?:public|internal|private|protected)?\s*"
    r"(?:static\s+|abstract\s+|sealed\s+|partial\s+)*"
    r"class\s+(\w+)"
    r"(?:\s*<[^>]*>)?"           # optional generic params
    r"(?:\s*:\s*([\w,\s<>.]+?))?",  # optional base list
    re.MULTILINE,
)

# public interface IUserService : IBase { ...
_INTERFACE_PATTERN = re.compile(
    r"^\s*(?:public|internal|private|protected)?\s*"
    r"interface\s+(\w+)",
    re.MULTILINE,
)

# Method: public async Task<User> GetUser(int id)
_METHOD_PATTERN = re.compile(
    r"^\s*(?:public|private|protected|internal|static|async|virtual|"
    r"override|abstract|sealed|new)(?:\s+(?:public|private|protected|"
    r"internal|static|async|virtual|override|abstract|sealed|new))*"
    r"\s+[\w<>\[\]?]+\s+(\w+)\s*\(",
    re.MULTILINE,
)

# NuGet-style dependency hints from .csproj or using statements
# We treat the top-level namespace component as a "dependency" marker
_WELL_KNOWN_EXTERNAL: frozenset[str] = frozenset({
    "Microsoft",
    "System",
    "Newtonsoft",
    "AutoMapper",
    "Serilog",
    "NLog",
    "FluentValidation",
    "MediatR",
    "Polly",
    "Dapper",
    "EntityFramework",
    "AspNetCore",
    "IdentityServer",
    "StackExchange",
    "Bogus",
    "xUnit",
    "NUnit",
    "Moq",
    "FluentAssertions",
})


# ── Service ───────────────────────────────────────────────────────────────


class AnalyzerService:
    """
    Singleton service that performs structural analysis on C# code.

    All heavy work is regex-based and runs in a thread executor to avoid
    blocking the FastAPI event loop.
    """

    _instance: Optional["AnalyzerService"] = None

    def __new__(cls) -> "AnalyzerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AnalyzerService":
        """Return the process-wide AnalyzerService singleton."""
        return cls()

    # ── Public API ────────────────────────────────────────────────────

    async def analyze_chunks(
        self,
        chunks: list[dict[str, Any]],
        parsed_files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze code chunks and parsed file metadata.

        Args:
            chunks:       List of chunk dicts produced by ParserService.
            parsed_files: List of ParsedFile-compatible dicts.

        Returns:
            Consolidated analysis dict (see module docstring for schema).
        """
        loop = asyncio.get_event_loop()
        analysis = await loop.run_in_executor(
            None,
            self._run_analysis,
            chunks,
            parsed_files,
        )
        return analysis

    # ── Core analysis (runs in executor) ──────────────────────────────

    def _run_analysis(
        self,
        chunks: list[dict[str, Any]],
        parsed_files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Synchronous analysis logic (called from executor)."""

        all_classes: list[str] = []
        all_methods: list[str] = []
        all_imports: list[str] = []
        all_interfaces: list[str] = []
        all_namespaces: list[str] = []
        all_base_classes: list[str] = []
        total_lines = 0

        # Analyse every chunk's content
        for chunk in chunks:
            content: str = chunk.get("content", "")
            if not content:
                continue

            all_namespaces.extend(self._extract_namespaces(content))
            all_imports.extend(self._extract_imports(content))
            all_classes.extend(self._extract_class_names(content))
            all_interfaces.extend(self._extract_interfaces(content))
            all_methods.extend(self._extract_methods(content))
            all_base_classes.extend(self._extract_base_classes(content))

        # Supplement with metadata from parsed_files
        for pf in parsed_files:
            total_lines += pf.get("lines", 0)
            for cls_name in pf.get("classes", []):
                if cls_name not in all_classes:
                    all_classes.append(cls_name)
            for mth_name in pf.get("methods", []):
                if mth_name not in all_methods:
                    all_methods.append(mth_name)

        # Derive external dependencies from import roots
        dependencies = self._derive_dependencies(all_imports, all_base_classes)

        # De-duplicate while preserving order
        return {
            "classes": _dedup(all_classes),
            "methods": _dedup(all_methods),
            "imports": _dedup(all_imports),
            "interfaces": _dedup(all_interfaces),
            "dependencies": _dedup(dependencies),
            "namespace": _primary_namespace(all_namespaces),
            "file_count": len(parsed_files),
            "total_lines": total_lines,
        }

    # ── Extraction helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_namespaces(source: str) -> list[str]:
        return [m.group(1) for m in _NS_PATTERN.finditer(source)]

    @staticmethod
    def _extract_imports(source: str) -> list[str]:
        return [m.group(1) for m in _USING_PATTERN.finditer(source)]

    @staticmethod
    def _extract_class_names(source: str) -> list[str]:
        return [m.group(1) for m in _CLASS_PATTERN.finditer(source)]

    @staticmethod
    def _extract_interfaces(source: str) -> list[str]:
        return [m.group(1) for m in _INTERFACE_PATTERN.finditer(source)]

    @staticmethod
    def _extract_methods(source: str) -> list[str]:
        return [m.group(1) for m in _METHOD_PATTERN.finditer(source)]

    @staticmethod
    def _extract_base_classes(source: str) -> list[str]:
        """Extract base-class and interface names from class declarations."""
        bases: list[str] = []
        for m in _CLASS_PATTERN.finditer(source):
            base_list = m.group(2)
            if base_list:
                for token in re.split(r"[,<>]", base_list):
                    token = token.strip()
                    # Keep only the simple name, not generic args
                    simple = re.match(r"(\w+)", token)
                    if simple:
                        bases.append(simple.group(1))
        return bases

    @staticmethod
    def _derive_dependencies(
        imports: list[str],
        base_classes: list[str],
    ) -> list[str]:
        """
        Infer external library dependencies from import root namespaces.

        A namespace root is considered external if it matches a well-known
        library prefix (e.g. "Microsoft", "Newtonsoft", "AutoMapper").
        """
        deps: list[str] = []
        candidates = [imp.split(".")[0] for imp in imports] + base_classes

        for candidate in candidates:
            # Check against well-known external roots
            if candidate in _WELL_KNOWN_EXTERNAL:
                # Include the second component for more specificity
                # e.g. "Microsoft.EntityFrameworkCore"
                for imp in imports:
                    parts = imp.split(".")
                    if parts[0] == candidate and len(parts) >= 2:
                        dep = f"{parts[0]}.{parts[1]}"
                        if dep not in deps:
                            deps.append(dep)
                        break
                else:
                    if candidate not in deps:
                        deps.append(candidate)

        return deps


# ── Module helpers ────────────────────────────────────────────────────────


def _dedup(items: list[str]) -> list[str]:
    """Return *items* with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _primary_namespace(namespaces: list[str]) -> str:
    """
    Return the most representative namespace.

    Prefers the shortest non-empty namespace (usually the root), which
    avoids selecting deeply nested helper namespaces as the primary.
    """
    if not namespaces:
        return ""
    unique = _dedup(namespaces)
    return min(unique, key=len)
