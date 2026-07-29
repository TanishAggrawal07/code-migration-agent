"""
Migrations API — CRUD and workflow execution endpoints.

Routes:
    POST   /api/migrations                        Create a migration
    GET    /api/migrations                        List all migrations
    GET    /api/migrations/{migration_id}         Get migration state
    POST   /api/migrations/{migration_id}/run     Execute workflow
    GET    /api/migrations/{migration_id}/status  Pipeline visualisation
    DELETE /api/migrations/{migration_id}         Delete migration
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.agents.workflow import get_workflow_engine
from app.core.exceptions import (
    MigrationAlreadyRunningException,
    MigrationNotFoundException,
    WorkflowException,
)
from app.services.migration_service import MigrationService
from app.services.filesystem_service import FileSystemService
import zipfile
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migrations", tags=["Migrations"])


# ── Request / Response schemas ────────────────────────────────────────────


class CreateMigrationRequest(BaseModel):
    """Payload for POST /api/migrations."""

    project_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name for the .NET project",
        examples=["MyEcommerceApp"],
    )
    uploaded_files: list[str] = Field(
        default_factory=list,
        description="Optional list of file paths/names to associate immediately",
    )


class CreateMigrationResponse(BaseModel):
    """Response for POST /api/migrations."""

    migration_id: str
    project_name: str
    status: str = "created"
    message: str = "Migration created successfully"


class RunWorkflowResponse(BaseModel):
    """Response for POST /api/migrations/{id}/run."""

    migration_id: str
    stage: str
    is_complete: bool
    is_failed: bool
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────


def _svc() -> MigrationService:
    return MigrationService.get_instance()


def _http_not_found(migration_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "MigrationNotFound", "migration_id": migration_id},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=CreateMigrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a migration",
)
async def create_migration(body: CreateMigrationRequest) -> CreateMigrationResponse:
    """
    Create a new migration record.

    Returns the ``migration_id`` needed to drive subsequent API calls.
    """
    state = await _svc().create_migration(
        project_name=body.project_name,
        uploaded_files=body.uploaded_files,
    )
    logger.info("POST /api/migrations — created id=%s", state.migration_id)
    return CreateMigrationResponse(
        migration_id=state.migration_id,
        project_name=state.project_name,
    )


@router.get(
    "",
    summary="List all migrations",
)
async def list_migrations() -> dict[str, Any]:
    """Return summary objects for every migration in the store."""
    migrations = await _svc().list_migrations()
    return {
        "total": len(migrations),
        "migrations": [m.to_summary() for m in migrations],
    }


@router.get(
    "/{migration_id}",
    summary="Get migration state",
)
async def get_migration(migration_id: str) -> dict[str, Any]:
    """
    Return the full :class:`~app.agents.state.MigrationState` for one migration.
    """
    try:
        state = await _svc().get_migration(migration_id)
    except MigrationNotFoundException:
        raise _http_not_found(migration_id)

    return state.model_dump(mode="json")


@router.post(
    "/{migration_id}/run",
    response_model=RunWorkflowResponse,
    summary="Execute workflow",
)
async def run_workflow(
    migration_id: str,
    background_tasks: BackgroundTasks,
) -> RunWorkflowResponse:
    """
    Execute the full migration pipeline for *migration_id*.

    The workflow runs **synchronously in the request** for this module
    (background / streaming execution arrives in Module 4).
    Returns the pipeline state after all nodes have completed.
    """
    svc = _svc()

    # 1. Fetch state
    try:
        state = await svc.get_migration(migration_id)
    except MigrationNotFoundException:
        raise _http_not_found(migration_id)

    # 2. Guard against concurrent runs
    try:
        await svc.guard_not_running(migration_id)
    except MigrationAlreadyRunningException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.to_dict(),
        )

    # 3. Mark as running
    await svc.set_workflow_running(migration_id, True)

    try:
        engine = get_workflow_engine()
        result = await engine.run_workflow(state)
        await svc.update_state(migration_id, result)
    except WorkflowException as exc:
        await svc.set_workflow_running(migration_id, False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.to_dict(),
        )
    except Exception as exc:  # pylint: disable=broad-except
        await svc.set_workflow_running(migration_id, False)
        logger.error("Unexpected error running workflow %s: %s", migration_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "InternalError", "message": str(exc)},
        )

    # 4. Clear running flag
    await svc.set_workflow_running(migration_id, False)

    logger.info(
        "POST /api/migrations/%s/run — stage=%s  failed=%s",
        migration_id,
        result.current_stage.value,
        result.is_failed,
    )

    return RunWorkflowResponse(
        migration_id=migration_id,
        stage=result.current_stage.value,
        is_complete=result.is_complete,
        is_failed=result.is_failed,
        message=(
            "Workflow completed successfully"
            if result.is_complete
            else (
                f"Workflow failed at stage: {result.current_stage.value}"
                if result.is_failed
                else f"Workflow advanced to: {result.current_stage.value}"
            )
        ),
    )


@router.get(
    "/{migration_id}/status",
    summary="Pipeline visualisation",
)
async def get_pipeline_status(migration_id: str) -> dict[str, Any]:
    """
    Return a structured pipeline status for the frontend visualiser.

    Response includes ``current_stage``, ``completed``, ``remaining``,
    and a ``progress_pct`` integer (0–100).
    """
    try:
        state = await _svc().get_migration(migration_id)
    except MigrationNotFoundException:
        raise _http_not_found(migration_id)

    engine = get_workflow_engine()
    return engine.get_pipeline_status(state)


@router.delete(
    "/{migration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Delete migration",
)
async def delete_migration(migration_id: str) -> Response:
    """Permanently remove a migration from the store."""
    deleted = await _svc().delete_migration(migration_id)
    if not deleted:
        raise _http_not_found(migration_id)
    logger.info("DELETE /api/migrations/%s", migration_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{migration_id}/download",
    summary="Download migrated Java files",
)
async def download_migration(migration_id: str) -> FileResponse:
    """
    Package all generated Java files for *migration_id* into a ZIP file
    and return it as a downloadable response.
    """
    # 1. Fetch migration (raises 404 if not found)
    svc = _svc()
    try:
        state = await svc.get_migration(migration_id)
    except MigrationNotFoundException:
        raise _http_not_found(migration_id)

    # 2. Get paths
    fs = FileSystemService.get_instance()
    generated_dir = fs.get_generated_path(migration_id)
    temp_dir = fs.get_temp_path(migration_id)

    # 3. Check if any java files were generated
    if not generated_dir.exists() or not list(generated_dir.glob("**/*.java")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "NoOutputGenerated",
                "message": "No Java output files have been generated/saved yet.",
            },
        )

    # 4. Create ZIP
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / f"{state.project_name}_migrated.zip"

    def _create_zip():
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in generated_dir.rglob("*"):
                if file_path.is_file():
                    # Preserve relative path hierarchy
                    rel_path = file_path.relative_to(generated_dir)
                    zf.write(file_path, arcname=rel_path)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _create_zip)

    logger.info("Created download ZIP archive at %s for migration %s", zip_path, migration_id)
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{state.project_name}_migrated.zip",
    )
