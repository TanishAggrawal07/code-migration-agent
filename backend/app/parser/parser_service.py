"""
Parser service — reads uploaded C# files and produces code chunks.

Responsibilities:
- Load .cs source files from disk via FileSystemService
- Try Tree-sitter for AST-based chunking; fall back to regex on any error
- Split each file into semantically meaningful CodeChunk objects
- Return enriched ParsedFile metadata alongside the chunks

Chunk schema:
    {
        "chunk_id":   str,          # UUID4
        "file_name":  str,          # e.g. "UserService.cs"
        "chunk_type": "class" | "method",
        "content":    str,          # raw source text
        "start_line": int,
        "end_line":   int,
    }

Usage:
    from app.parser.parser_service import ParserService
    svc = ParserService.get_instance()
    result = await svc.parse_migration(migration_id)
    # result.parsed_files  → list[ParsedFile]
    # result.chunks        → list[dict]
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

# Only parse C# source; skip project/solution/config files for chunking
_CS_EXTENSION = ".cs"

# Maximum lines a method can span before it gets its own chunk instead of
# being folded into the parent class chunk.
_METHOD_CHUNK_THRESHOLD = 30


# ── Data classes ──────────────────────────────────────────────────────────


@dataclass
class CodeChunk:
    """A single semantically meaningful chunk of C# source code."""

    chunk_id: str
    file_name: str
    chunk_type: str          # "class" | "method" | "file"
    content: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict matching the required chunk schema."""
        return {
            "chunk_id": self.chunk_id,
            "file_name": self.file_name,
            "chunk_type": self.chunk_type,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


@dataclass
class ParseResult:
    """Container for the output of parsing one migration's uploaded files."""

    migration_id: str
    parsed_files: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    parser_mode: str = "regex"   # "tree_sitter" | "regex"
    total_files: int = 0
    total_chunks: int = 0
    errors: list[str] = field(default_factory=list)


# ── Service ───────────────────────────────────────────────────────────────


