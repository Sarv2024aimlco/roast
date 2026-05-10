"""
Re-generate embeddings using Gemini gemini-embedding-001 (3072-dim).
Resumes from where it left off — only processes rows with NULL embeddings.

Usage:
    uv run python3 scripts/reembed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from ingestion.database import get_connection
from ingestion.embeddings import update_embedding
import time


def main():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, content FROM market_signals WHERE embedding IS NULL"
    ).fetchall()
    conn.close()

    total = len(rows)
    if total == 0:
        print("All embeddings already generated.")
        return

    print(f"Found {total} rows with missing embeddings. Generating...")

    done = 0
    for i, row in enumerate(rows, 1):
        try:
            update_embedding(row["id"], row["content"])
            done += 1
            if i % 10 == 0 or i == total:
                print(f"  {i}/{total} done")
            time.sleep(0.1)  # ~10 req/s, well within 1000/day limit
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"\nRate limit hit at row {row['id']}. Waiting 65s before retry...")
                time.sleep(65)
                try:
                    update_embedding(row["id"], row["content"])
                    done += 1
                    print(f"  {i}/{total} done (after retry)")
                except Exception as e2:
                    print(f"  FAILED row {row['id']} after retry: {e2}")
            else:
                print(f"  FAILED row {row['id']}: {e}")

    print(f"\nDone. {done}/{total} embeddings generated.")


if __name__ == "__main__":
    main()
