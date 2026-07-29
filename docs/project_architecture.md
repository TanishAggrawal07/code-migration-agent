# Project Architecture Specification (`project_architecture.md`)

## Overview

The **Code Migration Agent** is an enterprise-grade AI system designed for migrating legacy .NET (C#) applications into modern Java frameworks (Spring Boot 3, Quarkus). It uses a multi-tier, decoupled architecture consisting of a Next.js 16 web application, a FastAPI 0.115 asynchronous backend, a ChromaDB vector store, and a LangGraph Graph state machine.

---

## 🏛️ High-Level Architectural Diagram

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
│  │  [Groq] ── [Gemini] ── [Ollama] ── [OpenRouter] ── [Grok] ── [OpenAI] │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Architectural Subsystems

### 1. Web Frontend (`frontend/`)
- **Framework**: Next.js 16 using App Router and Turbopack compiler.
- **Dynamic Client URL Resolution**: `getApiBaseUrl()` in `src/lib/api.ts` automatically inspects `window.location.hostname` in the browser to route requests to backend port `8000` regardless of deployment IP or domain.
- **Key Modules**: Dashboard (`/dashboard`), Migrations (`/migrations`), History (`/history`), Settings (`/settings`), About (`/about`).

### 2. FastAPI Backend Core (`backend/`)
- **Framework**: FastAPI 0.115+ running on Uvicorn ASGI server.
- **Configuration**: Pydantic v2 `BaseSettings` singleton (`get_settings()`) loaded from `.env`.
- **Services**:
  - `MigrationService`: State management & CRUD operations.
  - `FileSystemService`: Operations on `storage/uploads/`, `storage/generated/`, and `storage/temp/`.

### 3. Provider-Agnostic LLM Layer (`backend/app/core/llm_providers.py`)
- **Base Interface**: `BaseProvider` enforcing asynchronous `generate_text()`.
- **Supported Providers**:
  - `GroqProvider`: `llama-3.3-70b-versatile` (Active in production EC2).
  - `GeminiProvider`: `gemini-2.5-flash`.
  - `OllamaProvider`: Local execution (`qwen2.5-coder`, `deepseek-coder`).
  - `OpenAICompatProvider`: Reusable wrapper powering **OpenRouter**, **Grok** (`x.ai`), and **OpenAI**.
- **Failover Chain**: `FailoverProvider` automatically retries requests across available providers if the primary provider experiences a failure.

### 4. Vector Database & RAG Subsystem (`backend/app/vectorstore/`, `backend/app/rag/`)
- **Embeddings**: `SentenceTransformer("all-MiniLM-L6-v2")` generating 384-dimensional dense vectors.
- **ChromaDB**: Persistent SQLite collection `migration_docs` in `storage/chroma_db/`.
- **RAG Retrieval**: Retrieves top-k semantically relevant context chunks during code generation.

### 5. Java Post-Processing Engine (`backend/app/utils/java_post_processor.py`)
- **Class Merging**: Cleans markdown formatting and merges duplicate class declarations.
- **Package Path Resolution**: Maps package statements to directory subpaths.
- **Mock Generator**: Automatically generates stub interfaces for external packages (Lombok, SLF4J, Spring annotations).
- **Compile Repair Loop**: Executes up to 3 LLM repair attempts when `javac` syntax errors are detected.
