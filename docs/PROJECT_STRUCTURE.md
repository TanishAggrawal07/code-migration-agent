# Repository Project Structure

```
code-migration-agent/
├── README.md                      # Primary project landing page & quickstart
├── docker-compose.yml             # Docker Compose stack definition (frontend + backend)
├── server.env                     # Server production environment template
├── bootstrap.sh                   # AWS EC2 initialization & swap setup script
├── cma-keypair.pem                # AWS SSH key pair
│
├── docs/                          # Centralized Project Documentation
│   ├── README.md                  # Centralized Documentation Index
│   ├── ARCHITECTURE.md            # System architecture specification
│   ├── WORKFLOW.md                # 14-stage migration workflow pipeline docs
│   ├── API.md                     # REST API reference and OpenAPI schema
│   ├── DEPLOYMENT.md              # AWS EC2 & Docker Compose deployment guide
│   ├── INSTALLATION.md            # Step-by-step local setup guide
│   ├── PROJECT_STRUCTURE.md       # Repository file directory reference
│   ├── TECHNOLOGY_STACK.md        # Consolidated technology stack specification
│   └── HANDOFF.md                 # Production state report and checklist
│
├── frontend/                      # Next.js 16 Web Application
│   ├── src/
│   │   ├── app/                   # App Router pages and layouts
│   │   │   ├── layout.tsx         # Root layout with Providers & Header
│   │   │   ├── page.tsx           # Home / Landing page
│   │   │   └── (shell)/           # Shell layout routes
│   │   │       ├── dashboard/     # Drag & drop migration dashboard
│   │   │       ├── migrations/    # Active & past migrations list
│   │   │       ├── history/       # Migration history & audit logs
│   │   │       ├── settings/      # AI Provider selection & server health
│   │   │       └── about/         # Architecture & documentation page
│   │   │
│   │   ├── components/            # UI components
│   │   │   ├── header.tsx         # Navigation header
│   │   │   ├── file-upload.tsx    # Drag-and-drop file uploader
│   │   │   ├── migration-stepper.tsx # Step-by-step visual progress bar
│   │   │   ├── log-panel.tsx      # Terminal-style real-time log viewer
│   │   │   ├── code-diff-viewer.tsx  # Side-by-side C# vs Java code diff
│   │   │   └── download-button.tsx# 1-click ZIP export download button
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts             # Typed Axios API client (dynamic hostname resolution)
│   │   │   └── utils.ts           # Classnames helper (cn)
│   │   │
│   │   └── types/
│   │       └── migration.ts       # TypeScript interfaces & API schemas
│   │
│   ├── public/                    # Static assets & SVG icons
│   ├── Dockerfile                 # Multi-stage Next.js production build
│   ├── .dockerignore              # Docker build exclusions for frontend
│   ├── package.json               # Node.js dependencies
│   ├── tsconfig.json              # TypeScript configuration
│   ├── README.md                  # Frontend documentation pointer
│   └── AGENTS.md                  # Frontend design rules and conventions
│
└── backend/                       # FastAPI Application & LangGraph Core
    ├── app/
    │   ├── api/                   # REST API route modules
    │   │   ├── migrations.py      # CRUD endpoints & workflow execution
    │   │   ├── upload.py          # File upload & ZIP extractor endpoint
    │   │   └── ai_status.py       # AI services & provider status endpoints
    │   │
    │   ├── agents/                # LangGraph agents & workflow
    │   │   ├── workflow.py        # 7-node LangGraph StateGraph engine
    │   │   ├── state.py           # MigrationState model & logs
    │   │   ├── base_agent.py      # Abstract agent & Java output cleaner
    │   │   └── registry.py        # Agent registry manager
    │   │
    │   ├── analyzer/              # AST & Structural Code Analyzer
    │   │   └── analyzer_service.py # Extracts classes, methods, imports, dependencies
    │   │
    │   ├── parser/                # Code Parser
    │   │   ├── parser_service.py  # Hybrid Tree-sitter & Regex parser
    │   │   └── tree_sitter_service.py # Tree-sitter AST parser
    │   │
    │   ├── embeddings/            # Embeddings Generator
    │   │   └── service.py         # SentenceTransformers all-MiniLM-L6-v2
    │   │
    │   ├── vectorstore/           # ChromaDB Persistence Layer
    │   │   ├── chroma_service.py  # Persistent ChromaDB client
    │   │   └── indexing_service.py# Chunk indexing & vector retrieval
    │   │
    │   ├── rag/                   # Retrieval-Augmented Generation
    │   │   └── retrieval_service.py # Semantic similarity search for context
    │   │
    │   ├── core/                  # System Infrastructure
    │   │   ├── config.py          # Pydantic v2 Settings singleton
    │   │   ├── llm_providers.py   # Multi-provider LLM abstraction layer
    │   │   ├── gemini_client.py   # LLM Provider Facade & initializer
    │   │   ├── exceptions.py      # Custom exception hierarchy
    │   │   ├── logger.py          # Structlog & standard logging setup
    │   │   └── startup.py         # Subsystem boot checks & state tracking
    │   │
    │   ├── services/              # Business Logic Services
    │   │   ├── filesystem_service.py # Physical storage manager
    │   │   └── migration_service.py  # In-memory & file state manager
    │   │
    │   └── utils/                 # Utilities & Post-Processing
    │       ├── java_post_processor.py # Package formatting, mock generation, javac check
    │       ├── upload_validator.py # Multipart upload validator
    │       └── zip_extractor.py   # Decompression helper for .zip archives
    │
    ├── tests/                     # Pytest Unit & Integration Test Suite
    │   ├── test_migrations_api.py
    │   ├── test_upload_api.py
    │   ├── test_migration_agent.py
    │   ├── test_java_post_processor.py
    │   ├── test_indexing_service.py
    │   ├── test_retrieval_service.py
    │   ├── test_analyzer_service.py
    │   └── test_parser_service.py
    │
    ├── e2e_deployed_groq_test.py  # Automated E2E verification test suite
    ├── Dockerfile                 # Multi-stage Python 3.11 production build
    ├── .dockerignore              # Docker build exclusions for backend
    ├── main.py                    # FastAPI application entry point
    └── requirements.txt           # Python dependency manifest
```
