# System Architecture

## Overview

The **Code Migration Agent** is a multi-tier, provider-agnostic system engineered to translate legacy .NET (C#) applications into modern Java frameworks (Spring Boot 3, Quarkus). The system is built around a decoupled architecture comprising a Next.js 16 frontend, a FastAPI 0.115 asynchronous backend, a persistent ChromaDB vector store, and a LangGraph Graph state machine for agent orchestration.

---

## 🏗️ High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js 16 Frontend                             │
│       (App Router, Turbopack, Dynamic Host Resolution, Axios)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (HTTP)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        FastAPI Backend Engine                          │
│                                                                        │
│  ┌───────────────────────┐             ┌────────────────────────────┐  │
│  │   API Route Layer     │             │    Migration State Store   │  │
│  │ (/api/migrations,     │────────────►│  (In-Memory & File Storage)│  │
│  │  /api/ai/provider)    │             │   storage/uploads & gen/   │  │
│  └───────────┬───────────┘             └─────────────▲──────────────┘  │
│              │                                       │                 │
│  ┌───────────▼───────────┐             ┌─────────────┴──────────────┐  │
│  │ LangGraph StateGraph  │             │   ChromaDB Vector Store    │  │
│  │ (7-Node Graph Machine)│────────────►│   (SentenceTransformers    │  │
│  └───────────┬───────────┘             │    all-MiniLM-L6-v2)       │  │
│              │                         └────────────────────────────┘  │
│  ┌───────────▼──────────────────────────────────────────────────────┐  │
│  │                  Provider-Agnostic LLM Layer                     │  │
│  │  [Ollama] ── [Groq] ── [Gemini] ── [OpenRouter] ── [Grok] ── [OpenAI] │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Architectural Components

### 1. Frontend Subsystem (`frontend/`)
- **Framework**: Next.js 16 using App Router and Turbopack compiler.
- **Dynamic Server Resolution**: `getApiBaseUrl()` in `src/lib/api.ts` automatically inspects `window.location.hostname` in the browser to route requests to backend port `8000` regardless of deployment IP or domain.
- **User Interface Pages**:
  - Landing (`/`): Product overview and key feature highlights.
  - Dashboard (`/dashboard`): Upload drag-and-drop area, migration configuration, progress progress bar, log console, code diff preview, and ZIP download button.
  - Migrations List (`/migrations`): Active and completed migration job history.
  - History (`/history`): Historical audit log of code migrations.
  - Settings (`/settings`): AI provider selection and system status.
  - About (`/about`): System architecture and documentation.

### 2. Backend API Engine (`backend/`)
- **Framework**: FastAPI 0.115+ running under Uvicorn ASGI server.
- **Configuration**: Pydantic v2 `BaseSettings` singleton (`get_settings()`) loading variables from `.env`.
- **API Services**:
  - `MigrationService`: Business logic for migration job lifecycle and state management.
  - `FileSystemService`: Operations on `storage/uploads/`, `storage/generated/`, and `storage/temp/`.

### 3. AI Provider Abstraction Layer (`backend/app/core/llm_providers.py`)
The system enforces strict provider independence through an abstract `BaseProvider` class.

```
                  ┌─────────────────┐
                  │  BaseProvider   │
                  └────────┬────────┘
                           │
    ┌─────────────┬────────┴────┬──────────────┬──────────────┬─────────────┐
    │             │             │              │              │             │
┌───▼────┐   ┌────▼───┐    ┌────▼───┐    ┌─────▼────┐   ┌─────▼────┐   ┌────▼───┐
│ Ollama │   │  Groq  │    │ Gemini │    │OpenRouter│   │   Grok   │   │ OpenAI │
└────────┘   └────────┘    └────────┘    └──────────┘   └──────────┘   └────────┘
```

- **Supported Providers**:
  - `OllamaProvider`: Local LLM execution via `http://localhost:11434` (`qwen2.5-coder`, `deepseek-coder`, etc.).
  - `GroqProvider`: High-throughput cloud LLM execution (`llama-3.3-70b-versatile`).
  - `GeminiProvider`: Google AI Studio (`gemini-2.5-flash`, `gemini-1.5-pro`).
  - `OpenAICompatProvider`: Reusable HTTP wrapper powering **OpenRouter**, **Grok** (`x.ai`), and **OpenAI**.
- **Failover Chain**: `FailoverProvider` automatically wraps the selected provider. If an active provider fails during generation, the failover sequence (`Ollama → Groq → Gemini → OpenRouter → Grok → OpenAI`) automatically retries with the next available provider.

### 4. Vector Database & RAG Subsystem (`backend/app/vectorstore/`, `backend/app/rag/`)
- **Embeddings Service**: `SentenceTransformer("all-MiniLM-L6-v2")` generating 384-dimensional dense vectors (uses CUDA GPU when present, falls back to CPU).
- **ChromaDB Client**: Persistent vector collection `migration_docs` stored in `storage/chroma_db/`.
- **RAG Retrieval**: Retrieves top-k semantically relevant code chunks and framework translation patterns to augment LLM prompts during code generation.

### 5. LangGraph Orchestration Engine (`backend/app/agents/workflow.py`)
A `StateGraph` state machine orchestrating 7 distinct execution nodes:
1. `_parser_node`: Tree-sitter / Regex parsing into code chunks.
2. `_analyzer_node`: AST structural code analysis and dependency extraction.
3. `_embedding_node`: Chunk vectorization via SentenceTransformers.
4. `_rag_node`: ChromaDB context retrieval.
5. `_migration_node`: Adaptive LLM code generation (Full-file → Chunk fallback).
6. `_compile_node`: Java post-processing, package-based file placement, and `javac` repair loop.
7. `_save_node`: Disk persistence to `storage/generated/{id}/`.

---

## 🔒 Provider-Agnostic Guarantee

Switching LLM providers requires **no code changes**. Updating environment settings in `.env` reconfigures the Provider Registry instantly:

```env
# Switch to Groq
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here

# Or switch to Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key

# Or switch to local Ollama
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```
