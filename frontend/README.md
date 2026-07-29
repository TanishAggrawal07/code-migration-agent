# Code Migration Agent — Frontend Web Application

> Next.js 16 Web Dashboard for the Code Migration Agent platform.

---

## 🎨 Overview

The frontend is a modern Next.js 16 application built with App Router and Turbopack. It provides a real-time migration control center where users can drag-and-drop .NET projects, view AST analysis, monitor real-time migration logs, inspect side-by-side C# vs Java code diffs, and download converted Java ZIP packages.

---

## 🚀 Key Features

- **Dynamic API Server Resolution**: `api.ts` automatically resolves the backend API URL dynamically based on `window.location.hostname` in the client's browser, eliminating hardcoded host issues across deployments.
- **Drag-and-Drop Uploader**: Accepts single `.cs` source files or complete `.zip` archives.
- **Live Progress Stepper**: Visual 8-step progress bar showing active stage (`uploaded` → `parsed` → `analyzed` → `embedded` → `retrieved` → `migrated` → `compiled` → `saved`).
- **Real-Time Log Streamer**: Terminal-style log panel displaying system events, LLM status, and error logs with auto-scroll.
- **Side-by-Side Code Diff**: Syntax-highlighted side-by-side view comparing original C# code against generated Java code.
- **1-Click ZIP Package Export**: Native browser download button for exporting converted Java projects.
- **Theme System**: Modern dark/light theme toggle with custom glassmorphic UI elements.

---

## 📂 Page Routes

| Route | Component File | Description |
|---|---|---|
| `/` | `src/app/page.tsx` | Landing page with hero banner and feature overview |
| `/dashboard` | `src/app/(shell)/dashboard/page.tsx` | Main migration workspace and control center |
| `/migrations` | `src/app/(shell)/migrations/page.tsx` | Active and past migration job management |
| `/history` | `src/app/(shell)/history/page.tsx` | Historical migration audit logs |
| `/settings` | `src/app/(shell)/settings/page.tsx` | AI provider configuration and backend server status |
| `/about` | `src/app/(shell)/about/page.tsx` | System architecture & documentation |

---

## 🛠️ Development & Building

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Lint codebase
npm run lint

# Build production bundle (standalone output for Docker)
npm run build
```

---

## 🐳 Docker Container

The frontend is packaged using a multi-stage `Dockerfile` with Next.js `standalone` output mode:

- **Image Size**: ~271 MB
- **Ports**: Exposed on port `3000` (mapped to port `80` and `3000` in `docker-compose.yml`).
