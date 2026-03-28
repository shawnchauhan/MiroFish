# MiroFish Frontend Reference

> Vue 3 SPA implementing a 5-step simulation pipeline. For high-level architecture, see [ARCHITECTURE.md](ARCHITECTURE.md). For backend API, see [API.md](API.md).

## Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Vue 3 | 3.5.24 | Composition API + `<script setup>` |
| Vue Router | 4.6.3 | Client-side routing with auth guards |
| Vite | 7.2.4 | Dev server (port 3000) with API proxy |
| D3.js | 7.9.0 | Knowledge graph visualization |
| Axios | 1.13.2 | HTTP client (5-min timeout, retry logic) |

## Project Structure

```
frontend/src/
├── main.js                    # App entry: mounts Vue + Router
├── App.vue                    # Root: auth bar + <router-view>
├── router/
│   ├── index.js               # 7 routes (Login, Home, Process, Sim, SimRun, Report, Interaction)
│   └── guards.js              # Auth guard (redirects to /login if needed)
├── views/                     # Page-level components (one per route)
│   ├── Login.vue              # OAuth login (Google + GitHub)
│   ├── Home.vue               # Landing: file upload + history
│   ├── MainView.vue           # Steps 1-2: graph build + env setup
│   ├── SimulationView.vue     # Step 2 continued (existing sim)
│   ├── SimulationRunView.vue  # Step 3: run simulation
│   ├── ReportView.vue         # Step 4: generate report
│   └── InteractionView.vue    # Step 5: deep interaction
├── components/                # Step components + shared UI
│   ├── GraphPanel.vue         # D3 force graph visualization (1,423 lines)
│   ├── Step1GraphBuild.vue    # Ontology display + graph build progress
│   ├── Step2EnvSetup.vue      # Sim creation + profile gen + config (2,602 lines)
│   ├── Step3Simulation.vue    # Dual-platform sim execution (1,263 lines)
│   ├── Step4Report.vue        # Report gen + agent logs + chat (5,150 lines)
│   ├── Step5Interaction.vue   # Agent interviews + report chat (2,574 lines)
│   └── HistoryDatabase.vue    # Past simulation cards (1,340 lines)
├── api/                       # Axios API clients
│   ├── index.js               # Axios instance + interceptors + retry helper
│   ├── auth.js                # checkAuth, logout, loginUrl
│   ├── graph.js               # generateOntology, buildGraph, getTaskStatus, getGraphData, getProject
│   ├── simulation.js          # 19 exports: create, prepare, start, stop, profiles, interview, etc.
│   └── report.js              # generateReport, getReportStatus, getReport, getAgentLog, chatWithReport
├── store/                     # Reactive state
│   ├── auth.js                # authState: { authEnabled, authenticated, user, checked }
│   └── pendingUpload.js       # Deferred file upload state between Home → Process
└── assets/                    # Logos and images
```

---

## Routing

| Path | View | Props | Purpose |
|------|------|-------|---------|
| `/login` | Login.vue | -- | OAuth provider selection (public) |
| `/` | Home.vue | -- | Landing page, file upload, history |
| `/process/:projectId` | MainView.vue | projectId | Steps 1-2: graph build + env setup |
| `/simulation/:simulationId` | SimulationView.vue | simulationId | Step 2 for existing simulation |
| `/simulation/:simulationId/start` | SimulationRunView.vue | simulationId, query: maxRounds | Step 3: run simulation |
| `/report/:reportId` | ReportView.vue | reportId | Step 4: report generation |
| `/interaction/:reportId` | InteractionView.vue | reportId | Step 5: deep interaction |

**Auth guard** (`guards.js`): All routes except `/login` require authentication when `authState.authEnabled` is true. Guard checks `authState.checked` before proceeding, redirects to `/login` if not authenticated.

---

## Component Hierarchy

