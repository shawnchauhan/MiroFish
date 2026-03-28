# MiroFish Service Layer Reference

> Deep dive into backend services, data models, and utilities. For high-level architecture, see [ARCHITECTURE.md](ARCHITECTURE.md). For API endpoints, see [API.md](API.md).

## Service Map

```
backend/app/
├── services/                          # Core business logic
│   ├── ontology_generator.py          # LLM-based ontology design
│   ├── graph_builder.py               # Zep graph creation + ingestion
│   ├── text_processor.py              # Text chunking with overlap
│   ├── zep_entity_reader.py           # Entity extraction from Zep graphs
│   ├── oasis_profile_generator.py     # Graph entities → OASIS agent profiles
│   ├── simulation_config_generator.py # LLM-generated simulation parameters
│   ├── simulation_manager.py          # Simulation lifecycle orchestration
│   ├── simulation_runner.py           # Subprocess management for OASIS
│   ├── simulation_ipc.py             # File-based IPC (Flask ↔ OASIS subprocess)
│   ├── zep_graph_memory_updater.py    # Feed sim activity back into graph
│   ├── zep_tools.py                   # Graph search tools for ReportAgent
│   └── report_agent.py               # ReACT-pattern report generation + chat
├── models/                            # Data models
│   ├── user.py                        # SQLite-backed user model (OAuth)
│   ├── project.py                     # File-based project state machine
│   └── task.py                        # In-memory async task tracker
└── utils/                             # Shared utilities
    ├── llm_client.py                  # OpenAI-compatible LLM wrapper
    ├── file_parser.py                 # PDF/MD/TXT text extraction
    ├── zep_paging.py                  # Paginated Zep API fetches
    ├── paths.py                       # User-scoped path helpers
    ├── logger.py                      # Structured rotating log setup
    └── retry.py                       # Retry with backoff
```

---

## Data Models

### User Model (`models/user.py`)

SQLite-backed user model for OAuth authentication. Implements Flask-Login's `UserMixin`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `provider` | string | OAuth provider (`google`, `github`) |
| `provider_id` | string | Provider-specific user ID |
| `email` | string | User email |
| `display_name` | string | Display name from provider |
| `avatar_url` | string | Profile picture URL |
| `created_at` | datetime | First login |
| `last_login_at` | datetime | Most recent login |

**Key methods:**
- `User.upsert(provider, provider_id, email, display_name, avatar_url)` -- Atomic insert-or-update on login
- `User.get_by_provider(provider, provider_id)` -- Lookup for OAuth callback
- `User.get_by_id(user_id)` -- Flask-Login user loader

**Uniqueness:** `(provider, provider_id)` composite unique constraint.

**Dev mode:** When `AUTH_ENABLED=false`, a deterministic `dev-local-user` ID is used for consistent file scoping.

---

### Project Model (`models/project.py`)

File-based project state machine. Each project is a directory under `uploads/{user_id}/projects/{project_id}/`.

**State machine:**
```
CREATED → ONTOLOGY_GENERATED → GRAPH_BUILDING → GRAPH_COMPLETED
                                     ↓
                                   FAILED
```

**Project dataclass fields:**

| Field | Description |
|-------|-------------|
| `project_id` | UUID |
| `name` | Project name (auto-generated if omitted) |
| `status` | Current state (ProjectStatus enum) |
| `files` | List of {filename, path, size} |
| `total_text_length` | Combined extracted text length |
| `ontology` | Generated ontology (entity_types, edge_types) |
| `graph_id` | Zep graph identifier |
| `graph_build_task_id` | Async task reference |
| `simulation_requirement` | User's natural-language prompt |
| `chunk_size` / `chunk_overlap` | Text chunking parameters |

**File layout:**
```
uploads/{user_id}/projects/{project_id}/
├── project.json          # Serialized ProjectState
├── files/                # Uploaded documents
│   ├── report.pdf
│   └── article.md
└── extracted_text.txt    # Combined extracted text
```

**ProjectManager** (static methods): `create()`, `get()`, `list()`, `delete()`, `reset()`, `save_file_to_project()`, `get_extracted_text()`.

---

### Task Model (`models/task.py`)

