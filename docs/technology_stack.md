# Technology Stack Specification (`technology_stack.md`)

## Overview

The **Code Migration Agent** is built on a modern technology stack. This document details the technology choices across all layers of the application stack.

---

## 🎨 Frontend Stack

| Layer / Concern | Technology | Purpose |
|---|---|---|
| **Framework** | Next.js 16 (App Router, React 19) | Server-side rendering, client routing, and standalone production build |
| **Compiler** | Turbopack | Incremental compilation and fast HMR |
| **Language** | TypeScript 5.0+ | Strict type safety and interface definitions |
| **Styling** | Vanilla CSS / TailwindCSS v4 | High-performance custom layout and glassmorphic UI elements |
| **HTTP Client** | Axios | REST API integration with dynamic host resolution (`getApiBaseUrl()`) |
| **Icons** | Lucide React | Clean, responsive vector icons |
| **State & Data Fetching** | TanStack Query v5 (React Query) | Server state management, live polling, and cache management |

---

## ⚡ Backend Stack

| Layer / Concern | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI 0.115+ | Asynchronous REST API framework with OpenAPI schema auto-generation |
| **ASGI Server** | Uvicorn | High-performance ASGI web server |
| **Language** | Python 3.11 | Modern Python runtime |
| **Orchestration** | LangGraph 0.2.60 | 7-node Graph state machine for multi-agent migration workflow |
| **Settings & Validation** | Pydantic v2 & `pydantic-settings` | Type validation and environment variable singleton management |
| **Concurrency & Locks** | Python `asyncio` & `aiofiles` | Non-blocking file I/O and per-migration concurrency locking |
| **Logging** | Structlog & Python `logging` | Structured JSON and colored console logging |

---

## 🤖 AI & LLM Provider Layer

The system features a **Provider-Agnostic LLM Layer** (`backend/app/core/llm_providers.py`) with support for 6 cloud and local providers:

| Provider | Model | Connection Protocol | Primary Use Case |
|---|---|---|---|
| **Groq** *(Cloud)* | `llama-3.3-70b-versatile` | OpenAI-compatible HTTP REST | High-throughput cloud LLM inference (Default in EC2) |
| **Gemini** *(Cloud)* | `gemini-2.5-flash` / `gemini-1.5-pro` | Google GenAI SDK | Secondary cloud fallback provider |
| **Ollama** *(Local)* | `qwen2.5-coder`, `deepseek-coder` | Local HTTP REST (`:11434`) | On-premise offline migration |
| **OpenRouter** *(Cloud)* | `openai/gpt-4o-mini`, `claude-3.5-sonnet` | OpenAI-compatible HTTP REST | OpenRouter API gateway |
| **Grok** *(Cloud)* | `grok-2-1212` | OpenAI-compatible HTTP REST | xAI cloud LLM provider |
| **OpenAI** *(Cloud)* | `gpt-4o-mini`, `gpt-4o` | OpenAI-compatible HTTP REST | OpenAI API gateway |

---

## 🧠 Embeddings & Vector Database

| Subsystem | Technology | Configuration / Model |
|---|---|---|
| **Embeddings Engine** | SentenceTransformers | `all-MiniLM-L6-v2` (384-dimensional dense vectors, CPU/GPU) |
| **Vector Store** | ChromaDB 0.5+ | Persistent SQLite collection `migration_docs` with HNSW cosine similarity index |

---

## 🔍 Code Parsing & AST Analysis

| Subsystem | Technology | Description |
|---|---|---|
| **AST Parser** | Tree-sitter 0.23+ | Native AST parser for C# grammar extracting classes, methods, and syntax trees |
| **Fallback Parser** | Regex Syntax Engine | Fallback parser ensuring continuity if native C++ bindings are unavailable |
| **Post-Processor** | Java Syntax Engine | Custom cleaner, package-path resolver, mock dependency generator, and `javac` repair loop |

---

## 🐳 Containerization & Cloud Infrastructure

| Infrastructure Layer | Technology | Details |
|---|---|---|
| **Containers** | Docker & Docker Compose | Multi-stage production builds for frontend and backend containers |
| **Cloud Hosting** | AWS EC2 | `t3.small` Ubuntu 22.04 LTS with 2GB Swap space |
| **Network & Security** | Elastic IP & Security Groups | Static IP `3.109.164.178`, open ports `80`, `3000`, `8000`, `22` |
