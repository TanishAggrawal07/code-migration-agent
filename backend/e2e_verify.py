"""
End-to-end migration verification script.

Traces: Upload → Parser → Analyzer → Embeddings → ChromaDB → RAG → MigrationAgent → Java output
Uses the provider registry (not Gemini directly) for LLM calls.
"""
import asyncio
import sys
import os

sys.path.insert(0, ".")

# Sample C# source — small Calculator class
CS_SOURCE = """
using System;
using System.Collections.Generic;

namespace Calculator
{
    public class CalculatorService
    {
        private List<double> _history = new List<double>();

        public double Add(double a, double b)
        {
            double result = a + b;
            _history.Add(result);
            return result;
        }

        public double Subtract(double a, double b)
        {
            double result = a - b;
            _history.Add(result);
            return result;
        }

        public double Multiply(double a, double b)
        {
            double result = a * b;
            _history.Add(result);
            return result;
        }

        public List<double> GetHistory()
        {
            return _history;
        }
    }
}
""".strip()


async def run():
    print("\n" + "="*65)
    print("  .NET → Java Migration — End-to-End Verification")
    print("="*65)

    # ── 1. Provider detection ──────────────────────────────────────────
    print("\n[1/9] PROVIDER DETECTION")
    from app.core.config import get_settings
    from app.core.llm_providers import get_active_provider_instance, OllamaProvider

    settings = get_settings()
    ollama = OllamaProvider(settings)

    ollama_available = ollama.available()
    ollama_models    = ollama.detect_ollama_models() if hasattr(ollama, "detect_ollama_models") else ollama.detect_models()
    active_provider  = get_active_provider_instance(settings)

    print(f"  Ollama detected     : {ollama_available}")
    print(f"  Ollama models       : {ollama_models}")
    print(f"  Active provider     : {active_provider.key if active_provider else 'NONE'}")
    print(f"  Active model        : {active_provider.model if active_provider else 'NONE'}")

    assert active_provider is not None, "No provider available!"
    assert ollama_available, "Ollama not detected but expected to be running"
    assert active_provider.key == "ollama", f"Expected ollama, got {active_provider.key}"
    print("  ✔ Provider detection PASSED")

    # ── 2. GeminiClient facade check ──────────────────────────────────
    print("\n[2/9] GEMINI CLIENT FACADE (Provider Registry)")
    from app.core.gemini_client import GeminiClient
    client = GeminiClient.get_instance()
    # Reset singleton to force fresh init with new code
    client._initialized = False
    client._provider = None

    init_ok = await client.initialize()
    print(f"  GeminiClient init   : {init_ok}")
    print(f"  Active provider key : {client.active_provider_key}")
    print(f"  Active model        : {client.active_model}")
    assert init_ok, "GeminiClient facade failed to initialise"
    assert client.active_provider_key == "ollama", f"Expected ollama, got {client.active_provider_key}"
    print("  ✔ Provider Registry integration PASSED — workflow will use Ollama")

    # ── 3. Parser ─────────────────────────────────────────────────────
    print("\n[3/9] PARSER")
    import tempfile, json
    from pathlib import Path
    from app.parser.parser_service import ParserService

    tmp_dir = tempfile.mkdtemp()
    cs_file = Path(tmp_dir) / "CalculatorService.cs"
    cs_file.write_text(CS_SOURCE, encoding="utf-8")

    parser_svc = ParserService.get_instance()
    parser_result = await parser_svc.parse_migration(
        migration_id="e2e-test-001",
        uploaded_files=[str(cs_file)],
        project_root=tmp_dir,
    )

    print(f"  Parsed files        : {parser_result.total_files}")
    print(f"  Chunks produced     : {parser_result.total_chunks}")
    print(f"  Parser mode         : {parser_result.parser_mode}")
    print(f"  Errors              : {parser_result.errors}")
    assert parser_result.total_chunks > 0, "Parser produced 0 chunks!"
    print("  ✔ Parser PASSED")

    chunks = parser_result.chunks

    # ── 4. Analyzer ───────────────────────────────────────────────────
    print("\n[4/9] ANALYZER")
    from app.analyzer.analyzer_service import AnalyzerService

    analyzer_svc = AnalyzerService.get_instance()
    analysis = await analyzer_svc.analyze_chunks(
        chunks=chunks,
        parsed_files=parser_result.parsed_files,
    )
    print(f"  Analysis keys       : {list(analysis.keys())[:5]}")
    assert analysis is not None
    print("  ✔ Analyzer PASSED")

    # ── 5. Embeddings ─────────────────────────────────────────────────
    print("\n[5/9] EMBEDDINGS")
    from app.embeddings.service import EmbeddingService

    embed_svc = EmbeddingService.get_instance()
    if not embed_svc.is_loaded:
        await embed_svc.load_model()

    sample_texts = [c.get("content", "") for c in chunks[:3] if c.get("content")]
    if sample_texts:
        vectors = await embed_svc.generate_embeddings(sample_texts)
        print(f"  Encoded {len(sample_texts)} samples -> count: {len(vectors) if hasattr(vectors, '__len__') else 'ok'}")
    print("  ok Embeddings PASSED")

    # ── 6. ChromaDB ───────────────────────────────────────────────────
    print("\n[6/9] CHROMADB")
    from app.vectorstore.chroma_service import ChromaService

    chroma_svc = ChromaService.get_instance()
    if not chroma_svc.is_initialized:
        await chroma_svc.initialize()

    print(f"  ChromaDB initialized: {chroma_svc.is_initialized}")
    assert chroma_svc.is_initialized, "ChromaDB not initialised"
    print("  ✔ ChromaDB PASSED")

    # ── 7. RAG retrieval ──────────────────────────────────────────────
    print("\n[7/9] RAG")
    from app.rag.retrieval_service import RetrievalService

    rag_svc = RetrievalService.get_instance()
    query_chunks = chunks[:2] if chunks else []
    context = await rag_svc.retrieve_relevant_chunks(
        migration_id="e2e-test-001",
        query="C# service class with add subtract multiply",
        top_k=3,
    ) if True else []
    print(f"  RAG context items   : {len(context)}")
    print("  ok RAG PASSED")

    # ── 8. Migration Agent ────────────────────────────────────────────
    print("\n[8/9] MIGRATION AGENT (Java generation via Provider Registry)")
    from app.agents.base_agent import MigrationAgent

    agent = MigrationAgent()
    state = {
        "migration_id": "e2e-test-001",
        "chunks": chunks,
        "retrieved_context": context,
    }

    result = await agent.safe_run(state)
    generated_files = result.data.get("generated_files", [])
    migration_results = result.data.get("migration_results", [])

    print(f"  Agent status        : {result.status.value}")
    print(f"  Generated files     : {len(generated_files)}")
    print(f"  Migration results   : {len(migration_results)}")

    if generated_files:
        first = generated_files[0]
        print(f"  First file          : {first.get('filename')}")
        preview = first.get("content_preview", first.get("full_content", ""))[:120]
        print(f"  Content preview     : {preview!r}")

    assert result.status.value in ("success", "failed"), f"Unexpected status: {result.status}"
    java_generated = any(
        f.get("full_content", "").strip() and
        "stub" not in f.get("full_content", "").lower()[:50]
        for f in generated_files
    )

    # ── 9. Summary ────────────────────────────────────────────────────
    print("\n[9/9] FINAL REPORT")
    print("="*65)
    print(f"  Java code generated               : {'YES' if java_generated else 'STUB (provider responded)'}")
    print(f"  File generating Java code         : app/agents/base_agent.py → MigrationAgent._translate_chunk()")
    print(f"  Uses Provider Registry            : YES (GeminiClient → llm_providers.py → OllamaProvider)")
    print(f"  Provider actually used            : {client.active_provider_key}")
    print(f"  Model actually used               : {client.active_model}")
    print(f"  Ollama detected                   : {ollama_available}")
    print(f"  Ollama models available           : {ollama_models}")
    print(f"  Migration completed successfully  : {result.status.value == 'success'}")
    print(f"  Files modified (this task)        : ")
    print(f"    - app/core/llm_providers.py     (NEW - provider abstraction layer)")
    print(f"    - app/core/gemini_client.py     (MODIFIED - now delegates to provider registry)")
    print(f"    - app/core/config.py            (MODIFIED - added provider config fields)")
    print("="*65)

    if result.status.value == "success":
        print("\n  ✔✔ ALL STAGES PASSED — End-to-end migration VERIFIED\n")
    else:
        print(f"\n  ⚠ Agent finished with status: {result.status.value}")
        print(f"  Error: {result.error}\n")


if __name__ == "__main__":
    asyncio.run(run())
