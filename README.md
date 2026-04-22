# qwen-vlrag

A local multimodal retrieval system that ingests images with Qwen3-VL embeddings, stores them in Neo4j, and lets you search by text or reference image through a lightweight web console.

## What it does

- embeds images with a Qwen3-VL embedding server
- stores image metadata + vectors in Neo4j
- supports text-to-image and image-to-image retrieval
- includes a simple FastAPI backend and single-file HTML frontend

## Architecture

```text
Qwen VL Embedding Server (port 8000)
        ↕
FastAPI Backend (port 8001)
        ↕
Neo4j (bolt://localhost:7687)
        ↕
VLRAG Console (frontend HTML)
```

## Prerequisites

- Python 3.10+
- [Neo4j](https://neo4j.com/download/) running locally
- A Qwen3-VL embedding server running on port 8000
  - Qwen docs: https://github.com/QwenLM/Qwen3-VL

## Quickstart

Recommended setup order:

### 1. Start the Qwen VL embedding server

Run your Qwen3-VL embedding server first so the backend and CLI tools can request embeddings.

### 2. Start Neo4j

Make sure Neo4j is running and reachable at your configured Bolt URL.

### 3. Create and activate a virtual environment

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On macOS and Linux, this avoids installing packages into the system Python.

### 4. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 5. Copy the env template and fill in your local values

```bash
cp backend/.env.example backend/.env
```

At minimum, set:

- `QVLRAG_NEO4J_PASS`
- `QVLRAG_LIBRARY_ROOT`

The backend and CLI scripts load `backend/.env` automatically if it exists.

### 6. Create the Neo4j vector index

Run this before `ingest.py` on a fresh database:

```bash
python setup_neo4j.py
```

### 7. Start the backend

From the repo root:

```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8001 --reload
```

### 8. Serve the frontend locally and open it in your browser

Because the backend now uses a safer default CORS configuration, serve the frontend over `http://localhost` instead of opening `console.html` directly with `file://`.

From the repo root:

```bash
cd frontend
python -m http.server 8080
```

Then open:

- http://127.0.0.1:8080/console.html
- or http://localhost:8080/console.html

On macOS you can do:

```bash
open http://127.0.0.1:8080/console.html
```

## Minimal run commands

Once Qwen and Neo4j are already running, the shortest path is:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# edit backend/.env with your Neo4j password and image library path

python setup_neo4j.py
uvicorn backend.app:app --port 8001

cd frontend && python -m http.server 8080
```

Then open `http://127.0.0.1:8080/console.html` in your browser.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `QVLRAG_QWEN_URL` | `http://localhost:8000` | Qwen embedding server URL |
| `QVLRAG_NEO4J_URI` | `bolt://localhost:7687` | Neo4j bolt URI |
| `QVLRAG_NEO4J_USER` | `neo4j` | Neo4j username |
| `QVLRAG_NEO4J_PASS` | (none) | Neo4j password |
| `QVLRAG_LIBRARY_ROOT` | (none) | Root directory of images to ingest |
| `QVLRAG_VECTOR_INDEX` | `velvet_image_vector` | Neo4j vector index name |
| `QVLRAG_API_HOST` | `127.0.0.1` | Backend bind host |
| `QVLRAG_API_PORT` | `8001` | Backend bind port |
| `QVLRAG_CORS_ORIGINS` | `http://localhost:8001,http://127.0.0.1:8001,http://localhost:8080,http://127.0.0.1:8080` | Allowed CORS origins |

## CLI Usage

### Ingest images

If `QVLRAG_LIBRARY_ROOT` is set in `backend/.env`:

```bash
python ingest.py --limit 50
```

Or override the root directly:

```bash
python ingest.py --root /path/to/your/images --limit 50
```

See all options:

```bash
python ingest.py --help
```

### Search from the CLI

```bash
python search.py "your text query"
python search.py --image /path/to/reference.png
```

To open matches in your system viewer:

```bash
python search.py "your text query" --open
```

`--open` works on macOS via `open` and on Linux via `xdg-open`.

## Important Notes

### Vector dimension must match the embedding model

`setup_neo4j.py` creates the Neo4j vector index with `VECTOR_DIM = 2048`, which matches `Qwen3-VL-Embedding-2B`.

If you use a different embedding model with a different output dimension, update `VECTOR_DIM` in `setup_neo4j.py` before running it.

### Fresh database setup

On a clean Neo4j instance, run:

```bash
python setup_neo4j.py
```

before running:

```bash
python ingest.py
```

### Image inputs are sent as bytes

`ingest.py`, CLI image search, and the web upload path send image content to the Qwen server as bytes/base64.

That means you do not need to enable path-based image loading on the Qwen server for normal use.

### Safer file opening behavior

The backend `POST /api/open` endpoint only opens files that resolve inside `QVLRAG_LIBRARY_ROOT`.

This is intentional: it keeps the convenience feature for browsing retrieved images, while avoiding arbitrary host-path opens outside the configured library.

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service health + node count |
| `/api/search` | POST | Text or image search (multipart/form-data) |
| `/api/ingest` | POST | Start ingest job (SSE log streaming) |
| `/api/open` | POST | Open an image from `QVLRAG_LIBRARY_ROOT` in the system viewer |

## Project Structure

```text
qwen-vlrag/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── thumbs.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   └── console.html
├── ingest.py
├── search.py
├── setup_neo4j.py
└── README.md
```

## License

MIT
