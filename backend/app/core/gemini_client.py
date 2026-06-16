"""
Gemini 2.5 Flash client — singleton with retry, timeout, and health-check.

Usage:
    from app.core.gemini_client import GeminiClient
    client = GeminiClient.get_instance()
    await client.initialize()
    text = await client.generate_text("Hello, Gemini!")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Lazy import so the server starts even if the package is absent
try:
    import google.generativeai as genai  # type: ignore[import]
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    _GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed — GeminiClient will be unavailable")


class GeminiClientError(Exception):
    """Raised when the Gemini client encounters an unrecoverable error."""


class GeminiClient:
    """
    Singleton wrapper around the google-generativeai SDK.

    Provides:
    - Lazy initialization with ``initialize()``
    - Retry with exponential back-off via tenacity
    - Configurable timeout (``gemini_timeout_seconds`` in Settings)
    - Graceful degradation when the API key is absent
    """

    _instance: Optional["GeminiClient"] = None
    _model: object = None           # genai.GenerativeModel
    _initialized: bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GeminiClient":
        """Return the application-wide GeminiClient singleton."""
        return cls()

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """
        Configure the Gemini SDK and create the generative model.

        Returns:
            ``True`` on success, ``False`` if the key is absent or the
            package is not installed.
        """
        if self._initialized:
            return True

        settings = get_settings()

        if not _GENAI_AVAILABLE:
            logger.warning("Skipping Gemini init — google-generativeai not installed")
            return False

        if not settings.gemini_configured:
            logger.warning(
                "Skipping Gemini init — GEMINI_API_KEY not set in environment"
            )
            return False

        try:
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel(model_name=settings.gemini_model)
            self._initialized = True
            logger.info("GeminiClient initialized — model=%s", settings.gemini_model)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("GeminiClient initialization failed: %s", exc)
            return False

    # ── Core generation ───────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt using Gemini 2.5 Flash.

        Args:
            prompt: The user prompt string.

        Returns:
            The model's text response.

        Raises:
            GeminiClientError: If the client is not initialized or generation fails.
        """
        if not self._initialized:
            raise GeminiClientError(
                "GeminiClient is not initialized. Call await client.initialize() first."
            )

        if self._model is None:
            raise GeminiClientError("Gemini model is not loaded.")

        settings = get_settings()

        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, self._model.generate_content, prompt),  # type: ignore[attr-defined]
                timeout=settings.gemini_timeout_seconds,
            )
            text: str = response.text
            logger.debug("Gemini generation complete — chars=%d", len(text))
            return text

        except asyncio.TimeoutError as exc:
            logger.error("Gemini request timed out after %ds", settings.gemini_timeout_seconds)
            raise GeminiClientError("Gemini request timed out") from exc
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Gemini generation error: %s", exc)
            raise

    # ── Health check ──────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """
        Verify that the Gemini API is reachable and responding.

        Returns:
            ``True`` if the API responds successfully, ``False`` otherwise.
        """
        if not self._initialized:
            return False

        try:
            response = await self.generate_text("Reply with: OK")
            return bool(response and "OK" in response)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Gemini health check failed: %s", exc)
            return False

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        """Whether the client has been successfully initialized."""
        return self._initialized

    @property
    def is_available(self) -> bool:
        """Whether the google-generativeai package is installed."""
        return _GENAI_AVAILABLE