```
App.vue
├── Auth Bar (conditional: user avatar, name, logout)
└── <router-view>
    ├── Login.vue
    │   └── OAuth buttons (Google, GitHub)
    │
    ├── Home.vue
    │   ├── Navbar (brand, GitHub link)
    │   ├── Hero section (logo, tagline)
    │   ├── Dashboard (file upload zone + sim requirement textarea)
    │   └── HistoryDatabase.vue (past simulation cards)
    │
    ├── MainView.vue (split-panel layout)
    │   ├── GraphPanel.vue (left: D3 graph)
    │   └── Step1GraphBuild.vue | Step2EnvSetup.vue (right: step content)
    │
    ├── SimulationView.vue (split-panel layout)
    │   ├── GraphPanel.vue (left)
    │   └── Step2EnvSetup.vue (right)
    │
    ├── SimulationRunView.vue (split-panel layout)
    │   ├── GraphPanel.vue (left, auto-refreshes every 30s)
    │   └── Step3Simulation.vue (right)
    │
    ├── ReportView.vue
    │   ├── GraphPanel.vue (left, optional)
    │   └── Step4Report.vue (right, default: full width)
    │
    └── InteractionView.vue
        ├── GraphPanel.vue (left, optional)
        └── Step5Interaction.vue (right, default: full width)
```

---

## View Details

### MainView.vue (Steps 1-2 Hub)

The central workflow hub. Manages split-panel layout with three view modes:

| Mode | Layout |
|------|--------|
| `graph` | GraphPanel full width |
| `split` | 50/50 graph + step content |
| `workbench` | Step content full width |

**Key state:**
- `currentStep` (1-5): Which step component to show
- `currentPhase` (-1 to 2): Progress within Step 1 (-1=upload, 0=ontology, 1=building, 2=complete)
- `projectData`, `graphData`: Loaded from backend

**Initialization logic:**
1. If `projectId === 'new'`: Retrieves files from `pendingUpload` store, calls `generateOntology()`, gets back `project_id`, replaces URL
2. If existing project: Loads project state, resumes at appropriate phase

**Polling:** Two independent polling loops:
- Task status polling (2s interval) during graph build
- Graph data polling (10s interval) once `graph_id` is available

### SimulationRunView.vue (Step 3 Hub)

**Graph refresh:** Auto-refreshes graph visualization every 30 seconds during active simulation to show memory updates from `ZepGraphMemoryUpdater`.

**Config loading:** Reads `minutes_per_round` from simulation config for display.

---

## Step Components

### Step1GraphBuild.vue

Displays ontology generation results and graph building progress.

**Three cards:**
1. **Ontology Generation** -- Shows generated entity types (as clickable tags) and relation types. Detail overlay shows attributes, examples, connections.
2. **Graph Building** -- Progress bar, build stats (nodes, edges), build timeline (extraction → assembly).
3. **System Logs** -- Scrollable timestamped log window.

**Props:** `currentPhase`, `projectData`, `ontologyProgress`, `buildProgress`, `graphData`, `systemLogs`
**Events:** `@next-step`

### Step2EnvSetup.vue (2,602 lines)

The most complex setup component. Four phases:

| Phase | Action | API Calls |
|-------|--------|-----------|
| 0 | Create simulation | `POST /api/simulation/create` |
| 1 | Generate agent profiles | `POST /api/simulation/prepare` + poll status |
| 2 | Configure simulation | Entity types, platforms, memory options |
| 3 | Ready to launch | Summary + "Start Simulation" button |

**Profile generation UI:**
- Progress percentage with expected agent count
- Real-time profile list as they generate (username, profession, bio, topics)
- Profile detail overlay on selection
- Stats: current agents, expected total, topic count

**Configuration options:**
- Entity type selection with counts
- LLM-based profile generation toggle
- Parallel generation count
- Platform toggles (Twitter/Reddit)
- Memory configuration

**Props:** `simulationId`, `projectData`, `graphData`, `systemLogs`
**Events:** `@go-back`, `@next-step`, `@add-log`, `@update-status`

### Step3Simulation.vue (1,263 lines)

