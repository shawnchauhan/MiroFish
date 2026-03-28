# MiroFish API Reference

Base URL: `http://localhost:5001`

All endpoints return JSON with the structure:
```json
{
  "success": true|false,
  "data": { ... },
  "error": "message (only on failure)"
}
```

---

## Graph API (`/api/graph`)

### Generate Ontology

```
POST /api/graph/ontology/generate
Content-Type: multipart/form-data
```

Upload documents and generate an entity/relationship ontology.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | File[] | Yes | PDF, MD, or TXT files (max 50MB each) |
| `simulation_requirement` | string | Yes | Natural language description of what to simulate |
| `project_name` | string | No | Project name (auto-generated if omitted) |
| `additional_context` | string | No | Extra context for ontology design |

**Response:**
```json
{
  "project_id": "uuid",
  "ontology": {
    "entity_types": [
      {
        "name": "PascalCase",
        "description": "...",
        "attributes": [{"name": "snake_case", "type": "text"}],
        "examples": ["..."]
      }
    ],
    "edge_types": [
      {
        "name": "UPPER_SNAKE_CASE",
        "description": "...",
        "source_targets": [{"source": "Type1", "target": "Type2"}]
      }
    ],
    "analysis_summary": "..."
  },
  "files": ["filename1.pdf", ...],
  "text_length": 12345
}
```

**Notes:**
- Always produces exactly 10 entity types (8 domain-specific + Person + Organization fallbacks)
- 6-10 edge types
- Ontology is constrained by Zep's limit of 10 entity types and 10 edge types

---

### Build Graph

```
POST /api/graph/build
Content-Type: application/json
```

```json
{
  "project_id": "uuid",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "graph_name": "optional_custom_name",
  "force": false
}
```

Starts async graph construction. Returns immediately with a task ID.

**Response:**
```json
{
  "task_id": "uuid",
  "graph_id": "mirofish_XXXXXXXXXXXXXXXX",
  "message": "Graph build started"
}
```

---

### Get Task Status

```
GET /api/graph/task/<task_id>
```

**Response:**
```json
{
  "task_id": "uuid",
  "status": "processing|completed|failed",
  "progress": 75,
  "message": "Processing batch 3/4...",
  "result": { "graph_id": "...", "node_count": 42, "edge_count": 87 }
}
```

---

### Get Graph Data

```
GET /api/graph/data/<graph_id>
```

Returns full graph for visualization.

**Response:**
```json
{
  "nodes": [
    {
      "uuid": "...",
      "name": "Entity Name",
      "labels": ["Person"],
      "summary": "...",
      "attributes": { "role": "journalist" },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "edges": [
    {
      "uuid": "...",
      "name": "WORKS_FOR",
      "fact": "Alice works for NewsOrg",
      "source_uuid": "...",
      "target_uuid": "...",
      "created_at": "..."
    }
  ],
  "node_count": 42,
  "edge_count": 87
}
```

---

### Project Management

```
GET    /api/graph/project/<project_id>     # Get project details
GET    /api/graph/project/list             # List all projects
DELETE /api/graph/project/<project_id>     # Delete project
POST   /api/graph/project/<project_id>/reset  # Reset project state
```

```
GET    /api/graph/tasks                    # List all tasks
DELETE /api/graph/delete/<graph_id>        # Delete Zep graph
```

---

## Simulation API (`/api/simulation`)

### Create Simulation

```
POST /api/simulation/create
Content-Type: application/json
```

```json
{
  "project_id": "uuid",
  "graph_id": "mirofish_XXX (optional, auto-read from project)",
  "enable_twitter": true,
  "enable_reddit": true
}
```

**Response:**
```json
{
  "simulation_id": "uuid"
}
```

---

### Prepare Simulation (Async)

```
POST /api/simulation/prepare
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid",
  "entity_types": ["Person", "Organization"],
  "use_llm_for_profiles": true,
  "parallel_profile_count": 3
}
```

Generates agent profiles from graph entities and simulation config via LLM.

**Response:**
```json
{
  "task_id": "uuid",
  "message": "Preparation started"
}
```

---

### Check Preparation Status

```
POST /api/simulation/prepare/status
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid"
}
```

**Response:**
```json
{
  "progress": 80,
  "profiles_count": 25,
  "config_generated": true,
  "status": "ready"
}
```

---

### Get Profiles

```
GET /api/simulation/<simulation_id>/profiles?platform=twitter|reddit
GET /api/simulation/<simulation_id>/profiles/realtime?platform=twitter|reddit
```

The `realtime` variant streams profiles as they're generated.

---

### Start Simulation

