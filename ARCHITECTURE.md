# MiroFish Architecture

> A next-generation AI prediction engine powered by multi-agent swarm intelligence simulation.

## High-Level Overview

MiroFish is a full-stack application that takes seed documents (news articles, reports, novel texts), builds a knowledge graph from them, spawns AI agents with distinct personalities derived from the graph entities, runs social media simulations across Twitter and Reddit-like platforms, and produces analytical prediction reports — all orchestrated through a 5-step wizard UI.

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3 + Vite)                 │
│  Home → Step 1 (Graph) → Step 2 (Env) → Step 3 (Sim) →    │
│  Step 4 (Report) → Step 5 (Interaction)                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (axios)
┌──────────────────────────▼──────────────────────────────────┐
│                  Backend (Flask + Python 3.11)               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐         │
│  │ Graph API │  │ Simulation   │  │  Report API   │         │
│  │ Blueprint │  │ API Blueprint│  │  Blueprint    │         │
│  └─────┬─────┘  └──────┬───────┘  └──────┬────────┘         │
│        │               │                 │                   │
│  ┌─────▼─────┐  ┌──────▼───────┐  ┌──────▼────────┐        │
│  │  Services  │  │  Services    │  │  Services     │        │
│  │ (Graph     │  │ (Simulation  │  │ (Report Agent │        │
│  │  Builder,  │  │  Manager,    │  │  Zep Tools)   │        │
│  │  Ontology) │  │  Runner,IPC) │  │               │        │
│  └─────┬──────┘  └──────┬───────┘  └──────┬────────┘        │
└────────┼────────────────┼─────────────────┼─────────────────┘
         │                │                 │
    ┌────▼────┐    ┌──────▼──────┐   ┌──────▼──────┐
    │ Zep Cloud│    │ OASIS Engine│   │ LLM (OpenAI │
    │ (GraphRAG│    │ (camel-ai/  │   │  compatible) │
    │  Memory) │    │  oasis)     │   │              │
    └─────────┘    └─────────────┘   └──────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Vue 3, Vue Router, Vite 7, D3.js, Axios | SPA with graph visualization |
| **Backend** | Flask 3, Flask-CORS, Python 3.11+ | REST API server |
| **LLM** | OpenAI SDK (any compatible API) | Ontology generation, profile generation, config generation, report writing, agent chat |
| **Knowledge Graph** | Zep Cloud API | GraphRAG — entity/relationship extraction, graph storage, semantic search |
| **Simulation Engine** | OASIS (camel-ai/oasis v0.2.5) | Multi-agent social media simulation (Twitter + Reddit) |
| **Package Management** | npm (frontend), uv (backend) | Dependency management |
| **Deployment** | Docker, docker-compose | Containerized deployment |

## Project Structure

