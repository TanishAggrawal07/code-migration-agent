# Production & Local Deployment Guide

This document covers deployment procedures for **AWS EC2**, **Docker Compose**, and **Local Development**.

---

## ☁️ AWS EC2 Deployment (Production)

The production environment is deployed on an **AWS EC2** instance running Ubuntu 22.04 LTS.

### Instance Specs
- **Instance Type**: `t3.small` (2 vCPU, 2GB RAM + 2GB configured Swap file)
- **Region**: `ap-south-1` (Mumbai)
- **Elastic IP**: `3.109.164.178`
- **Security Group**: `cma-sg` (`sg-02f20cea31e0604be`)
  - Port `22` (SSH management)
  - Port `80` (Web Interface - Next.js Frontend)
  - Port `3000` (Next.js Frontend fallback)
  - Port `8000` (FastAPI Backend)

### 1. EC2 Swap Space Setup
To support heavy ML dependencies (PyTorch, ChromaDB, SentenceTransformers) on `t3.small`:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### 2. Environment Configuration File (`/opt/cma/code-migration-agent/.env`)

```env
# AI Provider Configuration
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Fallback Cloud Provider
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_TIMEOUT_SECONDS=120
GEMINI_MAX_RETRIES=2

# Vector Database & File Paths
CHROMA_DB_PATH=/app/chroma_db
UPLOAD_DIR=/app/uploads
OUTPUT_DIR=/app/outputs
STORAGE_ROOT=/app/storage

# Production Settings
APP_ENV=production
LOG_LEVEL=INFO

# Network & CORS
CORS_ORIGINS=http://3.109.164.178,http://3.109.164.178:80,http://3.109.164.178:3000
NEXT_PUBLIC_API_URL=http://3.109.164.178:8000
```

### 3. Container Orchestration
The deployment runs two main containers managed via Docker Compose:

```bash
cd /opt/cma/code-migration-agent
sudo docker compose up -d
```

- **Backend Container (`cma-backend`)**: Runs FastAPI on port 8000 (`0.0.0.0:8000->8000/tcp`).
- **Frontend Container (`cma-frontend`)**: Runs Next.js 16 standalone build mapped to ports 80 and 3000 (`0.0.0.0:80->3000/tcp`, `0.0.0.0:3000->3000/tcp`).

---

## 🐳 Docker Compose Deployment (Local / On-Prem)

To run the complete stack locally using Docker:

```bash
# 1. Clone repo
git clone https://github.com/your-org/code-migration-agent.git
cd code-migration-agent

# 2. Configure environment
cp server.env .env
# Edit .env with your desired AI_PROVIDER and API keys

# 3. Build & launch containers
docker compose up -d --build
```

### Docker Compose Architecture (`docker-compose.yml`)

```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: cma-backend
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AI_PROVIDER=${AI_PROVIDER:-auto}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}
    volumes:
      - backend_uploads:/app/uploads
      - backend_outputs:/app/outputs
      - chroma_data:/app/chroma_db

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: cma-frontend
    ports:
      - "80:3000"
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
```

---

## ⚙️ Complete Environment Variable Reference

| Variable Name | Description | Default Value | Required? |
|---|---|---|---|
| `AI_PROVIDER` | Selected LLM provider (`auto`, `groq`, `gemini`, `ollama`, `openrouter`, `grok`, `openai`) | `auto` | No |
| `GROQ_API_KEY` | Groq Cloud API Key | — | If `AI_PROVIDER=groq` |
| `GROQ_MODEL` | Groq Model Name | `llama-3.3-70b-versatile` | No |
| `GEMINI_API_KEY` | Google AI Studio API Key | — | If `AI_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini Model Name | `gemini-2.5-flash` | No |
| `OLLAMA_BASE_URL` | Ollama HTTP endpoint | `http://localhost:11434` | If `AI_PROVIDER=ollama` |
| `OPENROUTER_API_KEY` | OpenRouter API Key | — | If `AI_PROVIDER=openrouter` |
| `GROK_API_KEY` | xAI Grok API Key | — | If `AI_PROVIDER=grok` |
| `OPENAI_API_KEY` | OpenAI API Key | — | If `AI_PROVIDER=openai` |
| `CHROMA_DB_PATH` | ChromaDB persistence path | `./chroma_db` | No |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:3000` | No |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL override | `http://localhost:8000` | No |
