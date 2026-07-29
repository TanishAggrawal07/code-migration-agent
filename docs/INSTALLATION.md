# Local Installation & Setup Guide

This guide provides step-by-step instructions for installing and running the **Code Migration Agent** locally for development and testing.

---

## 📋 Prerequisites

Before starting, ensure you have the following installed on your system:

- **Node.js**: `v18.0.0` or higher (Node.js 20+ recommended)
- **npm**: `v9.0.0` or higher
- **Python**: `v3.11` (Python 3.11.x recommended)
- **Git**: `v2.30` or higher
- **C++ Compiler** *(Optional)*: `gcc` / `g++` / MSVC (required for Tree-sitter native bindings; regex parser fallback will be used if absent)

---

## 🚀 Step-by-Step Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/code-migration-agent.git
cd code-migration-agent
```

---

### Step 2: Backend Setup (FastAPI)

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Linux / macOS:
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install required Python packages:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   # Create .env file from template
   cp .env.example .env
   ```

   Edit `.env` and set your preferred AI provider:
   ```env
   # Example: Groq Provider Configuration
   AI_PROVIDER=groq
   GROQ_API_KEY=gsk_your_groq_key_here

   # Example: Gemini Provider Configuration
   # AI_PROVIDER=gemini
   # GEMINI_API_KEY=your_gemini_key_here
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   - Backend URL: `http://localhost:8000`
   - API Health Check: `http://localhost:8000/health`
   - Interactive Swagger Docs: `http://localhost:8000/docs`

---

### Step 3: Frontend Setup (Next.js 16)

1. Open a new terminal window and navigate to `frontend/`:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Configure frontend environment variables:
   ```bash
   cp .env.example .env.local
   ```

   `.env.local` contents:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```

   - Frontend Web App: `http://localhost:3000`

---

## 🧪 Running Tests

### Backend Test Suite (Pytest)

The backend includes comprehensive unit and integration tests covering providers, services, parsers, and APIs:

```bash
cd backend
pytest tests/ -v
```

### End-to-End (E2E) Test Suite

Run the 8-step End-to-End test suite against a running local or remote instance:

```bash
cd backend
python e2e_deployed_groq_test.py
```
