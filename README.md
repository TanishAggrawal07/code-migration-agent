# Code Migration Agent

> Enterprise-grade AI-powered .NET (C#) → Java (Spring Boot / Quarkus) code migration platform using LangGraph, RAG, ChromaDB, Tree-sitter, and a Provider-Agnostic LLM layer.

---

## 🚀 Overview

The **Code Migration Agent** is a full-stack, enterprise-grade AI solution that automates the migration of legacy .NET (C#) codebases to modern Java frameworks (Spring Boot 3, Quarkus). It combines structural AST analysis, semantic vector retrieval (RAG), and a multi-agent LangGraph workflow with an intelligent, self-healing compilation and validation pipeline.

### Key Capabilities
- **Provider-Agnostic AI Layer**: Seamlessly switch between **Ollama**, **Groq**, **Gemini**, **OpenRouter**, **Grok**, and **OpenAI** via environment configuration without changing code.
- **Hybrid Parsing Engine**: Uses **Tree-sitter** AST parsing for deep semantic code structure analysis with a robust regex fallback.
- **Context-Aware RAG Pipeline**: Embeds source code chunks into a persistent **ChromaDB** vector database with **SentenceTransformers** (`all-MiniLM-L6-v2`).
- **LangGraph Multi-Agent Orchestration**: A 7-node Graph state machine ensuring reliable, stage-by-stage migration.
- **Adaptive Code Generation**: Attempts full-file migration first, falling back to intelligent chunked migration for massive files.
- **Self-Healing Compile & Repair Loop**: Validates Java package structure and syntax with an automatic LLM repair loop.
- **Modern Next.js 16 Web Dashboard**: Real-time progress visualization, terminal-style log streaming, and one-click ZIP package download.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js 16 Frontend                             │
│     (Upload UI → Real-time Log Stream → Pipeline Visualizer → Download) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (Port 80 / 3000 / 8000)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        FastAPI 0.115 Backend                           │
│                                                                        │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │   Parser   │   │  Analyzer   │   │ Vector Store │   │ LangGraph  │  │
│  │Tree-sitter │   │ Structural  │   │  ChromaDB    │   │ Workflow   │  │
│  └────────────┘   └─────────────┘   └──────────────┘   └────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                 Provider-Agnostic LLM Layer                      │  │
│  │  [Ollama] ── [Groq] ── [Gemini] ── [OpenRouter] ── [Grok] ── [OpenAI] │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Multi-Provider LLM Support

The application is completely **provider-agnostic**. Changing providers requires **zero code changes** — simply set `AI_PROVIDER` and the matching API key in your `.env` file and restart the backend.

| Provider | Supported Models | Required Environment Variables |
|---|---|---|
| **Ollama** *(Local)* | `qwen2.5-coder`, `deepseek-coder`, `llama3`, etc. | `OLLAMA_BASE_URL=http://localhost:11434` |
| **Groq** *(Cloud)* | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` | `GROQ_API_KEY=gsk_...` |
| **Gemini** *(Cloud)* | `gemini-2.5-flash`, `gemini-1.5-pro` | `GEMINI_API_KEY=AQ...` |
| **OpenRouter** *(Cloud)* | `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY=sk-or-...` |
| **Grok** *(Cloud)* | `grok-2-1212` | `GROK_API_KEY=xai-...` |
| **OpenAI** *(Cloud)* | `gpt-4o-mini`, `gpt-4o` | `OPENAI_API_KEY=sk-...` |

*If `AI_PROVIDER=auto` is configured, the backend automatically probes available providers in order: Ollama → Groq → Gemini → OpenRouter → Grok → OpenAI.*

---

## 🔄 14-Stage Migration Pipeline

```
Upload → Parser → Analyzer → Embeddings → ChromaDB → RAG → Adaptive Full-File Migration
  → Intelligent Chunk Fallback → Structural Verification → Semantic Verification
  → Compile → Compile Repair Loop → Save → Download
```

1. **Upload**: Accepts single C# source files or `.zip` project archives.
2. **Parser**: Tree-sitter / Regex extracts namespaces, classes, methods, and statements.
3. **Analyzer**: Builds code structure metadata and dependency graphs.
4. **Embeddings**: SentenceTransformers generates 384-dimensional vector embeddings.
5. **ChromaDB**: Persists embeddings into ChromaDB collection `migration_docs`.
6. **RAG**: Retrieves relevant context & framework translation rules.
7. **Adaptive Migration**: Generates Java source code using the configured LLM.
8. **Compile & Repair Loop**: Formats package structures, validates syntax with `javac`, and runs automatic repair retries on error.
9. **Save & Export**: Persists output Java files to `storage/generated/{id}/` and exports a ZIP bundle.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router, Turbopack), TypeScript, Vanilla CSS / TailwindCSS, Axios |
| **Backend** | Python 3.11, FastAPI 0.115, LangGraph, Pydantic v2 Settings |
| **AI / LLM** | Groq, Gemini 2.5 Flash, Ollama, OpenRouter, Grok, OpenAI |
| **Vector DB** | ChromaDB 0.5+ |
| **Embeddings** | SentenceTransformers (`all-MiniLM-L6-v2`) |
| **Parsing** | Tree-sitter (.NET C# grammar) with Regex fallback |
| **Containers & Orchestration** | Docker, Docker Compose |
| **Cloud Deployment** | AWS EC2 (Ubuntu 22.04 LTS), Elastic IP, Docker Compose |

---

## 📁 Repository Navigation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Deep architectural specification and module design.
- [WORKFLOW.md](WORKFLOW.md) — Complete 14-stage migration workflow documentation.
- [API.md](API.md) — REST API endpoint reference and request/response schemas.
- [DEPLOYMENT.md](DEPLOYMENT.md) — AWS EC2, Docker Compose, and production deployment guide.
- [INSTALLATION.md](INSTALLATION.md) — Local development and installation guide.
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — Detailed codebase file tree.

---

## 🚀 Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/code-migration-agent.git
cd code-migration-agent

# 2. Configure environment
cp server.env .env
# Edit .env to add your GROQ_API_KEY or GEMINI_API_KEY

# 3. Start full stack with Docker Compose
docker compose up -d --build
```

- **Web Application**: `http://localhost` (or `http://localhost:3000`)
- **Backend API**: `http://localhost:8000`
- **Swagger API Docs**: `http://localhost:8000/docs`

---

## 📄 License

Distributed under the MIT License.
