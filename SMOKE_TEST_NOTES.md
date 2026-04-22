# qwen-vlrag — Immediate Smoke Test Notes

Current local prototype wiring as of 2026-04-11:

## Services
- Qwen embedding server: `http://localhost:8000`
- velvet-rag FastAPI wrapper: `http://127.0.0.1:8001`
- frontend file: `/home/metik2009/AI/velvet-rag/qvl-console.html`

## Backend endpoints now scaffolded
- `GET /api/health`
- `POST /api/search`
- `POST /api/open`
- `POST /api/ingest` (SSE log streaming)

## Run sequence

```bash
# 1. Start qwen embedding server first
# (use existing qwen3-vl-embedding-server flow)

# 2. Start backend
cd /home/metik2009/AI/velvet-rag/backend
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8001 --reload

# 3. Health check
curl http://127.0.0.1:8001/api/health

# 4. Text search smoke test
curl -X POST http://127.0.0.1:8001/api/search \
  -F 'text=dark hair portrait' \
  -F 'top_n=5'

# 5. Open frontend
xdg-open /home/metik2009/AI/velvet-rag/qvl-console.html
```

## Expected early failure points
- Qwen not running
- Neo4j not running
- vector index missing (`setup_neo4j.py` not run)
- backend venv missing dependencies
- browser file-origin/CORS quirks from local HTML file

## If search works but UI is weird
That is acceptable for now. The real milestone is backend usability first, then UI cleanup.