```
MiroFish/
├── package.json              # Root orchestrator (concurrently runs frontend + backend)
├── docker-compose.yml        # Single-container deployment
├── Dockerfile                # Python 3.11 + Node.js + uv
├── .env.example              # LLM_API_KEY, ZEP_API_KEY, optional boost LLM
│
├── frontend/                 # Vue 3 SPA
│   ├── src/
│   │   ├── main.js           # App entry, mounts Vue + Router
│   │   ├── App.vue           # Root component (just <router-view>)
│   │   ├── router/index.js   # 6 routes: Home, Process, Simulation, SimulationRun, Report, Interaction
│   │   ├── api/              # Axios API clients
│   │   │   ├── index.js      # Axios instance (baseURL localhost:5001, 5min timeout, retry logic)
│   │   │   ├── graph.js      # Graph API calls (ontology, build, task status, graph data)
│   │   │   ├── simulation.js # Simulation API calls (create, prepare, start, stop, status, interview)
│   │   │   └── report.js     # Report API calls (generate, status, chat, sections, download)
│   │   ├── views/            # Page-level components
│   │   │   ├── Home.vue      # Landing page, project list, create new project
│   │   │   ├── MainView.vue  # Main workspace: split-pane with graph + step panels
│   │   │   ├── SimulationView.vue
│   │   │   ├── SimulationRunView.vue
│   │   │   ├── ReportView.vue
│   │   │   └── InteractionView.vue
│   │   ├── components/       # Reusable UI components
│   │   │   ├── GraphPanel.vue          # D3-powered knowledge graph visualization
│   │   │   ├── Step1GraphBuild.vue     # Upload docs + generate ontology + build graph
│   │   │   ├── Step2EnvSetup.vue       # Entity filtering + profile generation + config
│   │   │   ├── Step3Simulation.vue     # Run simulation, real-time round tracking
│   │   │   ├── Step4Report.vue         # Report generation with progress + section streaming
│   │   │   ├── Step5Interaction.vue    # Chat with Report Agent and individual agents
│   │   │   └── HistoryDatabase.vue     # History/project browser
│   │   ├── store/
│   │   │   └── pendingUpload.js        # Temporary upload state management
│   │   └── assets/                     # Logos and images
│   └── vite.config.js
│
├── backend/
│   ├── run.py                # Entry point: validates config, starts Flask on port 5001
│   ├── pyproject.toml        # Python deps: flask, openai, zep-cloud, camel-oasis, PyMuPDF, pydantic
│   ├── app/
│   │   ├── __init__.py       # Flask app factory: CORS, blueprints, cleanup hooks
│   │   ├── config.py         # Centralized config from .env (LLM, Zep, OASIS, uploads)
│   │   ├── api/              # Flask Blueprints (REST endpoints)
│   │   │   ├── __init__.py   # Registers graph_bp, simulation_bp, report_bp
│   │   │   ├── graph.py      # /api/graph/* — ontology, build, task status, graph data, project CRUD
│   │   │   ├── simulation.py # /api/simulation/* — create, prepare, start, stop, status, interview, profiles
│   │   │   └── report.py     # /api/report/* — generate, status, get, chat, sections, agent-log, download
│   │   ├── models/           # Data models (in-memory + file-persisted)
│   │   │   ├── project.py    # Project: status machine (created→ontology→building→completed)
│   │   │   └── task.py       # TaskManager: thread-safe singleton for async task tracking
│   │   ├── services/         # Core business logic
│   │   │   ├── ontology_generator.py        # LLM-based ontology design from documents
│   │   │   ├── graph_builder.py             # Zep graph creation, ontology setting, text ingestion
│   │   │   ├── text_processor.py            # Text chunking with overlap
│   │   │   ├── zep_entity_reader.py         # Read + filter entities from Zep graph
│   │   │   ├── oasis_profile_generator.py   # Convert graph entities → OASIS agent profiles (LLM-enhanced)
│   │   │   ├── simulation_config_generator.py # LLM-generated simulation parameters (time, events, activity)
│   │   │   ├── simulation_manager.py        # Simulation lifecycle (create → prepare → ready → run)
│   │   │   ├── simulation_runner.py         # Subprocess management for OASIS simulation scripts
│   │   │   ├── simulation_ipc.py            # File-based IPC between Flask and simulation subprocess
│   │   │   ├── zep_graph_memory_updater.py  # Feed simulation activity back into Zep graph (temporal memory)
│   │   │   ├── zep_tools.py                 # Graph search tools: InsightForge, PanoramaSearch, QuickSearch
│   │   │   └── report_agent.py              # ReACT-pattern report generation + conversational agent
│   │   └── utils/
│   │       ├── llm_client.py    # OpenAI-compatible LLM wrapper
│   │       ├── file_parser.py   # PDF/MD/TXT text extraction (PyMuPDF)
│   │       ├── zep_paging.py    # Paginated fetch for Zep nodes/edges
│   │       ├── logger.py        # Structured logging setup
│   │       └── retry.py         # Retry utilities
│   ├── scripts/               # Standalone simulation runner scripts
│   │   ├── run_twitter_simulation.py
│   │   ├── run_reddit_simulation.py
│   │   ├── run_parallel_simulation.py
│   │   ├── action_logger.py
│   │   └── test_profile_format.py
│   └── uploads/               # Runtime data directory (gitignored)
│       ├── projects/          # Per-project files, extracted text, ontology
│       ├── simulations/       # Per-simulation state, profiles, configs, action logs
│       └── reports/           # Generated reports, sections, agent logs
│
└── static/                    # README images and screenshots
```

## Core Workflow (5 Steps)

The application follows a strict 5-step pipeline, each backed by specific API endpoints and services:

### Step 1: Graph Building

**Purpose:** Extract knowledge from seed documents and build a structured knowledge graph.

**Flow:**
1. User uploads documents (PDF, MD, TXT) along with a natural-language simulation requirement
2. `FileParser` extracts text from uploaded files
3. `TextProcessor` preprocesses the text
4. `OntologyGenerator` calls the LLM to analyze the text and design an ontology (entity types like `Person`, `Organization`, `Media` with attributes; edge types like `works_for`, `criticizes` with source/target constraints)
5. `GraphBuilderService` creates a Zep Standalone Graph, sets the ontology schema, chunks the text, and ingests it in batches
6. Zep processes the text asynchronously — the backend polls episode `processed` status
7. The resulting graph (nodes + edges) is returned and visualized in the `GraphPanel` component using D3.js

