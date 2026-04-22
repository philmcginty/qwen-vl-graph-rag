"""
setup_neo4j.py — One-time Neo4j setup for qwen-vlrag
Creates vector indexes and constraints. Run once before ingest.

Environment variables:
    QVLRAG_NEO4J_URI  — Neo4j bolt URI (default: bolt://localhost:7687)
    QVLRAG_NEO4J_USER — Neo4j username (default: neo4j)
    QVLRAG_NEO4J_PASS — Neo4j password (default: empty)
"""

import os
import sys

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("QVLRAG_NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("QVLRAG_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("QVLRAG_NEO4J_PASS", "")
VECTOR_DIM = 2048  # Qwen3-VL-Embedding-2B output dimension


def run(driver):
    with driver.session() as session:

        # ── Constraints ───────────────────────────────────────────────
        print("Creating constraints...")
        session.run("""
            CREATE CONSTRAINT velvet_image_path IF NOT EXISTS
            FOR (i:VelvetImage) REQUIRE i.path IS UNIQUE
        """)
        print("  ✓ VelvetImage.path uniqueness constraint")

        # ── Vector Indexes ────────────────────────────────────────────
        print("Creating vector indexes...")

        result = session.run("""
            SHOW INDEXES YIELD name, type
            WHERE name = 'velvet_image_vector'
            RETURN name
        """)
        if result.single():
            print("  ⚠ velvet_image_vector already exists — skipping")
        else:
            session.run(f"""
                CREATE VECTOR INDEX velvet_image_vector IF NOT EXISTS
                FOR (i:VelvetImage) ON (i.embedding)
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {VECTOR_DIM},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
            """)
            print(f"  ✓ velvet_image_vector ({VECTOR_DIM}d, cosine)")

        # ── Verify ────────────────────────────────────────────────────
        print("\nCurrent indexes:")
        result = session.run("""
            SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state
            WHERE type IN ['VECTOR', 'RANGE', 'UNIQUENESS']
            RETURN name, type, labelsOrTypes, properties, state
            ORDER BY type, name
        """)
        for row in result:
            print(f"  [{row['state']:7}] {row['type']:12} {row['name']} — {row['labelsOrTypes']} {row['properties']}")

        print("\n✅ Setup complete. Neo4j is ready for image ingestion.")


def main():
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        driver.verify_connectivity()
        print("  ✓ Connected\n")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        sys.exit(1)

    try:
        run(driver)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
