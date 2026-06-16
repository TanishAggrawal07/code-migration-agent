"""
Safe ZIP extraction utility.

Extracts a ZIP archive into a target directory while:
- Preventing Zip Slip attacks (path traversal via ``../`` in archive names)
- Filtering extracted files to allowed extensions only
- Logging every extracted file

Usage:
    from app.utils.zip_extractor import extract_zip
    extracted = await extract_zip(zip_bytes, target_dir)
"""

from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from pathlib import Path

from app.core.exceptions import ValidationException
from app.utils.upload_validator import ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)


async def extract_zip(
    zip_bytes: bytes,
    target_dir: Path,
) -> list[str]:
    """
    Extract a ZIP archive into *target_dir* asynchronously.

    Args:
        zip_bytes:  Raw bytes of the ZIP file.
        target_dir: Destination directory (created if absent).

    Returns:
        List of relative paths (relative to *target_dir*) that were extracted.

    Raises:
        :class:`~app.core.exceptions.ValidationException`: If the archive is
            invalid or a Zip Slip attack is detected.
    """
    loop = asyncio.get_event_loop()
    extracted = await loop.run_in_executor(
        None,
        lambda: _extract_sync(zip_bytes, target_dir),
    )
    return extracted


def _extract_sync(zip_bytes: bytes, target_dir: Path) -> list[str]:
    """Synchronous extraction — runs in a thread executor."""
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Validate the archive first
            bad = zf.testzip()
            if bad is not None:
                raise ValidationException(f"ZIP archive is corrupt near '{bad}'.")

            extracted: list[str] = []

            for member in zf.infolist():
                # Skip directories
                if member.is_dir():
                    continue

                member_path = Path(member.filename)

                # ── Zip Slip guard ────────────────────────────────────
                # Resolve where extraction would land and confirm it's
                # inside target_dir.
                dest = (target_dir / member_path).resolve()
                try:
                    dest.relative_to(target_dir.resolve())
                except ValueError:
                    raise ValidationException(
                        f"Zip Slip detected: '{member.filename}' would extract "
                        "outside the target directory."
                    )

                # ── Extension filter ──────────────────────────────────
                ext = member_path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    logger.debug("Skipping unsupported file in ZIP — %s", member.filename)
                    continue

                # ── Extract ───────────────────────────────────────────
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as out:
                    out.write(src.read())

                rel = str(dest.relative_to(target_dir.resolve()))
                extracted.append(rel)
                logger.debug("Extracted — %s  size=%d bytes", rel, member.file_size)

            logger.info("ZIP extraction complete — %d file(s) extracted", len(extracted))
            return extracted

    except zipfile.BadZipFile as exc:
        raise ValidationException(f"Invalid ZIP file: {exc}") from exc