**Key APIs:**
- `POST /api/graph/ontology/generate` — Upload files + get ontology (synchronous)
- `POST /api/graph/build` — Start async graph construction (returns task_id)
- `GET /api/graph/task/<task_id>` — Poll build progress
- `GET /api/graph/data/<graph_id>` — Fetch graph nodes/edges for visualization

### Step 2: Environment Setup

**Purpose:** Transform graph entities into simulation-ready AI agent profiles.

**Flow:**
1. `ZepEntityReader` reads all nodes from the Zep graph and filters to defined entity types
2. `OasisProfileGenerator` converts each entity into an OASIS-compatible agent profile:
   - Optionally enriches profiles via Zep graph search for additional context
   - Uses LLM to generate detailed personas (bio, personality, MBTI, interests)
   - Supports parallel generation for speed
   - Outputs Twitter CSV or Reddit JSON format as required by OASIS
3. `SimulationConfigGenerator` uses the LLM to intelligently determine simulation parameters:
   - Time configuration (simulated duration, rounds)
   - Per-agent activity schedules (with China timezone awareness)
   - Event injection timing
   - Platform-specific settings (available actions for Twitter vs Reddit)

**Key APIs:**
- `POST /api/simulation/create` — Initialize simulation state
- `POST /api/simulation/prepare` — Async: entity reading → profile generation → config generation
- `POST /api/simulation/prepare/status` — Poll preparation progress

### Step 3: Simulation

**Purpose:** Run multi-agent social media simulations on dual platforms.

**Flow:**
1. `SimulationRunner` launches OASIS simulation scripts as subprocesses
2. Scripts (in `backend/scripts/`) run Twitter and/or Reddit simulations in parallel
3. Each round, agents autonomously choose actions (CREATE_POST, LIKE, REPOST, COMMENT, FOLLOW, etc.) based on their personas
4. `SimulationIPC` provides file-based inter-process communication between Flask and the simulation subprocess (commands directory + responses directory)
5. `ZepGraphMemoryManager` feeds agent activities back into the Zep graph as temporal episodes, enabling the graph to evolve with the simulation
6. Action logs are recorded per-round with agent names, action types, and content

**Key APIs:**
- `POST /api/simulation/<id>/start` — Launch simulation subprocess
- `GET /api/simulation/<id>/status` — Real-time round progress
- `POST /api/simulation/<id>/stop` — Graceful shutdown
- `GET /api/simulation/<id>/actions` — Action log retrieval
- `POST /api/simulation/<id>/interview` — Interview a specific agent mid-simulation

### Step 4: Report Generation

**Purpose:** Generate analytical prediction reports from simulation results.

**Flow:**
1. `ReportAgent` uses a ReACT (Reasoning + Acting) pattern:
   - **Planning phase:** LLM designs a report outline (sections and their goals)
   - **Generation phase:** For each section, the agent iteratively:
     - Reasons about what information is needed
     - Calls retrieval tools (InsightForge, PanoramaSearch, QuickSearch) to query the Zep graph
     - Reflects on gathered information
     - Writes the section content
2. Sections are saved incrementally — the frontend can stream sections as they complete
3. `ReportLogger` records every agent action (tool calls, LLM responses) for transparency
4. Final report is a Markdown document downloadable by the user

**Zep Retrieval Tools (`zep_tools.py`):**
- **InsightForge** — Deep hybrid search: auto-generates sub-questions, searches across multiple dimensions
- **PanoramaSearch** — Broad search including expired/historical content
- **QuickSearch** — Fast single-query search

**Key APIs:**
- `POST /api/report/generate` — Async report generation (returns task_id + report_id)
- `GET /api/report/<id>/progress` — Real-time progress
- `GET /api/report/<id>/sections` — Stream completed sections
- `GET /api/report/<id>/agent-log` — Incremental agent action log
- `GET /api/report/<id>` — Full report content

### Step 5: Deep Interaction

**Purpose:** Chat with the Report Agent or individual simulation agents.

**Flow:**
1. **Report Agent Chat:** Users ask follow-up questions; the agent autonomously calls graph retrieval tools to find answers
2. **Agent Interview:** Users can talk to any specific agent from the simulation, asking about their reasoning and actions

**Key APIs:**
- `POST /api/report/chat` — Conversational interaction with Report Agent
- `POST /api/simulation/<id>/interview` — Chat with a specific simulation agent

## Data Flow & Persistence

### State Management

MiroFish uses **file-based persistence** (no external database):

