# Code Migration Agent — Project Handoff Document

> **Prepared for:** Antigravity AI Agent  
> **Date:** June 2026  
> **Status:** Modules 0A → 3 complete. Ready for Module 4.  
> **Test suite:** 226 / 226 passing  
> **Build:** `npm run build` passes (Next.js 16.2.9, 7 routes)

---


## 1. PROJECT OVERVIEW

**Name:** Code Migration Agent  
**Objective:** An AI-powered full-stack application that migrates enterprise .NET (C#) codebases to Java using a multi-agent RAG pipeline powered by Gemini 2.5 Flash, LangGraph, ChromaDB, and Tree-sitter.

**User flow (as implemented):**
1. Open `/dashboard` → create a migration (provide project name)
2. Upload `.NET` files (`.cs`, `.csproj`, `.sln`, `.xml`, `.json`, `.zip`)
3. Click **Run Migration** → 8-stage pipeline executes
4. Watch real-time status, logs, and pipeline visualisation (3 s polling)
5. View generated Java files and compile status

**Implementation status:**
- Modules 0A, 0B, 0C, 1, 2, 3 — **complete and tested**
- Module 4 (Parser & Chunking) — **not started**
- Modules 5–8 (Embeddings, RAG, LLM Migration, Compile) — **not started**
- All pipeline stages beyond `parsed` currently return **mock/stub data**

---

## 2. FOLDER STRUCTURE

```
code-migration-agent/
│
├── frontend/                          Next.js 16 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             Root layout (QueryProvider + ThemeProvider + ToastContainer)
│   │   │   ├── page.tsx               Landing page (/)
│   │   │   ├── globals.css            Tailwind v4 + CSS variables (light/dark theme)
│   │   │   └── (shell)/              Route group — all app pages share sidebar+navbar layout
│   │   │       ├── layout.tsx         Shell layout (Navbar + collapsible Sidebar)
│   │   │       ├── dashboard/page.tsx ★ FULLY INTEGRATED — create/upload/run/poll
│   │   │       ├── migrations/page.tsx  Placeholder (list view, not yet connected)
│   │   │       ├── history/page.tsx     Placeholder
│   │   │       ├── about/page.tsx       Architecture overview (static)
│   │   │       └── settings/page.tsx    Settings (static placeholders)
│   │   ├── components/
│   │   │   ├── upload-card.tsx        ★ Connected — real multipart upload + progress
│   │   │   ├── log-panel.tsx          ★ Connected — shows real backend LogEntry[]
│   │   │   ├── pipeline-view.tsx      ★ Connected — driven by currentStage + completedStages
│   │   │   ├── migration-status.tsx   ★ New — progress bar, stage badges, stat cells
│   │   │   ├── stats-card.tsx         Reusable metric card + skeleton variant
│   │   │   ├── navbar.tsx             Sticky header (brand, theme toggle, avatar)
│   │   │   ├── sidebar.tsx            Collapsible nav (Dashboard, Migrations, History, Architecture, Settings)
│   │   │   ├── toast-container.tsx    ★ New — success/error/info/warning toasts
│   │   │   ├── theme-provider.tsx     Dark/light/system theme (localStorage)
│   │   │   ├── theme-toggle.tsx       Sun/Moon toggle button
│   │   │   └── ui/                    shadcn/ui primitives
│   │   │       ├── badge.tsx
│   │   │       ├── button.tsx
│   │   │       ├── scroll-area.tsx
│   │   │       ├── separator.tsx
│   │   │       ├── skeleton.tsx
│   │   │       └── tooltip.tsx
│   │   ├── hooks/
│   │   │   ├── use-migration.ts       ★ All React Query hooks (create/get/upload/run/poll)
│   │   │   └── use-toast.ts           Custom event-bus toast hook
│   │   ├── lib/
│   │   │   ├── api.ts                 ★ Typed Axios API client (all endpoints)
│   │   │   ├── query-client.ts        QueryClient singleton + queryKeys factory
│   │   │   └── utils.ts               cn() helper (clsx + tailwind-merge)
│   │   ├── providers/
│   │   │   └── query-provider.tsx     TanStack Query provider wrapper
│   │   └── types/
│   │       └── migration.ts           ★ Complete TypeScript types for all backend models
│   ├── .env.local                     NEXT_PUBLIC_API_URL=http://localhost:8000
│   ├── .env.example
│   ├── next.config.ts
│   ├── tailwind.config (inline v4)
│   ├── components.json                shadcn/ui config (base-nova style, base-ui)
│   └── package.json
│
├── backend/                           Python 3.10 FastAPI application
│   ├── main.py                        App factory, lifespan, all routers registered
│   ├── requirements.txt               All pinned dependencies
│   ├── .env / .env.example
│   ├── Dockerfile                     Multi-stage builder → runtime
│   │
│   ├── app/
│   │   ├── api/
│   │   │   ├── health.py              GET /health
│   │   │   ├── ai_status.py           GET /api/ai/status, GET /api/ai/services
│   │   │   ├── migrations.py          CRUD + run + status endpoints
│   │   │   ├── upload.py              POST /upload, GET /files, DELETE /files
│   │   │   └── error_handlers.py      Global 422/500/domain exception handlers
│   │   │
│   │   ├── agents/
│   │   │   ├── base_agent.py          BaseAgent ABC + AgentResult + AgentStatus
│   │   │   ├── registry.py            AgentRegistry singleton (register/get/list)
│   │   │   ├── state.py               MigrationState Pydantic model + enums
│   │   │   └── workflow.py            LangGraph WorkflowEngine (7-node pipeline)
│   │   │
│   │   ├── core/
│   │   │   ├── config.py              Pydantic Settings (all env vars + computed paths)
│   │   │   ├── logger.py              Console + rotating file + error-only file handlers
│   │   │   ├── gemini_client.py       GeminiClient singleton (tenacity retry, async timeout)
│   │   │   ├── startup.py             Concurrent service initialisation at startup
│   │   │   └── exceptions.py          MigrationAgentError hierarchy
│   │   │
│   │   ├── embeddings/
│   │   │   └── service.py             EmbeddingService singleton (Sentence Transformers, GPU/CPU)
│   │   │
│   │   ├── vectorstore/
│   │   │   └── chroma_service.py      ChromaService singleton (persistent ChromaDB)
│   │   │
│   │   ├── parser/
│   │   │   └── tree_sitter_service.py TreeSitterService (C# grammar + regex stub fallback)
│   │   │
│   │   ├── mcp/
│   │   │   └── filesystem_mcp.py      MCPFilesystem tool layer (read/write/list/create/delete)
│   │   │
│   │   ├── services/
│   │   │   ├── migration_service.py   MigrationService in-memory CRUD store
│   │   │   └── filesystem_service.py  FileSystemService (async, per-migration locks)
│   │   │
│   │   ├── utils/
│   │   │   ├── upload_validator.py    Extension allowlist, size, empty, duplicate checks
│   │   │   └── zip_extractor.py       Safe async ZIP extraction (Zip-slip guard)
│   │   │
│   │   ├── compiler/                  Empty — for Module 5+
│   │   └── rag/                       Empty — for Module 5+
│   │
│   ├── storage/                       ★ Structured file storage (Module 2)
│   │   ├── uploads/{migration_id}/    Uploaded .NET source files
│   │   ├── generated/{migration_id}/  Output Java files (future)
│   │   └── temp/{migration_id}/       Ephemeral working space
│   │
│   ├── chroma_db/                     ChromaDB persistence (SQLite)
│   ├── logs/
│   │   ├── app.log                    All levels, rotating 10 MB
│   │   └── error.log                  ERROR+ only, rotating
│   │
│   └── tests/                         226 tests, all passing
│       ├── test_health.py
│       ├── test_config.py
│       ├── test_ai_status.py
│       ├── test_gemini_client.py
│       ├── test_embeddings.py
│       ├── test_chromadb.py
│       ├── test_tree_sitter.py
│       ├── test_exceptions.py
│       ├── test_agent_registry.py
│       ├── test_migration_state.py
│       ├── test_migration_service.py
│       ├── test_migrations_api.py
│       ├── test_workflow.py
│       ├── test_filesystem_service.py
│       ├── test_mcp_filesystem.py
│       ├── test_upload_api.py
│       ├── test_upload_validator.py
│       └── test_zip_extractor.py
│
├── docs/
│   └── HANDOFF.md                     ← This document
│
├── docker-compose.yml                 Backend + frontend service skeletons
├── .gitignore
└── README.md
```

---

## 3. TECH STACK

### Frontend
| Concern | Technology |
|---|---|
| Framework | Next.js 16.2.9 (App Router, React 19) |
| Language | TypeScript 5 (strict mode) |
| Styling | Tailwind CSS v4 + CSS variables (light/dark) |
| Component library | shadcn/ui (`base-nova` style, `@base-ui/react` primitives) |
| Icons | lucide-react |
| State management | TanStack Query v5 (React Query) — mutations, caching, polling |
| HTTP client | Axios 1.18 |
| File upload | Native `FormData` + Axios `onUploadProgress` |
| Toast notifications | Custom DOM event bus (`CustomEvent`) |
| Font | Geist Sans + Geist Mono (Google Fonts) |
| Build tool | Turbopack (Next.js built-in) |

### Backend
| Concern | Technology |
|---|---|
| Framework | FastAPI 0.115+ |
| Server | Uvicorn with standard extras |
| Language | Python 3.10 (venv) |
| Orchestration | LangGraph 0.2.60 (StateGraph, async nodes) |
| LLM | google-generativeai 0.8.3 → Gemini 2.5 Flash |
| Vector DB | ChromaDB 0.5.23 (persistent, cosine similarity) |
| Embeddings | Sentence Transformers 3.3.1 → `all-MiniLM-L6-v2` |
| Code parsing | tree-sitter 0.23.2 (C# grammar via regex stub fallback) |
| Retry logic | tenacity 9.0.0 |
| Validation | Pydantic v2 + pydantic-settings |
| File I/O | aiofiles + pathlib (async, per-migration locks) |
| Testing | pytest 9.1 + pytest-asyncio |
| Logging | Python logging — console + rotating file + error file |

---

## 4. IMPLEMENTED MODULES

### Module 0A — Project Setup & Environment
**Commit:** `fa0fa82`

**Files created:**
- `frontend/` — Next.js 16 app (TypeScript, Tailwind, ESLint, shadcn/ui, App Router)
- `backend/main.py` — FastAPI entry point
- `backend/app/core/config.py` — Pydantic Settings
- `backend/app/api/health.py` — GET /health
- `backend/requirements.txt` — all pinned deps
- `backend/.env.example` — all environment variables
- `docker-compose.yml` — skeleton
- `README.md` — project documentation

**APIs created:** `GET /health`

**Verified:** Backend runs on `:8000`, frontend on `:3000`, `/health` returns `{"status":"healthy"}`

---

### Module 0B — Frontend Foundation & Design System
**Commit:** `438d353`

**Files created:**
- `src/app/globals.css` — brand blue CSS variables, dark/light themes, gradient utilities
- `src/app/layout.tsx` — root layout with ThemeProvider
- `src/app/(shell)/layout.tsx` — shell with navbar + collapsible sidebar
- `src/app/(shell)/dashboard/page.tsx` — static dashboard
- `src/app/(shell)/about/page.tsx` — architecture page
- `src/app/(shell)/migrations/page.tsx` — placeholder
- `src/app/(shell)/history/page.tsx` — placeholder
- `src/app/(shell)/settings/page.tsx` — placeholder
- `src/app/page.tsx` — landing page (hero, features, CTA)
- `src/components/navbar.tsx` — sticky header
- `src/components/sidebar.tsx` — collapsible nav with tooltips
- `src/components/upload-card.tsx` — drag-drop zone (static)
- `src/components/log-panel.tsx` — terminal UI (mock logs)
- `src/components/stats-card.tsx` — metric card + skeleton
- `src/components/pipeline-view.tsx` — 8-stage pipeline visual
- `src/components/theme-provider.tsx` — localStorage theme
- `src/components/theme-toggle.tsx` — sun/moon toggle
- `src/components/ui/` — badge, button, scroll-area, separator, skeleton, tooltip

**Verified:** `npm run build` passes, 0 TS errors, 0 lint errors

---

### Module 0C — AI Foundation
**Commit:** `35026a8`

**Files created:**
- `app/core/gemini_client.py` — `GeminiClient` singleton, async `generate_text()`, retry, timeout, `health_check()`
- `app/core/logger.py` — `configure_logging()`, `ColouredFormatter`, rotating file handlers
- `app/core/startup.py` — concurrent service initialisation, `ServiceStatus` dataclass
- `app/embeddings/service.py` — `EmbeddingService` singleton, lazy load, GPU/CPU detection, batch embeddings
- `app/vectorstore/chroma_service.py` — `ChromaService` singleton, `create_collection()`, `add_documents()`, `query()`, `delete_collection()`
- `app/parser/tree_sitter_service.py` — `TreeSitterService` with C# grammar attempt + regex stub, `parse_code()`, `extract_classes()`, `extract_methods()`
- `app/api/ai_status.py` — `GET /api/ai/status`, `GET /api/ai/services`

**APIs created:**
- `GET /api/ai/status` — returns `{gemini, embeddings, chromadb, tree_sitter, all_healthy}`
- `GET /api/ai/services` — extended detail per service

**Tests:** 49 tests covering config, Gemini client, embeddings, ChromaDB, Tree-sitter

---

### Module 1 — Workflow Engine & Agent Orchestration
**Commit:** `e90e5df`

**Files created:**
- `app/agents/state.py` — `MigrationState` (Pydantic), `MigrationStage` enum, `LogEntry`, `ParsedFile`, `GeneratedFile`
- `app/agents/registry.py` — `AgentRegistry` singleton with `register()`, `get()`, `list_agents()`
- `app/agents/workflow.py` — `WorkflowEngine` (LangGraph `StateGraph`, 7 async nodes, `ainvoke`)
- `app/agents/base_agent.py` — `BaseAgent` ABC, `AgentResult`, `safe_run()`, stub agents
- `app/services/migration_service.py` — `MigrationService` in-memory CRUD, asyncio locks, concurrency guard
- `app/core/exceptions.py` — `MigrationAgentError` hierarchy (Agent, Workflow, Service, NotFound, AlreadyRunning, Validation)
- `app/api/migrations.py` — all migration endpoints
- `app/api/error_handlers.py` — global exception handlers

**APIs created:**
- `POST /api/migrations` — create migration
- `GET /api/migrations` — list all
- `GET /api/migrations/{id}` — get full state
- `POST /api/migrations/{id}/run` — execute workflow
- `GET /api/migrations/{id}/status` — pipeline visualisation
- `DELETE /api/migrations/{id}` — delete migration

**Tests:** 142 total (all Module 0C + 1 tests passing)

---

### Module 2 — Upload + MCP Filesystem
**Commit:** `9d03167`

**Files created:**
- `app/services/filesystem_service.py` — `FileSystemService` singleton, async I/O, per-migration asyncio locks, `create_project_dir()`, `save_files()`, `list_files()`, `read_file()`, `delete_project()`
- `app/mcp/filesystem_mcp.py` — `MCPFilesystem` MCP-style tool layer, path-traversal guard, `read_file()`, `write_file()`, `list_directory()`, `create_directory()`, `delete_directory()`, `file_exists()`, `get_file_info()`
- `app/utils/upload_validator.py` — extension allowlist, size limits (20 MB/file, 200 MB total), empty/duplicate checks
- `app/utils/zip_extractor.py` — async ZIP extraction, Zip-slip prevention, extension filtering, preserves subdirectory structure
- `app/api/upload.py` — upload/list/delete file endpoints

**Storage layout created:**
```
backend/storage/
├── uploads/{migration_id}/     ← uploaded .NET source files
├── generated/{migration_id}/   ← Java output (future modules)
└── temp/{migration_id}/        ← ephemeral working space
```

**APIs created:**
- `POST /api/migrations/{id}/upload` — multipart file upload
- `GET /api/migrations/{id}/files` — list uploaded files
- `DELETE /api/migrations/{id}/files` — delete all files for migration

**State fields added to `MigrationState`:**
- `project_root: str` — absolute path to `storage/uploads/{id}/`
- `last_upload_time: datetime | None`

**Parser node updated:** loads real files from disk via `FileSystemService` instead of dummy names.

**Tests:** 226 total (all modules passing)

---

### Module 3 — Frontend ↔ Backend Integration
**Commit:** `9ca3286`

**Files created:**
- `src/types/migration.ts` — complete TypeScript interfaces for all backend models (zero `any`)
- `src/lib/api.ts` — typed Axios client: `createMigration`, `getMigration`, `listMigrations`, `deleteMigration`, `uploadFiles` (with progress), `runMigration`, `getMigrationStatus`, `getHealthStatus`; `ApiClientError` wrapper
- `src/lib/query-client.ts` — `QueryClient` singleton + type-safe `queryKeys` factory
- `src/providers/query-provider.tsx` — `QueryClientProvider` wrapper
- `src/hooks/use-migration.ts` — all React Query hooks with live 3 s polling, cache invalidation, upload progress state
- `src/hooks/use-toast.ts` — custom DOM event-bus toast hook
- `src/components/toast-container.tsx` — toast renderer (auto-dismiss 4 s)
- `src/components/migration-status.tsx` — `MigrationStatusPanel` (progress bar, stage badges, stat cells, error display)

**Components updated:**
- `upload-card.tsx` — real multipart upload, progress bar, per-file remove, toast feedback
- `log-panel.tsx` — real `LogEntry[]` from backend, no setState-in-effect, live indicator
- `pipeline-view.tsx` — driven by `currentStage` + `completedStages` props
- `src/app/(shell)/dashboard/page.tsx` — fully integrated (create → upload → run → poll)
- `src/app/layout.tsx` — wraps with `QueryProvider` + `ToastContainer`

**Verified:** End-to-end flow works: create migration → upload 3 files → run workflow → `progress_pct: 100`, `stage: saved`

---

## 5. CURRENT API LIST

### Infrastructure

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Service health check — `{status, version, environment}` |
| `GET` | `/api/ai/status` | AI service liveness — `{gemini, embeddings, chromadb, tree_sitter, all_healthy}` |
| `GET` | `/api/ai/services` | Extended AI service details per subsystem |

### Migrations

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/migrations` | Create a migration — body: `{project_name, uploaded_files?}` |
| `GET` | `/api/migrations` | List all migrations — returns `{total, migrations[]}` |
| `GET` | `/api/migrations/{id}` | Get full `MigrationState` for one migration |
| `POST` | `/api/migrations/{id}/run` | Execute full 8-stage workflow — returns `{stage, is_complete, is_failed}` |
| `GET` | `/api/migrations/{id}/status` | Pipeline visualisation — `{current_stage, completed[], remaining[], progress_pct}` |
| `DELETE` | `/api/migrations/{id}` | Permanently delete migration from store |

### File Upload

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/migrations/{id}/upload` | Multipart upload — accepts `.cs .csproj .sln .config .xml .json .zip` |
| `GET` | `/api/migrations/{id}/files` | List files in `storage/uploads/{id}/` |
| `DELETE` | `/api/migrations/{id}/files` | Delete all filesystem files for migration |

### Swagger UI
Available at `http://localhost:8000/docs` — all endpoints with request/response schemas.

---

## 6. DATABASE AND STORAGE

### In-memory Migration Store
`MigrationService` uses a plain Python `dict[str, MigrationState]` with per-migration `asyncio.Lock`.  
**Not persisted** — all state is lost on server restart.  
⚠️ **Module 4+** should add SQLite or PostgreSQL persistence via SQLAlchemy async.

### ChromaDB
- **Path:** `backend/chroma_db/chroma.sqlite3`
- **Collection:** `migration_docs` (cosine similarity, HNSW index)
- **Current state:** Initialised and healthy, but **no documents embedded yet** (embedding pipeline not implemented)
- **Telemetry:** Disabled (`anonymized_telemetry=False`)

### File Storage
```
backend/storage/
├── uploads/{migration_id}/         Real uploaded .NET files (persists across restarts)
│   ├── UserService.cs
│   ├── OrderService.cs
│   └── App.csproj
├── generated/{migration_id}/       Java output — empty (Module 5+)
└── temp/{migration_id}/            Working space — empty (Module 5+)
```

### MigrationState Fields (key fields)
```python
migration_id: str              # UUID4, auto-generated
project_name: str
uploaded_files: list[str]      # relative filenames in storage/uploads/{id}/
project_root: str              # absolute path to storage/uploads/{id}/
last_upload_time: datetime
parsed_files: list[ParsedFile] # populated by parser_node (stubs in Module 3)
chunks: list[str]              # code chunks for embedding (Module 4+)
embeddings_created: bool
retrieved_context: list[str]   # RAG results (Module 5+)
generated_java_files: list[GeneratedFile]
compile_status: str            # pending | success | failed | skipped
current_stage: MigrationStage
completed_stages: list[MigrationStage]
logs: list[LogEntry]           # all pipeline log entries
errors: list[str]
```

---

## 7. WORKFLOW ARCHITECTURE

The workflow is a LangGraph `StateGraph` compiled once at startup. It uses `ainvoke` (async). All nodes receive and return a `dict` with key `"migration_state"`.

### Pipeline topology (linear)
```
START → parser_node → analyzer_node → embedding_node → rag_node
      → migration_node → compile_node → save_node → END
```

### Stage status per node

| Node | Stage advanced to | Implementation status |
|---|---|---|
| `parser_node` | `parsed` | **Partially real** — loads actual file list from disk via `FileSystemService`; builds `ParsedFile` stubs (no AST yet) |
| `analyzer_node` | `analyzed` | **Stub** — calls `AnalyzerAgent.run()`, stores mock result in context |
| `embedding_node` | `embedded` | **Stub** — creates one chunk per parsed file, sets `embeddings_created=True` |
| `rag_node` | `retrieved` | **Stub** — returns 3 hardcoded Java pattern strings |
| `migration_node` | `migrated` | **Stub** — calls `MigrationAgent.run()`, generates `GeneratedFile` stubs |
| `compile_node` | `compiled` | **Stub** — marks all files `compile_success=True` |
| `save_node` | `saved` | **Stub** — sets `context["output_path"]`, no real file write |

### Failure handling
- Every node is wrapped in a `try/except`; exceptions call `ms.mark_failed(reason)`
- Failed state short-circuits remaining nodes (each node checks `if ms.is_failed: return`)
- `WorkflowException` is raised to the API layer on unhandled graph errors

---

## 8. CURRENT AGENTS

### ParserAgent (`app/agents/base_agent.py`)
- **Registered name:** `parser_agent`
- **Status:** Stub
- **Current behaviour:** `validate()` checks for `source_code` or `project_path` in state; `run()` returns a placeholder `AgentResult` with `{"parsed": True, "message": "Parser stub"}`
- **Used by:** `parser_node` in workflow — the node itself does real file loading, but AST parsing is not implemented
- **Module 4 task:** Replace stub with real Tree-sitter C# parsing and code chunking

### AnalyzerAgent (`app/agents/base_agent.py`)
- **Registered name:** `analyzer_agent`
- **Status:** Stub
- **Current behaviour:** Always returns `{"analyzed": True, "message": "Analyzer stub"}`
- **Module 5 task:** Implement semantic analysis (type extraction, dependency graph, namespace mapping)

### MigrationAgent (`app/agents/base_agent.py`)
- **Registered name:** `migration_agent`
- **Status:** Stub
- **Current behaviour:** Always returns `{"migrated": True, "message": "Migration stub"}`
- **Module 6 task:** Implement actual Gemini 2.5 Flash translation using RAG context

### Agent Registry (`app/agents/registry.py`)
- **Singleton:** `agent_registry` (process-wide)
- All three agents auto-registered at import time
- Supports `register()`, `register_or_replace()`, `get()`, `list_agents()`, `is_registered()`
- New agents can be added via `@agent_registry.register` decorator

---

## 9. KNOWN ISSUES

### 1. Tree-sitter C# Grammar Missing — NON-BLOCKING
- **Issue:** `tree-sitter==0.23.2` is installed but neither `tree-sitter-languages` nor `tree-sitter-c-sharp` grammar package is installed
- **Effect:** `TreeSitterService` initialises in **stub/regex mode** (`using_stub=True`). Class and method extraction uses regex fallback — works for simple files, misses complex cases
- **Impact:** Non-blocking. Parser node in workflow uses file listing, not AST. Stub extracts class/method names correctly for basic cases
- **Fix in Module 4:** Install `tree-sitter-languages` or `tree-sitter-c-sharp` (the correct package for tree-sitter 0.23.x). See `_load_grammar()` in `tree_sitter_service.py`
- **Command:** `pip install tree-sitter-languages` (covers most grammars including C#)

### 2. Python 3.10 Google API Warning — NON-BLOCKING
- **Issue:** `google-api-core` emits a `FutureWarning` about Python 3.10 reaching end-of-life in October 2026
- **Effect:** Warning appears in test output and server logs; does not affect functionality
- **Impact:** Non-blocking. Everything works correctly on Python 3.10
- **Fix:** Upgrade to Python 3.11+ when convenient. The venv path is `backend/venv/`

### 3. ChromaDB Pydantic Deprecation Warning — NON-BLOCKING
- **Issue:** `chromadb` 0.5.23 accesses `model_fields` on instances (deprecated in Pydantic v2.11+)
- **Effect:** Warning in test output: `PydanticDeprecatedSince211: Accessing the 'model_fields' attribute on the instance is deprecated`
- **Impact:** Non-blocking. ChromaDB initialises and queries correctly
- **Fix:** Upgrade ChromaDB to 0.6+ when stable

### 4. Migration State Not Persisted — KNOWN LIMITATION
- **Issue:** `MigrationService` uses an in-memory `dict`; all state is lost on server restart
- **Effect:** After restarting the backend, all migrations disappear. Uploaded files in `storage/uploads/` persist (filesystem), but the migration record does not
- **Impact:** Non-blocking for development; blocking for production
- **Fix in Module 4 or later:** Add SQLite/PostgreSQL persistence via SQLAlchemy async

### 5. Starlette `httpx` Deprecation Warning in Tests — NON-BLOCKING
- **Issue:** `starlette.testclient` warns about using `httpx` and suggests `httpx2`
- **Impact:** Non-blocking. Tests pass correctly
- **Fix:** Install `httpx2` package when it becomes stable

### 6. `httpx2` / TestClient — NON-BLOCKING
- `fastapi.testclient` shows `StarletteDeprecationWarning`. Tests run correctly. No action needed.

---

## 10. NEXT MODULE

### Module 4 — Parser & Chunking

**Goal:** Replace the stub `ParserAgent` and `parser_node` with real Tree-sitter AST parsing and intelligent code chunking. This is the first module that implements actual AI pipeline logic.

**Requirements:**

#### What to implement:
1. **Install C# grammar** — `pip install tree-sitter-languages` and update `tree_sitter_service.py` to use it (the `_load_grammar()` method already tries `tree-sitter-languages` first)
2. **Real `parse_code()`** — return full class/method/property/namespace structure from AST
3. **Real `extract_classes()`** — populate `ClassInfo.classes`, `ClassInfo.methods`, `ClassInfo.lines` from Tree-sitter nodes
4. **Code chunking strategy** — split C# files into semantically meaningful chunks:
   - One chunk per class
   - One chunk per method (for large methods)
   - Max ~500 tokens per chunk
   - Preserve context (class name, namespace, file path) in each chunk
5. **Update `parser_node`** in `workflow.py`:
   - Load files from disk via `FileSystemService` (already done)
   - Parse each `.cs` file with `TreeSitterService`
   - Populate `MigrationState.parsed_files` with real `ParsedFile` objects
   - Populate `MigrationState.chunks` with code chunks
6. **Update `ParserAgent.run()`** — implement real parsing logic using `TreeSitterService`
7. **Regex fallback** — keep the existing regex stub as a fallback for files that fail Tree-sitter parsing

#### Files to modify:
- `app/parser/tree_sitter_service.py` — enable real grammar, improve `extract_classes()` and `extract_methods()`
- `app/agents/base_agent.py` — implement `ParserAgent.run()` with real logic
- `app/agents/workflow.py` — update `_parser_node()` to call real parsing and chunking
- `requirements.txt` — add `tree-sitter-languages` (or `tree-sitter-c-sharp`)

#### Files to create:
- `app/parser/chunker.py` — `CodeChunker` class with `chunk_file()`, `chunk_class()`, `chunk_method()` methods

#### Do NOT:
- Modify any existing API endpoints
- Break the frontend integration
- Change `MigrationState` field names (only populate existing `chunks` and `parsed_files` fields)
- Remove the regex fallback

#### Tests to create:
- `tests/test_parser.py` — test real C# parsing with known input
- `tests/test_chunker.py` — test chunking strategies
- Target: all 226 existing tests continue passing + new parser/chunker tests

---

## APPENDIX: LOCAL DEVELOPMENT SETUP

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# Add GEMINI_API_KEY to .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
# .env.local already contains NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### Run tests
```bash
cd backend
python -m pytest tests/ -v
# Expected: 226 passed
```

### Environment variables (backend `.env`)
```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_DB_PATH=./chroma_db
CHROMA_COLLECTION_NAME=migration_docs
STORAGE_ROOT=./storage
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
LOG_LEVEL=INFO
LOG_DIR=./logs
APP_ENV=development
CORS_ORIGINS=http://localhost:3000
```

### Git history
```
9ca3286  feat(frontend): Module 3 — full backend integration, API client, React Query, live polling
9d03167  feat(backend): Module 2 — file upload, MCP filesystem, ZIP extraction, storage layout
e90e5df  feat(backend): Module 1 — workflow engine, agent registry, migration service, orchestration API
35026a8  feat(backend): Module 0C — AI foundation: Gemini, embeddings, ChromaDB, Tree-sitter, LangGraph
438d353  feat(frontend): Module 0B — design system, layout, all pages
cac6ba6  fix: integrate frontend into monorepo (remove submodule)
fa0fa82  feat: initial project scaffolding — Module 0A
```
