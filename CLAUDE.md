# MiroFish Development Context

## What is MiroFish?

A swarm intelligence prediction engine. Users upload documents, build knowledge graphs, spawn AI agents with personas derived from graph entities, run social media simulations (Twitter + Reddit), and get analytical prediction reports.

## Quick Start

```bash
cp .env.example .env   # Add LLM_API_KEY and ZEP_API_KEY
npm run setup:all      # Install frontend + backend deps
npm run dev            # Start both servers (localhost:3000 + :5001)
```

## Stack

- **Frontend:** Vue 3 + Vite + D3.js + Axios (port 3000)
- **Backend:** Flask + Python 3.11 (port 5001)
- **LLM:** OpenAI-compatible API (configured via .env)
- **Knowledge Graph:** Zep Cloud (GraphRAG)
- **Simulation:** OASIS (camel-ai/oasis)
- **No database** — file-based persistence in `backend/uploads/`

## Architecture

The app is a 5-step wizard pipeline:

1. **Graph Build** — Upload docs → LLM generates ontology → Zep builds knowledge graph
2. **Env Setup** — Graph entities → OASIS agent profiles + LLM-generated sim config
3. **Simulation** — OASIS subprocess runs Twitter/Reddit simulation with LLM agents
4. **Report** — ReACT agent queries graph + writes report section-by-section
5. **Interaction** — Chat with Report Agent or interview individual agents

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

## Key Files

### Backend entry points
- `backend/run.py` — Flask app entry point
- `backend/app/config.py` — All config loaded from .env
- `backend/app/__init__.py` — App factory, blueprint registration

### Backend API blueprints
- `backend/app/api/graph.py` — `/api/graph/*` endpoints
- `backend/app/api/simulation.py` — `/api/simulation/*` endpoints
- `backend/app/api/report.py` — `/api/report/*` endpoints

### Core services
- `backend/app/services/ontology_generator.py` — LLM-based ontology from documents
- `backend/app/services/graph_builder.py` — Zep graph creation and text ingestion
- `backend/app/services/oasis_profile_generator.py` — Entity → OASIS agent profiles
- `backend/app/services/simulation_config_generator.py` — LLM-generated sim params
- `backend/app/services/simulation_manager.py` — Simulation lifecycle orchestration
- `backend/app/services/simulation_runner.py` — Subprocess management for OASIS
- `backend/app/services/report_agent.py` — ReACT-pattern report generation + chat
- `backend/app/services/zep_tools.py` — Graph search tools (InsightForge, PanoramaSearch, QuickSearch)

### Frontend
- `frontend/src/views/` — Page-level components (one per route)
- `frontend/src/components/` — Step1-5 components + GraphPanel (D3 visualization)
- `frontend/src/api/` — Axios clients matching backend blueprints

## Common Patterns

### Async tasks
Long operations return a `task_id` immediately. A background thread does the work, updating progress via `TaskManager`. Frontend polls status every 2s.

### LLM calls
All go through `backend/app/utils/llm_client.py` — wraps OpenAI SDK, strips `<think>` tags from reasoning models, supports JSON mode.

### File persistence
Each project/simulation/report gets a directory under `backend/uploads/`. No SQL.

### Simulation subprocess
OASIS runs as a separate process (`backend/scripts/run_*.py`). IPC via file-based commands in a shared directory.

## Running Tests

No test framework is currently configured.

## Environment Variables

Required:
- `LLM_API_KEY` — OpenAI-compatible LLM API key
- `ZEP_API_KEY` — Zep Cloud API key

Optional:
- `LLM_BASE_URL` — Custom LLM endpoint (default: OpenAI)
- `LLM_MODEL_NAME` — Model name (default: gpt-4o-mini)
- `LLM_BOOST_*` — Secondary LLM for performance-critical calls

## Useful Commands

```bash
npm run dev            # Start both frontend + backend
npm run dev:frontend   # Frontend only
npm run dev:backend    # Backend only
npm run setup:all      # Install all deps
npm run build          # Build frontend for production
```
