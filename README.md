# Code Migration Agent

> AI-powered .NET → Java code migration using Gemini 2.5 Flash, RAG, LangGraph, ChromaDB, and MCP.

---

## Overview

The **Code Migration Agent** is a full-stack AI system that automates the translation of enterprise .NET codebases to production-ready Java. It combines:

- **AST-based parsing** (Tree-sitter) to deeply understand C# source structure
- **RAG pipeline** (ChromaDB + Sentence Transformers) to ground migrations in real Java idioms
- **LangGraph** multi-agent orchestration for reliable, step-by-step transformation
- **Gemini 2.5 Flash** for accurate, context-aware code generation
- **MCP** (Model Context Protocol) for standardized tool use (compilers, linters, validators)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Next.js Frontend                     │
│  (Upload UI → Migration Dashboard → Download Results)    │
└──────────────────────┬──────────────────────────────────┘
                       │ REST / HTTP
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Parser  │  │   RAG    │  │ LangGraph│  │  MCP   │  │
│  │Tree-sitter│  │ChromaDB │  │  Agents  │  │ Tools  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
│                       │                                   │
│  ┌────────────────────▼──────────────────────────────┐  │
│  │              Gemini 2.5 Flash API                   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer         | Technology                                      |
|---------------|-------------------------------------------------|
| Frontend      | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui |
| Backend       | Python 3.11, FastAPI, LangGraph                 |
| LLM           | Gemini 2.5 Flash (Google AI)                    |
| Vector Store  | ChromaDB                                        |
| Embeddings    | Sentence Transformers                           |
| Parsing       | Tree-sitter (.NET / C# grammar)                 |
| Protocol      | MCP (Model Context Protocol)                    |
| Deployment    | Vercel (frontend), Render (backend)             |
| Containers    | Docker, Docker Compose                          |

---

## Project Structure

```
code-migration-agent/
├── frontend/                  # Next.js 15 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx       # Home / landing page
│   │   │   ├── dashboard/     # Migration dashboard
│   │   │   └── about/         # About & architecture
│   │   ├── components/
│   │   └── lib/
│   └── ...
│
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── api/               # Route handlers
│   │   ├── agents/            # LangGraph agent definitions
│   │   ├── parser/            # Tree-sitter .NET parser
│   │   ├── rag/               # RAG pipeline
│   │   ├── embeddings/        # Sentence Transformer helpers
│   │   ├── vectorstore/       # ChromaDB client
│   │   ├── mcp/               # MCP tool definitions
│   │   ├── compiler/          # Java compile / lint validators
│   │   ├── utils/             # Shared utilities
│   │   └── core/              # Settings, logging, lifespan
│   ├── uploads/               # Uploaded .NET projects (gitignored)
│   ├── outputs/               # Generated Java projects (gitignored)
│   ├── chroma_db/             # ChromaDB persistence (gitignored)
│   ├── tests/                 # pytest test suite
│   ├── main.py                # FastAPI app entry point
│   └── requirements.txt
│
├── docs/                      # Architecture diagrams & notes
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Node.js ≥ 18
- Python ≥ 3.11
- Git

### 1. Clone the repository

```bash
git clone https://github.com/your-org/code-migration-agent.git
cd code-migration-agent
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if your backend runs on a different port

# Start the dev server
npm run dev
```

Frontend available at: http://localhost:3000

### 4. Docker (Full Stack)

```bash
# From project root
cp backend/.env.example backend/.env
# Add your GEMINI_API_KEY to backend/.env

docker compose up --build
```

---

## API Endpoints

| Method | Path      | Description         |
|--------|-----------|---------------------|
| GET    | /health   | Service health check |
| GET    | /docs     | Swagger UI           |
| GET    | /redoc    | ReDoc UI             |

---

## Environment Variables

### Backend (`backend/.env`)

| Variable           | Description                          | Default              |
|--------------------|--------------------------------------|----------------------|
| `GEMINI_API_KEY`   | Google AI API key                    | —                    |
| `CHROMA_DB_PATH`   | ChromaDB storage directory           | `./chroma_db`        |
| `UPLOAD_DIR`       | Uploaded project storage             | `./uploads`          |
| `OUTPUT_DIR`       | Generated Java project storage       | `./outputs`          |
| `APP_ENV`          | `development` or `production`        | `development`        |
| `CORS_ORIGINS`     | Allowed CORS origins (comma-sep)     | `http://localhost:3000` |

### Frontend (`frontend/.env.local`)

| Variable              | Description              | Default                  |
|-----------------------|--------------------------|--------------------------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL     | `http://localhost:8000`  |

---

## Development

```bash
# Run backend tests
cd backend && pytest tests/ -v

# Lint frontend
cd frontend && npm run lint

# Type-check frontend
cd frontend && npx tsc --noEmit
```

---

## Deployment

- **Frontend**: Deploy the `frontend/` directory to [Vercel](https://vercel.com). Set `NEXT_PUBLIC_API_URL` in Vercel environment variables.
- **Backend**: Deploy the `backend/` directory to [Render](https://render.com) as a Docker service. Set all backend env vars in Render's dashboard.

---

## License

MIT
