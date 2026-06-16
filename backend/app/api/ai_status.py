"""
AI services status endpoint.

GET /api/ai/status — returns liveness state of each AI subsystem.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Services"])


class AIStatusResponse(BaseModel):
    """Response schema for the AI status endpoint."""

    gemini: bool
    embeddings: bool
    chromadb: bool
    tree_sitter: bool
    all_healthy: bool


@router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="AI services health",
    description=(
        "Returns the initialisation status of each AI subsystem. "
        "A ``false`` value means the service is unavailable (missing package "
        "or unconfigured API key) but the server is still operational."
    ),
)
async def ai_status() -> AIStatusResponse:
    """
    Perform lightweight health checks on each AI service.

    Does NOT re-initialise services; reads the in-memory status set at startup.
    """
    from app.core.startup import get_service_status
    from app.core.gemini_client import GeminiClient
    from app.embeddings.service import EmbeddingService
    from app.vectorstore.chroma_service import ChromaService
    from app.parser.tree_sitter_service import TreeSitterService

    startup_status = get_service_status()

    # Lightweight live checks (no network calls)
    gemini_ok     = GeminiClient.get_instance().is_initialized
    embeddings_ok = EmbeddingService.get_instance().is_loaded
    chroma_ok     = ChromaService.get_instance().is_initialized
    tree_ok       = TreeSitterService.get_instance().is_initialized

    # Union of startup result and current live state
    final_gemini     = startup_status.gemini     and gemini_ok
    final_embeddings = startup_status.embeddings and embeddings_ok
    final_chroma     = startup_status.chromadb   and chroma_ok
    final_tree       = startup_status.tree_sitter and tree_ok

    all_healthy = all([final_gemini, final_embeddings, final_chroma, final_tree])

    logger.debug(
        "AI status — gemini=%s embeddings=%s chromadb=%s tree_sitter=%s",
        final_gemini, final_embeddings, final_chroma, final_tree,
    )

    return AIStatusResponse(
        gemini=final_gemini,
        embeddings=final_embeddings,
        chromadb=final_chroma,
        tree_sitter=final_tree,
        all_healthy=all_healthy,
    )


@router.get(
    "/services",
    summary="AI services detail",
    description="Returns availability and initialisation details for each AI service.",
)
async def ai_services_detail() -> dict[str, Any]:
    """Extended service info including package availability."""
    from app.core.gemini_client import GeminiClient
    from app.embeddings.service import EmbeddingService
    from app.vectorstore.chroma_service import ChromaService
    from app.parser.tree_sitter_service import TreeSitterService
    from app.core.config import get_settings

    settings = get_settings()
    gemini  = GeminiClient.get_instance()
    embed   = EmbeddingService.get_instance()
    chroma  = ChromaService.get_instance()
    ts      = TreeSitterService.get_instance()

    return {
        "gemini": {
            "package_available": gemini.is_available,
            "initialized": gemini.is_initialized,
            "model": settings.gemini_model,
            "api_key_configured": settings.gemini_configured,
        },
        "embeddings": {
            "package_available": embed.is_available,
            "initialized": embed.is_loaded,
            "model": embed.model_name,
            "device": embed.device,
        },
        "chromadb": {
            "package_available": chroma.is_available,
            "initialized": chroma.is_initialized,
            "path": settings.chroma_db_path,
            "collection": settings.chroma_collection_name,
        },
        "tree_sitter": {
            "package_available": ts.is_available,
            "initialized": ts.is_initialized,
            "using_stub": ts.using_stub,
        },
    }
