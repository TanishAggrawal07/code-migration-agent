"""
Tests for MigrationAgent (M8).

Patching strategy: uses patch.object on GeminiClient.get_instance
since GeminiClient is imported lazily inside run() and _translate_chunk().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import AgentStatus, MigrationAgent, _clean_java_output
from app.core.gemini_client import GeminiClient


# ── Fixtures ──────────────────────────────────────────────────────────────

CS_CHUNK = {
    "chunk_id":   "c-001",
    "file_name":  "UserService.cs",
    "chunk_type": "class",
    "content": (
        "using System;\n"
        "namespace MyApp.Services {\n"
        "    public class UserService {\n"
        "        public string GetUser(int id) { return id.ToString(); }\n"
        "    }\n"
        "}"
    ),
    "start_line": 1,
    "end_line":   7,
}

JAVA_CONTEXT = [
    "// Java pattern: Spring @Service replaces C# [Service]",
    "// Java pattern: Optional<T> replaces C# Nullable<T>",
]


def _agent() -> MigrationAgent:
    return MigrationAgent()


def _state(chunks=None, context=None, migration_id="test-001"):
    return {
        "chunks":            chunks if chunks is not None else [CS_CHUNK],
        "retrieved_context": context if context is not None else JAVA_CONTEXT,
        "migration_id":      migration_id,
    }


def _mock_gemini(initialized: bool = True, response: str = "public class UserService {}") -> MagicMock:
    m = MagicMock()
    m.is_initialized = initialized
    m.generate_text = AsyncMock(return_value=response)
    return m


# ── _clean_java_output ────────────────────────────────────────────────────


class TestCleanJavaOutput:

    def test_strips_java_fence(self):
        raw = "```java\npublic class Foo {}\n```"
        assert _clean_java_output(raw) == "public class Foo {}"

    def test_strips_generic_fence(self):
        raw = "```\npublic class Bar {}\n```"
        assert _clean_java_output(raw) == "public class Bar {}"

    def test_no_fence_unchanged(self):
        code = "public class Baz {}"
        assert _clean_java_output(code) == code

    def test_strips_surrounding_whitespace(self):
        assert _clean_java_output("  \npublic class X {}\n  ") == "public class X {}"


# ── _make_stub ────────────────────────────────────────────────────────────


class TestMakeStub:

    def test_uses_class_name_from_source(self):
        agent = _agent()
        stub = agent._make_stub(CS_CHUNK["content"], "UserService.cs")
        assert "UserService" in stub

    def test_stub_contains_spring_annotation(self):
        # The stub only includes Spring annotations for webapi/mvc project types.
        # The test must pass the matching project_type to _make_stub.
        agent = _agent()
        stub = agent._make_stub(CS_CHUNK["content"], "UserService.cs", project_type="webapi")
        assert "@Service" in stub

    def test_stub_contains_original_source_commented(self):
        agent = _agent()
        stub = agent._make_stub("public class Foo {}", "Foo.cs")
        assert "public class Foo {}" in stub

    def test_fallback_name_from_filename(self):
        agent = _agent()
        stub = agent._make_stub("void helper() {}", "Helper.cs")
        assert "Helper" in stub


# ── _build_prompt ─────────────────────────────────────────────────────────


class TestBuildPrompt:

    def test_prompt_contains_system_message(self):
        # System prompts now start with the CRITICAL CONSTRAINTS header.
        agent = _agent()
        prompt = agent._build_prompt("public class Foo {}", "")
        assert "DETERMINISTIC SOURCE-TO-SOURCE MIGRATION TOOL" in prompt

    def test_prompt_contains_source(self):
        agent = _agent()
        prompt = agent._build_prompt("public class Foo {}", "")
        assert "public class Foo {}" in prompt

    def test_prompt_contains_context_when_provided(self):
        agent = _agent()
        prompt = agent._build_prompt("public class Foo {}", "// Java hint: use @Service")
        assert "// Java hint: use @Service" in prompt

    def test_prompt_excludes_context_block_when_empty(self):
        agent = _agent()
        prompt = agent._build_prompt("public class Foo {}", "")
        assert "Reference Java/Spring patterns" not in prompt


# ── run() — Gemini unavailable (stub mode) ────────────────────────────────


class TestMigrationAgentStubMode:

    @pytest.mark.asyncio
    async def test_stub_mode_returns_success(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        assert result.status == AgentStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_stub_mode_generates_java_file(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        files = result.data.get("generated_files", [])
        assert len(files) >= 1
        assert files[0]["filename"].endswith(".java")

    @pytest.mark.asyncio
    async def test_stub_mode_model_is_stub(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        migration_results = result.data.get("migration_results", [])
        assert all(r["model"] == "stub" for r in migration_results)

    @pytest.mark.asyncio
    async def test_empty_chunks_produces_fallback_file(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state(chunks=[]))

        files = result.data.get("generated_files", [])
        assert len(files) == 1
        assert files[0]["filename"] == "Migration.java"


# ── run() — Gemini available ──────────────────────────────────────────────


class TestMigrationAgentGeminiMode:

    @pytest.mark.asyncio
    async def test_gemini_output_used_as_java_code(self):
        agent = _agent()
        java_response = (
            "import org.springframework.stereotype.Service;\n"
            "@Service\npublic class UserService {}"
        )
        mock_gemini = _mock_gemini(initialized=True, response=java_response)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        migration_results = result.data.get("migration_results", [])
        assert any(java_response in r["java_code"] for r in migration_results)

    @pytest.mark.asyncio
    async def test_gemini_exception_falls_back_to_stub(self):
        agent = _agent()
        mock_gemini = MagicMock()
        mock_gemini.is_initialized = True
        mock_gemini.generate_text = AsyncMock(side_effect=Exception("API error"))

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        assert result.status == AgentStatus.SUCCESS
        migration_results = result.data.get("migration_results", [])
        assert all(r["model"] == "stub-fallback" for r in migration_results)

    @pytest.mark.asyncio
    async def test_gemini_strips_markdown_fences(self):
        agent = _agent()
        fenced_response = "```java\npublic class Clean {}\n```"
        mock_gemini = _mock_gemini(initialized=True, response=fenced_response)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        migration_results = result.data.get("migration_results", [])
        assert all("```" not in r["java_code"] for r in migration_results)


# ── Result schema ─────────────────────────────────────────────────────────


class TestMigrationAgentResultSchema:

    @pytest.mark.asyncio
    async def test_result_data_keys(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        assert "migration_results" in result.data
        assert "generated_files" in result.data
        assert "gemini_available" in result.data

    @pytest.mark.asyncio
    async def test_migration_result_schema(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        for mr in result.data.get("migration_results", []):
            assert "source_chunk_id" in mr
            assert "java_code" in mr
            assert "model" in mr
            assert "tokens_used" in mr
            assert "source_file" in mr

    @pytest.mark.asyncio
    async def test_generated_file_schema(self):
        agent = _agent()
        mock_gemini = _mock_gemini(initialized=False)

        with patch.object(GeminiClient, "get_instance", return_value=mock_gemini):
            result = await agent.run(_state())

        for gf in result.data.get("generated_files", []):
            assert "filename" in gf
            assert "path" in gf
            assert "source_file" in gf
            assert "compile_success" in gf
            assert "content_preview" in gf
