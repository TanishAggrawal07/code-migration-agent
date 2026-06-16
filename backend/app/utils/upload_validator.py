"""
Upload validation utilities.

Validates file extensions, sizes, and content before persisting to disk.
Centralises all upload constraints so the API layer stays thin.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)

# ── Allowed file extensions ────────────────────────────────────────────────

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".cs",
    ".csproj",
    ".sln",
    ".config",
    ".xml",
    ".json",
    ".zip",
})

# Extensions that should be extracted (not stored as-is)
ZIP_EXTENSIONS: frozenset[str] = frozenset({".zip"})

# Extensions that count as .NET source files
SOURCE_EXTENSIONS: frozenset[str] = frozenset({
    ".cs", ".csproj", ".sln", ".config", ".xml", ".json",
})


def get_extension(filename: str) -> str:
    """Return the lowercase extension of *filename* including the dot."""
    return Path(filename).suffix.lower()


def is_allowed(filename: str) -> bool:
    """Return True if *filename* has a permitted extension."""
    return get_extension(filename) in ALLOWED_EXTENSIONS


def is_zip(filename: str) -> bool:
    """Return True if *filename* is a ZIP archive."""
    return get_extension(filename) in ZIP_EXTENSIONS


async def validate_upload_file(
    upload: UploadFile,
    existing_names: set[str],
) -> bytes:
    """
    Read and fully validate a single :class:`~fastapi.UploadFile`.

    Checks:
    - Non-empty filename
    - Allowed extension
    - No duplicate filename (against *existing_names*)
    - File not empty (zero bytes)
    - File not exceeding per-file size limit

    Args:
        upload:         The FastAPI UploadFile object.
        existing_names: Set of already-seen filenames in this request batch.

    Returns:
        Raw file bytes if all checks pass.

    Raises:
        :class:`~app.core.exceptions.ValidationException`: On any failure.
    """
    settings = get_settings()

    # 1. Non-empty filename
    filename = (upload.filename or "").strip()
    if not filename:
        raise ValidationException("File must have a non-empty filename.")

    # 2. Allowed extension
    if not is_allowed(filename):
        ext = get_extension(filename)
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationException(
            f"File '{filename}' has unsupported extension '{ext}'. "
            f"Allowed: {allowed}"
        )

    # 3. Duplicate check
    safe_name = Path(filename).name
    if safe_name in existing_names:
        raise ValidationException(
            f"Duplicate filename '{safe_name}'. Each file must have a unique name."
        )

    # 4. Read content
    content = await upload.read()

    # 5. Empty file
    if len(content) == 0:
        raise ValidationException(f"File '{filename}' is empty (0 bytes).")

    # 6. Per-file size limit
    limit = settings.max_file_size_bytes
    if len(content) > limit:
        size_mb = len(content) / (1024 * 1024)
        raise ValidationException(
            f"File '{filename}' is {size_mb:.1f} MB which exceeds the "
            f"{settings.max_file_size_mb} MB per-file limit."
        )

    logger.debug("Validated upload — file=%s  size=%d bytes", filename, len(content))
    return content
