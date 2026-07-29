"""
Tests for AnalyzerService (M5).

Covers:
- Namespace extraction
- Using/import extraction
- Class name extraction
- Interface detection
- Method extraction
- Dependency derivation
- Consolidated analysis output schema
- Empty input returns empty but valid analysis
"""

from __future__ import annotations

import pytest

from app.analyzer.analyzer_service import AnalyzerService, _dedup, _primary_namespace


# ── Sample source ─────────────────────────────────────────────────────────

FULL_CS = """\
using System;
using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;
using AutoMapper;
using Serilog;

namespace MyApp.Services
{
    public interface IUserService
    {
        Task<User> GetUserAsync(int id);
    }

    public class UserService : IUserService, IDisposable
    {
        private readonly AppDbContext _db;
        private readonly IMapper _mapper;

        public UserService(AppDbContext db, IMapper mapper)
        {
            _db = db;
            _mapper = mapper;
        }

        public async Task<User> GetUserAsync(int id)
        {
            return await _db.Users.FindAsync(id);
        }

        public async Task<List<User>> GetAllUsersAsync()
        {
            return await _db.Users.ToListAsync();
        }

        public void Dispose()
        {
            _db.Dispose();
        }
    }
}
"""

NAMESPACE_ONLY_CS = """\
namespace Acme.Core.Utilities;

public class Helper { }
"""

EMPTY_CS = ""


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_chunks(content: str, file_name: str = "Test.cs") -> list[dict]:
    return [{
        "chunk_id": "test-id",
        "file_name": file_name,
        "chunk_type": "class",
        "content": content,
        "start_line": 1,
        "end_line": content.count("\n") + 1,
    }]


def _make_parsed_files(classes: list[str], methods: list[str], lines: int = 50) -> list[dict]:
    return [{
        "filename": "Test.cs",
        "path": "Test.cs",
        "classes": classes,
        "methods": methods,
        "lines": lines,
        "parsed": True,
    }]


# ── Unit tests for extraction helpers ─────────────────────────────────────


class TestExtractionHelpers:

    def _svc(self) -> AnalyzerService:
        AnalyzerService._instance = None
        return AnalyzerService.get_instance()

    def test_extract_namespaces(self):
        svc = self._svc()
        result = svc._extract_namespaces(FULL_CS)
        assert "MyApp.Services" in result

    def test_extract_imports(self):
        svc = self._svc()
        imports = svc._extract_imports(FULL_CS)
        assert "System" in imports
        assert "System.Collections.Generic" in imports
        assert "Microsoft.EntityFrameworkCore" in imports
        assert "AutoMapper" in imports

    def test_extract_class_names(self):
        svc = self._svc()
        classes = svc._extract_class_names(FULL_CS)
        assert "UserService" in classes

    def test_extract_interfaces(self):
        svc = self._svc()
        interfaces = svc._extract_interfaces(FULL_CS)
        assert "IUserService" in interfaces

    def test_extract_methods(self):
        svc = self._svc()
        methods = svc._extract_methods(FULL_CS)
        # At least some methods should be detected
        assert len(methods) >= 1

    def test_extract_base_classes(self):
        svc = self._svc()
        bases = svc._extract_base_classes(FULL_CS)
        # IUserService and IDisposable appear in the base list of UserService
        assert len(bases) >= 1

    def test_derive_dependencies_known_libs(self):
        svc = self._svc()
        imports = [
            "Microsoft.EntityFrameworkCore",
            "AutoMapper",
            "Serilog",
            "System.Linq",
        ]
        deps = svc._derive_dependencies(imports, [])
        # Microsoft.EntityFrameworkCore → Microsoft.EntityFrameworkCore
        assert any("Microsoft" in d for d in deps)
        assert any("AutoMapper" in d for d in deps)
        assert any("Serilog" in d for d in deps)

    def test_extract_file_scoped_namespace(self):
        svc = self._svc()
        ns = svc._extract_namespaces(NAMESPACE_ONLY_CS)
        assert "Acme.Core.Utilities" in ns


# ── Integration tests for analyze_chunks() ────────────────────────────────