| Entity | Storage Location | Format |
|--------|-----------------|--------|
| Projects | `uploads/projects/<project_id>/` | `project.json`, extracted text, uploaded files |
| Tasks | In-memory (singleton `TaskManager`) | Thread-safe dict with lock |
| Simulations | `uploads/simulations/<sim_id>/` | `state.json`, profiles (CSV/JSON), config, action logs |
| Reports | `uploads/reports/<report_id>/` | `report.json`, `section_*.md`, `agent_log.jsonl`, `console.log` |

### External Service Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| **LLM API** (OpenAI-compatible) | Ontology design, profile generation, config generation, report writing, chat | Yes |
| **Zep Cloud** | Knowledge graph storage, GraphRAG search, temporal memory | Yes |
| **OASIS** (bundled Python package) | Social media multi-agent simulation engine | Yes (installed via pip) |

### Async Task Pattern

Long-running operations use a consistent pattern:
1. API endpoint creates a `Task` via `TaskManager`, returns `task_id` immediately
2. Work runs in a background `threading.Thread` (daemon)
3. Thread updates task progress via `TaskManager.update_task()`
4. Frontend polls a status endpoint with the `task_id`
5. On completion, results are stored in the task and in persistent files

This pattern is used for: graph building, simulation preparation, simulation execution, and report generation.

## API Blueprint Summary

### `/api/graph` — Graph Blueprint
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/ontology/generate` | Upload docs + generate ontology |
| POST | `/build` | Start graph construction |
| GET | `/task/<task_id>` | Query task progress |
| GET | `/tasks` | List all tasks |
| GET | `/data/<graph_id>` | Get graph nodes + edges |
| DELETE | `/delete/<graph_id>` | Delete a Zep graph |
| GET | `/project/<id>` | Get project details |
| GET | `/project/list` | List all projects |
| DELETE | `/project/<id>` | Delete project |
| POST | `/project/<id>/reset` | Reset project state |

### `/api/simulation` — Simulation Blueprint
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/create` | Create simulation |
| POST | `/prepare` | Async: prepare environment |
| POST | `/prepare/status` | Poll preparation progress |
| GET | `/<id>` | Get simulation state |
| GET | `/list` | List simulations |
| POST | `/<id>/start` | Launch simulation |
| POST | `/<id>/stop` | Stop simulation |
| GET | `/<id>/status` | Real-time simulation status |
| GET | `/<id>/actions` | Get action logs |
| GET | `/<id>/profiles` | Get agent profiles |
| POST | `/<id>/interview` | Interview an agent |

### `/api/report` — Report Blueprint
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/generate` | Async: generate report |
| POST | `/generate/status` | Poll generation progress |
| GET | `/<id>` | Get full report |
| GET | `/by-simulation/<sim_id>` | Get report by simulation |
| GET | `/list` | List all reports |
| GET | `/<id>/download` | Download as Markdown |
| DELETE | `/<id>` | Delete report |
| POST | `/chat` | Chat with Report Agent |
| GET | `/<id>/progress` | Real-time generation progress |
| GET | `/<id>/sections` | Stream completed sections |
| GET | `/<id>/section/<idx>` | Get single section |
| GET | `/<id>/agent-log` | Incremental agent log |
| GET | `/<id>/console-log` | Console output log |
| GET | `/check/<sim_id>` | Check if report exists |

## Key Design Decisions

1. **File-based persistence over database:** Keeps deployment simple (no DB setup). Each project/simulation/report gets its own directory. Trade-off: no query capabilities, manual file management.

2. **Zep Cloud for GraphRAG:** Offloads entity extraction, relationship detection, and semantic search to Zep's managed service. The ontology is dynamically created from LLM-analyzed document content.

3. **OASIS as simulation engine:** Leverages the open-source CAMEL-AI OASIS platform for realistic social media agent behavior, supporting both Twitter and Reddit interaction models.

4. **Subprocess isolation for simulations:** OASIS runs as a separate Python subprocess (not in-process), communicating via file-based IPC. This prevents simulation crashes from taking down the Flask server.

5. **ReACT pattern for reports:** The Report Agent doesn't just summarize — it actively queries the knowledge graph during generation, making reports grounded in the actual simulation data.

6. **LLM-driven automation at every step:** From ontology design to agent personas to simulation parameters to report writing — the LLM handles decisions that would traditionally require expert configuration.

7. **Temporal memory feedback loop:** Simulation activities are fed back into the Zep graph as new episodes, meaning the knowledge graph evolves during simulation — enabling richer post-simulation queries.

## Deployment

**Source (recommended):**
```bash
npm run setup:all   # Install all dependencies
npm run dev          # Start frontend (port 3000) + backend (port 5001)
```

**Docker:**
```bash
docker compose up -d  # Single container, ports 3000 + 5001
```

Both require `.env` with `LLM_API_KEY` and `ZEP_API_KEY`.
