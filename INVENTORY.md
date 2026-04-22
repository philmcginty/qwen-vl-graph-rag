# qwen-vlrag Inventory Notes

## Purpose

This file captures the initial reconnaissance pass on the existing phase-2 VLRAG work so it can be pulled forward into `qwen-vlrag` later without re-scanning everything from scratch.

## Main existing source directory

Primary WIP source identified by Phil:

- `/home/metik2009/AI/velvet-rag`

This appears to be the current **phase-2 layer**, separate from the standalone Qwen embedding server repo.

## High-level read

`velvet-rag` is not a blank stub. It already contains a compact but real prototype stack:
- working ingestion logic
- working search logic
- Neo4j setup logic
- a frontend console UI
- a backend/API spec for the missing wrapper layer
- a local Python virtual environment

Current maturity read at first pass:

> This is a script-first working prototype with a UI shell and a written backend plan, but not yet a fully wrapped, public-facing product.

Updated maturity read after 2026-04-11 implementation work:

> It is now a working end-to-end local prototype with a real FastAPI wrapper, successful ingest, and successful frontend search — still rough, but no longer merely planned.

## Current directory contents observed

From quick scan of `/home/metik2009/AI/velvet-rag`:

- `/home/metik2009/AI/velvet-rag/BACKEND_SPEC.md`
- `/home/metik2009/AI/velvet-rag/ingest.py`
- `/home/metik2009/AI/velvet-rag/search.py`
- `/home/metik2009/AI/velvet-rag/setup_neo4j.py`
- `/home/metik2009/AI/velvet-rag/qvl-console.html`
- `/home/metik2009/AI/velvet-rag/ingest_failures.log`
- `/home/metik2009/AI/velvet-rag/.venv/`

## Key file findings

### 1. Backend/API design note
**Path:** `/home/metik2009/AI/velvet-rag/BACKEND_SPEC.md`

This file describes the intended FastAPI wrapper around the existing scripts.

Important planned endpoints:
- `GET /api/health`
- `POST /api/ingest` (SSE streaming)
- `POST /api/search`
- `POST /api/open`

Takeaway:
- the missing integration layer is already conceptually defined
- the repo knows what backend it wants, even if it is not yet implemented

### 2. Ingestion script
**Path:** `/home/metik2009/AI/velvet-rag/ingest.py`

What it does:
- scans a local image library
- embeds images via the Qwen server
- writes records into Neo4j as `VelvetImage` nodes
- supports resumable ingestion by skipping already-ingested paths

Important hardcoded dependencies observed:
- image root: `/home/metik2009/AI/Velvet_Library`
- Qwen endpoint: `http://localhost:8000/v1/embeddings`
- Neo4j URI: `bolt://localhost:7687`
- Neo4j credentials: `neo4j / neo4j`

Useful behavior already present:
- `--dry-run`
- `--limit`
- `--folder`
- `--force`
- `--root`
- batching
- failure logging to `ingest_failures.log`
- Qwen healthcheck before ingest

Takeaway:
- ingestion is already real and usable
- but config is currently local/hardcoded and will need cleanup for a public repo

### 3. Search script
**Path:** `/home/metik2009/AI/velvet-rag/search.py`

What it does:
- embeds either text or a reference image through the Qwen server
- queries Neo4j vector index `velvet_image_vector`
- returns ranked matches with path / filename / score / category data
- can optionally open results in the system viewer

Important dependencies observed:
- Qwen endpoint: `http://localhost:8000/v1/embeddings`
- Neo4j URI: `bolt://localhost:7687`
- vector index name: `velvet_image_vector`

Useful behavior already present:
- text query mode
- image query mode
- top-N control
- category filtering
- optional `--open` behavior

Takeaway:
- retrieval logic already exists
- this likely becomes the core of the first search service in `qwen-vlrag`

### 4. Neo4j setup script
**Path:** `/home/metik2009/AI/velvet-rag/setup_neo4j.py`

What it does:
- creates uniqueness constraint on `VelvetImage.path`
- creates vector index `velvet_image_vector`
- assumes embedding dimension `2048`
- uses cosine similarity

Important dependencies observed:
- Neo4j URI: `bolt://localhost:7687`
- credentials: `neo4j / neo4j`

Takeaway:
- schema/index bootstrapping exists already
- useful source material for infra setup in the new project

### 5. Frontend UI
**Path:** `/home/metik2009/AI/velvet-rag/qvl-console.html`

What it appears to be:
- a fairly polished dark-mode console UI for ingestion + search
- includes status indicators, ingest controls, terminal output area, search controls, and result cards

Critical finding:
- UI is currently set to `MOCK_MODE: true`
- API base is intended as `http://localhost:8000/api`

Takeaway:
- frontend exists and is visually ahead of the backend integration state
- likely good source material for an admin/debug console in `qwen-vlrag`

## Environment findings

### Local virtualenv
**Path:** `/home/metik2009/AI/velvet-rag/.venv`

Observed:
- Python present and working in venv
- `requests` import works
- `neo4j` import works

Takeaway:
- the local project environment is not empty or obviously broken
- useful as a source of dependency hints, but likely not something to copy directly into a public-facing consolidated repo

### Library root exists
**Path:** `/home/metik2009/AI/Velvet_Library`

Observed top-level categories:
- `Large`
- `Medium`
- `Small`
- `Video`

Takeaway:
- ingest target exists and matches the assumptions in `ingest.py`

## Current structural assessment

What appears complete enough to reuse:
- ingestion logic
- search logic
- Neo4j vector setup logic
- frontend console concepts/UI
- backend endpoint spec

What appeared missing or incomplete on the first pass:
- actual FastAPI wrapper / API server
- environment/config cleanup for public use
- repo structure cleanup
- clearer separation of reusable library code vs one-off scripts
- end-to-end packaging/documentation for a public repo

What changed on 2026-04-11:
- a FastAPI wrapper now exists under `velvet-rag/backend/`
- health, search, open, and ingest endpoints are functioning
- the frontend has been switched from mock mode to the real backend
- ingest has been validated against live Qwen + Neo4j services
- frontend search has returned expected real results

What remains missing or incomplete now:
- oversized-image fallback/downscaling
- config normalization across old scripts and new backend
- public-facing repo structure and packaging
- clearer extraction boundary for what should move into `qwen-vlrag`
- higher-order graph relationships / richer metadata model

## Most important interpretation

The highest-value next move is probably **not** greenfield building.
It is:
- extracting the working parts from `velvet-rag`
- normalizing configuration
- wrapping them behind a proper API/service boundary
- documenting the architecture cleanly in `qwen-vlrag`

## Likely role in new project

Best current read:
- `velvet-rag` should be treated as **source material / precursor implementation**
- `qwen-vlrag` should become the cleaner, public-facing consolidated repo
- the new repo should absorb or rewrite the good parts rather than inheriting the WIP structure wholesale

## Suggested next pass later

When returning to this project, likely useful follow-up tasks:
1. map all related directories/repositories beyond `velvet-rag`
2. inspect the Qwen embedding server repo side-by-side with this one
3. define the target repo layout for `qwen-vlrag`
4. decide what gets copied, adapted, or rewritten
5. create a `PLAN.md` for prototype assembly sequence
