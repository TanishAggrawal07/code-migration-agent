# Environment & System Configuration Reference

## Overview

Configuration management is powered by Pydantic v2 `BaseSettings` (`backend/app/core/config.py`). All configuration parameters can be set via environment variables or specified in a `.env` file at the root of the application backend.

---

## ⚙️ Application Settings

| Variable Name | Type | Default Value | Description |
|---|---|---|---|
| `APP_NAME` | `str` | `Code Migration Agent` | System name echoed in health checks |
| `APP_VERSION` | `str` | `0.1.0` | Backend semantic version string |
| `APP_ENV` | `str` | `development` | Deployment environment (`development` / `production`) |
| `LOG_LEVEL` | `str` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## 🤖 AI Provider Settings

| Variable Name | Type | Default Value | Description |
|---|---|---|---|
| `AI_PROVIDER` | `str` | `auto` | Active provider (`auto`, `groq`, `gemini`, `ollama`, `openrouter`, `grok`, `openai`) |
| `GROQ_API_KEY` | `str` | `""` | API Key for Groq Cloud LLM service |
| `GROQ_MODEL` | `str` | `llama-3.3-70b-versatile` | Model name for Groq inference |
| `GEMINI_API_KEY` | `str` | `""` | API Key for Google AI Studio Gemini models |
| `GEMINI_MODEL` | `str` | `gemini-2.5-flash` | Model name for Gemini inference |
| `GEMINI_TIMEOUT_SECONDS` | `int` | `60` | HTTP timeout in seconds for Gemini calls |
| `GEMINI_MAX_RETRIES` | `int` | `3` | Maximum retry attempts for Gemini API calls |
| `OLLAMA_BASE_URL` | `str` | `http://localhost:11434` | HTTP endpoint for local Ollama daemon |
| `OLLAMA_MODEL` | `str` | `""` | Explicit model override for Ollama |
| `OLLAMA_MODEL_PRIORITY` | `str` | `qwen2.5-coder,deepseek-coder...` | Priority list for auto-detecting installed Ollama models |
| `OPENROUTER_API_KEY` | `str` | `""` | API Key for OpenRouter AI gateway |
| `OPENROUTER_MODEL` | `str` | `openai/gpt-4o-mini` | Model identifier for OpenRouter |
| `GROK_API_KEY` | `str` | `""` | API Key for xAI Grok API |
| `GROK_MODEL` | `str` | `grok-2-1212` | Model identifier for Grok |
| `OPENAI_API_KEY` | `str` | `""` | API Key for OpenAI REST API |
| `OPENAI_MODEL` | `str` | `gpt-4o-mini` | Model identifier for OpenAI |

---

## 🧠 Embeddings & Vector Database Settings

| Variable Name | Type | Default Value | Description |
|---|---|---|---|
| `EMBEDDING_MODEL` | `str` | `all-MiniLM-L6-v2` | SentenceTransformers model name |
| `EMBEDDING_BATCH_SIZE` | `int` | `32` | Batch size for vector embedding generation |
| `CHROMA_DB_PATH` | `str` | `./chroma_db` | Disk directory for persistent ChromaDB storage |
| `CHROMA_COLLECTION_NAME` | `str` | `migration_docs` | Collection name inside ChromaDB vector database |

---

## 📁 Storage & Upload Constraints

| Variable Name | Type | Default Value | Description |
|---|---|---|---|
| `STORAGE_ROOT` | `str` | `./storage` | Parent directory for all migration files (`uploads/`, `generated/`, `temp/`) |
| `UPLOAD_DIR` | `str` | `./uploads` | Backward-compatibility upload path |
| `OUTPUT_DIR` | `str` | `./outputs` | Backward-compatibility output path |
| `MAX_FILE_SIZE_MB` | `int` | `20` | Maximum allowed size in MB per uploaded source file |
| `MAX_REQUEST_SIZE_MB` | `int` | `200` | Maximum total size in MB per multipart upload request |

---

## 🌐 Network & CORS Settings

| Variable Name | Type | Default Value | Description |
|---|---|---|---|
| `CORS_ORIGINS` | `str` | `http://localhost:3000` | Comma-separated list of allowed CORS browser origins |
| `NEXT_PUBLIC_API_URL` | `str` | `http://localhost:8000` | Base URL used by Next.js frontend client |
