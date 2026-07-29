"""
LLM Client facade — delegates to the active provider via the Provider Registry.

Preserves the GeminiClient interface so no callers need to change.

Usage:
    from app.core.gemini_client import GeminiClient
    client = GeminiClient.get_instance()
    await client.initialize()
    text = await client.generate_text("Hello!")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    """Raised when the LLM client encounters an unrecoverable error."""


class GeminiClient:
    """
    Singleton facade delegating to the active LLM provider
    (Ollama, Gemini, OpenRouter, Grok, OpenAI, etc.) via the Provider Registry.

    All callers continue to use GeminiClient.get_instance() and generate_text()
    — no migration workflow changes required.
    """

    _instance: Optional["GeminiClient"] = None
    _provider: Any = None
    _initialized: bool = False

    # ── Singleton ─────────────────────────────────────────────────────

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GeminiClient":
        """Return the application-wide client singleton."""
        return cls()

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """
        Detect and initialise the active LLM provider.

        Priority: Ollama → Gemini → OpenRouter → Grok → OpenAI.
        Returns True on success, False when no provider is available.
        """
        if self._initialized:
            return True

        settings = get_settings()

        try:
            from app.core.llm_providers import get_active_provider_instance
            self._provider = get_active_provider_instance(settings)

            if self._provider:
                self._initialized = True
                logger.info(
                    "LLM Provider Facade initialized — provider=%s  model=%s",
                    self._provider.key,
                    self._provider.model,
                )
                return True
            else:
                logger.warning(
                    "LLM Provider Facade init — no provider available "
                    "(Ollama not running, no API keys configured)"
                )
                return False

        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM Provider Facade initialization failed: %s", exc)
            return False

    def get_capabilities(self) -> Any:
        """Return ProviderCapabilities of the active provider, or conservative default if uninitialized."""
        if self._provider and hasattr(self._provider, "capabilities"):
            return self._provider.capabilities
        from app.core.llm_providers import ProviderCapabilities
        return ProviderCapabilities()

    # ── Core generation ───────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(GeminiClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=15),
        reraise=True,
    )
    async def generate_text(self, prompt: str) -> str:
        """
        Generate text from a prompt using the active LLM provider.

        Args:
            prompt: The user prompt string.

        Returns:
            The model's text response.

        Raises:
            GeminiClientError: If no provider is available or generation fails.
        """
        # Auto-initialise on first call if needed
        if not self._initialized:
            ok = await self.initialize()
            if not ok:
                raise GeminiClientError(
                    "LLM provider is not initialised — no provider available."
                )

        if self._provider is None:
            raise GeminiClientError("LLM provider is not loaded.")

        try:
            res = await self._provider.generate(prompt)
            if res.ok:
                logger.debug(
                    "LLM generation complete — provider=%s chars=%d",
                    self._provider.key,
                    len(res.text),
                )
                return res.text
            else:
                raise GeminiClientError(f"LLM generation failed: {res.error}")

        except GeminiClientError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM generation error: %s", exc)
            raise GeminiClientError(str(exc)) from exc

    # ── Health check ──────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """
        Verify that the active LLM provider is reachable and responding.

        Returns:
            True if the provider responds, False otherwise.
        """
        if not self._initialized:
            return False

        try:
            response = await self.generate_text("Reply with: OK")
            return bool(response and "OK" in response)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("LLM health check failed: %s", exc)
            return False

    # ── Introspection ─────────────────────────────────────────────────

    @property
    def active_provider_key(self) -> str:
        """Key of the currently active provider (e.g. 'ollama', 'gemini')."""
        if self._provider:
            return self._provider.key
        return "none"

    @property
    def active_model(self) -> str:
        """Model name of the currently active provider."""
        if self._provider:
            return self._provider.model
        return "none"

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        """Whether the client has been successfully initialised."""
        return self._initialized

    @property
    def is_available(self) -> bool:
        """Always True — the facade is always importable."""
        return True
