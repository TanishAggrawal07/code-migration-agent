"""
MCP Filesystem — Model Context Protocol–style filesystem capabilities.

Exposes a clean, tool-like interface that future agents will call instead of
directly importing :class:`~app.services.filesystem_service.FileSystemService`.
This layer mirrors the MCP filesystem server contract so swapping to a real
MCP server in a future module requires only replacing the import.

Tools exposed:
    read_file(path)             → str
    write_file(path, content)   → bool
    list_directory(path)        → list[str]
    create_directory(path)      → bool
    delete_directory(path)      → bool
    file_exists(path)           → bool
    get_file_info(path)         → FileInfo

Usage (by agents):
    from app.mcp.filesystem_mcp import MCPFilesystem
    mcp = MCPFilesystem(migration_id)
    files = await mcp.list_directory(".")
    content = await mcp.read_file("Program.cs")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.filesystem_service import FileSystemError, FileSystemService

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Metadata about a file returned by :meth:`MCPFilesystem.get_file_info`."""

    name: str
    path: str
    size_bytes: int
    is_directory: bool
    extension: str


class MCPFilesystem:
    """
    MCP-style filesystem tool set scoped to one migration project.

    All paths passed to methods are *relative* to the migration's upload
    directory.  Absolute paths or ``..`` traversal attempts raise
    :class:`~app.services.filesystem_service.FileSystemError`.
    """

    def __init__(self, migration_id: str) -> None:
        self._migration_id = migration_id
        self._fs = FileSystemService.get_instance()

    # ── Internal helpers ──────────────────────────────────────────────

    def _resolve(self, relative: str) -> Path:
        """
        Resolve a relative path against the project root.

        Raises :class:`FileSystemError` if the result would escape the root.
        """
        root = self._fs.get_project_path(self._migration_id).resolve()
        resolved = (root / relative).resolve()

        # Zip-slip / path-traversal guard
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise FileSystemError(
                f"Path traversal detected: '{relative}' escapes project root"
            ) from exc

        return resolved

    # ── MCP tools ─────────────────────────────────────────────────────

    async def read_file(self, path: str) -> str:
        """
        Read *path* (relative to project root) and return its text content.

        Args:
            path: Relative path within the migration project directory.

        Returns:
            Decoded text content of the file.

        Raises:
            :class:`FileSystemError`: If the file does not exist.
        """
        resolved = self._resolve(path)
        content = await self._fs.read_file_text(resolved)
        logger.debug("MCP read_file — %s  chars=%d", path, len(content))
        return content

    async def write_file(self, path: str, content: str) -> bool:
        """
        Write *content* to *path* relative to the project root.

        Creates parent directories automatically.

        Args:
            path:    Relative path within the migration project directory.
            content: Text content to write (UTF-8 encoded).

        Returns:
            ``True`` on success.
        """
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        logger.debug("MCP write_file — %s  chars=%d", path, len(content))
        return True

    async def list_directory(
        self,
        path: str = ".",
        extensions: Optional[set[str]] = None,
    ) -> list[str]:
        """
        List file paths within *path* (relative to project root).

        Args:
            path:       Relative subdirectory to list (``"."`` for root).
            extensions: Optional filter on file extensions.

        Returns:
            Sorted list of relative file paths.
        """
        resolved = self._resolve(path)
        if not resolved.exists():
            return []

        results: list[str] = []
        root = self._fs.get_project_path(self._migration_id).resolve()
        for p in sorted(resolved.rglob("*")):
            if p.is_file():
                if extensions is None or p.suffix.lower() in extensions:
                    results.append(str(p.resolve().relative_to(root)))
        return results

    async def create_directory(self, path: str) -> bool:
        """
        Create *path* (relative to project root) including all parents.

        Returns:
            ``True`` on success.
        """
        resolved = self._resolve(path)
        resolved.mkdir(parents=True, exist_ok=True)
        logger.debug("MCP create_directory — %s", path)
        return True

    async def delete_directory(self, path: str) -> bool:
        """
        Recursively delete *path* (relative to project root).

        Args:
            path: Relative path to delete.

        Returns:
            ``True`` if the directory existed and was removed, ``False`` otherwise.
        """
        import shutil
        resolved = self._resolve(path)
        if not resolved.exists():
            return False
        shutil.rmtree(resolved)
        logger.debug("MCP delete_directory — %s", path)
        return True

    async def file_exists(self, path: str) -> bool:
        """Return True if *path* exists as a file within the project."""
        try:
            resolved = self._resolve(path)
            return resolved.is_file()
        except FileSystemError:
            return False

    async def get_file_info(self, path: str) -> FileInfo:
        """
        Return metadata about the file at *path*.

        Args:
            path: Relative path within the project.

        Returns:
            :class:`FileInfo` dataclass.

        Raises:
            :class:`FileSystemError`: If the path does not exist.
        """
        resolved = self._resolve(path)
        if not resolved.exists():
            raise FileSystemError(f"Path not found: '{path}'")

        stat = resolved.stat()
        return FileInfo(
            name=resolved.name,
            path=path,
            size_bytes=stat.st_size,
            is_directory=resolved.is_dir(),
            extension=resolved.suffix.lower(),
        )