class ParserService:
    """
    Singleton service that parses uploaded C# files and produces code chunks.

    Tree-sitter is tried first; if the grammar is unavailable or parsing
    fails the service falls back silently to regex-based extraction so
    the pipeline always progresses.
    """

    _instance: Optional["ParserService"] = None

    def __new__(cls) -> "ParserService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ts_available = False
            cls._instance._ts_checked = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ParserService":
        """Return the process-wide ParserService singleton."""
        return cls()

    # ── Tree-sitter probe ─────────────────────────────────────────────

    def _check_tree_sitter(self) -> bool:
        """Return True if a usable C# Tree-sitter grammar is available."""
        if self._ts_checked:
            return self._ts_available

        self._ts_checked = True
        try:
            from app.parser.tree_sitter_service import TreeSitterService
            svc = TreeSitterService.get_instance()
            self._ts_available = svc.is_initialized and not svc.using_stub
        except Exception:  # pylint: disable=broad-except
            self._ts_available = False

        return self._ts_available

    # ── Public API ────────────────────────────────────────────────────

    async def parse_migration(
        self,
        migration_id: str,
        uploaded_files: list[str],
        project_root: str,
    ) -> ParseResult:
        """
        Parse all C# files for a migration and return chunks + metadata.

        Args:
            migration_id:    Migration UUID (used for logging).
            uploaded_files:  List of relative filenames in the upload dir.
            project_root:    Absolute path to ``storage/uploads/{id}/``.

        Returns:
            :class:`ParseResult` with ``parsed_files`` and ``chunks``.
        """
        result = ParseResult(migration_id=migration_id)

        if not project_root or not uploaded_files:
            logger.warning(
                "ParserService — no files to parse for migration_id=%s", migration_id
            )
            return result

        root_path = Path(project_root)
        use_ts = self._check_tree_sitter()

        if use_ts:
            logger.info("Using Tree-sitter parser for migration_id=%s", migration_id)
            result.parser_mode = "tree_sitter"
        else:
            logger.info("Using Regex fallback parser for migration_id=%s", migration_id)
            result.parser_mode = "regex"

        for relative_path in uploaded_files:
            file_path = root_path / relative_path
            if not file_path.exists():
                logger.warning("File not found on disk, skipping: %s", file_path)
                result.errors.append(f"File not found: {relative_path}")
                continue

            # Only chunk .cs files; record other files as parsed=False entries
            if file_path.suffix.lower() != _CS_EXTENSION:
                result.parsed_files.append({
                    "filename": file_path.name,
                    "path": relative_path,
                    "classes": [],
                    "methods": [],
                    "lines": 0,
                    "parsed": False,
                })
                continue

            try:
                loop = asyncio.get_event_loop()
                source = await loop.run_in_executor(
                    None, lambda p=file_path: p.read_text(encoding="utf-8", errors="replace")
                )
                file_chunks, parsed_meta = await self._parse_file(
                    source=source,
                    file_name=file_path.name,
                    relative_path=relative_path,
                    use_ts=use_ts,
                )
                result.parsed_files.append(parsed_meta)
                result.chunks.extend([c.to_dict() for c in file_chunks])

            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "Error parsing file %s: %s", relative_path, exc, exc_info=True
                )
                result.errors.append(f"Parse error in '{relative_path}': {exc}")
                # Add a minimal stub entry so the file is still tracked
                result.parsed_files.append({
                    "filename": file_path.name,
                    "path": relative_path,
                    "classes": [],
                    "methods": [],
                    "lines": 0,
                    "parsed": False,
                })

        result.total_files = len(result.parsed_files)
        result.total_chunks = len(result.chunks)
        return result

    # ── File-level parsing ────────────────────────────────────────────

    async def _parse_file(
        self,
        source: str,
        file_name: str,
        relative_path: str,
        use_ts: bool,
    ) -> tuple[list[CodeChunk], dict[str, Any]]:
        """
        Parse one C# file; return (chunks, ParsedFile-compatible dict).
        """
        chunks: list[CodeChunk] = []
        classes: list[str] = []
        methods: list[str] = []
        lines = source.count("\n") + 1

        if use_ts:
            chunks, classes, methods = await self._ts_chunk(source, file_name)
        
        # If tree-sitter produced nothing (or wasn't used), fall back
        if not chunks:
            chunks, classes, methods = self._regex_chunk(source, file_name)

        parsed_meta: dict[str, Any] = {
            "filename": file_name,
            "path": relative_path,
            "classes": classes,
            "methods": methods,
            "lines": lines,
            "parsed": True,
        }
        return chunks, parsed_meta

    # ── Tree-sitter chunking ──────────────────────────────────────────

    async def _ts_chunk(
        self, source: str, file_name: str
    ) -> tuple[list[CodeChunk], list[str], list[str]]:
        """
        Use TreeSitterService to extract classes and methods, then build chunks.
        Falls back gracefully if the service raises.
        """
        try:
            from app.parser.tree_sitter_service import TreeSitterService
            svc = TreeSitterService.get_instance()

            loop = asyncio.get_event_loop()
            class_infos = await svc.extract_classes(source)
            method_infos = await svc.extract_methods(source)

            chunks: list[CodeChunk] = []
            class_names: list[str] = []
            method_names: list[str] = []
            lines = source.splitlines()

            # One chunk per class
            for cls in class_infos:
                class_names.append(cls.name)
                raw = cls.raw_text or "\n".join(
                    lines[cls.start_line - 1: cls.end_line]
                )
                chunks.append(CodeChunk(
                    chunk_id=str(uuid.uuid4()),
                    file_name=file_name,
                    chunk_type="class",
                    content=raw,
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                ))

            # Additional per-method chunks for large methods
            for mth in method_infos:
                method_names.append(mth.name)
                span = mth.end_line - mth.start_line
                if span >= _METHOD_CHUNK_THRESHOLD:
                    raw = mth.raw_text or "\n".join(
                        lines[mth.start_line - 1: mth.end_line]
                    )
                    chunks.append(CodeChunk(
                        chunk_id=str(uuid.uuid4()),
                        file_name=file_name,
                        chunk_type="method",
                        content=raw,
                        start_line=mth.start_line,
                        end_line=mth.end_line,
                    ))

            # If tree-sitter found classes/methods but produced no chunks
            # (e.g. all methods were tiny), add a file-level chunk
            if not chunks and (class_names or method_names):
                chunks = self._file_chunk(source, file_name)

            return chunks, class_names, method_names

        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Tree-sitter chunking failed for %s (%s) — using regex", file_name, exc
            )
            return [], [], []

    # ── Regex chunking ────────────────────────────────────────────────

    def _regex_chunk(
        self, source: str, file_name: str
    ) -> tuple[list[CodeChunk], list[str], list[str]]:
        """
        Pure-regex fallback chunker.

        Finds class boundaries, then carves out per-method chunks for
        methods that exceed the threshold; otherwise keeps the whole
        class body as a single chunk.
        """
        chunks: list[CodeChunk] = []
        class_names: list[str] = []
        method_names: list[str] = []
        src_lines = source.splitlines()

        # ── Class detection ───────────────────────────────────────────
        class_pattern = re.compile(
            r"^\s*(?:public|internal|private|protected)?\s*"
            r"(?:static\s+|abstract\s+|sealed\s+|partial\s+)*"
            r"class\s+(\w+)",
            re.MULTILINE,
        )

        class_matches = list(class_pattern.finditer(source))

        if not class_matches:
            # No classes found — treat entire file as one chunk
            return self._file_chunk(source, file_name), [], []

        # Compute class line ranges
        class_regions: list[tuple[str, int, int]] = []
        for i, m in enumerate(class_matches):
            start_line = source[: m.start()].count("\n") + 1
            if i + 1 < len(class_matches):
                end_line = source[: class_matches[i + 1].start()].count("\n")
            else:
                end_line = len(src_lines)
            class_names.append(m.group(1))
            class_regions.append((m.group(1), start_line, end_line))

        # ── Method detection inside each class ────────────────────────
        method_pattern = re.compile(
            r"^\s*(?:public|private|protected|internal|static|async|virtual|override|abstract)"
            r"(?:\s+(?:public|private|protected|internal|static|async|virtual|override|abstract))*"
            r"\s+[\w<>\[\]?]+\s+(\w+)\s*\([^)]*\)\s*(?:where\s+\w.*?)?\{",
            re.MULTILINE,
        )

        for cls_name, cls_start, cls_end in class_regions:
            # Extract the text for this class region
            cls_lines = src_lines[cls_start - 1: cls_end]
            cls_text = "\n".join(cls_lines)

            method_matches = list(method_pattern.finditer(cls_text))

            if not method_matches:
                # Whole class → one chunk
                chunks.append(CodeChunk(
                    chunk_id=str(uuid.uuid4()),
                    file_name=file_name,
                    chunk_type="class",
                    content=cls_text,
                    start_line=cls_start,
                    end_line=cls_end,
                ))
                continue

            # Class-level chunk (everything up to first method)
            first_method_offset = cls_text[: method_matches[0].start()].count("\n")
            header_end = cls_start + first_method_offset - 1
            if header_end >= cls_start:
                header_text = "\n".join(src_lines[cls_start - 1: header_end])
                if header_text.strip():
                    chunks.append(CodeChunk(
                        chunk_id=str(uuid.uuid4()),
                        file_name=file_name,
                        chunk_type="class",
                        content=header_text,
                        start_line=cls_start,
                        end_line=header_end,
                    ))

            # Per-method chunks
            for j, mm in enumerate(method_matches):
                mth_name = mm.group(1)
                method_names.append(mth_name)

                mth_start_in_cls = cls_text[: mm.start()].count("\n")
                if j + 1 < len(method_matches):
                    mth_end_in_cls = cls_text[: method_matches[j + 1].start()].count("\n") - 1
                else:
                    mth_end_in_cls = len(cls_lines) - 1

                abs_start = cls_start + mth_start_in_cls
                abs_end = cls_start + mth_end_in_cls
                mth_text = "\n".join(cls_lines[mth_start_in_cls: mth_end_in_cls + 1])

                chunks.append(CodeChunk(
                    chunk_id=str(uuid.uuid4()),
                    file_name=file_name,
                    chunk_type="method",
                    content=mth_text,
                    start_line=abs_start,
                    end_line=abs_end,
                ))

        return chunks, class_names, method_names

    # ── Helpers ───────────────────────────────────────────────────────

    def _file_chunk(self, source: str, file_name: str) -> list[CodeChunk]:
        """Return a single chunk covering the entire file."""
        lines = source.count("\n") + 1
        return [
            CodeChunk(
                chunk_id=str(uuid.uuid4()),
                file_name=file_name,
                chunk_type="file",
                content=source,
                start_line=1,
                end_line=lines,
            )
        ]
