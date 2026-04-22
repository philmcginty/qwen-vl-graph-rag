from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]


class Settings:
    def __init__(self) -> None:
        self.qwen_url: str = os.getenv("QVLRAG_QWEN_URL", "http://localhost:8000")
        self.neo4j_uri: str = os.getenv("QVLRAG_NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user: str = os.getenv("QVLRAG_NEO4J_USER", "neo4j")
        self.neo4j_pass: str = os.getenv("QVLRAG_NEO4J_PASS", "")

        library_root = os.getenv("QVLRAG_LIBRARY_ROOT", "").strip()
        self.library_root: Path | None = Path(library_root).expanduser().resolve() if library_root else None

        self.vector_index: str = os.getenv("QVLRAG_VECTOR_INDEX", "velvet_image_vector")
        self.api_host: str = os.getenv("QVLRAG_API_HOST", "127.0.0.1")
        self.api_port: int = int(os.getenv("QVLRAG_API_PORT", "8001"))

        cors_origins_raw = os.getenv("QVLRAG_CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS))
        parsed_cors_origins = [
            origin.strip()
            for origin in cors_origins_raw.split(",")
            if origin.strip()
        ]
        self.cors_origins: list[str] = parsed_cors_origins or DEFAULT_CORS_ORIGINS.copy()


settings = Settings()
