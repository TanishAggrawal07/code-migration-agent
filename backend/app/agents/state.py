"""
Migration pipeline state model.

MigrationState is the single source of truth that flows through every
LangGraph node and is persisted (in-memory for now, database in a later
module).

Enums:
    MigrationStage  — lifecycle stages of a migration run

Models:
    LogEntry        — a single structured log line
    ParsedFile      — metadata for one parsed C# source file
    GeneratedFile   — metadata for one generated Java output file
    MigrationState  — the complete pipeline state
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────


class MigrationStage(str, Enum):
    """Ordered lifecycle stages for a migration run.

    The workflow engine progresses through these stages left-to-right.
    ``FAILED`` can be reached from any stage.
    """

    UPLOADED   = "uploaded"
    PARSED     = "parsed"
    ANALYZED   = "analyzed"
    EMBEDDED   = "embedded"
    RETRIEVED  = "retrieved"
    MIGRATED   = "migrated"
    COMPILED   = "compiled"
    SAVED      = "saved"
    FAILED     = "failed"


# Ordered sequence used by the pipeline visualiser (excludes FAILED)
STAGE_ORDER: list[MigrationStage] = [
    MigrationStage.UPLOADED,
    MigrationStage.PARSED,
    MigrationStage.ANALYZED,
    MigrationStage.EMBEDDED,
    MigrationStage.RETRIEVED,
    MigrationStage.MIGRATED,
    MigrationStage.COMPILED,
    MigrationStage.SAVED,
]


class LogLevel(str, Enum):
    """Severity levels for structured migration log entries."""

    DEBUG   = "DEBUG"
    INFO    = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR   = "ERROR"


# ── Sub-models ────────────────────────────────────────────────────────────


class LogEntry(BaseModel):
    """A single structured log line stored inside MigrationState."""

    level: LogLevel = LogLevel.INFO
    message: str
    stage: Optional[MigrationStage] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: Optional[str] = None

    model_config = {"use_enum_values": True}


class ParsedFile(BaseModel):
    """Metadata for one parsed C# source file."""

    filename: str
    path: str
    classes: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    lines: int = 0
    parsed: bool = False


class GeneratedFile(BaseModel):
    """Metadata for one generated Java output file."""

    filename: str
    path: str
    source_file: str = ""        # originating C# file
    compile_success: bool = False
    content_preview: str = ""    # first 200 chars for UI display


# ── Primary state model ───────────────────────────────────────────────────


class MigrationState(BaseModel):
    """
    Complete state for a single migration run.

    This model is passed between LangGraph nodes and persisted by
    :class:`~app.services.migration_service.MigrationService`.
    Every field has a safe default so nodes can assume the object
    always exists and read any field without a KeyError.
    """

    # ── Identity ──────────────────────────────────────────────────────
    migration_id: str = Field(default_factory=lambda: str(uuid4()))
    project_name: str = "unnamed_project"

    # ── Input files ───────────────────────────────────────────────────
    uploaded_files: list[str] = Field(
        default_factory=list,
        description="Paths/names of uploaded .NET source files",
    )

    # ── Parser output ─────────────────────────────────────────────────
    parsed_files: list[ParsedFile] = Field(
        default_factory=list,
        description="Structured metadata extracted from each C# file",
    )

    # ── Embedding input ───────────────────────────────────────────────
    chunks: list[str] = Field(
        default_factory=list,
        description="Code chunks prepared for embedding",
    )

    # ── Embedding output ──────────────────────────────────────────────
    embeddings_created: bool = False
    embedding_count: int = 0

    # ── RAG output ────────────────────────────────────────────────────
    retrieved_context: list[str] = Field(
        default_factory=list,
        description="Java migration patterns retrieved from ChromaDB",
    )

    # ── Migration output ──────────────────────────────────────────────
    generated_java_files: list[GeneratedFile] = Field(
        default_factory=list,
        description="Generated Java source files",
    )

    # ── Compilation ───────────────────────────────────────────────────
    compile_status: str = "pending"   # pending | success | failed | skipped
    compile_errors: list[str] = Field(default_factory=list)

    # ── Error tracking ────────────────────────────────────────────────
    errors: list[str] = Field(
        default_factory=list,
        description="Accumulated error messages across all stages",
    )

    # ── Structured logs ───────────────────────────────────────────────
    logs: list[LogEntry] = Field(
        default_factory=list,
        description="Ordered execution log for this migration run",
    )

    # ── Pipeline progress ─────────────────────────────────────────────
    current_stage: MigrationStage = MigrationStage.UPLOADED
    completed_stages: list[MigrationStage] = Field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Extra context (arbitrary key-value pairs from nodes) ──────────
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary extra data written by workflow nodes",
    )

    model_config = {"use_enum_values": False}

    # ── Helpers ───────────────────────────────────────────────────────

    def add_log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        agent: Optional[str] = None,
    ) -> None:
        """Append a structured log entry and update ``updated_at``."""
        self.logs.append(
            LogEntry(
                level=level,
                message=message,
                stage=self.current_stage,
                agent=agent,
            )
        )
        self.updated_at = datetime.now(timezone.utc)

    def advance_stage(self, stage: MigrationStage) -> None:
        """
        Mark the current stage complete and advance to *stage*.

        The previous stage is appended to ``completed_stages`` if not already
        present.
        """
        if self.current_stage not in self.completed_stages:
            self.completed_stages.append(self.current_stage)
        self.current_stage = stage
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, reason: str) -> None:
        """Transition to FAILED, recording *reason* in both errors and logs."""
        self.errors.append(reason)
        self.add_log(reason, level=LogLevel.ERROR)
        self.current_stage = MigrationStage.FAILED
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_failed(self) -> bool:
        """True when the migration is in FAILED state."""
        return self.current_stage == MigrationStage.FAILED

    @property
    def is_complete(self) -> bool:
        """True when the migration reached the SAVED stage."""
        return self.current_stage == MigrationStage.SAVED

    def to_summary(self) -> dict[str, Any]:
        """Return a lightweight summary dict for API list responses."""
        return {
            "migration_id": self.migration_id,
            "project_name": self.project_name,
            "current_stage": self.current_stage.value,
            "is_failed": self.is_failed,
            "is_complete": self.is_complete,
            "file_count": len(self.uploaded_files),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
