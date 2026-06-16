"""
FileSystemService — async-compatible file I/O for migration projects.

Storage layout:
    storage/
    ├── uploads/{migration_id}/     ← uploaded .NET source files
    ├── generated/{migration_id}/   ← output Java files (later modules)
    └── temp/{migration_id}/        ← ephemeral working space

All paths use :mod:`pathlib`.  Methods are async-compatible: heavy I/O
runs in a thread executor so the FastAPI event loop is never blocked.

Usage:
    from app.services.filesystem_service import FileSystemService
    fs = FileSystemService.get_instance()
    project_dir = await fs.create_project_dir(migration_id)
    paths = await fs.save_files(migration_id, [(filename, content_bytes)])
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FileSystemError(Exception):
    """Raised when a filesystem operation fails."""


class FileSystemService:
    """
    Singleton async-compatible filesystem service.

    All mutating operations acquire a per-migration asyncio.Lock to
    serialise concurrent writes to the same project directory.
    """

    _instance: Optional["FileSystemService"] = None
    _locks: dict[str, asyncio.Lock]

    def __new__(cls) -> "FileSystemService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._locks = {}
        return cls._instance

    @classmethod
    def get_instance(cls) -> "FileSystemService":
        """Return the process-wide FileSystemService singleton."""
        return cls()

    # ── Internal helpers ──────────────────────────────────────────────

    def _lock_for(self, migration_id: str) -> asyncio.Lock:
        if migration_id not in self._locks:
            self._locks[migration_id] = asyncio.Lock()
        return self._locks[migration_id]

    def _uploads_root(self) -> Path:
        return get_settings().uploads_path

    def _generated_root(self) -> Path:
        return get_settings().generated_path

    def _temp_root(self) -> Path:
        return get_settings().temp_path

    # ── Directory management ──────────────────────────────────────────

    def get_project_path(self, migration_id: str) -> Path:
        """
        Return the upload directory path for *migration_id*.

        Does NOT create the directory; call :meth:`create_project_dir` for that.
        """
        return self._uploads_root() / migration_id

    def get_generated_path(self, migration_id: str) -> Path:
        """Return the generated-output directory path for *migration_id*."""
        return self._generated_root() / migration_id

    def get_temp_path(self, migration_id: str) -> Path:
        """Return the temp directory path for *migration_id*."""
        return self._temp_root() / migration_id

    async def create_project_dir(self, migration_id: str) -> Path:
        """
        Create (or confirm) the upload directory for *migration_id*.

        Also creates ``generated/`` and ``temp/`` sibling directories.

        Args:
            migration_id: UUID of the migration.

        Returns:
            The :class:`~pathlib.Path` to the upload directory.
        """
        project_dir = self.get_project_path(migration_id)

        async with self._lock_for(migration_id):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: project_dir.mkdir(parents=True, exist_ok=True))
            await loop.run_in_executor(None, lambda: self.get_generated_path(migration_id).mkdir(parents=True, exist_ok=True))
            await loop.run_in_executor(None, lambda: self.get_temp_path(migration_id).mkdir(parents=True, exist_ok=True))

        logger.info("Project dirs created — migration_id=%s  path=%s", migration_id, project_dir)
        return project_dir

    # ── File operations ───────────────────────────────────────────────

    async def save_files(
        self,
        migration_id: str,
        files: list[tuple[str, bytes]],
    ) -> list[str]:
        """
        Write a list of ``(filename, content)`` pairs to disk.

        Args:
            migration_id: Target migration UUID.
            files:        List of ``(relative_filename, raw_bytes)`` tuples.

        Returns:
            List of relative paths (relative to project root) that were saved.

        Raises:
            :class:`FileSystemError`: On I/O failure.
        """
        project_dir = self.get_project_path(migration_id)

        async with self._lock_for(migration_id):
            project_dir.mkdir(parents=True, exist_ok=True)
            saved: list[str] = []

            for filename, content in files:
                # Sanitise: flatten path separators that could escape the dir
                safe_name = Path(filename).name
                dest = project_dir / safe_name
                try:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, dest.write_bytes, content)
                    saved.append(safe_name)
                    logger.debug("Saved file — %s  size=%d bytes", dest, len(content))
                except OSError as exc:
                    logger.error("Failed to write %s: %s", dest, exc)
                    raise FileSystemError(f"Failed to write '{safe_name}': {exc}") from exc

        logger.info("Saved %d file(s) for migration_id=%s", len(saved), migration_id)
        return saved

    async def save_file_with_path(
        self,
        migration_id: str,
        relative_path: str,
        content: bytes,
    ) -> str:
        """
        Write a single file preserving its relative directory structure.

        Args:
            migration_id:   Target migration UUID.
            relative_path:  Path relative to the project root (e.g. ``src/Foo.cs``).
            content:        Raw file bytes.

        Returns:
            The relative path of the saved file.
        """
        project_dir = self.get_project_path(migration_id)
        dest = project_dir / relative_path
        dest_dir = dest.parent

        async with self._lock_for(migration_id):
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: dest_dir.mkdir(parents=True, exist_ok=True))
            await loop.run_in_executor(None, dest.write_bytes, content)

        logger.debug("Saved file with path — %s", dest)
        return relative_path

    async def list_files(
        self,
        migration_id: str,
        extensions: Optional[set[str]] = None,
    ) -> list[str]:
        """
        List all files in the project upload directory.

        Args:
            migration_id: Target migration UUID.
            extensions:   Optional set of lowercase extensions to filter by
                          (e.g. ``{".cs", ".csproj"}``).  ``None`` returns all.

        Returns:
            Sorted list of relative paths (relative to project root).
        """
        project_dir = self.get_project_path(migration_id)
        if not project_dir.exists():
            return []

        loop = asyncio.get_event_loop()

        def _scan() -> list[str]:
            results: list[str] = []
            for p in project_dir.rglob("*"):
                if p.is_file():
                    if extensions is None or p.suffix.lower() in extensions:
                        results.append(str(p.relative_to(project_dir)))
            return sorted(results)

        return await loop.run_in_executor(None, _scan)

    async def read_file(self, file_path: Path) -> bytes:
        """
        Read and return the raw bytes of *file_path*.

        Args:
            file_path: Absolute or relative :class:`~pathlib.Path`.

        Returns:
            Raw file bytes.

        Raises:
            :class:`FileSystemError`: If the file does not exist or cannot be read.
        """
        if not file_path.exists():
            raise FileSystemError(f"File not found: {file_path}")

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, file_path.read_bytes)
        except OSError as exc:
            raise FileSystemError(f"Cannot read '{file_path}': {exc}") from exc

    async def read_file_text(self, file_path: Path, encoding: str = "utf-8") -> str:
        """Read a file as decoded text, falling back to latin-1 on errors."""
        raw = await self.read_file(file_path)
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    async def delete_project(self, migration_id: str) -> bool:
        """
        Recursively delete all directories for *migration_id*.

        Args:
            migration_id: Target migration UUID.

        Returns:
            ``True`` if any directory was deleted, ``False`` if none existed.
        """
        deleted_any = False

        for base_fn in (
            self.get_project_path,
            self.get_generated_path,
            self.get_temp_path,
        ):
            target = base_fn(migration_id)
            if target.exists():
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, shutil.rmtree, target)
                logger.info("Deleted directory — %s", target)
                deleted_any = True

        if migration_id in self._locks:
            del self._locks[migration_id]

        return deleted_any

    # ── Utility ───────────────────────────────────────────────────────

    async def project_exists(self, migration_id: str) -> bool:
        """Return True if the upload directory for *migration_id* exists."""
        return self.get_project_path(migration_id).exists()

    async def get_file_size(self, file_path: Path) -> int:
        """Return the size in bytes of *file_path*, or 0 if missing."""
        try:
            loop = asyncio.get_event_loop()
            stat = await loop.run_in_executor(None, file_path.stat)
            return stat.st_size
        except OSError:
            return 0

    def ensure_storage_dirs(self) -> None:
        """Create all top-level storage directories synchronously (called at startup)."""
        settings = get_settings()
        for path in (
            settings.uploads_path,
            settings.generated_path,
            settings.temp_path,
        ):
            path.mkdir(parents=True, exist_ok=True)
        logger.info("Storage directories ensured — root=%s", settings.storage_root)