Executes simulation on dual platforms simultaneously.

**Dual platform display:**

| Platform | Label | Actions |
|----------|-------|---------|
| Twitter | "Info Plaza" | POST, LIKE, REPOST, QUOTE, FOLLOW, IDLE |
| Reddit | "Topic Community" | POST, COMMENT, LIKE, DISLIKE, SEARCH, TREND, FOLLOW, MUTE, REFRESH, IDLE |

**Per-platform tracking:** Current round, total rounds, elapsed time, action count, completion badge.

**Polling:** Status polled every 2-5 seconds via `GET /api/simulation/{id}/run-status`.

**Post-completion:** Auto-generates report via `POST /api/report/generate`, then navigates to ReportView.

### Step4Report.vue (5,150 lines -- largest component)

Report generation, display, and agent interaction.

**Tab navigation:**
1. **Report** -- Generated content (summary, findings, statistics, timeline, sentiment analysis)
2. **Agent Logs** -- Streamed JSONL showing agent reasoning and tool calls (incremental via `from_line`)
3. **Console** -- System output and debug info
4. **Chat** -- Interactive Q&A with ReportAgent

**Report chat:** Sends messages to `POST /api/report/chat` with full chat history. Agent autonomously calls graph tools to answer questions.

**Polling:** Report status polled every 2s during generation. Logs streamed incrementally.

### Step5Interaction.vue (2,574 lines)

Deep interaction with simulation agents and report.

**Features:**
- **Agent interview panel**: Searchable/filterable agent list, custom prompt entry, interview results display
- **Report Agent chat**: Continued Q&A (same as Step4 chat)
- **Simulation timeline**: Round-by-round action timeline with platform filtering
- **Agent profiles browser**: Quick access to all agent metadata

---

## GraphPanel.vue (D3 Visualization)

Force-directed graph visualization with interactive features.

**Props:**
- `graphData` -- Nodes and edges
- `loading` -- Show spinner
- `currentPhase` -- Adjusts UI for building/simulation/report stages
- `isSimulating` -- Shows "memory updating" indicator

**D3 rendering:**
- Node colors by entity type
- Node size by connection degree
- Edge stroke width by relationship strength
- Force layout with gravity/repulsion
- Click to select node/edge and show detail panel

**Detail panel (on node click):**
- Name, UUID, created_at
- Attributes/properties
- Summary
- Labels

**Detail panel (on edge click):**
- Relationship name, fact, fact_type
- Self-loop group display
- Connected episodes

**Events:** `@refresh` (manual reload), `@toggle-maximize` (fullscreen toggle)

---

## API Layer

### Axios Instance (`api/index.js`)

```
Base URL: VITE_API_BASE_URL || http://localhost:5001
Timeout: 300 seconds (5 minutes)
Credentials: enabled (for session cookies)
```

**Request interceptor:** Error logging.

**Response interceptor:**
- Checks `response.data.success` flag
- 401 → redirects to `/login`
- `ECONNABORTED` → logs timeout
- Network Error → logs connectivity failure

**Retry helper:** `requestWithRetry(fn, maxRetries=3, delay=1000)` with exponential backoff (delay * 2^i).

### API Module Summary

| Module | Exports | Key Endpoints |
|--------|---------|---------------|
| `auth.js` | 3 | `GET /api/auth/status`, `POST /api/auth/logout`, OAuth URLs |
| `graph.js` | 5 | Ontology generate, graph build, task status, graph data, project |
| `simulation.js` | 19 | Full simulation lifecycle + profiles + interviews + history |
| `report.js` | 6 | Report generate, status, get, logs, chat |

---

## State Management

### Auth Store (`store/auth.js`)

Reactive object (not Pinia/Vuex):

```javascript
authState = {
  authEnabled: boolean,    // Is OAuth configured?
  authenticated: boolean,  // Is user logged in?
  user: {                  // Current user (null if not authenticated)
    id, email, display_name, avatar_url, provider
  },
  checked: boolean         // Has auth been checked this session?
}
```

