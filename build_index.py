"""Embed chunks and load them into a persistent ChromaDB collection.

Input:   documents/processed/chunks.jsonl   (from chunk.py)
Output:  chroma_db/                          (persistent vector store)

Embedding model: all-MiniLM-L6-v2 via sentence-transformers (local, 384-dim).
Distance: cosine (Chroma reports distance = 1 - cosine similarity, so lower
is better and ~0 is a near-exact match).

Usage:   python build_index.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("documents/processed/chunks.jsonl")
DB_DIR = "chroma_db"
COLLECTION = "unofficial_guide"
MODEL_NAME = "all-MiniLM-L6-v2"


def build_index() -> None:
    chunks = [json.loads(line) for line in open(CHUNKS_FILE)]
    print(f"Embedding {len(chunks)} chunks with {MODEL_NAME}…")

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        [c["text"] for c in chunks],
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    client = chromadb.PersistentClient(path=DB_DIR)
    try:                                       # rebuild from scratch every run
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        embeddings=embeddings.tolist(),
        documents=[c["text"] for c in chunks],
        metadatas=[{
            "source": c["source"],
            "title": c["title"],
            "source_type": c["source_type"],
            "url": c["url"],
            "year": c["year"],
            "score": c["score"],
            "kind": c["kind"],
            "position": c["position"],
        } for c in chunks],
    )
    print(f"Indexed {collection.count()} chunks -> {DB_DIR}/ ({COLLECTION})")


if __name__ == "__main__":
    build_index()
