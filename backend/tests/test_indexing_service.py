"""
Tests for IndexingService (M6).

Patching strategy: services are imported lazily inside index_chunks()
so we patch the singleton get_instance class method directly on the
class objects (which are always importable at module level).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.vectorstore.indexing_service import IndexingResult, IndexingService, _guess_class_name
from app.embeddings.service import EmbeddingService
from app.vectorstore.chroma_service import ChromaService


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_CHUNKS = [
    {
        "chunk_id":   "chunk-001",
        "file_name":  "UserService.cs",
        "chunk_type": "class",
        "content":    "public class UserService { public void GetUser() {} }",
        "start_line": 1,
        "end_line":   5,
    },
    {
        "chunk_id":   "chunk-002",
        "file_name":  "OrderService.cs",
        "chunk_type": "method",
        "content":    "public Order PlaceOrder(int id) { return new Order(); }",
        "start_line": 10,
        "end_line":   15,
    },
]

SAMPLE_ANALYSIS = {
    "namespace":    "MyApp.Services",
    "classes":      ["UserService", "OrderService"],
    "methods":      ["GetUser", "PlaceOrder"],
    "imports":      ["System"],
    "interfaces":   [],
    "dependencies": [],
    "file_count":   2,
    "total_lines":  50,
}


def _fresh_svc() -> IndexingService:
    IndexingService._instance = None
    return IndexingService.get_instance()


def _mock_emb(loaded: bool = True) -> MagicMock:
    m = MagicMock()
    m.is_loaded = loaded
    m.generate_embeddings = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    return m


def _mock_chroma(initialized: bool = True) -> MagicMock:
    m = MagicMock()
    m.is_initialized = initialized
    m.add_documents = AsyncMock(return_value=True)
    return m


# ── Unit tests ────────────────────────────────────────────────────────────


class TestIndexingServiceDegradation:

    @pytest.mark.asyncio
    async def test_no_embedding_service_returns_degraded(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb(loaded=False)
        mock_chroma = _mock_chroma(initialized=True)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.index_chunks("mig-001", SAMPLE_CHUNKS, SAMPLE_ANALYSIS)

        assert result.mode == "degraded"
        assert result.indexed == 0

    @pytest.mark.asyncio
    async def test_no_chroma_returns_degraded(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb(loaded=True)
        mock_chroma = _mock_chroma(initialized=False)

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.index_chunks("mig-002", SAMPLE_CHUNKS, SAMPLE_ANALYSIS)

        assert result.mode == "degraded"

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_live(self):
        svc = _fresh_svc()
        result = await svc.index_chunks("mig-003", [], SAMPLE_ANALYSIS)
        assert result.indexed == 0
        assert result.mode == "live"


class TestIndexingServiceSuccess:

    @pytest.mark.asyncio
    async def test_successful_indexing_returns_live_mode(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma()

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.index_chunks("mig-004", SAMPLE_CHUNKS, SAMPLE_ANALYSIS)

        assert result.mode == "live"
        assert result.indexed == 2
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_chunks_missing_content_are_skipped(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_emb.generate_embeddings = AsyncMock(return_value=[[0.1] * 384])
        mock_chroma = _mock_chroma()

        bad_chunks = [
            {"chunk_id": "good-001", "file_name": "A.cs", "chunk_type": "class",
             "content": "public class A {}", "start_line": 1, "end_line": 3},
            {"chunk_id": "", "file_name": "B.cs", "chunk_type": "class",
             "content": "public class B {}", "start_line": 1, "end_line": 3},
            {"chunk_id": "bad-001", "file_name": "C.cs", "chunk_type": "class",
             "content": "   ", "start_line": 1, "end_line": 1},
        ]

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.index_chunks("mig-005", bad_chunks, {})

        assert result.indexed == 1
        assert result.skipped == 2

    @pytest.mark.asyncio
    async def test_metadata_passed_to_chroma(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_chroma = _mock_chroma()

        captured_meta: dict = {}

        async def capture_add(documents, embeddings, metadatas, ids):
            captured_meta["metadatas"] = metadatas
            return True

        mock_chroma.add_documents = capture_add

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            await svc.index_chunks("mig-006", SAMPLE_CHUNKS, SAMPLE_ANALYSIS)

        metas = captured_meta.get("metadatas", [])
        assert len(metas) == 2
        assert metas[0]["migration_id"] == "mig-006"
        assert metas[0]["namespace"] == "MyApp.Services"
        assert metas[0]["chunk_type"] in {"class", "method"}

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_degraded(self):
        svc = _fresh_svc()
        mock_emb = _mock_emb()
        mock_emb.generate_embeddings = AsyncMock(side_effect=RuntimeError("embed fail"))
        mock_chroma = _mock_chroma()

        with patch.object(EmbeddingService, "get_instance", return_value=mock_emb), \
             patch.object(ChromaService, "get_instance", return_value=mock_chroma):
            result = await svc.index_chunks("mig-007", SAMPLE_CHUNKS, SAMPLE_ANALYSIS)

        assert result.mode == "degraded"
        assert result.failed > 0


class TestIndexingResultToDict:

    def test_to_dict_keys(self):
        r = IndexingResult(indexed=5, skipped=1, failed=0, mode="live")
        d = r.to_dict()
        assert d["indexed"] == 5
        assert d["skipped"] == 1
        assert d["failed"] == 0
        assert d["mode"] == "live"


class TestGuessClassName:

    def test_known_class_found_in_content(self):
        result = _guess_class_name("public class UserService {}", ["UserService"])
        assert result == "UserService"

    def test_regex_fallback(self):
        result = _guess_class_name("public class OrderService {}", [])
        assert result == "OrderService"

    def test_no_class_returns_empty(self):
        result = _guess_class_name("void doSomething() {}", [])
        assert result == ""