class TestAnalyzerServiceIntegration:

    def _svc(self) -> AnalyzerService:
        AnalyzerService._instance = None
        return AnalyzerService.get_instance()

    @pytest.mark.asyncio
    async def test_full_analysis_schema(self):
        svc = self._svc()
        chunks = _make_chunks(FULL_CS)
        parsed_files = _make_parsed_files(["UserService"], ["GetUserAsync", "Dispose"])

        result = await svc.analyze_chunks(chunks, parsed_files)

        # All required keys present
        assert "classes" in result
        assert "methods" in result
        assert "imports" in result
        assert "interfaces" in result
        assert "dependencies" in result
        assert "namespace" in result
        assert "file_count" in result
        assert "total_lines" in result

    @pytest.mark.asyncio
    async def test_classes_found(self):
        svc = self._svc()
        chunks = _make_chunks(FULL_CS)
        result = await svc.analyze_chunks(chunks, [])
        assert "UserService" in result["classes"]

    @pytest.mark.asyncio
    async def test_interfaces_found(self):
        svc = self._svc()
        chunks = _make_chunks(FULL_CS)
        result = await svc.analyze_chunks(chunks, [])
        assert "IUserService" in result["interfaces"]

    @pytest.mark.asyncio
    async def test_namespace_detected(self):
        svc = self._svc()
        chunks = _make_chunks(FULL_CS)
        result = await svc.analyze_chunks(chunks, [])
        assert result["namespace"] == "MyApp.Services"

    @pytest.mark.asyncio
    async def test_imports_detected(self):
        svc = self._svc()
        chunks = _make_chunks(FULL_CS)
        result = await svc.analyze_chunks(chunks, [])
        assert "System" in result["imports"]
        assert "Microsoft.EntityFrameworkCore" in result["imports"]

    @pytest.mark.asyncio
    async def test_file_count_from_parsed_files(self):
        svc = self._svc()
        parsed_files = _make_parsed_files(["Foo"], ["Bar"]) + _make_parsed_files(["Baz"], ["Qux"])
        result = await svc.analyze_chunks([], parsed_files)
        assert result["file_count"] == 2

    @pytest.mark.asyncio
    async def test_total_lines_summed(self):
        svc = self._svc()
        pf1 = {"filename": "A.cs", "path": "A.cs", "classes": [], "methods": [], "lines": 100, "parsed": True}
        pf2 = {"filename": "B.cs", "path": "B.cs", "classes": [], "methods": [], "lines": 200, "parsed": True}
        result = await svc.analyze_chunks([], [pf1, pf2])
        assert result["total_lines"] == 300

    @pytest.mark.asyncio
    async def test_empty_input_returns_valid_schema(self):
        svc = self._svc()
        result = await svc.analyze_chunks([], [])

        assert result["classes"] == []
        assert result["methods"] == []
        assert result["imports"] == []
        assert result["interfaces"] == []
        assert result["dependencies"] == []
        assert result["namespace"] == ""
        assert result["file_count"] == 0
        assert result["total_lines"] == 0

    @pytest.mark.asyncio
    async def test_no_duplicate_classes(self):
        """Same class appearing in multiple chunks should not be duplicated."""
        svc = self._svc()
        chunk_a = _make_chunks(FULL_CS, "A.cs")[0]
        chunk_b = _make_chunks(FULL_CS, "B.cs")[0]   # same content, different file
        result = await svc.analyze_chunks([chunk_a, chunk_b], [])
        assert result["classes"].count("UserService") == 1

    @pytest.mark.asyncio
    async def test_parsed_file_classes_merged(self):
        """Classes in parsed_files metadata but not in chunks should still appear."""
        svc = self._svc()
        parsed_files = _make_parsed_files(["ExtraClass"], [])
        result = await svc.analyze_chunks([], parsed_files)
        assert "ExtraClass" in result["classes"]


# ── Helper function tests ──────────────────────────────────────────────────


class TestHelperFunctions:

    def test_dedup_preserves_order(self):
        result = _dedup(["b", "a", "b", "c", "a"])
        assert result == ["b", "a", "c"]

    def test_dedup_strips_whitespace(self):
        result = _dedup(["  foo  ", "bar", "foo"])
        assert result == ["foo", "bar"]

    def test_dedup_empty(self):
        assert _dedup([]) == []

    def test_primary_namespace_shortest(self):
        ns = _primary_namespace(["MyApp.Services.Users", "MyApp.Services", "MyApp"])
        assert ns == "MyApp"

    def test_primary_namespace_empty(self):
        assert _primary_namespace([]) == ""

    def test_primary_namespace_single(self):
        assert _primary_namespace(["Acme.Core"]) == "Acme.Core"
