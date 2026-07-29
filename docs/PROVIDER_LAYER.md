# Provider Layer Specification

## Overview

The **Code Migration Agent** implements a **Provider-Agnostic AI Layer** (`backend/app/core/llm_providers.py`). The system decouples LLM generation logic from specific cloud vendor APIs, allowing seamless execution across 6 supported LLM providers without code modifications.

---

## 🏛️ Provider Architecture & Abstraction

```
                            ┌───────────────────┐
                            │   BaseProvider    │
                            │ (Abstract Class)  │
                            └─────────┬─────────┘
                                      │
    ┌──────────────┬──────────────────┼──────────────────┬──────────────┐
    │              │                  │                  │              │
┌───▼────┐   ┌─────▼────┐       ┌─────▼────┐       ┌─────▼────┐   ┌─────▼────┐
│ Ollama │   │  Gemini  │       │   Groq   │       │OpenRouter│   │   Grok   │
└────────┘   └──────────┘       └──────────┘       └──────────┘   └──────────┘
                                                         │
                                                   ┌─────▼────┐
                                                   │  OpenAI  │
                                                   └──────────┘
```

The base class `BaseProvider` enforces an asynchronous text generation interface:

```python
class BaseProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        """Asynchronously invoke LLM provider to generate code or text."""
        pass

    @property
    @abstractmethod
    def provider_key(self) -> str:
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        pass
```

---

## 🤖 Supported Providers

### 1. Groq (`GroqProvider`)
- **Key**: `groq`
- **Default Model**: `llama-3.3-70b-versatile`
- **Protocol**: OpenAI-compatible HTTP REST (`https://api.groq.com/openai/v1`)
- **Environment Key**: `GROQ_API_KEY`
- **Use Case**: High-throughput cloud LLM inference (Default active provider in production EC2).

### 2. Gemini (`GeminiProvider`)
- **Key**: `gemini`
- **Default Model**: `gemini-2.5-flash`
- **Protocol**: Google GenAI Python SDK (`google-generativeai`)
- **Environment Key**: `GEMINI_API_KEY`
- **Use Case**: Secondary cloud fallback provider.

### 3. Ollama (`OllamaProvider`)
- **Key**: `ollama`
- **Default Model Selection**: Auto-discovers local models in priority order: `qwen2.5-coder` → `deepseek-coder` → `kimi-k2` → `gemma3` → `llama3`.
- **Protocol**: Local HTTP REST API (`http://localhost:11434/api`)
- **Environment Key**: `OLLAMA_BASE_URL`
- **Use Case**: Fully offline, on-premise local code migration.

### 4. OpenRouter (`OpenAICompatProvider`)
- **Key**: `openrouter`
- **Default Model**: `openai/gpt-4o-mini`
- **Protocol**: OpenAI-compatible HTTP REST (`https://openrouter.ai/api/v1`)
- **Environment Key**: `OPENROUTER_API_KEY`
- **Use Case**: Multi-vendor cloud API gateway.

### 5. Grok (`OpenAICompatProvider`)
- **Key**: `grok`
- **Default Model**: `grok-2-1212`
- **Protocol**: OpenAI-compatible HTTP REST (`https://api.x.ai/v1`)
- **Environment Key**: `GROK_API_KEY`
- **Use Case**: xAI Grok LLM provider.

### 6. OpenAI (`OpenAICompatProvider`)
- **Key**: `openai`
- **Default Model**: `gpt-4o-mini`
- **Protocol**: OpenAI-compatible HTTP REST (`https://api.openai.com/v1`)
- **Environment Key**: `OPENAI_API_KEY`
- **Use Case**: Direct OpenAI cloud API integration.

---

## ⚡ Failover Engine (`FailoverProvider`)

When `AI_PROVIDER=auto` is configured (or when an active provider experiences a transient runtime error), `FailoverProvider` automatically wraps the selected provider. It probes and executes providers according to the strict priority chain:

$$\text{Ollama} \longrightarrow \text{Groq} \longrightarrow \text{Gemini} \longrightarrow \text{OpenRouter} \longrightarrow \text{Grok} \longrightarrow \text{OpenAI}$$

If the primary provider fails or times out, `FailoverProvider` transparently catches the exception, logs a warning, and re-executes the prompt against the next available provider in the chain.

---

## ⚙️ Provider Switching Configuration

Switching providers requires **no code edits** — simply change environment settings in `.env` and restart the backend server:

```env
# Example: Select Groq Provider
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_api_key_here

# Example: Select Gemini Provider
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Example: Automatic Failover Mode
AI_PROVIDER=auto
```
