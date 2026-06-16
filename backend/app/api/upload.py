"""
File upload endpoint.

POST /api/migrations/{migration_id}/upload
    Accept: multipart/form-data
    Fields: files (one or more UploadFile)

Validates each file, saves to storage/uploads/{migration_id}/,
extracts ZIP archives, updates MigrationState, and returns a
frontend-friendly summary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.agents.state import LogLevel
from app.core.exceptions import MigrationNotFoundException, ValidationException
from app.services.filesystem_service import FileSystemService
from app.services.migration_service import MigrationService
from app.utils.upload_validator import is_zip, validate_upload_file
from app.utils.zip_extractor import extract_zip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migrations", tags=["Upload"])


# ── Response schema ────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Response payload for the upload endpoint."""

    migration_id: str
    project_name: str
    uploaded_count: int
    uploaded_files: list[str]
    project_root: str
    message: str


class ListFilesResponse(BaseModel):
    """Response payload for the list-files endpoint."""

    migration_id: str
    file_count: int
    files: list[str]


# ── Helpers ────────────────────────────────────────────────────────────────


def _svc() -> MigrationService:
    return MigrationService.get_instance()


def _fs() -> FileSystemService:
    return FileSystemService.get_instance()


def _not_found(migration_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "MigrationNotFound", "migration_id": migration_id},
    )


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post(
    "/{migration_id}/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload .NET project files",
    description=(
        "Upload one or more .NET source files for a migration. "
        "Accepted extensions: .cs .csproj .sln .config .xml .json .zip. "
        "ZIP files are automatically extracted. "
        "Max 20 MB per file, 200 MB total."
    ),
)
async def upload_files(
    migration_id: str,
    files: Annotated[list[UploadFile], File(description="One or more .NET source files")],
) -> UploadResponse:
    """
    Accept multipart file uploads and persist them under
    ``storage/uploads/{migration_id}/``.
    """
    # 1. Fetch migration (raises 404 if not found)
    try:
        state = await _svc().get_migration(migration_id)
    except MigrationNotFoundException:
        raise _not_found(migration_id)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "NoFiles", "message": "At least one file must be provided."},
        )

    # 2. Ensure project directory exists
    fs = _fs()
    project_dir = await fs.create_project_dir(migration_id)

    # 3. Validate & save each file
    seen_names: set[str] = set()
    all_saved: list[str] = []

    for upload in files:
        # Validate (reads content, checks size/ext/dupe)
        try:
            content = await validate_upload_file(upload, seen_names)
        except ValidationException as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "ValidationError", "message": exc.message},
            )

        filename = (upload.filename or "file").strip()
        seen_names.add(filename)

        if is_zip(filename):
            # Extract ZIP into project dir
            try:
                extracted = await extract_zip(content, project_dir)
                all_saved.extend(extracted)
                state.add_log(
                    f"[INFO] ZIP extracted — {len(extracted)} file(s) from '{filename}'",
                    LogLevel.INFO,
                    agent="upload",
                )
            except ValidationException as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": "ZipError", "message": exc.message},
                )
        else:
            # Save regular file
            saved = await fs.save_files(migration_id, [(filename, content)])
            all_saved.extend(saved)
            state.add_log(
                f"[INFO] Uploaded '{filename}' ({len(content):,} bytes)",
                LogLevel.INFO,
                agent="upload",
            )

    # 4. Update MigrationState
    state.uploaded_files = sorted(set(state.uploaded_files) | set(all_saved))
    state.project_root = str(project_dir)
    state.last_upload_time = datetime.now(timezone.utc)
    state.add_log(
        f"[SUCCESS] Upload complete — {len(all_saved)} file(s) stored",
        LogLevel.SUCCESS,
        agent="upload",
    )

    await _svc().update_state(migration_id, state)

    logger.info(
        "Upload complete — migration_id=%s  files=%d  project_root=%s",
        migration_id,
        len(all_saved),
        project_dir,
    )

    return UploadResponse(
        migration_id=migration_id,
        project_name=state.project_name,
        uploaded_count=len(all_saved),
        uploaded_files=all_saved,
        project_root=str(project_dir),
        message=f"Successfully uploaded {len(all_saved)} file(s).",
    )


@router.get(
    "/{migration_id}/files",
    response_model=ListFilesResponse,
    summary="List uploaded project files",
    description="List all files currently stored for a migration.",
)
async def list_project_files(migration_id: str) -> ListFilesResponse:
    """Return the list of files in ``storage/uploads/{migration_id}/``."""
    try:
        await _svc().get_migration(migration_id)  # 404 guard
    except MigrationNotFoundException:
        raise _not_found(migration_id)

    files = await _fs().list_files(migration_id)
    return ListFilesResponse(
        migration_id=migration_id,
        file_count=len(files),
        files=files,
    )


@router.delete(
    "/{migration_id}/files",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete all uploaded files",
    description="Remove all stored files for a migration (filesystem only, state is preserved).",
)
async def delete_project_files(migration_id: str) -> None:
    """Delete the filesystem contents for *migration_id*."""
    try:
        await _svc().get_migration(migration_id)  # 404 guard
    except MigrationNotFoundException:
        raise _not_found(migration_id)

    await _fs().delete_project(migration_id)
    logger.info("Files deleted — migration_id=%s", migration_id)
