# Contributing to MiroFish

## Development Setup

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **uv** (Python package manager) — install via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **API Keys:** You need a `.env` file with `LLM_API_KEY` and `ZEP_API_KEY` (see `.env.example`)

### Quick Start

```bash
# Clone
git clone https://github.com/shawnchauhan/MiroFish.git
cd MiroFish

# Configure
cp .env.example .env
# Edit .env with your API keys

# Install all dependencies (frontend + backend)
npm run setup:all

# Start development servers
npm run dev
```

This starts:
- **Frontend** at `http://localhost:3000` (Vite dev server with HMR)
- **Backend** at `http://localhost:5001` (Flask with auto-reload)

The frontend proxies `/api/*` requests to the backend automatically via Vite config.

### Manual Setup

**Frontend only:**
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

**Backend only:**
```bash
cd backend
uv sync            # Install Python deps via uv
uv run python run.py   # http://localhost:5001
```

### Docker

```bash
cp .env.example .env
docker compose up -d
```

Single container exposes both ports 3000 and 5001.

---

## Project Layout

| Directory | What lives here |
|-----------|----------------|
| `frontend/src/views/` | Page-level Vue components (one per route) |
| `frontend/src/components/` | Step components (Step1-5) and shared UI |
| `frontend/src/api/` | Axios API clients — one per backend blueprint |
| `backend/app/api/` | Flask blueprints — REST endpoint handlers |
| `backend/app/services/` | Core business logic (graph building, simulation, reporting) |
| `backend/app/models/` | Data models with file-based persistence |
| `backend/app/utils/` | Shared utilities (LLM client, file parsing, retry, logging) |
| `backend/scripts/` | Standalone OASIS simulation runner scripts |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical architecture.

---

## How the 5-Step Pipeline Works

Understanding the pipeline is essential before making changes:

1. **Graph Build** — User uploads documents. Backend extracts text, generates ontology via LLM, builds a Zep knowledge graph.
2. **Environment Setup** — Entities from the graph become OASIS agent profiles. LLM generates simulation config.
3. **Simulation** — OASIS runs as a subprocess. Agents interact on simulated Twitter/Reddit. Actions feed back into the graph.
4. **Report** — ReACT agent queries the evolved graph and writes an analytical report section-by-section.
5. **Interaction** — User chats with the Report Agent or interviews individual simulation agents.

Each step has a corresponding:
- **Frontend component** (`Step{N}*.vue`) with its own state and polling logic
- **API blueprint** (`backend/app/api/`) handling HTTP endpoints
- **Service layer** (`backend/app/services/`) with the actual business logic

---

## Key Patterns

### Async Tasks

Long-running operations (graph build, simulation prep, report generation) follow this pattern:

1. POST endpoint creates a `Task` via `TaskManager`, returns `task_id`
2. Background thread does the work, updating progress via `TaskManager.update_task()`
3. Frontend polls a status endpoint every 2 seconds
4. On completion, results are in the task object and persisted to disk

### File-Based Persistence

No external database. Each entity gets a directory:
- `uploads/projects/<project_id>/` — project metadata, uploaded files, extracted text
- `uploads/simulations/<sim_id>/` — state, profiles (CSV/JSON), config, action logs
- `uploads/reports/<report_id>/` — report metadata, sections, agent logs

### LLM Integration

All LLM calls go through `backend/app/utils/llm_client.py` which wraps the OpenAI SDK. The client:
- Supports any OpenAI-compatible API (configurable `LLM_BASE_URL`)
- Strips `<think>` blocks from reasoning models
- Has a `chat_json()` method for structured JSON responses

### Subprocess Simulation

OASIS simulations run as separate Python processes (`backend/scripts/run_*.py`). Communication uses file-based IPC (`simulation_ipc.py`) — command files written to a shared directory, responses read back.

---

## Making Changes

### Adding a New API Endpoint

1. Add the route handler in the relevant blueprint (`backend/app/api/graph.py`, `simulation.py`, or `report.py`)
2. Add business logic in a service (`backend/app/services/`)
3. Add the frontend API call in `frontend/src/api/`
4. Wire it into the relevant Step component

### Modifying the Ontology/Graph Pipeline

- Ontology schema: `backend/app/services/ontology_generator.py` — modify LLM prompts and validation
- Graph construction: `backend/app/services/graph_builder.py` — modify chunking, Zep interactions
- Text extraction: `backend/app/utils/file_parser.py` — add support for new file types

### Modifying Simulation Behavior

- Agent profiles: `backend/app/services/oasis_profile_generator.py`
- Simulation config: `backend/app/services/simulation_config_generator.py`
- OASIS scripts: `backend/scripts/run_twitter_simulation.py` and `run_reddit_simulation.py`
- Available actions are defined in `backend/app/config.py` (`OASIS_TWITTER_ACTIONS`, `OASIS_REDDIT_ACTIONS`)

### Modifying Report Generation

- Report structure: `backend/app/services/report_agent.py` — modify outline generation and section writing
- Search tools: `backend/app/services/zep_tools.py` — InsightForge, PanoramaSearch, QuickSearch
- Report config: `backend/app/config.py` — temperature, max tool calls, reflection rounds

---

## External Service Dependencies

| Service | What it does | How to get access |
|---------|-------------|------------------|
| **LLM API** | Powers all AI features (ontology, profiles, config, reports, chat) | Any OpenAI-compatible API. Recommended: Alibaba Qwen via Bailian |
| **Zep Cloud** | Knowledge graph storage, entity extraction, semantic search | Sign up at [getzep.com](https://www.getzep.com/) |
| **OASIS** | Multi-agent social simulation engine | Installed as Python package (`camel-oasis`) |

---

## Code Style

- **Frontend:** Vue 3 Composition API with `<script setup>`, standard Vue conventions
- **Backend:** Flask blueprints, Python type hints where practical, PEP 8
- **Naming:** camelCase in frontend JS, snake_case in backend Python
- **No test framework currently configured** — contributions adding tests are welcome

## License

MiroFish is licensed under the [Mulan PSL v2](LICENSE).
