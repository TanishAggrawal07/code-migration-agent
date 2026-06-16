"""
ChromaDB vector-store service — persistent collection management.

Usage:
    from app.vectorstore.chroma_service import ChromaService
    svc = ChromaService.get_instance()
    await svc.initialize()
    await svc.add_documents(["code snippet"], [[0.1, 0.2, ...]], [{"source": "foo.cs"}])
    results = await svc.query([0.1, 0.2, ...], n_results=5)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import chromadb  # type: ignore[import]
    from chromadb.config import Settings as ChromaSettings  # type: ignore[import]
    _CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None          # type: ignore[assignment]
    ChromaSettings = None    # type: ignore[assignment,misc]
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed — ChromaService will be unavailable")


class ChromaServiceError(Exception):
    """Raised when ChromaDB operations fail."""


class ChromaService:
    """
    Singleton wrapper around ChromaDB with persistent on-disk storage.

    The default collection is ``migration_docs`` (configurable via
    ``CHROMA_COLLECTION_NAME`` env var).
    """

    _instance: Optional["ChromaService"] = None
    _client: Any = None         # chromadb.PersistentClient
    _collection: Any = None     # chromadb.Collection
    _initialized: bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    def __new__(cls) -> "ChromaService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ChromaService":
        """Return the application-wide ChromaService singleton."""
        return cls()

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """
        Connect to (or create) the persistent ChromaDB store and
        ensure the default collection exists.

        Returns:
            ``True`` on success, ``False`` if unavailable.
        """
        if self._initialized:
            return True

        if not _CHROMA_AVAILABLE:
            logger.warning("Skipping ChromaDB init — package not installed")
            return False

        settings = get_settings()

        try:
            loop = asyncio.get_event_loop()
            self._client = await loop.run_in_executor(
                None,
                lambda: chromadb.PersistentClient(
                    path=settings.chroma_db_path,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                    ),
                ),
            )
            self._collection = await self.create_collection(settings.chroma_collection_name)
            self._initialized = True
            logger.info(
                "ChromaService initialized — path=%s  collection=%s",
                settings.chroma_db_path,
                settings.chroma_collection_name,
            )
            return True

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ChromaDB initialization failed: %s", exc)
            return False

    # ── Collection management ─────────────────────────────────────────

    async def create_collection(self, name: str) -> Any:
        """
        Get or create a named ChromaDB collection.

        Args:
            name: Collection name.

        Returns:
            The ChromaDB collection object.

        Raises:
            ChromaServiceError: If ChromaDB is not available or the client
            is not initialized.
        """
        if not _CHROMA_AVAILABLE or self._client is None:
            raise ChromaServiceError("ChromaDB client is not initialized.")

        loop = asyncio.get_event_loop()
        collection = await loop.run_in_executor(
            None,
            lambda: self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            ),
        )
        logger.info("Collection ready — name=%s", name)
        return collection

    async def delete_collection(self, name: str) -> bool:
        """
        Delete a named collection from ChromaDB.

        Args:
            name: Collection name to delete.

        Returns:
            ``True`` if deleted, ``False`` on error.
        """
        if not _CHROMA_AVAILABLE or self._client is None:
            return False

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_collection(name),
            )
            logger.info("Collection deleted — name=%s", name)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to delete collection %r: %s", name, exc)
            return False

    # ── CRUD operations ───────────────────────────────────────────────

    async def add_documents(
        self,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict[str, Any]]] = None,
        ids: Optional[list[str]] = None,
        collection_name: Optional[str] = None,
    ) -> bool:
        """
        Upsert documents with pre-computed embeddings into a collection.

        Args:
            documents:  Raw text documents.
            embeddings: Pre-computed embedding vectors (one per document).
            metadatas:  Optional metadata dicts (one per document).
            ids:        Optional unique IDs; auto-generated if omitted.
            collection_name: Override the default collection.

        Returns:
            ``True`` on success.

        Raises:
            ChromaServiceError: If the service is not initialized.
        """
        if not self._initialized:
            raise ChromaServiceError("ChromaService is not initialized.")

        if not documents:
            return True

        # Resolve collection
        if collection_name is not None:
            collection = await self.create_collection(collection_name)
        else:
            collection = self._collection

        # Auto-generate IDs if not provided
        if ids is None:
            import hashlib
            ids = [
                hashlib.md5(doc.encode()).hexdigest()  # noqa: S324
                for doc in documents
            ]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: collection.upsert(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                ),
            )
            logger.debug("Upserted %d documents into ChromaDB", len(documents))
            return True

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ChromaDB upsert failed: %s", exc)
            raise ChromaServiceError(f"Upsert failed: {exc}") from exc

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Query the collection for the closest documents.

        Args:
            query_embedding: The query embedding vector.
            n_results:        Number of results to return.
            where:            Optional metadata filter dict.
            collection_name:  Override the default collection.

        Returns:
            ChromaDB query result dict with keys:
            ``ids``, ``documents``, ``metadatas``, ``distances``.

        Raises:
            ChromaServiceError: If the service is not initialized.
        """
        if not self._initialized:
            raise ChromaServiceError("ChromaService is not initialized.")

        if collection_name is not None:
            collection = await self.create_collection(collection_name)
        else:
            collection = self._collection

        try:
            loop = asyncio.get_event_loop()
            kwargs: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where

            result: dict[str, Any] = await loop.run_in_executor(
                None,
                lambda: collection.query(**kwargs),
            )
            logger.debug("ChromaDB query returned %d results", len(result.get("ids", [[]])[0]))
            return result

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("ChromaDB query failed: %s", exc)
            raise ChromaServiceError(f"Query failed: {exc}") from exc

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        """Whether ChromaDB has been successfully initialized."""
        return self._initialized

    @property
    def is_available(self) -> bool:
        """Whether the chromadb package is installed."""
        return _CHROMA_AVAILABLE
