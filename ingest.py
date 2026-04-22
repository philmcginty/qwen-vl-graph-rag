"""
ingest.py — Image ingestion into Neo4j via Qwen VL embeddings

Walks an image directory tree, embeds each image via a Qwen VL embedding server,
and stores as VelvetImage nodes in Neo4j. Resumable — skips already-embedded images.

Usage:
    python ingest.py --root /path/to/images            # ingest everything
    python ingest.py --dry-run                         # use QVLRAG_LIBRARY_ROOT from backend/.env
    python ingest.py --limit 100                       # ingest first N images
    python ingest.py --folder Large                    # ingest one subfolder only

Environment variables (loaded automatically from backend/.env if present):
    QVLRAG_QWEN_URL   — Qwen server URL (default: http://localhost:8000)
    QVLRAG_NEO4J_URI  — Neo4j bolt URI (default: bolt://localhost:7687)
    QVLRAG_NEO4J_USER — Neo4j username (default: neo4j)
    QVLRAG_NEO4J_PASS — Neo4j password (default: empty)
"""

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent / "backend" / ".env")

# ── Config (from environment, with sensible defaults) ─────────────────────────

QWEN_BASE = os.getenv("QVLRAG_QWEN_URL", "http://localhost:8000")
QWEN_URL = f"{QWEN_BASE}/v1/embeddings"
NEO4J_URI = os.getenv("QVLRAG_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("QVLRAG_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("QVLRAG_NEO4J_PASS", "")
LIBRARY_ROOT = os.getenv("QVLRAG_LIBRARY_ROOT", "")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
BATCH_SIZE = 5          # Images per Neo4j write batch
REQUEST_TIMEOUT = 60    # Seconds to wait for Qwen per image

# ── Image Discovery ───────────────────────────────────────────────────────────

def find_images(root: Path, folder_filter: str = None):
    """Walk library tree and return all image paths."""
    images = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if folder_filter and folder_filter.lower() not in str(path).lower():
            continue
        images.append(path)
    return images


def get_size_category(path: Path, root: Path) -> str:
    """Extract size category from path (Large/Medium/Small/Video)."""
    parts = path.relative_to(root).parts
    if parts:
        top = parts[0]
        if top in ("Large", "Medium", "Small", "Video"):
            return top
    return "Unknown"


def get_subfolder(path: Path, root: Path) -> str:
    """Get the immediate subfolder name within the size category."""
    parts = path.relative_to(root).parts
    if len(parts) >= 2:
        return parts[1]
    return ""

# ── Already-Ingested Check ────────────────────────────────────────────────────

def get_ingested_paths(driver) -> set:
    """Return set of file paths already in Neo4j."""
    with driver.session() as session:
        result = session.run("MATCH (i:VelvetImage) RETURN i.path AS path")
        return {row["path"] for row in result}

# ── Qwen Embedding ────────────────────────────────────────────────────────────

def embed_image(image_path: Path) -> list[float] | None:
    """Get embedding for an image file via Qwen server."""
    try:
        payload = {
            "input": {
                "text": "",  # Empty text — pure visual embedding
                "image": {
                    "type": "path",
                    "data": str(image_path)
                }
            },
            "model": "qwen-vl-embedding"
        }
        resp = requests.post(QWEN_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]
    except requests.exceptions.Timeout:
        print(f"    ⏱ Timeout: {image_path.name}")
        return None
    except Exception as e:
        print(f"    ✗ Embed error {image_path.name}: {e}")
        return None

# ── Neo4j Write ───────────────────────────────────────────────────────────────

def write_batch(driver, batch: list[dict]):
    """Write a batch of image nodes to Neo4j."""
    with driver.session() as session:
        session.run("""
            UNWIND $nodes AS n
            MERGE (i:VelvetImage {path: n.path})
            SET i.filename = n.filename,
                i.size_category = n.size_category,
                i.subfolder = n.subfolder,
                i.extension = n.extension,
                i.file_size_bytes = n.file_size_bytes,
                i.embedding = n.embedding,
                i.ingested_at = n.ingested_at
        """, nodes=batch)

# ── Progress Tracking ─────────────────────────────────────────────────────────

def format_eta(elapsed: float, done: int, total: int) -> str:
    if done == 0:
        return "calculating..."
    rate = done / elapsed
    remaining = (total - done) / rate
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return f"{mins}m {secs}s"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Image → Neo4j ingestion via Qwen VL embeddings")
    parser.add_argument(
        "--root",
        type=str,
        default=LIBRARY_ROOT,
        required=not bool(LIBRARY_ROOT),
        help="Root directory of images to ingest (defaults to QVLRAG_LIBRARY_ROOT)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested without doing it")
    parser.add_argument("--limit", type=int, default=None, help="Max images to ingest")
    parser.add_argument("--folder", type=str, default=None, help="Only ingest images from this folder (e.g. 'Large')")
    parser.add_argument("--force", action="store_true", help="Re-embed even if already in Neo4j")
    args = parser.parse_args()

    library_root = Path(args.root)
    if not library_root.is_dir():
        print(f"Error: {library_root} is not a directory")
        sys.exit(1)

    # Connect to Neo4j
    print(f"Connecting to Neo4j...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        driver.verify_connectivity()
        print("  ✓ Connected")
    except Exception as e:
        print(f"  ✗ Neo4j connection failed: {e}")
        sys.exit(1)

    # Check Qwen server
    print(f"Checking Qwen embedding server...")
    try:
        health = requests.get(f"{QWEN_BASE}/health", timeout=5).json()
        print(f"  ✓ {health.get('model', 'OK')} on {health.get('device', 'unknown')}")
    except Exception as e:
        print(f"  ✗ Qwen server not reachable: {e}")
        sys.exit(1)

    # Discover images
    print(f"\nScanning {library_root}...")
    all_images = find_images(library_root, args.folder)
    print(f"  Found {len(all_images)} images")

    # Get already-ingested (for resume)
    if not args.force:
        print("  Checking already-ingested images...")
        ingested = get_ingested_paths(driver)
        pending = [p for p in all_images if str(p) not in ingested]
        print(f"  Already ingested: {len(ingested)}")
        print(f"  Pending: {len(pending)}")
    else:
        pending = all_images
        print("  --force: re-embedding all images")

    if args.limit:
        pending = pending[:args.limit]
        print(f"  --limit: processing first {args.limit}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would ingest {len(pending)} images:")
        for p in pending[:20]:
            print(f"  {get_size_category(p, library_root):8} | {get_subfolder(p, library_root):20} | {p.name}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")
        driver.close()
        return

    if not pending:
        print("\n✅ All images already ingested. Nothing to do.")
        driver.close()
        return

    # Ingest
    print(f"\nIngesting {len(pending)} images...")
    print(f"Batch size: {BATCH_SIZE} | Timeout per image: {REQUEST_TIMEOUT}s")
    print("-" * 60)

    start_time = time.time()
    batch = []
    done = 0
    failed = 0
    failed_paths = []

    for i, image_path in enumerate(pending):
        # Progress
        elapsed = time.time() - start_time
        eta = format_eta(elapsed, done, len(pending))
        print(f"[{i+1:4d}/{len(pending)}] {get_size_category(image_path, library_root):7} | {image_path.name[:40]:40} | ETA: {eta}", end="\r")

        # Embed
        embedding = embed_image(image_path)

        if embedding is None:
            failed += 1
            failed_paths.append(str(image_path))
            continue

        # Build node data
        try:
            file_size = image_path.stat().st_size
        except:
            file_size = 0

        batch.append({
            "path": str(image_path),
            "filename": image_path.name,
            "size_category": get_size_category(image_path, library_root),
            "subfolder": get_subfolder(image_path, library_root),
            "extension": image_path.suffix.lower(),
            "file_size_bytes": file_size,
            "embedding": embedding,
            "ingested_at": time.time()
        })
        done += 1

        # Write batch
        if len(batch) >= BATCH_SIZE:
            write_batch(driver, batch)
            batch = []

    # Final batch
    if batch:
        write_batch(driver, batch)

    # Done
    elapsed = time.time() - start_time
    print(" " * 80)  # clear progress line
    print("-" * 60)
    print(f"✅ Ingestion complete!")
    print(f"   Ingested: {done}")
    print(f"   Failed:   {failed}")
    print(f"   Time:     {elapsed/60:.1f} minutes")
    print(f"   Rate:     {done/elapsed:.1f} images/sec")

    if failed_paths:
        log_path = Path("ingest_failures.log")
        log_path.write_text("\n".join(failed_paths))
        print(f"   Failures logged to: {log_path}")

    driver.close()


if __name__ == "__main__":
    main()
