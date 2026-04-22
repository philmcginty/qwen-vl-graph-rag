"""
search.py — Visual similarity search against Neo4j
Query by text description or by reference image.

Usage:
    python search.py "red dress outdoor portrait"          # text query
    python search.py --image /path/to/reference.png        # image query
    python search.py "dark hair" --top 10                  # more results
    python search.py "portrait" --category Large           # filter by category

Environment variables (loaded automatically from backend/.env if present):
    QVLRAG_QWEN_URL   — Qwen server URL (default: http://localhost:8000)
    QVLRAG_NEO4J_URI  — Neo4j bolt URI (default: bolt://localhost:7687)
    QVLRAG_NEO4J_USER — Neo4j username (default: neo4j)
    QVLRAG_NEO4J_PASS — Neo4j password (default: empty)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")

QWEN_BASE = os.getenv("QVLRAG_QWEN_URL", "http://localhost:8000")
QWEN_URL = f"{QWEN_BASE}/v1/embeddings"
NEO4J_URI = os.getenv("QVLRAG_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("QVLRAG_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("QVLRAG_NEO4J_PASS", "")
VECTOR_INDEX = os.getenv("QVLRAG_VECTOR_INDEX", "velvet_image_vector")


def validate_vector_index_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid QVLRAG_VECTOR_INDEX: {name!r}")
    return name


def embed_text(text: str) -> list[float]:
    resp = requests.post(QWEN_URL, json={
        "input": text,
        "model": "qwen-vl-embedding"
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def embed_image(image_path: str) -> list[float]:
    resp = requests.post(QWEN_URL, json={
        "input": {
            "text": "",
            "image": {"type": "path", "data": image_path}
        },
        "model": "qwen-vl-embedding"
    }, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def search(driver, embedding: list[float], top_n: int = 5, category: str | None = None) -> list[dict]:
    vector_index = validate_vector_index_name(VECTOR_INDEX)

    with driver.session() as session:
        if category:
            result = session.run(f"""
                CALL db.index.vector.queryNodes('{vector_index}', $top_n, $embedding)
                YIELD node, score
                WHERE node.size_category = $category
                RETURN node.path AS path,
                       node.filename AS filename,
                       node.size_category AS category,
                       node.subfolder AS subfolder,
                       score
                ORDER BY score DESC
            """, embedding=embedding, top_n=top_n * 3, category=category)
        else:
            result = session.run(f"""
                CALL db.index.vector.queryNodes('{vector_index}', $top_n, $embedding)
                YIELD node, score
                RETURN node.path AS path,
                       node.filename AS filename,
                       node.size_category AS category,
                       node.subfolder AS subfolder,
                       score
                ORDER BY score DESC
            """, embedding=embedding, top_n=top_n)

        return [dict(row) for row in result][:top_n]


def open_with_default_app(path: str):
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


def open_images(paths: list[str]):
    """Open images in default viewer."""
    for path in paths:
        try:
            open_with_default_app(path)
        except Exception as e:
            print(f"  Could not open {path}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Visual similarity search")
    parser.add_argument("query", nargs="?", help="Text description to search for")
    parser.add_argument("--image", type=str, help="Path to reference image")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--category", type=str, help="Filter by size category (Large/Medium/Small)")
    parser.add_argument("--open", action="store_true", help="Open result images in viewer")
    args = parser.parse_args()

    if not args.query and not args.image:
        parser.print_help()
        sys.exit(1)

    # Connect
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Neo4j connection failed: {e}")
        sys.exit(1)

    # Embed query
    if args.image:
        print(f"Embedding reference image: {args.image}")
        embedding = embed_image(args.image)
    else:
        print(f"Searching for: \"{args.query}\"")
        embedding = embed_text(args.query)

    # Search
    filter_str = f" in {args.category}" if args.category else ""
    print(f"Finding top {args.top} matches{filter_str}...\n")

    results = search(driver, embedding, top_n=args.top, category=args.category)

    if not results:
        print("No results found. Is the library ingested? Run ingest.py first.")
        driver.close()
        return

    # Display
    print(f"{'#':>3}  {'Score':>6}  {'Category':8}  {'Subfolder':20}  Filename")
    print("-" * 80)
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        cat = r.get("category", "?")
        sub = (r.get("subfolder") or "")[:18]
        fname = r.get("filename", "?")[:35]
        print(f"{i:>3}.  {score:.4f}  {cat:8}  {sub:20}  {fname}")

    print()

    # Full paths
    print("Full paths:")
    paths = [r["path"] for r in results]
    for p in paths:
        print(f"  {p}")

    if args.open:
        print(f"\nOpening {len(paths)} images...")
        open_images(paths)

    driver.close()


if __name__ == "__main__":
    main()