**Functions:** `checkAuth()` (debounced), `clearAuth()`.

### Pending Upload Store (`store/pendingUpload.js`)

Defers file upload from Home page to Process page:

```javascript
state = {
  files: File[],               // Uploaded documents
  simulationRequirement: string, // User's prompt
  isPending: boolean           // Has data waiting?
}
```

**Flow:** Home.vue calls `setPendingUpload()` → navigates to `/process/new` → MainView.vue calls `getPendingUpload()` → submits to API → calls `clearPendingUpload()`.

---

## Polling Patterns

All long-running operations use polling since the backend has no WebSocket support:

| What | Endpoint | Interval | Component |
|------|----------|----------|-----------|
| Graph build progress | `GET /api/graph/task/{taskId}` | 2s | MainView |
| Graph data refresh | `GET /api/graph/data/{graphId}` | 10s | MainView |
| Profile generation | `POST /api/simulation/prepare/status` | 2s | Step2EnvSetup |
| Simulation status | `GET /api/simulation/{id}/run-status` | 2-5s | Step3Simulation |
| Graph memory refresh | `GET /api/graph/data/{graphId}` | 30s | SimulationRunView |
| Report generation | `POST /api/report/generate/status` | 2s | Step4Report |
| Agent log stream | `GET /api/report/{id}/agent-log?from_line=N` | on demand | Step4Report |
| Console log stream | `GET /api/report/{id}/console-log?from_line=N` | on demand | Step4Report |

**Cleanup:** All polling intervals are cleared on component unmount (`onUnmounted`).

---

## User Journey

```
Home.vue                          MainView.vue
┌─────────────┐                   ┌─────────────────────────────┐
│ Upload docs  │──→ /process/new ──→│ Step 1: Ontology + Graph    │
│ Enter prompt │                   │   (polls task + graph data) │
│ Start Engine │                   │                             │
└─────────────┘                   │ Step 2: Create Sim + Profiles│
                                  │   (polls prepare status)     │
                                  └──────────┬──────────────────┘
                                             │
                          SimulationView.vue  │  (existing sim path)
                          ┌──────────────────┘
                          ↓
                SimulationRunView.vue
                ┌─────────────────────────────┐
                │ Step 3: Run Simulation       │
                │   Twitter + Reddit parallel  │
                │   (polls run-status 2-5s)    │
                │   (graph refresh 30s)        │
                └──────────┬──────────────────┘
                           │ auto-generates report
                           ↓
                    ReportView.vue
                ┌─────────────────────────────┐
                │ Step 4: Report + Agent Logs  │
                │   (polls generation status)  │
                │   (streams logs incremental) │
                │   (chat with ReportAgent)    │
                └──────────┬──────────────────┘
                           ↓
                InteractionView.vue
                ┌─────────────────────────────┐
                │ Step 5: Deep Interaction     │
                │   Interview agents           │
                │   Chat with ReportAgent      │
                │   Browse timeline + profiles │
                └─────────────────────────────┘
```

---

## Design Patterns

1. **Deferred form submission**: Home stores files in reactive store; Process page submits to API
2. **Split-panel layout**: Responsive graph + workbench with three modes (graph/split/workbench)
3. **Component composition**: Step components are self-contained, communicate via props down / events up
4. **Route-based state**: Project/Simulation/Report IDs in URL params (bookmarkable)
5. **Incremental log streaming**: Agent logs use `from_line` parameter for pagination without re-fetching
6. **Polling with cleanup**: All `setInterval` calls tracked and cleared on unmount
7. **Graceful shutdown**: View components close simulation environment before navigating away

## Styling

- **Fonts:** JetBrains Mono (code/data), Space Grotesk (headings), Noto Sans SC (Chinese text)
- **Theme:** Dark/tech aesthetic with grid patterns, smooth transitions, glowing accents
- **Responsive:** Split-panel adapts via view mode toggle
- **Custom scrollbars:** Thin dark scrollbars matching theme
