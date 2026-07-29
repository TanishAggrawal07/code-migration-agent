"""
Application startup orchestrator.

Initialises all AI services during the FastAPI lifespan event.
Each service fails gracefully — a missing package or absent API key
will not crash the server; it will only mark that service as unavailable.

Usage (in lifespan):
    from app.core.startup import initialize_services, shutdown_services
    await initialize_services()
    ...
    await shutdown_services()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Tracks the initialisation result of each AI service."""

    gemini: bool = False
    embeddings: bool = False
    chromadb: bool = False
    tree_sitter: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "gemini": self.gemini,
            "embeddings": self.embeddings,
            "chromadb": self.chromadb,
            "tree_sitter": self.tree_sitter,
        }


# Module-level singleton so the API can read it without re-initialising
_status = ServiceStatus()


def get_service_status() -> ServiceStatus:
    """Return the current service initialisation status."""
    return _status


async def initialize_services() -> ServiceStatus:
    """
    Initialise every AI service.

    Services are started concurrently where possible.
    A failure in any single service is logged but does not abort startup.

    Returns:
        :class:`ServiceStatus` reflecting which services are healthy.
    """
    import asyncio

    from app.core.gemini_client import GeminiClient
    from app.embeddings.service import EmbeddingService
    from app.vectorstore.chroma_service import ChromaService
    from app.parser.tree_sitter_service import TreeSitterService

    logger.info("Initialising AI services …")

    # Run initialisation concurrently
    results = await asyncio.gather(
        _init_gemini(GeminiClient.get_instance()),
        _init_embeddings(EmbeddingService.get_instance()),
        _init_chromadb(ChromaService.get_instance()),
        _init_tree_sitter(TreeSitterService.get_instance()),
        return_exceptions=True,
    )

    _status.gemini      = bool(results[0]) if not isinstance(results[0], Exception) else False
    _status.embeddings  = bool(results[1]) if not isinstance(results[1], Exception) else False
    _status.chromadb    = bool(results[2]) if not isinstance(results[2], Exception) else False
    _status.tree_sitter = bool(results[3]) if not isinstance(results[3], Exception) else False

    logger.info(
        "Service status — gemini=%s  embeddings=%s  chromadb=%s  tree_sitter=%s",
        _status.gemini,
        _status.embeddings,
        _status.chromadb,
        _status.tree_sitter,
    )
    return _status


async def shutdown_services() -> None:
    """Release AI service resources on shutdown."""
    logger.info("Shutting down AI services")
    # Placeholder for future resource cleanup (e.g. closing DB connections)


# ── Private init helpers ──────────────────────────────────────────────────

async def _init_gemini(client: object) -> bool:
    try:
        result: bool = await client.initialize()  # type: ignore[attr-defined]
        if result:
            provider_key = getattr(client, "active_provider_key", "unknown")
            model_name   = getattr(client, "active_model", "unknown")
            logger.info(
                "\n"
                "  ┌─ LLM Provider Ready ─────────────────────────────────\n"
                "  │  Provider selected : %s\n"
                "  │  Model selected    : %s\n"
                "  └──────────────────────────────────────────────────────",
                provider_key,
                model_name,
            )
        else:
            logger.warning(
                "LLM provider initialization failed — "
                "no provider available (Ollama not running, no API keys configured)."
            )
        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Gemini init error: %s", exc)
        return False


async def _init_embeddings(service: object) -> bool:
    try:
        result: bool = await service.load_model()  # type: ignore[attr-defined]
        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Embedding service init error: %s", exc)
        return False


async def _init_chromadb(service: object) -> bool:
    try:
        result: bool = await service.initialize()  # type: ignore[attr-defined]
        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("ChromaDB init error: %s", exc)
        return False


async def _init_tree_sitter(service: object) -> bool:
    try:
        result: bool = await service.initialize()  # type: ignore[attr-defined]
        return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Tree-sitter init error: %s", exc)
        return False
