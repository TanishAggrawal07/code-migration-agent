"""
Tests for RetrievalService (M7).

Patching strategy: uses patch.object on class get_instance methods
since services are lazily imported inside retrieve_relevant_chunks().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.retrieval_service import RetrievalService, _flatten_chroma_results
from app.embeddings.service import EmbeddingService
from app.vectorstore.chroma_service import ChromaService


# ── Helpers ───────────────────────────────────────────────────────────────

def _fresh_svc() -> RetrievalService:
    RetrievalService._instance = None
    return RetrievalService.get_instance()


def _mock_chroma_result(
    ids: list[str],
    docs: list[str],
    metas: list[dict],
    distances: list[float],
) -> dict:
    return {
        "ids":       [ids],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
    }


SAMPLE_META = {"migration_id": "mig-001", "chunk_id": "c-001", "chunk_type": "class"}
SAMPLE_RESULT = _mock_chroma_result(
    ids=["c-001"],
    docs=["public class UserService {}"],
    metas=[SAMPLE_META],
    distances=[0.12],
)
EMPTY_RESULT = _mock_chroma_result([], [], [], [])


def _mock_emb(loaded: bool = True) -> MagicMock:
    m = MagicMock()
    m.is_loaded = loaded
    m.generate_embedding = AsyncMock(return_value=[0.5] * 384)
    return m


def _mock_chroma(initialized: bool = True, query_result=None) -> MagicMock:
    m = MagicMock()
    m.is_initialized = initialized
    m.query = AsyncMock(return_value=query_result or SAMPLE_RESULT)
    return m


# ── Degradation tests ─────────────────────────────────────────────────────


class TestRetrievalDegradation:

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        svc = _fresh_svc()
        result = await svc.retrieve_relevant_chunks("mig-001", "   ", top_k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_embedding_service_not_loaded(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb(loaded=False)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb):
            result = await svc.retrieve_relevant_chunks("mig-001", "find user", top_k=5)

        assert result == []

    @pytest.mark.asyncio
    async def test_chroma_not_initialised(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma(initialized=False)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.retrieve_relevant_chunks("mig-001", "find user", top_k=5)

        assert result == []

    @pytest.mark.asyncio
    async def test_embedding_error_returns_empty(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_emb.generate_embedding = AsyncMock(side_effect=RuntimeError("boom"))
        mock_chroma = _mock_chroma()

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.retrieve_relevant_chunks("mig-001", "query", top_k=5)

        assert result == []


# ── Success tests ─────────────────────────────────────────────────────────


class TestRetrievalSuccess:

    @pytest.mark.asyncio
    async def test_successful_retrieval_returns_results(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma(query_result=SAMPLE_RESULT)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            results = await svc.retrieve_relevant_chunks("mig-001", "UserService", top_k=5)

        assert len(results) == 1
        assert results[0]["chunk_id"] == "c-001"
        assert results[0]["content"] == "public class UserService {}"
        assert results[0]["score"] == pytest.approx(0.12)

    @pytest.mark.asyncio
    async def test_migration_scoped_empty_falls_back_to_global(self):
        """When the migration-scoped query returns empty, a global search is done."""
        svc = _fresh_svc()
        mock_emb = _mock_emb()

        call_count = 0

        async def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            return EMPTY_RESULT if call_count == 1 else SAMPLE_RESULT

        mock_chroma = MagicMock()
        mock_chroma.is_initialized = True
        mock_chroma.query = mock_query

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            results = await svc.retrieve_relevant_chunks("mig-999", "query", top_k=5)

        assert call_count == 2
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_result_schema_keys(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma(query_result=SAMPLE_RESULT)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            results = await svc.retrieve_relevant_chunks("mig-001", "query", top_k=5)

        for r in results:
            assert "chunk_id" in r
            assert "content" in r
            assert "metadata" in r
            assert "score" in r


class TestRetrieveForChunks:

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_empty(self):
        svc = _fresh_svc()
        result = await svc.retrieve_for_chunks("mig-001", [], top_k=3)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_plain_text_list(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma(query_result=SAMPLE_RESULT)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            chunks = [{"content": "public class Foo {}", "file_name": "Foo.cs"}]
            result = await svc.retrieve_for_chunks("mig-001", chunks, top_k=3)

        assert isinstance(result, list)
        assert all(isinstance(r, str) for r in result)


# ── Helper function tests ──────────────────────────────────────────────────


class TestFlattenChromaResults:

    def test_basic_flatten(self):
        raw = _mock_chroma_result(
            ids=["a", "b"],
            docs=["doc A", "doc B"],
            metas=[{"chunk_id": "a"}, {"chunk_id": "b"}],
            distances=[0.1, 0.3],
        )
        results = _flatten_chroma_results(raw)
        assert len(results) == 2
        assert results[0]["content"] == "doc A"
        assert results[1]["score"] == pytest.approx(0.3)

    def test_empty_result(self):
        results = _flatten_chroma_results(EMPTY_RESULT)
        assert results == []

    def test_chunk_id_falls_back_to_doc_id(self):
        raw = _mock_chroma_result(
            ids=["doc-xyz"],
            docs=["some code"],
            metas=[{}],
            distances=[0.5],
        )
        results = _flatten_chroma_results(raw)
        assert results[0]["chunk_id"] == "doc-xyz"
