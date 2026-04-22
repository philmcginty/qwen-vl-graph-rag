from __future__ import annotations

import os
from pathlib import Path


class Settings:
    qwen_url: str = os.getenv("QVLRAG_QWEN_URL", "http://localhost:8000")
    neo4j_uri: str = os.getenv("QVLRAG_NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("QVLRAG_NEO4J_USER", "neo4j")
    neo4j_pass: str = os.getenv("QVLRAG_NEO4J_PASS", "")
    library_root: Path = Path(os.getenv("QVLRAG_LIBRARY_ROOT", ""))
    vector_index: str = os.getenv("QVLRAG_VECTOR_INDEX", "velvet_image_vector")
    api_host: str = os.getenv("QVLRAG_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("QVLRAG_API_PORT", "8001"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("QVLRAG_CORS_ORIGINS", "http://localhost:8001,http://127.0.0.1:8001,null").split(",")
        if origin.strip()
    ]


settings = Settings()
