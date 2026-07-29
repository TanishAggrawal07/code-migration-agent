"""
Indexing service — embeds code chunks and stores them in ChromaDB (M6).

Responsibilities:
- Accept CodeChunk dicts from ParserAgent
- Generate embeddings via EmbeddingService (all-MiniLM-L6-v2)
- Upsert into ChromaDB collection ``migration_docs`` with rich metadata
- Avoid duplicate insertions (chunk_id is used as the Chroma document ID)
- Gracefully degrade when EmbeddingService or ChromaDB are unavailable

Metadata stored per document:
    {
        "migration_id": str,
        "file_path":    str,
        "chunk_id":     str,
        "chunk_type":   "class" | "method" | "file",
        "namespace":    str,   # from analysis, may be empty
        "class_name":   str,   # first class in the chunk, may be empty
    }

Usage:
    from app.vectorstore.indexing_service import IndexingService
    svc = IndexingService.get_instance()
    result = await svc.index_chunks(
        migration_id="abc-123",
        chunks=[{"chunk_id": ..., "content": ..., ...}],
        analysis={"namespace": "MyApp", ...},
    )
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Maximum characters to embed per chunk — truncated to avoid token limits
_MAX_CONTENT_CHARS = 4000


class IndexingResult:
    """Summary of a completed indexing operation."""

    def __init__(
        self,
        indexed: int = 0,
        skipped: int = 0,
        failed: int = 0,
        mode: str = "live",   # "live" | "degraded" (when services unavailable)
    ) -> None:
        self.indexed = indexed
        self.skipped = skipped
        self.failed = failed
        self.mode = mode

    def to_dict(self) -> dict[str, Any]:
        return {
            "indexed": self.indexed,
            "skipped": self.skipped,
            "failed": self.failed,
            "mode": self.mode,
        }


class IndexingService:
    """
    Singleton service that embeds code chunks and stores them in ChromaDB.

    Degrades gracefully: if EmbeddingService or ChromaDB are not initialised
    at the time of indexing, the method returns an ``IndexingResult`` with
    ``mode="degraded"`` and ``indexed=0`` rather than raising.
    """

    _instance: Optional["IndexingService"] = None

    def __new__(cls) -> "IndexingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "IndexingService":
        """Return the process-wide IndexingService singleton."""
        return cls()

    # ── Public API ────────────────────────────────────────────────────

    async def index_chunks(
        self,
        migration_id: str,
        chunks: list[dict[str, Any]],
        analysis: Optional[dict[str, Any]] = None,
    ) -> IndexingResult:
        """
        Embed *chunks* and upsert them into ChromaDB.

        Args:
            migration_id: UUID of the owning migration.
            chunks:       List of CodeChunk dicts (must have ``chunk_id``
                          and ``content`` keys).
            analysis:     Optional AnalyzerService output (used to enrich
                          metadata with ``namespace`` and class names).

        Returns:
            :class:`IndexingResult` describing what was indexed.
        """
        if not chunks:
            logger.info("IndexingService — no chunks to index for migration_id=%s", migration_id)
            return IndexingResult(mode="live")

        # ── Resolve services ──────────────────────────────────────────
        from app.embeddings.service import EmbeddingService
        from app.vectorstore.chroma_service import ChromaService

        emb_svc = EmbeddingService.get_instance()
        chroma_svc = ChromaService.get_instance()

        if not emb_svc.is_loaded:
            logger.warning(
                "IndexingService — EmbeddingService not loaded, skipping indexing "
                "for migration_id=%s",
                migration_id,
            )
            return IndexingResult(mode="degraded")

        if not chroma_svc.is_initialized:
            logger.warning(
                "IndexingService — ChromaService not initialised, skipping indexing "
                "for migration_id=%s",
                migration_id,
            )
            return IndexingResult(mode="degraded")

        # ── Prepare data ──────────────────────────────────────────────
        analysis = analysis or {}
        namespace: str = analysis.get("namespace", "")
        class_list: list[str] = analysis.get("classes", [])

        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        indexed = 0
        skipped = 0
        failed = 0

        for chunk in chunks:
            chunk_id: str = chunk.get("chunk_id", "")
            content: str = chunk.get("content", "").strip()
            file_name: str = chunk.get("file_name", "")
            chunk_type: str = chunk.get("chunk_type", "file")

            if not chunk_id or not content:
                skipped += 1
                continue

            # Truncate oversized content
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[:_MAX_CONTENT_CHARS]

            # Best-effort class name: first class found in chunk content
            class_name = _guess_class_name(content, class_list)

            documents.append(content)
            metadatas.append({
                "migration_id": migration_id,
                "file_path":    file_name,
                "chunk_id":     chunk_id,
                "chunk_type":   chunk_type,
                "namespace":    namespace,
                "class_name":   class_name,
            })
            ids.append(chunk_id)   # chunk_id is already a UUID4 — unique per run

        if not documents:
            logger.info(
                "IndexingService — all chunks skipped for migration_id=%s", migration_id
            )
            return IndexingResult(skipped=skipped, mode="live")

        # ── Generate embeddings in batch ──────────────────────────────
        try:
            embeddings = await emb_svc.generate_embeddings(documents)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "IndexingService — embedding generation failed for migration_id=%s: %s",
                migration_id,
                exc,
            )
            return IndexingResult(skipped=skipped, failed=len(documents), mode="degraded")

        # ── Upsert into ChromaDB ──────────────────────────────────────
        try:
            await chroma_svc.add_documents(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            indexed = len(documents)
            logger.info(
                "Indexed %d chunks — migration_id=%s  Stored in ChromaDB",
                indexed,
                migration_id,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "IndexingService — ChromaDB upsert failed for migration_id=%s: %s",
                migration_id,
                exc,
            )
            return IndexingResult(skipped=skipped, failed=len(documents), mode="degraded")

        return IndexingResult(indexed=indexed, skipped=skipped, failed=failed, mode="live")


# ── Module helpers ────────────────────────────────────────────────────────


def _guess_class_name(content: str, known_classes: list[str]) -> str:
    """
    Return the first known class name that appears in *content*, or "".

    Falls back to a quick regex scan if *known_classes* is empty.
    """
    for cls in known_classes:
        if cls in content:
            return cls

    import re
    m = re.search(r"\bclass\s+(\w+)", content)
    return m.group(1) if m else ""
