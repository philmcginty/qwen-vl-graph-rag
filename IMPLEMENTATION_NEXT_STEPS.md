# qwen-vlrag — Remaining Steps to Reach Usable / Integration-Ready State

This file is about the shortest path from the current `velvet-rag` prototype to something we can actually use as a real multimodal memory sidecar for agent loops / OpenClaw experiments.

It is **not** the full polish/publishing plan. It is the practical path to "running, queryable, and ready to integrate."

---

## Current Reality Check

What already exists in `/home/metik2009/AI/velvet-rag`:

- `ingest.py` — working image ingestion into Neo4j
- `search.py` — working text/image vector search against Neo4j
- `setup_neo4j.py` — vector index + constraint setup
- `qvl-console.html` — frontend/admin console
- `BACKEND_SPEC.md` — clear FastAPI wrapper spec

What is missing:

- actual FastAPI backend
- non-hardcoded config
- API responses shaped for the UI
- a stable retrieval surface for agent integration
- packaging/docs good enough for repeated use

---

## Target for "Usable"

A usable v1 means:

1. Qwen embedding server can stay running locally
2. Neo4j can be initialized with one command
3. ingest can be triggered through an API
4. search can be called through an API using text or image
5. results come back in a stable JSON shape
6. frontend works against real endpoints
7. an agent loop can call the service programmatically

If all seven are true, the system is no longer a pile of scripts — it is a usable memory service.

---

## Recommended Runtime Shape

### Services

- **Qwen embedding server** → `localhost:8000`
- **qwen-vlrag / velvet API** → `localhost:8001`
- **Neo4j** → `bolt://localhost:7687`

### Why this split matters

The current frontend assumes:
- API base at `/api`
- Qwen health on port `8000`

So the clean setup is:
- keep Qwen on `8000`
- run the new FastAPI wrapper on `8001`
- point frontend to `http://localhost:8001/api`

Do **not** try to colocate the wrapper on the same port as Qwen.

---

## Phase 1 — Wrap Existing Scripts Behind a Real Backend

### 1. Create a FastAPI app

Build a small backend, probably something like:

```text
backend/
  app.py
  config.py
  services/
    ingest_service.py
    search_service.py
    neo4j_service.py
    thumbs.py
```

Goal:
- avoid keeping all logic inside route handlers
- keep script-wrapping separate from API layer
- make later refactor from subprocess → shared library easier

### 2. Implement the four core endpoints from `BACKEND_SPEC.md`

#### `GET /api/health`
Should report:
- whether Qwen is reachable
- whether Neo4j is reachable
- current indexed node count

Return shape:

```json
{
  "qwen_up": true,
  "neo4j_up": true,
  "node_count": 1245
}
```

#### `POST /api/ingest`
Use subprocess wrapping first. Do not overengineer.

Requirements:
- accept `folder`, `limit`, `resume`
- map `resume=true` to default behavior
- map `resume=false` to `--force`
- stream logs as SSE
- prevent duplicate concurrent ingest jobs

Practical note:
- v1 can be "one ingest job at a time"
- we do not need distributed job management yet

#### `POST /api/search`
Accept:
- text query
- image upload
- category filter
- top N

Return:
- filename
- score
- path
- category/subfolder
- thumbnail

Important:
- keep this endpoint stable because this is the one agents/UI will depend on most

#### `POST /api/open`
Thin wrapper around local file open.

Use for the UI only.

---

## Phase 2 — Normalize Configuration

Right now the scripts hardcode:

- Qwen URL
- Neo4j URI
- Neo4j credentials
- library root
- vector index name

That is fine for local hacking but bad for reuse.

### Replace hardcoded values with config

Use env vars or a `.env` file for:

- `QVLRAG_QWEN_URL`
- `QVLRAG_NEO4J_URI`
- `QVLRAG_NEO4J_USER`
- `QVLRAG_NEO4J_PASS`
- `QVLRAG_LIBRARY_ROOT`
- `QVLRAG_VECTOR_INDEX`
- `QVLRAG_API_HOST`
- `QVLRAG_API_PORT`

### Minimum goal

Even if the internal scripts still exist, the backend should read all runtime config from one place.

