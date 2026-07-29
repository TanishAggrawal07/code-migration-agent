"""
RAG retrieval service — semantic similarity search over ChromaDB (M7).

Implements retrieve_relevant_chunks() which:
1. Embeds the query text using EmbeddingService
2. Searches the ChromaDB ``migration_docs`` collection
3. Returns ranked results with chunk text, metadata, and similarity score

Return schema per result:
    {
        "chunk_id":   str,
        "content":    str,
        "metadata":   dict,
        "score":      float,   # cosine similarity (0 = identical, 2 = opposite)
    }

Graceful degradation: if EmbeddingService or ChromaDB are unavailable
the function returns an empty list rather than raising.

Usage:
    from app.rag.retrieval_service import RetrievalService
    svc = RetrievalService.get_instance()
    results = await svc.retrieve_relevant_chunks(
        migration_id="abc-123",
        query="public class UserService",
        top_k=5,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Singleton RAG retrieval service backed by ChromaDB + EmbeddingService.

    Each call to :meth:`retrieve_relevant_chunks` embeds the query fresh
    (no caching) to avoid stale vectors when the collection changes.
    """

    _instance: Optional["RetrievalService"] = None

    def __new__(cls) -> "RetrievalService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "RetrievalService":
        """Return the process-wide RetrievalService singleton."""
        return cls()

    # ── Public API ────────────────────────────────────────────────────

    async def retrieve_relevant_chunks(
        self,
        migration_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the *top_k* most similar chunks to *query*.

        The search is optionally filtered to the given *migration_id* when
        enough chunks are indexed for that migration; otherwise it searches
        the full collection so the model always gets useful context.

        Args:
            migration_id: Migration UUID (used for metadata filtering).
            query:        Natural-language or code query string.
            top_k:        Maximum number of results to return.

        Returns:
            List of result dicts with keys: ``chunk_id``, ``content``,
            ``metadata``, ``score``.  Empty list on service degradation.
        """
        if not query.strip():
            return []

        # ── Resolve services ──────────────────────────────────────────
        from app.embeddings.service import EmbeddingService
        from app.vectorstore.chroma_service import ChromaService

        emb_svc = EmbeddingService.get_instance()
        chroma_svc = ChromaService.get_instance()

        if not emb_svc.is_loaded:
            logger.warning(
                "RetrievalService — EmbeddingService not loaded, returning empty context "
                "for migration_id=%s",
                migration_id,
            )
            return []

        if not chroma_svc.is_initialized:
            logger.warning(
                "RetrievalService — ChromaService not initialised, returning empty context "
                "for migration_id=%s",
                migration_id,
            )
            return []

        # ── Embed query ───────────────────────────────────────────────
        try:
            query_embedding = await emb_svc.generate_embedding(query)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "RetrievalService — query embedding failed for migration_id=%s: %s",
                migration_id,
                exc,
            )
            return []

        # ── Search ChromaDB ───────────────────────────────────────────
        try:
            # First try: filter to this migration's indexed chunks
            where_filter: Optional[dict[str, Any]] = {"migration_id": migration_id}
            raw = await chroma_svc.query(
                query_embedding=query_embedding,
                n_results=top_k,
                where=where_filter,
            )

            # If no results for this migration, fall back to global search
            ids_found = raw.get("ids", [[]])[0]
            if not ids_found:
                logger.debug(
                    "RetrievalService — no migration-scoped results, falling back to global search "
                    "for migration_id=%s",
                    migration_id,
                )
                raw = await chroma_svc.query(
                    query_embedding=query_embedding,
                    n_results=top_k,
                )

        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "RetrievalService — ChromaDB query failed for migration_id=%s: %s",
                migration_id,
                exc,
            )
            return []

        # ── Flatten results ───────────────────────────────────────────
        results = _flatten_chroma_results(raw)
        logger.info(
            "RetrievalService — retrieved %d result(s) for migration_id=%s",
            len(results),
            migration_id,
        )
        return results

    async def retrieve_for_chunks(
        self,
        migration_id: str,
        chunks: list[dict[str, Any]],
        top_k: int = 3,
    ) -> list[str]:
        """
        Retrieve context for a list of code chunks (convenience wrapper).

        Concatenates chunk content into a single query and returns
        the plain text of the top results.

        Args:
            migration_id: Migration UUID.
            chunks:       List of CodeChunk dicts.
            top_k:        Max results per batch query.

        Returns:
            List of plain text strings (retrieved chunk contents).
        """
        if not chunks:
            return []

        # Build a representative query from the first few chunks
        sample = "\n".join(c.get("content", "")[:200] for c in chunks[:3])
        results = await self.retrieve_relevant_chunks(
            migration_id=migration_id,
            query=sample,
            top_k=top_k,
        )
        return [r["content"] for r in results]


# ── Module helpers ────────────────────────────────────────────────────────


def _flatten_chroma_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert the nested ChromaDB query response into a flat list.

    ChromaDB returns results as lists-of-lists (one outer list per query).
    We always issue single queries so we index ``[0]``.
    """
    ids: list[str] = raw.get("ids", [[]])[0]
    docs: list[str] = raw.get("documents", [[]])[0]
    metas: list[dict] = raw.get("metadatas", [[]])[0]
    distances: list[float] = raw.get("distances", [[]])[0]

    results: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        results.append({
            "chunk_id": meta.get("chunk_id", doc_id),
            "content":  docs[i] if i < len(docs) else "",
            "metadata": meta,
            "score":    distances[i] if i < len(distances) else 1.0,
        })

    return results
