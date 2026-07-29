# Migration Workflow Specification

## Overview

The migration pipeline is implemented as a 14-stage process managed by a **LangGraph StateGraph** machine. The workflow accepts .NET (C#) codebases and transforms them into structured Java (Spring Boot / Quarkus) applications.

---

## 🔄 Complete 14-Stage Migration Flow Diagram

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

## 📋 Detailed Stage Breakdown

### Stage 1: Upload (`POST /api/migrations/{id}/upload`)
- **Input**: Single `.cs` source file or `.zip` project archive.
- **Process**: `UploadValidator` verifies file sizes and extensions. `ZipExtractor` decompresses `.zip` files while ignoring binaries and node modules. Files are persisted under `storage/uploads/{migration_id}/`.

### Stage 2: Parser Node (`_parser_node`)
- **Engine**: Tree-sitter AST parser with regex fallback.
- **Process**: Parses C# source files into code chunks. Extracts syntax nodes (class declarations, method signatures, properties, namespace declarations).

### Stage 3: Analyzer Node (`_analyzer_node`)
- **Process**: Performs structural analysis across parsed code chunks. Inventories classes, methods, fields, interfaces, and framework dependencies (`using` directives, NuGet references). Updates `MigrationState.analysis`.

### Stage 4: Embeddings Node (`_embedding_node`)
- **Engine**: SentenceTransformers (`all-MiniLM-L6-v2`).
- **Process**: Converts each code chunk and AST summary into 384-dimensional vector embeddings.

### Stage 5: ChromaDB Persistence
- **Engine**: Persistent ChromaDB client (`storage/chroma_db/`).
- **Process**: Stores chunk vectors, document text, and metadata in the `migration_docs` collection under the current `migration_id`.

### Stage 6: RAG Retrieval Node (`_rag_node`)
- **Engine**: Semantic similarity search in ChromaDB.
- **Process**: Queries ChromaDB for top-5 contextually matching rules and code snippets. Complements search results with framework translation rules (e.g. C# `[Service]` → Java `@Service`).

### Stage 7: Adaptive Full-File Migration (`_migration_node`)
- **Engine**: Configured LLM Provider (Ollama / Groq / Gemini / OpenRouter / Grok / OpenAI).
- **Process**: Attempts full-file migration by constructing an augmented prompt containing context, AST metadata, and target framework guidelines.

### Stage 8: Intelligent Chunk Fallback
- **Trigger**: Activated if a source file exceeds the active model's context window.
- **Process**: Splits the file into logical structural chunks, migrates each chunk independently, and reassembles the class structure.

### Stage 9: Structural Verification
- **Engine**: `java_post_processor.py` (`clean_and_merge_java_source`).
- **Process**: Merges duplicate class definitions, cleans markdown code fences, standardizes class indentation, and formats method signatures.

### Stage 10: Semantic Verification
- **Engine**: `MigrationAgent._validate_final_output()`.
- **Process**: Scans output code for lingering C# syntax leaks (e.g., `string.IsNullOrEmpty`, `Console.WriteLine`, `using System;`) and flags issues.

### Stage 11: Compile Node (`_compile_node`)
- **Process**: 
  1. Extracts Java `package` declaration (e.g., `package com.myapp.services;`).
  2. Renames and places files under package-based relative paths (e.g., `com/myapp/services/CalculatorService.java`).
  3. `setup_mock_dependencies()` generates mock stub interfaces for external packages (Lombok, SLF4J, Spring annotations).
  4. Invokes `javac` compiler for syntax validation. If `javac` is not installed on the host environment, compilation validation logs a notice and cleanly skips to the next stage.

### Stage 12: Compile Repair Loop
- **Trigger**: Activated if `javac` reports compilation errors.
- **Process**: Executes up to 3 automated repair attempts by sending compiler error output and original code back to the LLM to auto-correct syntax errors.

### Stage 13: Save Node (`_save_node`)
- **Process**: Writes final Java source files to `storage/generated/{migration_id}/` and updates `MigrationState.current_stage` to `saved`.

### Stage 14: Download (`GET /api/migrations/{id}/download`)
- **Process**: Bundles all generated Java files from `storage/generated/{migration_id}/` into a `.zip` archive and streams it directly to the user's browser.
