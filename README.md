# Code Migration Agent

> Enterprise-grade AI-powered .NET (C#) → Java (Spring Boot / Quarkus) code migration platform using LangGraph, RAG, ChromaDB, Tree-sitter, and a Provider-Agnostic LLM layer.

---

## 🚀 Overview

The **Code Migration Agent** is a full-stack, enterprise-grade AI solution that automates the migration of legacy .NET (C#) codebases to modern Java frameworks (Spring Boot 3, Quarkus). It combines structural AST analysis, semantic vector retrieval (RAG), and a multi-agent LangGraph workflow with an intelligent, self-healing compilation and validation pipeline.

### Key Capabilities
- **Provider-Agnostic AI Layer**: Seamlessly switch between **Groq**, **Gemini**, **Ollama**, **OpenRouter**, **Grok**, and **OpenAI** via environment configuration without code changes.
- **Hybrid Parsing Engine**: Uses **Tree-sitter** AST parsing for deep semantic code structure analysis with a robust regex fallback.
- **Context-Aware RAG Pipeline**: Embeds source code chunks into a persistent **ChromaDB** vector database with **SentenceTransformers** (`all-MiniLM-L6-v2`).
- **LangGraph Multi-Agent Orchestration**: A 7-node Graph state machine ensuring reliable, stage-by-stage migration.
- **Adaptive Code Generation**: Attempts full-file migration first, falling back to intelligent chunked migration for massive files.
- **Self-Healing Compile & Repair Loop**: Validates Java package structure and syntax with an automatic LLM repair loop.
- **Modern Next.js 16 Web Dashboard**: Real-time progress visualization, terminal-style log streaming, and one-click ZIP package download.

---

## 📚 Centralized Documentation

All technical documentation is organized within the [`docs/`](docs/) directory:

| Document | Description |
|---|---|
| 📐 [Architecture Specification](docs/ARCHITECTURE.md) | High-level system architecture, component design, and workflow nodes |
| 🤖 [Provider Layer Specification](docs/PROVIDER_LAYER.md) | LLM provider abstraction layer, failover engine, and provider keys |
| ⚙️ [Configuration Reference](docs/CONFIGURATION.md) | Every supported environment variable, storage limit, and AI parameter |
| 🛠️ [Technology Stack](docs/TECHNOLOGY_STACK.md) | Frameworks, AI engines, vector databases, parsers, and deployment tools |
| 🔄 [Migration Workflow](docs/WORKFLOW.md) | 14-stage migration pipeline documentation |
| 🌐 [REST API Reference](docs/API.md) | Endpoint specifications, schemas, and status codes |
| ☁️ [Deployment Guide](docs/DEPLOYMENT.md) | Production setup for AWS EC2, Docker Compose, and environment variables |
| 💻 [Installation Guide](docs/INSTALLATION.md) | Step-by-step local development setup instructions |
| 📁 [Project Structure](docs/PROJECT_STRUCTURE.md) | Repository directory tree and file map |
| 🤝 [Project Handoff](docs/HANDOFF.md) | Production state report and verification checklist |

---

## 🏛️ System Architecture Overview

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
│  │  [Groq] ── [Gemini] ── [Ollama] ── [OpenRouter] ── [Grok] ── [OpenAI] │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

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

- **Web Application Interface**: `http://localhost` (or `http://localhost:3000`)
- **Backend REST API**: `http://localhost:8000`
- **Swagger API Docs**: `http://localhost:8000/docs`

---

## 📄 License

Distributed under the MIT License.