In-memory singleton for tracking async operations. Thread-safe via `threading.Lock`.

**Task states:** `PENDING → PROCESSING → COMPLETED | FAILED`

**Task dataclass fields:**

| Field | Description |
|-------|-------------|
| `task_id` | UUID |
| `task_type` | Operation type (e.g., `graph_build`, `sim_prepare`, `report_generate`) |
| `status` | TaskStatus enum |
| `progress` | 0-100 integer |
| `message` | Human-readable progress message |
| `result` | Completion payload (dict) |
| `error` | Failure message |
| `progress_detail` | Structured progress metadata |

**TaskManager** (singleton): `create_task()`, `get_task()`, `update_task()`, `complete_task()`, `fail_task()`.

**Usage pattern:**
```python
task_id = TaskManager.create_task("graph_build")
# In background thread:
TaskManager.update_task(task_id, progress=50, message="Processing batch 3/4")
TaskManager.complete_task(task_id, result={"graph_id": "...", "node_count": 42})
# Frontend polls:
task = TaskManager.get_task(task_id)
```

---

## Services

### OntologyGenerator (`services/ontology_generator.py`)

Analyzes uploaded documents via LLM to design a knowledge graph schema.

**Input:** Document texts, simulation requirement, optional additional context.

**Output:** Ontology dict with:
- `entity_types` (exactly 10): 8 domain-specific + Person + Organization fallbacks. Each has name (PascalCase), description, attributes (name + type), examples.
- `edge_types` (6-10): Relationship types with UPPER_SNAKE_CASE names, descriptions, and source/target entity type constraints.
- `analysis_summary`: Chinese-language document analysis.

**Constraints:** Zep limits graphs to 10 entity types and 10 edge types, so the generator is hard-coded to respect this.

**Error handling:** Validates LLM JSON output, retries on malformed responses.

---

### GraphBuilderService (`services/graph_builder.py`)

Creates and populates Zep knowledge graphs.

**Key methods:**

| Method | Purpose |
|--------|---------|
| `create_graph(name)` | Creates empty Zep Standalone Graph |
| `set_ontology(graph_id, ontology)` | Applies entity/edge type definitions |
| `add_text_batches(graph_id, chunks, batch_size, progress_callback)` | Ingests text chunks in batches |
| `get_graph_data(graph_id)` | Retrieves full graph (nodes + edges) |
| `delete_graph(graph_id)` | Cleanup |

**Progress stages (during graph build):**
```
0-15%   → Initialization (create graph, set ontology)
15-55%  → Adding text chunks in batches
55-90%  → Waiting for Zep to process episodes
90-100% → Retrieving final graph data
```

**Zep episode processing:** After adding text, Zep asynchronously extracts entities and relationships. The service polls episode status until all are marked `processed`.

---

### TextProcessor (`services/text_processor.py`)

Static utility for text manipulation.

| Method | Purpose |
|--------|---------|
| `extract_from_files(file_paths)` | Multi-file text extraction |
| `split_text(text, chunk_size, overlap)` | Chunking with configurable overlap |
| `preprocess_text(text)` | Normalize whitespace and line endings |
| `get_text_stats(text)` | Character, line, and word counts |

**Chunking:** Splits at `chunk_size` characters with `chunk_overlap` character overlap between consecutive chunks. Defaults: 500 size, 50 overlap.

---

### ZepEntityReader (`services/zep_entity_reader.py`)

Reads and filters entities from populated Zep graphs.

**Data structures:**
- `EntityNode`: uuid, name, labels, summary, attributes, related_edges, related_nodes
- `FilteredEntities`: entities list, entity_types set, total/filtered counts

**Key methods:**

| Method | Purpose |
|--------|---------|
| `filter_defined_entities(graph_id, types, enrich)` | Filter nodes by ontology-defined types |
| `get_entity_with_context(graph_id, entity_uuid)` | Single entity with neighbor context |
| `get_entities_by_type(graph_id, entity_type, enrich)` | All entities of a specific type |

**Retry logic:** Exponential backoff (3 attempts, 2s initial delay) for Zep API resilience.

