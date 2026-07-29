# Agentic Workflow Specification (`agentic_workflow.md`)

## Overview

The migration pipeline is an AI-driven, multi-agent orchestration workflow implemented using **LangGraph** (`StateGraph` state machine in `backend/app/agents/workflow.py`). It coordinates 7 graph execution nodes and 14 pipeline stages to transform .NET (C#) codebases into production-ready Java (Spring Boot 3 / Quarkus) applications.

---

## 🔄 Complete 14-Stage Migration Pipeline Diagram

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  1. Upload   ├─────►│  2. Parser   ├─────►│ 3. Analyzer  ├─────►│4. Embeddings │
└──────────────┘      └──────────────┘      └──────────────┘      └──────┬───────┘
                                                                         │
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────▼───────┐
│ 8. Chunk     │◄─────┤ 7. Adaptive  │◄─────┤    6. RAG    │◄─────┤ 5. ChromaDB  │
│  Fallback    │      │  Full-File   │      │  Retrieval   │      │ Persistence  │
└──────┬───────┘      └──────────────┘      └──────────────┘      └──────────────┘
       │
       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│9. Structural │─────►│10. Semantic  ├─────►│ 11. Compile  ├─────►│ 12. Compile  │
│ Verification │      │ Verification │      │ Node & Fixes │      │ Repair Loop  │
└──────────────┘      └──────────────┘      └──────────────┘      └──────┬───────┘
                                                                         │
                                            ┌──────────────┐      ┌──────▼───────┐
                                            │ 14. Download │◄─────┤   13. Save   │
                                            └──────────────┘      └──────────────┘
```

---

## 🧩 LangGraph Execution Nodes (`workflow.py`)

### 1. `_parser_node` (Parser Agent Stage)
- **Input**: Source `.cs` files stored in `storage/uploads/{migration_id}/`.
- **Logic**: Invokes `TreeSitterService` to parse C# AST structures. If C++ native bindings are absent, falls back to the regex parser engine.
- **Output**: Populates `MigrationState.parsed_files` with class declarations, namespaces, method signatures, and statements.

### 2. `_analyzer_node` (Analyzer Agent Stage)
- **Logic**: Constructs a structural dependency graph across all parsed files. Extracts namespaces, imports (`using` directives), class hierarchies, interfaces, and field declarations.
- **Output**: Populates `MigrationState.analysis`.

### 3. `_embedding_node` (Vector Embedding Generation Stage)
- **Logic**: Invokes `EmbeddingService` (`SentenceTransformers("all-MiniLM-L6-v2")`) to convert parsed code chunks and structural summaries into 384-dimensional dense vector embeddings.
- **Output**: Sets `MigrationState.embeddings_created = True`.

### 4. `_rag_node` (RAG Context Retrieval Stage)
- **Logic**: Queries ChromaDB vector collection (`migration_docs`) for semantically similar C# chunks and Java migration patterns. Augments retrieved context with static translation rules (e.g. C# `[Service]` → Spring `@Service`).
- **Output**: Populates `MigrationState.retrieved_context`.

### 5. `_migration_node` (Adaptive LLM Code Generation Stage)
- **Logic**: Executes LLM code generation via the active provider in `llm_providers.py` (Groq `llama-3.3-70b-versatile`, Gemini 2.5 Flash, Ollama, OpenRouter, Grok, or OpenAI).
- **Adaptive Fallback**:
  - **Primary**: Full-File Migration constructing a unified prompt with complete class context.
  - **Fallback**: Intelligent Chunk Fallback splitting massive files into independent method chunks when context windows are exceeded.
- **Output**: Populates `MigrationState.generated_java_files` and `context["generated_file_contents"]`.

### 6. `_compile_node` (Java Post-Processing & Validation Stage)
- **Logic**:
  1. `clean_and_merge_java_source()` cleans markdown fences and merges duplicate class declarations.
  2. Parses `package` declarations (e.g. `package com.myapp.services;`) and formats package-based paths (`com/myapp/services/CalculatorService.java`).
  3. `setup_mock_dependencies()` generates mock stub interfaces for Lombok, SLF4J, and Spring annotations.
  4. Invokes `javac` compiler for syntax validation. If `javac` is not installed on the system, cleanly logs a notice and skips bytecode compilation without breaking the workflow.
- **Compile Repair Loop**: If syntax errors occur, `repair_java_code()` triggers up to 3 automatic LLM repair retries to fix syntax errors.

### 7. `_save_node` (Persistence & Export Stage)
- **Logic**: Writes validated Java source files to `storage/generated/{migration_id}/` and advances `MigrationState.current_stage` to `saved`.

---

## 📡 Progress Tracking & Log Streaming

The web frontend (`frontend/src/components/log-panel.tsx` and `migration-stepper.tsx`) polls `GET /api/migrations/{id}` every 3 seconds to render:
- **Progress Bar**: Computed progress percentage (`0%` → `100%`).
- **Log Streamer**: Terminal-style live view displaying structured timestamps, log levels (`INFO`, `WARNING`, `SUCCESS`, `ERROR`), and node messages.
