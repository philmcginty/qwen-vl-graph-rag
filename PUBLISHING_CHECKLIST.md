# qwen-vlrag — Prototype Publishing Checklist

This file is about getting the project into a state that is reasonable to publish on GitHub within the next week as a credible prototype.

Goal:
- not perfect
- not enterprise-ready
- but clean enough that someone can understand what it is, run it, and take the work seriously

---

## Publish Goal

A publishable prototype should communicate three things clearly:

1. **what it does**
2. **how to run it**
3. **why it matters**

For this repo, that means the public story should be:

> qwen-vlrag is a local multimodal retrieval prototype built around a Qwen3-VL embedding server, Neo4j vector search, and a lightweight UI/API layer for ingesting and querying image memory.

And the sharper research-facing angle can be mentioned without overselling:

> It is also part of a broader investigation into whether richer multimodal memory changes the failure modes of long-running agents compared to language-first memory systems.

---

## Phase A — Clean the Repository Shape

The current `velvet-rag` directory is a workable prototype but not a clean public repo.

### Target repo qualities

- clear file layout
- obvious entrypoints
- no local junk
- no machine-specific paths in committed source
- no secrets / bad defaults

### Likely target structure

```text
qwen-vlrag/
  README.md
  LICENSE
  .gitignore
  pyproject.toml
  .env.example
  backend/
    app.py
    config.py
    services/
  scripts/
    ingest.py
    search.py
    setup_neo4j.py
  frontend/
    qvl-console.html
  docs/
    ARCHITECTURE.md
    API.md
  examples/
    curl/
```

This does not need to be final, but it should feel intentional.

---

## Phase B — Remove Local Machine Leakage

Before publishing, remove or replace anything tied specifically to your workstation.

### Must fix

- absolute paths like `/home/metik2009/AI/...`
- hardcoded Neo4j credentials
- hardcoded localhost assumptions without explanation
- local `.venv/`
- `__pycache__/`
- generated logs like `ingest_failures.log`

### Action items

- move all runtime settings into config/env vars
- add `.gitignore`
- confirm repo tree is clean with `git status`

---

## Phase C — Add Minimal Packaging / Run Story

A public repo should have a single obvious install path.

### Good options

#### Option 1 — Keep it simple
- `pip install -r requirements.txt`
- `python backend/app.py`

#### Option 2 — Slightly cleaner
- `pyproject.toml`
- editable install
- `qvlrag-server` CLI entrypoint

My recommendation:
- if speed matters most this week, start with simple and readable
- if it only takes a bit more effort, use `pyproject.toml` because it makes the repo feel much more deliberate

---

## Phase D — Write the Public README Properly

The README matters a lot because it is what application reviewers and random GitHub visitors will actually see.

### README should answer

#### 1. What is this?
One-paragraph explanation.

#### 2. Why does it exist?
Tie together:
- local multimodal retrieval
- image memory / RAG
- agent memory experiments
- local/private workflows

#### 3. What can it do right now?
Be honest.

Example features section:
- ingest local image folders into Neo4j
- embed images and text with Qwen3-VL
- perform text-to-image and image-to-image retrieval
- browse results in a local web UI
- expose a lightweight API for integration

#### 4. Architecture at a glance
Show:
- frontend
- FastAPI wrapper
- Qwen server
- Neo4j
- local image library

#### 5. Quickstart
Exact commands.

#### 6. Status / scope
Call it a prototype explicitly.

#### 7. Roadmap
A short list of likely next steps.

### Important tone rule

Do not pretend it is more mature than it is.
"Prototype" is fine. "Experimental" is fine. Clean honesty reads better than inflated polish.

---

## Phase E — Add Basic Docs Beyond README

These do not need to be huge.

### `docs/ARCHITECTURE.md`
Should explain:
- data flow
- how ingest works
- how search works
- how the UI/backend/Qwen/Neo4j fit together

### `docs/API.md`
Should document:
- `/api/health`
- `/api/ingest`
- `/api/search`
- `/api/open`
- request/response examples

This gives the repo more legitimacy immediately.

---

## Phase F — Make Setup Repeatable

A public prototype should not require telepathy.

### Minimum viable setup story

Document:
- install Neo4j and how to start it
- how to run `setup_neo4j.py`
- how to run the Qwen embedding server
- how to run the API server
- how to open the frontend

### Nice-to-have if time allows

- `Makefile` or `justfile`
- helper scripts like:
  - `make setup`
  - `make run-api`
  - `make run-ui`
  - `make smoke-test`

Even a small `Makefile` makes the repo feel dramatically more usable.

---

## Phase G — Add a Few Screenshots / Demo Assets

For GitHub and application value, this is huge.

### Add at least:
- one screenshot of the UI
- one screenshot of search results
- maybe one screenshot of ingest/status

This makes the repo instantly more legible to reviewers.

If possible later:
- short GIF of search flow
- short GIF of ingest flow

---

## Phase H — Include a Tiny Example Dataset Story

The repo should explain what users are expected to point it at.

### Important because
Without this, people will wonder:
- what kind of images?
- how big?
- how should folders be structured?
- what metadata exists?

### Minimum solution
In README or docs, specify:
- supported file types
- example folder structure
- how category/subfolder is inferred

---

## Phase I — Add Roadmap / Known Limitations

This is especially important for a prototype repo.

### Good limitations section

Examples:
- local-only prototype
- no auth
- assumes Qwen server already running
- currently image-library oriented rather than general multimodal documents
- ingestion/search logic still maturing
- UI focused on exploration/debugging rather than polished product use

### Good roadmap section

Examples:
- replace subprocess wrapping with shared library code
- support richer metadata schemas
- expose cleaner retrieval endpoints for agent integration
- add configurable storage backends
- add evaluation harnesses for agent-memory experiments

This helps reviewers see direction without mistaking current scope.

---

## Phase J — GitHub Readiness Checklist

Before making the repo public:

- [ ] no secrets committed
- [ ] no local-only absolute paths remain in tracked source
- [ ] `.venv/` is excluded
- [ ] `__pycache__/` is excluded
- [ ] logs / outputs are excluded
- [ ] README is complete enough for first-time visitors
- [ ] install/run instructions work from a clean clone
- [ ] license is present
- [ ] screenshots added
- [ ] repo description/tagline chosen

Suggested short repo description:

> Local multimodal image-memory / VLRAG prototype using Qwen3-VL embeddings, Neo4j vector search, and a lightweight UI/API layer.

---

## Suggested This-Week Sequence

If the goal is GitHub by end of week, the likely best order is:

1. get the FastAPI wrapper working locally
2. hook up real search end to end
3. get ingest endpoint working
4. normalize config and remove local leakage
5. restructure repo just enough to be legible
6. write README + docs
7. add screenshots
8. publish as prototype

That is enough for a strong v1.

---

## What "Good Enough to Publish" Looks Like

The bar is not "finished product."
The bar is:

> a real, runnable prototype with a clear architecture, honest documentation, and enough polish that someone can see both the build quality and the research direction behind it.

That is absolutely achievable this week if scope stays disciplined.
