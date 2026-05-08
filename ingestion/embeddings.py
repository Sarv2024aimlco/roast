import numpy as np
from sentence_transformers import SentenceTransformer
from ingestion.database import get_connection

# Load the model once when this module is imported.
# All subsequent calls reuse the same loaded model — no re-downloading.
# all-MiniLM-L6-v2: small (90MB), fast, good quality. 384 dimensions per embedding.
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> bytes:
    """
    Convert a string into a 384-dimensional embedding vector.
    Returns the vector as raw bytes (BLOB) for SQLite storage.
    """
    vector = _model.encode(text, normalize_embeddings=True)
    # numpy array → raw bytes so SQLite can store it as BLOB
    return vector.astype(np.float32).tobytes()


def bytes_to_vector(blob: bytes) -> np.ndarray:
    """
    Convert raw bytes from SQLite back into a numpy array.
    Used during vector search to compare embeddings.
    """
    return np.frombuffer(blob, dtype=np.float32)


def update_embedding(row_id: int, text: str) -> None:
    """
    Generate an embedding for `text` and store it in the
    embedding column for the given row_id.
    """
    embedding_bytes = embed_text(text)

    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE market_signals SET embedding = ? WHERE id = ?",
            (embedding_bytes, row_id),
        )
    conn.close()


def embed_all_missing() -> int:
    """
    Find all rows with no embedding yet and generate one for each.
    Called after bulk inserts to fill in embeddings in one pass.
    Returns number of rows updated.
    """
    conn = get_connection()

    rows = conn.execute(
        "SELECT id, content FROM market_signals WHERE embedding IS NULL"
    ).fetchall()

    conn.close()

    for row in rows:
        update_embedding(row["id"], row["content"])

    return len(rows)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate how similar two vectors are.
    Returns a value between -1 and 1.
    1.0  = identical meaning
    0.0  = unrelated
    -1.0 = opposite meaning (rare in practice)

    Since we normalise embeddings on creation (normalize_embeddings=True),
    cosine similarity is just a dot product — fast.
    """
    return float(np.dot(a, b))


def search_by_embedding(
    query: str,
    role: str,
    company_type: str,
    market: str,
    limit: int = 15,
) -> list[dict]:
    """
    Find the most semantically similar signals to `query`
    for a given role + company_type + market combination.

    Steps:
    1. Embed the query
    2. Fetch all signals for the combination that have embeddings
    3. Compute cosine similarity between query and each signal
    4. Return top `limit` results sorted by similarity
    """
    query_vector = bytes_to_vector(embed_text(query))

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT id, role, company_type, market, source, signal_type, content, embedding
        FROM market_signals
        WHERE role = ? AND company_type = ? AND market = ?
        AND embedding IS NOT NULL
        AND fetched_at > (strftime('%s', 'now') - 3888000)
        """,
        (role, company_type, market),
    ).fetchall()

    conn.close()

    # Score each row by cosine similarity to the query
    scored = []
    for row in rows:
        vector = bytes_to_vector(row["embedding"])
        score = cosine_similarity(query_vector, vector)
        scored.append({
            "id": row["id"],
            "role": row["role"],
            "company_type": row["company_type"],
            "market": row["market"],
            "source": row["source"],
            "signal_type": row["signal_type"],
            "content": row["content"],
            "score": score,
        })

    # Sort by score descending — highest similarity first
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored[:limit]
