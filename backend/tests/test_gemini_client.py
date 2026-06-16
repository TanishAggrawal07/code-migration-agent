"""
Tests for GeminiClient — no real API calls are made.
"""

import asyncio
import pytest

from app.core.gemini_client import GeminiClient, GeminiClientError


def run(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


def test_gemini_client_is_singleton() -> None:
    """GeminiClient must be a singleton."""
    a = GeminiClient.get_instance()
    b = GeminiClient.get_instance()
    assert a is b


def test_gemini_client_not_initialized_without_key() -> None:
    """
    Without a real API key, initialize() must return False
    and is_initialized must stay False.
    """
    client = GeminiClient.get_instance()
    client._initialized = False
    client._model = None

    result = run(client.initialize())
    # Expect False — no key is set in test environment
    assert isinstance(result, bool)
    # If GEMINI_API_KEY is unset, result must be False
    from app.core.config import get_settings
    if not get_settings().gemini_configured:
        assert result is False


def test_gemini_generate_raises_when_not_initialized() -> None:
    """generate_text must raise GeminiClientError when not initialized."""
    client = GeminiClient.get_instance()
    client._initialized = False

    with pytest.raises(GeminiClientError):
        run(client.generate_text("test prompt"))


def test_gemini_health_check_false_when_not_initialized() -> None:
    """health_check must return False when client not initialized."""
    client = GeminiClient.get_instance()
    client._initialized = False

    result = run(client.health_check())
    assert result is False


def test_gemini_is_available_returns_bool() -> None:
    """is_available must be a bool."""
    client = GeminiClient.get_instance()
    assert isinstance(client.is_available, bool)


def test_gemini_is_initialized_false_after_reset() -> None:
    """is_initialized must reflect the internal state."""
    client = GeminiClient.get_instance()
    client._initialized = False
    assert client.is_initialized is False
