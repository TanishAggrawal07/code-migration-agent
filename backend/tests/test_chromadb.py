"""
Tests for ChromaService — uses an in-memory or temp-dir client.
"""

import asyncio
import pytest

from app.vectorstore.chroma_service import ChromaService, ChromaServiceError


def run(coro):  # type: ignore[no-untyped-def]
    """Run a coroutine in a fresh event loop."""
    return asyncio.new_event_loop().run_until_complete(coro)


def test_chroma_service_singleton() -> None:
    """ChromaService must be a singleton."""
    a = ChromaService.get_instance()
    b = ChromaService.get_instance()
    assert a is b


def test_chroma_service_reports_availability() -> None:
    """is_available must return a bool."""
    svc = ChromaService.get_instance()
    assert isinstance(svc.is_available, bool)


def test_chroma_add_raises_when_not_initialized() -> None:
    """add_documents must raise ChromaServiceError when not initialized."""
    svc = ChromaService.get_instance()
    svc._initialized = False

    with pytest.raises(ChromaServiceError):
        run(svc.add_documents(["test"], [[0.1, 0.2]]))


def test_chroma_query_raises_when_not_initialized() -> None:
    """query must raise ChromaServiceError when not initialized."""
    svc = ChromaService.get_instance()
    svc._initialized = False

    with pytest.raises(ChromaServiceError):
        run(svc.query([0.1, 0.2]))


def test_chroma_is_initialized_false_before_init() -> None:
    """is_initialized must be False before initialize() is called."""
    svc = ChromaService.get_instance()
    svc._initialized = False
    assert svc.is_initialized is False


@pytest.mark.skipif(
    not ChromaService.get_instance().is_available,
    reason="chromadb not installed",
)
def test_chroma_initialize_with_temp_dir(tmp_path: pytest.TempdirFactory) -> None:
    """ChromaService can initialize against a temp directory."""
    import chromadb
    from chromadb.config import Settings as CS

    svc = ChromaService()
    svc._initialized = False

    loop = asyncio.new_event_loop()

    svc._client = chromadb.PersistentClient(
        path=str(tmp_path),
        settings=CS(anonymized_telemetry=False),
    )
    svc._collection = loop.run_until_complete(
        svc.create_collection("test_col")
    )
    svc._initialized = True
    assert svc.is_initialized is True

    # Cleanup
    svc._initialized = False
    svc._client = None
    svc._collection = None
    loop.close()