```
POST /api/simulation/start
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid",
  "platform": "both|twitter|reddit",
  "max_rounds": 10,
  "enable_graph_memory_update": true
}
```

Launches OASIS subprocess(es).

---

### Get Run Status

```
GET /api/simulation/<simulation_id>/run-status
```

**Response:**
```json
{
  "status": "running|completed|failed",
  "twitter_current_round": 5,
  "twitter_max_rounds": 10,
  "twitter_completed": false,
  "twitter_actions_count": 47,
  "reddit_current_round": 5,
  "reddit_max_rounds": 10,
  "reddit_completed": false,
  "reddit_actions_count": 32,
  "elapsed_seconds": 120
}
```

---

### Simulation Results

```
GET /api/simulation/<simulation_id>/actions?platform=twitter&limit=50&offset=0
GET /api/simulation/<simulation_id>/timeline?start_round=1&end_round=5
GET /api/simulation/<simulation_id>/agent-stats
GET /api/simulation/<simulation_id>/posts?platform=twitter&limit=20&offset=0
```

---

### Stop Simulation

```
POST /api/simulation/stop
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid"
}
```

---

### Interview Agents

```
POST /api/simulation/interview/batch
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid",
  "interviews": [
    { "agent_id": "agent_1", "prompt": "What motivated your posts?" }
  ]
}
```

---

### Other Simulation Endpoints

```
GET  /api/simulation/<simulation_id>           # Get simulation state
GET  /api/simulation/list?project_id=uuid      # List simulations
GET  /api/simulation/<simulation_id>/config     # Get simulation config
POST /api/simulation/<simulation_id>/close-env  # Graceful shutdown
GET  /api/simulation/<simulation_id>/env-status # Environment health
GET  /api/simulation/history?limit=10           # Recent simulations
```

---

## Report API (`/api/report`)

### Generate Report

```
POST /api/report/generate
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid"
}
```

Starts async ReACT-pattern report generation.

**Response:**
```json
{
  "report_id": "uuid",
  "task_id": "uuid"
}
```

---

### Check Generation Status

```
POST /api/report/generate/status
Content-Type: application/json
```

```json
{
  "report_id": "uuid"
}
```

**Response:**
```json
{
  "status": "generating|completed|failed",
  "progress": 60,
  "current_section": "Analysis of Key Events",
  "sections_completed": 3,
  "sections_total": 5
}
```

---

### Get Report

```
GET /api/report/<report_id>
```

**Response:**
```json
{
  "report_id": "uuid",
  "simulation_id": "uuid",
  "title": "Simulation Analysis Report",
  "summary": "...",
  "sections": [
    { "title": "Executive Summary", "content": "..." },
    { "title": "Key Events Analysis", "content": "..." }
  ],
  "created_at": "...",
  "status": "completed"
}
```

---

### Stream Sections (Real-time)

```
GET /api/report/<report_id>/sections
```

Returns list of completed sections so far (poll during generation).

```
GET /api/report/<report_id>/section/<index>
```

Returns a single section by index (0-based).

---

### Agent Logs

```
GET /api/report/<report_id>/agent-log?from_line=0
GET /api/report/<report_id>/agent-log/stream
GET /api/report/<report_id>/console-log?from_line=0
GET /api/report/<report_id>/console-log/stream
```

Agent log returns JSONL with every tool call, LLM response, and reasoning step.

---

### Chat with Report Agent

```
POST /api/report/chat
Content-Type: application/json
```

```json
{
  "simulation_id": "uuid",
  "message": "What were the most surprising findings?",
  "chat_history": [
    { "role": "user", "content": "previous question" },
    { "role": "assistant", "content": "previous answer" }
  ]
}
```

**Response:**
```json
{
  "response": "Based on my analysis...",
  "tool_calls": ["InsightForge", "QuickSearch"],
  "sources": ["entity-uuid-1", "entity-uuid-2"]
}
```

---

### Other Report Endpoints

```
GET    /api/report/list?simulation_id=uuid       # List reports
GET    /api/report/by-simulation/<simulation_id>  # Get report by simulation
GET    /api/report/<report_id>/download           # Download as Markdown
DELETE /api/report/<report_id>                    # Delete report
GET    /api/report/<report_id>/progress           # Generation progress
GET    /api/report/check/<simulation_id>          # Check if report exists
POST   /api/report/tools/search                   # Debug: graph search
POST   /api/report/tools/statistics               # Debug: graph statistics
```

---

## Error Responses

All errors follow the format:

```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

Common HTTP status codes:
- `400` — Missing required fields or invalid input
- `404` — Entity not found (project, simulation, report, graph)
- `500` — Internal server error (LLM failure, Zep API error, etc.)