**Filtering logic:** Nodes in Zep carry multiple labels (e.g., `["Entity", "Person"]`). The reader filters to nodes where at least one label matches a defined entity type from the ontology.

---

### OasisProfileGenerator (`services/oasis_profile_generator.py`)

Converts graph entities into OASIS-compatible AI agent profiles.

**OasisAgentProfile fields:**

| Field | Description |
|-------|-------------|
| `user_id` | Unique agent identifier |
| `user_name` | Username (derived from entity name) |
| `name` | Display name |
| `bio` | Agent biography |
| `persona` | Detailed personality description |
| `age`, `gender`, `MBTI` | Demographics |
| `country`, `profession` | Background |
| `interested_topics` | Topic list for simulation behavior |
| Platform-specific | `karma` (Reddit), `follower_count` etc. (Twitter) |

**Generation modes:**
1. **LLM-enhanced** (`use_llm=true`): Enriches entity via Zep graph search, then LLM generates detailed persona with bio, personality, MBTI, interests.
2. **Template-based** (`use_llm=false`): Maps entity attributes directly to profile fields.

**Parallel processing:** Uses `ThreadPoolExecutor` with configurable `parallel_count` for speed.

**Output formats:**
- `to_twitter_format()` -- CSV-compatible dict
- `to_reddit_format()` -- JSON-compatible dict

---

### SimulationConfigGenerator (`services/simulation_config_generator.py`)

Uses LLM to generate intelligent simulation parameters.

**Config classes:**

| Class | Key Fields |
|-------|-----------|
| `TimeSimulationConfig` | total_hours, minutes_per_round, peak/off_peak hours, activity multipliers |
| `AgentActivityConfig` | Per-agent: activity_level, posts_per_hour, sentiment_bias, stance, influence_weight |
| `PlatformConfig` | Platform-specific parameters |

**Generation pipeline (4 LLM calls):**
1. **Time config** -- Simulation duration, round length, peak hours (defaults to China timezone: peak 19-22h, off-peak 0-5h)
2. **Event config** -- Trigger events to inject during simulation
3. **Agent configs** -- Per-agent behavior params (batched with retry)
4. **Platform config** -- Platform-specific settings

---

### SimulationManager (`services/simulation_manager.py`)

Orchestrates the full simulation lifecycle.

**State machine:**
```
CREATED → PREPARING → READY → RUNNING → COMPLETED
                ↓                ↓
              FAILED           STOPPED
```

**SimulationState fields:**

| Field | Description |
|-------|-------------|
| `simulation_id` | UUID |
| `project_id` / `graph_id` | Parent references |
| `enable_twitter` / `enable_reddit` | Platform toggles |
| `entities_count` / `profiles_count` | Preparation counts |
| `config_generated` / `config_reasoning` | Config status |
| `current_round` | Runtime progress |
| `twitter_status` / `reddit_status` | Per-platform status |

**File layout:**
```
uploads/{user_id}/simulations/{simulation_id}/
├── state.json              # Serialized SimulationState
├── reddit_profiles.json    # Generated Reddit agent profiles
├── twitter_profiles.csv    # Generated Twitter agent profiles
├── simulation_config.json  # Generated simulation parameters
├── scripts/                # Copied OASIS runner scripts
└── actions/                # Runtime action logs per round
```

**Preparation stages:**
```
0-20%   → Reading entities from Zep graph
20-70%  → Generating OASIS agent profiles (LLM)
70-90%  → Generating simulation config (LLM)
90-100% → Copying runner scripts to simulation directory
```

---

### SimulationRunner (`services/simulation_runner.py`)

Manages OASIS simulation as a subprocess.

**RunnerStatus:** `NOT_STARTED → RUNNING → COMPLETED | STOPPED | FAILED`

**Key methods:**

| Method | Purpose |
|--------|---------|
| `run_simulation(sim_id, config, max_rounds, callback)` | Spawns subprocess |
| `interview_agent(sim_id, agent_id, prompt)` | Queries agent state via IPC |
| `batch_interview(sim_id, agent_ids, prompt)` | Multi-agent query |
| `stop_simulation(sim_id)` | Graceful termination |

**Subprocess:** Runs `backend/scripts/run_parallel_simulation.py` which coordinates Twitter + Reddit simulations in parallel.

