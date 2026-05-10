"""
Re-generate all embeddings using the new Gemini text-embedding-004 model.
Run this once after switching from sentence-transformers to Gemini embeddings.

Usage:
    uv run python3 scripts/reembed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.database import get_connection
from ingestion.embeddings import update_embedding
import time

def main():
    # Clear all existing embeddings (they're 384-dim, incompatible with new 768-dim)
    conn = get_connection()
    with conn:
        conn.execute("UPDATE market_signals SET embedding = NULL")
    count = conn.execute("SELECT COUNT(*) FROM market_signals").fetchone()[0]
    conn.close()
    print(f"Cleared embeddings for {count} rows. Re-generating with Gemini...")

    conn = get_connection()
    rows = conn.execute("SELECT id, content FROM market_signals").fetchall()
    conn.close()

    total = len(rows)
    for i, row in enumerate(rows, 1):
        try:
            update_embedding(row["id"], row["content"])
            if i % 10 == 0 or i == total:
                print(f"  {i}/{total} done")
            # Stay within Gemini free tier (1500 RPM)
            if i % 20 == 0:
                time.sleep(1)
        except Exception as e:
            print(f"  FAILED row {row['id']}: {e}")

    print(f"\nDone. {total} embeddings regenerated.")

if __name__ == "__main__":
    main()
