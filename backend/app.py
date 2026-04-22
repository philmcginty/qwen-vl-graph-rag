from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from neo4j import GraphDatabase
from pydantic import BaseModel

try:
    from .config import settings
    from .thumbs import make_data_url
except ImportError:
    from config import settings
    from thumbs import make_data_url

app = FastAPI(title="qwen-vlrag API", version="0.1.0")
active_ingest_process: subprocess.Popen[str] | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_pass),
    )


def qwen_health() -> dict[str, Any]:
    response = requests.get(f"{settings.qwen_url}/health", timeout=5)
    response.raise_for_status()
    return response.json()


def validate_vector_index_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid QVLRAG_VECTOR_INDEX: {name!r}")
    return name


def resolve_library_path(path_str: str) -> Path:
    if settings.library_root is None:
        raise HTTPException(status_code=400, detail="QVLRAG_LIBRARY_ROOT is not configured")

    requested_path = Path(path_str).expanduser().resolve()

    try:
        requested_path.relative_to(settings.library_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Path must be inside QVLRAG_LIBRARY_ROOT") from exc

    return requested_path


def open_with_default_app(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def embed_text(text: str) -> list[float]:
    response = requests.post(
        f"{settings.qwen_url}/v1/embeddings",
        json={"input": text, "model": "qwen-vl-embedding"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def embed_uploaded_image(upload: UploadFile) -> list[float]:
    data = upload.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded image was empty")

    encoded = base64.b64encode(data).decode("utf-8")
    response = requests.post(
        f"{settings.qwen_url}/v1/embeddings",
        json={
            "input": {
                "text": "",
                "image": {"type": "base64", "data": encoded},
            },
            "model": "qwen-vl-embedding",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def query_vector_search(embedding: list[float], top_n: int = 20, category: str | None = None) -> list[dict[str, Any]]:
    vector_index = validate_vector_index_name(settings.vector_index)

    query_all = f"""
        CALL db.index.vector.queryNodes('{vector_index}', $top_n, $embedding)
        YIELD node, score
        RETURN node.path AS path,
               node.filename AS filename,
               node.size_category AS category,
               node.subfolder AS subfolder,
               score
        ORDER BY score DESC
    """

    query_filtered = f"""
        CALL db.index.vector.queryNodes('{vector_index}', $top_n, $embedding)
        YIELD node, score
        WHERE node.size_category = $category
        RETURN node.path AS path,
               node.filename AS filename,
               node.size_category AS category,
               node.subfolder AS subfolder,
               score
        ORDER BY score DESC
    """

    with get_driver() as driver:
        with driver.session() as session:
            if category and category != "All":
                result = session.run(
                    query_filtered,
                    embedding=embedding,
                    top_n=top_n * 3,
                    category=category,
                )
            else:
                result = session.run(
                    query_all,
                    embedding=embedding,
                    top_n=top_n,
                )

            rows = [dict(row) for row in result][:top_n]

    for row in rows:
        row["thumbnail"] = make_data_url(row["path"])

    return rows


class OpenRequest(BaseModel):
    path: str


class IngestRequest(BaseModel):
    folder: str = "All"
    limit: int | None = None
    resume: bool = True


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/health")
def health():
    qwen_up = False
    neo4j_up = False
    node_count = 0
    qwen_info: dict[str, Any] | None = None
    neo4j_error = None
    qwen_error = None

    try:
        qwen_info = qwen_health()
        qwen_up = True
    except Exception as exc:
        qwen_error = str(exc)

    try:
        with get_driver() as driver:
            driver.verify_connectivity()
            neo4j_up = True
            with driver.session() as session:
                row = session.run("MATCH (i:VelvetImage) RETURN count(i) AS count").single()
                node_count = int(row["count"] if row else 0)
    except Exception as exc:
        neo4j_error = str(exc)

    return {
        "qwen_up": qwen_up,
        "neo4j_up": neo4j_up,
        "node_count": node_count,
        "qwen": qwen_info,
        "errors": {
            "qwen": qwen_error,
            "neo4j": neo4j_error,
        },
    }


@app.post("/api/search")
def search(
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    category: str | None = Form(default=None),
    top_n: int = Form(default=20),
):
    if not text and not image:
        raise HTTPException(status_code=400, detail="Provide either text or image")

    if text and image:
        raise HTTPException(status_code=400, detail="Provide text or image, not both")

    if top_n < 1 or top_n > 100:
        raise HTTPException(status_code=400, detail="top_n must be between 1 and 100")

    try:
        embedding = embed_uploaded_image(image) if image else embed_text(text or "")
        return query_vector_search(embedding, top_n=top_n, category=category)
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"Qwen request failed: {detail}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/ingest")
async def ingest(request: IngestRequest):
    global active_ingest_process

    if active_ingest_process is not None and active_ingest_process.poll() is None:
        raise HTTPException(status_code=409, detail="An ingest job is already running")

    script_path = Path(__file__).resolve().parent.parent / "ingest.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="ingest.py not found")

    command = [sys.executable, str(script_path)]
    if request.folder and request.folder != "All":
        command.extend(["--folder", request.folder])
    if request.limit is not None:
        command.extend(["--limit", str(request.limit)])
    if not request.resume:
        command.append("--force")
    if settings.library_root:
        command.extend(["--root", str(settings.library_root)])

    async def event_stream():
        global active_ingest_process
        try:
            active_ingest_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})
            active_ingest_process = None
            return

        yield sse_event("start", {"command": command})

        assert active_ingest_process.stdout is not None
        loop = asyncio.get_running_loop()

        try:
            while True:
                line = await loop.run_in_executor(None, active_ingest_process.stdout.readline)
                if not line:
                    break
                yield sse_event("log", {"line": line.rstrip("\n")})

            return_code = await loop.run_in_executor(None, active_ingest_process.wait)
            if return_code == 0:
                yield sse_event("done", {"ok": True, "returncode": return_code})
            else:
                yield sse_event("done", {"ok": False, "returncode": return_code})
        finally:
            active_ingest_process = None

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/open")
def open_file(request: OpenRequest):
    path = resolve_library_path(request.path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        open_with_default_app(path)
        return {"ok": True, "path": str(path)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
def root():
    return {"name": "qwen-vlrag API", "status": "ok", "docs": "/docs", "health": "/api/health"}
