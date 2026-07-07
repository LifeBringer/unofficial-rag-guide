"""Retrieval for The Unofficial Guide.

retrieve(query, k=5) embeds the query with the same model used at index time
and returns the top-k chunks by cosine similarity, with their metadata and
distance (1 - cosine similarity; lower is better).

Usage:   python query.py "when should I start looking for an apartment?"
         python query.py --k 8 "is BART viable?"
"""

import argparse
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

DB_DIR = "chroma_db"
COLLECTION = "unofficial_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _collection():
    return chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k chunks for a query: [{text, distance, ...metadata}]."""
    embedding = _model().encode([query], normalize_embeddings=True)
    result = _collection().query(
        query_embeddings=embedding.tolist(),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"text": doc, "distance": round(dist, 3), **meta}
        for doc, dist, meta in zip(
            result["documents"][0], result["distances"][0], result["metadatas"][0]
        )
    ]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=TOP_K)
    args = ap.parse_args()

    for i, hit in enumerate(retrieve(args.query, args.k), 1):
        print(f"\n#{i}  distance={hit['distance']}  source={hit['source']} "
              f"({hit['kind']}, {hit['year']})")
        print(hit["text"])