That gives us:
- reproducibility
- easier local boot
- publishable defaults later

---

## Phase 3 — Make Search Results UI-Ready

The frontend expects visual results, so search responses should include thumbnails.

### Needed work

- generate thumbnail bytes from file path
- base64 encode them as `data:image/...;base64,...`
- include thumbnail in response payload

### Suggested response shape

```json
[
  {
    "filename": "img_123.jpg",
    "score": 0.88,
    "path": "/abs/path/img_123.jpg",
    "category": "Large",
    "subfolder": "Portraits",
    "thumbnail": "data:image/jpeg;base64,..."
  }
]
```

### Practical note

Do thumbnail generation on the backend, not the frontend.
The frontend should not need direct filesystem access.

---

## Phase 4 — Hook Up the Existing Frontend

### Required frontend changes

In `qvl-console.html`:
- set `MOCK_MODE = false`
- change `API_BASE` to `http://localhost:8001/api`
- keep `QWEN_URL` on `http://localhost:8000` if still used directly for status
- wire search and ingest to real endpoints

### Ingest notes

For ingest:
- use SSE from `/api/ingest`
- stream subprocess logs into the terminal panel
- update progress indicators from parsed messages if possible
- if parsing is messy at first, plain streamed logs are fine for v1

### Search notes

For search:
- send multipart form data
- render returned thumbnails and metadata
- wire "open" button to `/api/open`

---

## Phase 5 — Add an Agent-Facing Retrieval Surface

This is the step that makes it actually useful for OpenClaw/agent loops.

### Minimum useful endpoint

Either reuse `/api/search` or add a second endpoint like:

`POST /api/retrieve`

Body:

```json
{
  "text": "woman with dark hair in low light",
  "top_n": 10,
  "category": "Large"
}
```

Return:
- path
- score
- short metadata
- optionally thumbnail

### Why this matters

The frontend endpoint and the agent endpoint may be similar, but they are not conceptually identical.

The UI wants:
- thumbnails
- open buttons
- rich display fields

Agents want:
- stable JSON
- low ambiguity
- no UI-only junk
- predictable schema

A clean v1 can still share one endpoint, but we should keep this distinction in mind.

---

## Phase 6 — Smoke Test the Whole Stack

Before trying OpenClaw integration, prove these flows end to end:

### Flow A — Infra boot
- start Neo4j
- run setup script / setup endpoint
- start Qwen server
- start FastAPI wrapper
- load frontend
- verify health is green

### Flow B — Ingest
- ingest one small batch (`limit=10`)
- confirm nodes appear in Neo4j
- confirm frontend count updates

### Flow C — Search
- text search returns matches
- image search returns matches
- thumbnails render
- open action works

### Flow D — Agent-facing use
- curl or Python client calls the API
- retrieve a stable list of results
- confirm results are usable by a non-UI caller

If these four flows work, we can honestly say the prototype is integration-ready.

---

## Phase 7 — First OpenClaw / Agent Loop Integration

Only after the stack is stable.

### First integration target

Treat VLRAG as a **sidecar memory service**, not a replacement for OpenClaw memory.

That means:
- OpenClaw text memory remains primary
- VLRAG handles multimodal retrieval
- agent queries it selectively when image-grounded recall might help

### Good first use cases

- retrieve visually similar prior images from a personal library
- retrieve prior generated images from ComfyUI outputs
- attach visual examples to planning or style continuity
- build a tiny tool wrapper that queries VLRAG and returns top matches

### Bad first use case

Do **not** try to fully rewrite OpenClaw memory around VLRAG in v1.
That is how scope explodes.

---

## Suggested Build Order

If we want the fastest path to usable:

1. create FastAPI shell
2. implement `/api/health`
3. implement `/api/search`
4. add thumbnail generation
5. implement `/api/open`
6. implement `/api/ingest` SSE
7. point frontend at real backend
8. run end-to-end smoke tests
9. add minimal agent-facing retrieval wrapper

That order gets search working early, which is the most motivating visible milestone.

---

## Definition of Done for This File

This phase is complete when we can say:

> qwen-vlrag is no longer just scripts + mock UI; it is a runnable local multimodal retrieval service with a working frontend and a stable backend surface suitable for agent integration.
