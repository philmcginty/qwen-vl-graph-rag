# qwen-vlrag

A local multimodal retrieval system: ingest images via Qwen3-VL embeddings, store in Neo4j, and search with text or reference images through a web console.

## Architecture

```
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
- Qwen3-VL embedding server running on port 8000 (see [Qwen VL docs](https://github.com/QwenLM/Qwen3-VL))

## Setup

### 1. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Or set environment variables directly:

| Variable | Default | Description |
|---|---|---|
| `QVLRAG_QWEN_URL` | `http://localhost:8000` | Qwen embedding server URL |
| `QVLRAG_NEO4J_URI` | `bolt://localhost:7687` | Neo4j bolt URI |
| `QVLRAG_NEO4J_USER` | `neo4j` | Neo4j username |
| `QVLRAG_NEO4J_PASS` | (none) | Neo4j password |
| `QVLRAG_LIBRARY_ROOT` | (none — required for ingest) | Root directory of images to ingest |
| `QVLRAG_VECTOR_INDEX` | `velvet_image_vector` | Neo4j vector index name |
| `QVLRAG_API_HOST` | `127.0.0.1` | Backend bind host |
| `QVLRAG_API_PORT` | `8001` | Backend bind port |

### 3. Start the backend

```bash
cd backend
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

### 4. Open the frontend

Open `frontend/console.html` in a browser.

### 5. (Optional) Ingest images via CLI

```bash
python ingest.py --root /path/to/your/images --limit 50
```

See `python ingest.py --help` for all options.

### 6. (Optional) Search via CLI

```bash
python search.py "your text query"
python search.py --image /path/to/reference.png
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service health + node count |
| `/api/search` | POST | Text or image search (multipart/form-data) |
| `/api/ingest` | POST | Start ingest job (SSE log streaming) |
| `/api/open` | POST | Open image file in system viewer |

## Project Structure

```
qwen-vlrag/
├── backend/
│   ├── app.py          # FastAPI application
│   ├── config.py       # Environment-based settings
│   ├── thumbs.py       # Thumbnail generation
│   └── requirements.txt
├── frontend/
│   └── console.html    # VLRAG Control Console
├── ingest.py           # CLI image ingestion script
├── search.py           # CLI search script
├── setup_neo4j.py      # Neo4j index setup helper
└── README.md
```

## License

MIT
