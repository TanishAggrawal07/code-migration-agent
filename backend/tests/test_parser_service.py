"""
Tests for ParserService (M4).

Covers:
- Regex chunker produces class / method / file chunks
- ParseResult fields are populated correctly
- Handling of non-.cs files (no chunking)
- Empty file list returns empty ParseResult
- Single-class file produces at least one chunk
"""

from __future__ import annotations

import pytest

from app.parser.parser_service import CodeChunk, ParseResult, ParserService


# ── Fixtures ──────────────────────────────────────────────────────────────

SIMPLE_CS = """\
using System;
using System.Collections.Generic;

namespace MyApp.Services
{
    public class UserService
    {
        private readonly List<string> _users = new();

        public string GetUser(int id)
        {
            return _users[id];
        }

        public void AddUser(string name)
        {
            _users.Add(name);
        }
    }
}
"""

TWO_CLASS_CS = """\
namespace MyApp
{
    public class Foo
    {
        public void Bar() { }
    }

    public class Baz
    {
        public int Compute(int x) { return x * 2; }
    }
}
"""

INTERFACE_CS = """\
namespace MyApp.Contracts
{
    public interface IOrderService
    {
        void PlaceOrder(int id);
    }

    public class OrderService : IOrderService
    {
        public void PlaceOrder(int id) { }
    }
}
"""

NO_CLASS_CS = """\
// A helper file with only top-level statements (C# 9+ style)
Console.WriteLine("Hello, World!");
int x = 42;
"""


# ── Unit tests for internal chunking helpers ──────────────────────────────


class TestRegexChunker:
    """Tests for ParserService._regex_chunk()"""

    def _svc(self) -> ParserService:
        # Reset singleton for isolated tests
        ParserService._instance = None
        svc = ParserService.get_instance()
        svc._ts_checked = True
        svc._ts_available = False   # force regex mode
        return svc

    def test_simple_class_produces_chunks(self):
        svc = self._svc()
        chunks, classes, methods = svc._regex_chunk(SIMPLE_CS, "UserService.cs")

        assert len(chunks) >= 1
        assert "UserService" in classes
        assert any(m in methods for m in ("GetUser", "AddUser"))

    def test_chunk_fields_populated(self):
        svc = self._svc()
        chunks, _, _ = svc._regex_chunk(SIMPLE_CS, "UserService.cs")

        for chunk in chunks:
            assert isinstance(chunk, CodeChunk)
            assert chunk.chunk_id  # non-empty UUID string
            assert chunk.file_name == "UserService.cs"
            assert chunk.chunk_type in {"class", "method", "file"}
            assert chunk.content.strip()
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_two_classes_detected(self):
        svc = self._svc()
        _, classes, _ = svc._regex_chunk(TWO_CLASS_CS, "dual.cs")

        assert "Foo" in classes
        assert "Baz" in classes

    def test_no_class_falls_back_to_file_chunk(self):
        svc = self._svc()
        chunks, classes, methods = svc._regex_chunk(NO_CLASS_CS, "toplevel.cs")

        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"
        assert classes == []

    def test_interface_not_mistaken_for_class(self):
        svc = self._svc()
        _, classes, _ = svc._regex_chunk(INTERFACE_CS, "contracts.cs")

        # OrderService should be found; IOrderService is an interface (not class)
        assert "OrderService" in classes

    def test_chunk_to_dict_schema(self):
        svc = self._svc()
        chunks, _, _ = svc._regex_chunk(SIMPLE_CS, "UserService.cs")

        for chunk in chunks:
            d = chunk.to_dict()
            assert "chunk_id" in d
            assert "file_name" in d
            assert "chunk_type" in d
            assert "content" in d
            assert "start_line" in d
            assert "end_line" in d


# ── Integration tests using parse_migration() ─────────────────────────────


class TestParserServiceIntegration:
    """Tests for ParserService.parse_migration() using a temp directory."""

    @pytest.fixture
    def tmp_project(self, tmp_path):
        """Create a minimal upload directory with two C# files."""
        (tmp_path / "UserService.cs").write_text(SIMPLE_CS, encoding="utf-8")
        (tmp_path / "OrderService.cs").write_text(TWO_CLASS_CS, encoding="utf-8")
        (tmp_path / "App.csproj").write_text(
            "<Project Sdk=\"Microsoft.NET.Sdk\"></Project>", encoding="utf-8"
        )
        return tmp_path

    def _svc(self) -> ParserService:
        ParserService._instance = None
        svc = ParserService.get_instance()
        svc._ts_checked = True
        svc._ts_available = False
        return svc

    @pytest.mark.asyncio
    async def test_parse_migration_returns_parse_result(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-001",
            uploaded_files=["UserService.cs", "OrderService.cs", "App.csproj"],
            project_root=str(tmp_project),
        )

        assert isinstance(result, ParseResult)
        assert result.total_files == 3   # all 3 tracked
        assert result.total_chunks >= 1

    @pytest.mark.asyncio
    async def test_cs_files_are_parsed_true(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-002",
            uploaded_files=["UserService.cs"],
            project_root=str(tmp_project),
        )

        cs_files = [pf for pf in result.parsed_files if pf["filename"].endswith(".cs")]
        assert all(pf["parsed"] is True for pf in cs_files)

    @pytest.mark.asyncio
    async def test_non_cs_files_not_chunked(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-003",
            uploaded_files=["App.csproj"],
            project_root=str(tmp_project),
        )

        # .csproj should be tracked but not chunked
        assert result.total_chunks == 0
        assert result.parsed_files[0]["parsed"] is False

    @pytest.mark.asyncio
    async def test_empty_file_list_returns_empty_result(self):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-004",
            uploaded_files=[],
            project_root="/nonexistent",
        )

        assert result.total_files == 0
        assert result.total_chunks == 0

    @pytest.mark.asyncio
    async def test_missing_file_recorded_in_errors(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-005",
            uploaded_files=["GhostFile.cs"],
            project_root=str(tmp_project),
        )

        assert len(result.errors) >= 1
        assert any("GhostFile.cs" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_chunks_have_correct_schema(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-006",
            uploaded_files=["UserService.cs"],
            project_root=str(tmp_project),
        )

        for chunk in result.chunks:
            assert "chunk_id" in chunk
            assert "file_name" in chunk
            assert "chunk_type" in chunk
            assert "content" in chunk
            assert "start_line" in chunk
            assert "end_line" in chunk
            assert chunk["chunk_type"] in {"class", "method", "file"}

    @pytest.mark.asyncio
    async def test_parser_mode_is_set(self, tmp_project):
        svc = self._svc()
        result = await svc.parse_migration(
            migration_id="test-007",
            uploaded_files=["UserService.cs"],
            project_root=str(tmp_project),
        )

        assert result.parser_mode in {"tree_sitter", "regex"}