**IPC:** Uses Unix domain sockets (Linux/Mac) or Named Pipes (Windows) for real-time agent interview queries without blocking the simulation.

**Process tracking:** Maintains registry of running processes. Cleanup hooks registered at Flask app startup ensure processes are terminated on server shutdown.

**SimulationRunState:** In-memory cache of simulation metadata and action history, persisted to `uploads/{user_id}/run_states/{simulation_id}.json`.

---

### SimulationIPC (`services/simulation_ipc.py`)

File-based inter-process communication between Flask and OASIS subprocess.

**Communication pattern:**
```
Flask → commands/{uuid}.json → OASIS subprocess reads
OASIS → responses/{uuid}.json → Flask reads
```

Used primarily for agent interviews during active simulation.

---

### ZepGraphMemoryUpdater (`services/zep_graph_memory_updater.py`)

Feeds simulation agent activities back into the Zep graph as temporal episodes.

**Purpose:** The knowledge graph evolves during simulation. Agent posts, comments, and interactions are added as new episodes, enabling the graph to reflect simulation dynamics. This creates a feedback loop where post-simulation graph queries return richer results.

---

### ZepToolsService (`services/zep_tools.py`)

Graph search tools used by the ReportAgent during report generation and chat.

**Three search strategies:**

| Tool | Strategy | Use Case |
|------|----------|----------|
| **InsightForge** | Deep hybrid search: auto-generates sub-questions, searches multiple dimensions (entities, edges, temporal) | Primary tool for thorough analysis |
| **PanoramaSearch** | Breadth-first search including expired/historical content | When historical context matters |
| **QuickSearch** | Fast single-query semantic search | Quick lookups during chat |

**Additional methods:**

| Method | Purpose |
|--------|---------|
| `get_all_nodes(graph_id)` | Full node list |
| `get_all_edges(graph_id, include_temporal)` | Full edge list with expiry info |
| `get_node_detail(node_uuid)` | Single node deep info |
| `get_entity_summary(graph_id, entity_uuid)` | LLM-generated entity summary |
| `get_graph_statistics(graph_id)` | Node/edge counts, types, density |
| `get_simulation_context(graph_id, simulation_id)` | Contextual data for report |

---

### ReportAgent (`services/report_agent.py`)

ReACT-pattern agent for report generation and conversational interaction.

**Report generation pipeline:**

```
Stage 1: Planning
  └── LLM designs report outline (section titles + goals)

Stage 2: Per-section generation (iterative)
  ├── Reason: "What information do I need?"
  ├── Act: Call tools (InsightForge, get_graph_statistics, etc.)
  ├── Reflect: "Is this sufficient?"
  └── Write: Generate section content

  Config limits:
  - max_tool_calls per section (default: 5)
  - max_reflection_rounds (default: 2)
  - temperature (default: 0.5)
```

**ReportLogger:** Structured JSONL action logging. Each entry records timestamp, stage, section index, tool calls, LLM responses. Written line-by-line for real-time frontend retrieval via `from_line` parameter.

**Chat mode:** Interactive Q&A where the agent autonomously calls graph retrieval tools to answer user questions about the simulation.

**Report file layout:**
```
uploads/{user_id}/reports/{report_id}/
├── report.json         # Metadata (id, simulation_id, status, outline, timestamps)
├── report.md           # Full markdown content
├── section_01.md       # Individual sections
├── section_02.md
├── agent_log.jsonl     # Structured action log
└── console_log.txt     # Console output
```

---

## Utilities

### LLMClient (`utils/llm_client.py`)

Thin wrapper around OpenAI SDK for all LLM interactions.

| Method | Purpose |
|--------|---------|
| `chat(messages, temperature, max_tokens, response_format)` | Raw text response |
| `chat_json(messages, temperature, max_tokens)` | Parsed JSON response |

**Behaviors:**
- Strips `<think>` tags from reasoning models (e.g., MiniMax)
- `chat_json()` cleans markdown code blocks (` ```json...``` `) before parsing
- Falls back to Config values for api_key, base_url, model
- Raises `ValueError` on JSON parse failure

---

