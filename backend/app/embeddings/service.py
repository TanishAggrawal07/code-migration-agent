"""
Embedding service — wraps Sentence Transformers with lazy loading,
singleton pattern, and CPU/GPU detection.

Usage:
    from app.embeddings.service import EmbeddingService
    svc = EmbeddingService.get_instance()
    await svc.load_model()
    vec = await svc.generate_embedding("public class Foo {}")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Graceful fallback when heavy ML package is absent
try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import]
    import torch  # type: ignore[import]
    _ST_AVAILABLE = True
except ImportError:
    SentenceTransformer = None  # type: ignore[misc,assignment]
    torch = None                # type: ignore[assignment]
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not installed — EmbeddingService unavailable")


class EmbeddingServiceError(Exception):
    """Raised when embedding operations fail."""


class EmbeddingService:
    """
    Singleton Sentence Transformers embedding service.

    Features:
    - Lazy model loading (only downloaded on first call)
    - GPU acceleration when CUDA is available, CPU fallback otherwise
    - Thread-executor offload so FastAPI event loop is never blocked
    """

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[object] = None   # SentenceTransformer
    _device: str = "cpu"
    _loaded: bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        """Return the application-wide EmbeddingService singleton."""
        return cls()

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def load_model(self) -> bool:
        """
        Load the sentence-transformers model.

        The model is downloaded once and cached by the transformers library.
        Detects CUDA automatically; falls back to CPU.

        Returns:
            ``True`` on success, ``False`` if unavailable.
        """
        if self._loaded:
            return True

        if not _ST_AVAILABLE:
            logger.warning("Skipping embedding model load — sentence-transformers not installed")
            return False

        settings = get_settings()
        model_name = settings.embedding_model

        try:
            # Detect device
            if torch is not None and torch.cuda.is_available():
                self._device = "cuda"
                logger.info("GPU detected — using CUDA for embeddings")
            else:
                self._device = "cpu"
                logger.info("No GPU detected — using CPU for embeddings")

            # Load in thread executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(model_name, device=self._device),
            )
            self._loaded = True
            logger.info(
                "EmbeddingService loaded — model=%s  device=%s",
                model_name,
                self._device,
            )
            return True

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to load embedding model %r: %s", model_name, exc)
            return False

    # ── Embedding generation ──────────────────────────────────────────

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate a single embedding vector for *text*.

        Args:
            text: Source text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            EmbeddingServiceError: If the model is not loaded.
        """
        results = await self.generate_embeddings([text])
        return results[0]

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Batch-generate embedding vectors for a list of texts.

        Args:
            texts: List of source texts to embed.

        Returns:
            A list of embedding vectors (list of floats).

        Raises:
            EmbeddingServiceError: If the model is not loaded.
        """
        # Short-circuit before the model check — empty input never needs a model
        if not texts:
            return []

        if not self._loaded or self._model is None:
            raise EmbeddingServiceError(
                "EmbeddingService model not loaded. Call await svc.load_model() first."
            )

        settings = get_settings()
        batch_size = settings.embedding_batch_size

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(  # type: ignore[union-attr]
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ).tolist(),
            )
            logger.debug("Generated %d embeddings", len(embeddings))
            return embeddings

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Embedding generation failed: %s", exc)
            raise EmbeddingServiceError(f"Embedding generation failed: {exc}") from exc

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been successfully loaded."""
        return self._loaded

    @property
    def device(self) -> str:
        """The compute device in use: 'cuda' or 'cpu'."""
        return self._device

    @property
    def is_available(self) -> bool:
        """Whether sentence-transformers is installed."""
        return _ST_AVAILABLE

    @property
    def model_name(self) -> str:
        """The configured embedding model name."""
        return get_settings().embedding_model
