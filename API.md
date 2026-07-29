# REST API Reference

The backend API is implemented with **FastAPI 0.115** and provides JSON endpoints for managing code migrations, inspecting system health, querying LLM provider statuses, and downloading generated artifacts.

---

## 🌐 Base Server URLs

- **Local Server**: `http://localhost:8000`
- **AWS EC2 Production**: `http://3.109.164.178:8000`
- **Interactive OpenAPI Docs**: `http://3.109.164.178:8000/docs`
- **ReDoc Documentation**: `http://3.109.164.178:8000/redoc`

---

## 📋 Endpoints Overview

### 1. System Liveness

#### `GET /health`
Returns the status of the FastAPI backend application.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "production"
}
```

---

### 2. AI Subsystems & Provider Registry

#### `GET /api/ai/status`
Returns initialization status for core AI subsystems (LLM, Embeddings, ChromaDB, Tree-sitter).

**Response `200 OK`**:
```json
{
  "gemini": true,
  "embeddings": true,
  "chromadb": true,
  "tree_sitter": true,
  "all_healthy": true
}
```

#### `GET /api/ai/provider`
Returns details on the currently selected active LLM provider and model.

**Response `200 OK`**:
```json
{
  "configured_provider": "groq",
  "active_provider": "groq",
  "active_model": "llama-3.3-70b-versatile",
  "initialized": true
}
```

#### `GET /api/ai/providers`
Returns availability status for all 6 registered providers in the Provider Registry.

**Response `200 OK`**:
```json
{
  "providers": [
    { "key": "ollama", "available": false, "model": "qwen2.5-coder:7b", "models": [] },
    { "key": "groq", "available": true, "model": "llama-3.3-70b-versatile", "api_key_set": true },
    { "key": "gemini", "available": true, "model": "gemini-2.5-flash", "api_key_set": true },
    { "key": "openrouter", "available": false, "model": "openai/gpt-4o-mini", "api_key_set": false },
    { "key": "grok", "available": false, "model": "grok-2-1212", "api_key_set": false },
    { "key": "openai", "available": false, "model": "gpt-4o-mini", "api_key_set": false }
  ],
  "auto_selection_order": ["ollama", "groq", "gemini", "openrouter", "grok", "openai"]
}
```

#### `GET /api/ai/services`
Returns detailed runtime service configuration including device allocation (CPU/GPU) and package availability.

---

### 3. Migrations Management Lifecycle

#### `POST /api/migrations`
Create a new code migration job.

**Request Body**:
```json
{
  "project_name": "Calculator Service Migration",
  "source_framework": ".NET Core C#",
  "target_framework": "Spring Boot 3 Java"
}
```

**Response `200 OK` / `201 Created`**:
```json
{
  "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
  "project_name": "Calculator Service Migration",
  "status": "created",
  "message": "Migration created successfully"
}
```

#### `GET /api/migrations`
List all recorded migration jobs.

**Response `200 OK`**:
```json
{
  "total": 1,
  "migrations": [
    {
      "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
      "project_name": "Calculator Service Migration",
      "status": "created",
      "current_stage": "saved",
      "created_at": "2026-07-29T17:59:29.123456Z"
    }
  ]
}
```

#### `GET /api/migrations/{migration_id}`
Retrieve complete state, context, logs, and generated files for a migration job.

**Response `200 OK`**:
```json
{
  "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
  "project_name": "Calculator Service Migration",
  "current_stage": "saved",
  "completed_stages": ["uploaded", "parsed", "analyzed", "embedded", "retrieved", "migrated", "compiled"],
  "logs": [
    {
      "level": "SUCCESS",
      "message": "[SUCCESS] Migration completed via groq/llama-3.3-70b-versatile",
      "stage": "migrated",
      "timestamp": "2026-07-29T17:59:32.000000Z"
    }
  ],
  "context": {
    "generated_file_contents": {
      "com/myapp/services/CalculatorService.java": "package com.myapp.services;\n\npublic class CalculatorService {\n..."
    },
    "active_provider_key": "groq",
    "active_model": "llama-3.3-70b-versatile"
  }
}
```

#### `POST /api/migrations/{migration_id}/upload`
Upload C# source files or `.zip` archives.

- **Content-Type**: `multipart/form-data`
- **Body**: `files` (one or more binary file streams)

**Response `200 OK`**:
```json
{
  "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
  "status": "uploaded",
  "file_count": 1,
  "files": [
    {
      "filename": "CalculatorService.cs",
      "size": 262,
      "extension": ".cs"
    }
  ]
}
```

#### `POST /api/migrations/{migration_id}/run`
Trigger async execution of the 7-node LangGraph migration pipeline.

**Response `200 OK`**:
```json
{
  "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
  "status": "running",
  "message": "Workflow started successfully"
}
```

#### `GET /api/migrations/{migration_id}/status`
Get lightweight visualization state for frontend progress bars.

**Response `200 OK`**:
```json
{
  "migration_id": "df4efaf1-1ae8-4605-9f4d-3945685907c1",
  "current_stage": "saved",
  "progress_percentage": 100,
  "is_running": false,
  "is_completed": true,
  "is_failed": false
}
```

#### `GET /api/migrations/{migration_id}/download`
Download the generated Java project as a `.zip` archive.

- **Response `200 OK`**: Binary stream (`application/zip`) with `Content-Disposition: attachment; filename="migration_{id}.zip"`.

#### `DELETE /api/migrations/{migration_id}/files`
Delete uploaded files for a migration job (`204 No Content`).

#### `DELETE /api/migrations/{migration_id}`
Permanently delete a migration job (`204 No Content`).