### FileParser (`utils/file_parser.py`)

Multi-format text extraction.

| Format | Method |
|--------|--------|
| PDF | PyMuPDF (`fitz`) page-by-page extraction |
| MD/Markdown | Direct text read with encoding detection |
| TXT | Multi-level encoding fallback |

**Encoding detection chain:** UTF-8 → charset_normalizer → chardet → UTF-8 with replace. Handles Chinese text and mixed encodings reliably.

---

### Path Helpers (`utils/paths.py`)

User-scoped path functions with path traversal protection.

| Function | Returns |
|----------|---------|
| `user_upload_dir(user_id)` | `uploads/{user_id}` |
| `user_projects_dir(user_id)` | `uploads/{user_id}/projects` |
| `user_simulations_dir(user_id)` | `uploads/{user_id}/simulations` |
| `user_run_states_dir(user_id)` | `uploads/{user_id}/run_states` |
| `user_reports_dir(user_id)` | `uploads/{user_id}/reports` |

**Security:** `_safe_resolve()` validates all resolved paths stay within the base `uploads/` directory, preventing path traversal attacks.

---

### Zep Paging (`utils/zep_paging.py`)

Pagination helpers for large Zep API results.

| Function | Purpose |
|----------|---------|
| `fetch_all_nodes(client, graph_id)` | Auto-paged node retrieval |
| `fetch_all_edges(client, graph_id)` | Auto-paged edge retrieval |

---

### Logger (`utils/logger.py`)

Structured rotating log setup.

- **File handler:** `logs/{YYYY-MM-DD}.log`, 10MB rotating, 5 backups, UTF-8
- **Console handler:** INFO+ level, simple format
- `get_logger(name)` -- Retrieves or creates named logger

---

## Cross-Cutting Patterns

### Async Task Pattern

All long-running operations follow the same pattern:

```python
# 1. API creates task, returns task_id immediately
task_id = TaskManager.create_task("operation_type")

# 2. Background thread does work with progress callbacks
def background_work():
    TaskManager.update_task(task_id, progress=50, message="Halfway...")
    # ... do work ...
    TaskManager.complete_task(task_id, result={...})

thread = threading.Thread(target=background_work, daemon=True)
thread.start()

# 3. Frontend polls status endpoint every 2s
# GET /api/.../task/{task_id}
```

Used by: graph building, simulation preparation, simulation execution, report generation.

### User Isolation

Every file operation is scoped by `user_id`:

```python
from app.auth.helpers import get_current_user_id
from app.utils.paths import user_projects_dir

user_id = get_current_user_id()  # From session or dev-user
base = user_projects_dir(user_id)  # uploads/{user_id}/projects/
```

The `_safe_resolve()` function prevents path traversal. When `AUTH_ENABLED=false`, a deterministic dev user ID ensures consistent paths.

### LLM Call Pattern

All services use `LLMClient` for LLM interactions:

```python
client = LLMClient()  # Uses Config defaults
result = client.chat_json(messages=[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
])
```

`chat_json()` handles markdown stripping and JSON validation.

### Retry Pattern

Zep operations use exponential backoff:
- Max attempts: 3
- Initial delay: 2 seconds
- Backoff multiplier: 2x (2s → 4s → 8s)

---

## Simulation Scripts (`backend/scripts/`)

| Script | Size | Purpose |
|--------|------|---------|
| `run_parallel_simulation.py` | 61K | Main orchestrator: runs Twitter + Reddit in parallel |
| `run_twitter_simulation.py` | 27K | Standalone Twitter simulation |
| `run_reddit_simulation.py` | 27K | Standalone Reddit simulation |
| `action_logger.py` | 10K | Cross-platform agent action logging |
| `test_profile_format.py` | 5.7K | Profile JSON format validator |

**Execution:** `SimulationRunner` spawns `run_parallel_simulation.py` as a subprocess. The script reads `simulation_config.json` and profile files from the simulation directory, runs OASIS rounds, and maintains IPC channels for agent interviews.

**IPC protocol:** Unix domain sockets (Linux/Mac) or Named Pipes (Windows). Flask sends interview commands; the subprocess queries the agent's in-simulation state and returns responses.
