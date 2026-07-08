"""Stretch A — Hybrid retrieval: BM25 keyword search fused with semantic search.

Motivation: eval Q3 failed because the answering chunk ranked 8th by cosine
distance, but the query and answer share a rare literal token ("decline" —
only 5 chunks contain it). BM25 scores that token heavily; semantic search
can't see it.

Fusion: Reciprocal Rank Fusion (RRF). Each retriever contributes its top-N
ranking and a chunk's fused score is sum(1 / (60 + rank)). Rank fusion is
used instead of weighted score mixing because BM25 scores and cosine
distances live on incomparable scales — RRF needs no normalization and no
tuned weight.

Usage:   python hybrid.py "what happens if I decline my housing offer?"
         python hybrid.py --compare "…"     # side-by-side semantic/bm25/hybrid
"""

import argparse
import json
import re
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from query import retrieve

CHUNKS_FILE = Path("documents/processed/chunks.jsonl")
POOL = 20          # candidates taken from each retriever before fusion
RRF_K = 60         # standard RRF constant


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


@lru_cache(maxsize=1)
def _bm25_index():
    chunks = [json.loads(line) for line in open(CHUNKS_FILE)]
    return BM25Okapi([_tokenize(c["text"]) for c in chunks]), chunks


def retrieve_bm25(query: str, k: int = 5, source_type: str | None = None,
                  min_year: int | None = None) -> list[dict]:
    """Top-k chunks by BM25 keyword score (higher is better)."""
    bm25, chunks = _bm25_index()
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    hits = []
    for i in ranked:
        c = chunks[i]
        if source_type and c["source_type"] != source_type:
            continue
        if min_year and c["year"] < min_year:
            continue
        hits.append({**c, "bm25": round(scores[i], 2), "distance": None})
        if len(hits) == k:
            break
    return hits


def retrieve_hybrid(query: str, k: int = 5, source_type: str | None = None,
                    min_year: int | None = None) -> list[dict]:
    """Top-k chunks by RRF fusion of semantic (cosine) and BM25 rankings."""
    semantic = retrieve(query, k=POOL, source_type=source_type, min_year=min_year)
    keyword = retrieve_bm25(query, k=POOL, source_type=source_type,
                            min_year=min_year)

    fused: dict[str, dict] = {}
    for name, ranking in (("semantic", semantic), ("bm25", keyword)):
        for rank, hit in enumerate(ranking, 1):
            entry = fused.setdefault(hit["chunk_id"], {"hit": hit, "score": 0.0, "ranks": {}})
            entry["score"] += 1 / (RRF_K + rank)
            entry["ranks"][name] = rank

    top = sorted(fused.values(), key=lambda e: e["score"], reverse=True)[:k]
    return [{**e["hit"], "rrf": round(e["score"], 4), "ranks": e["ranks"]} for e in top]


def _show(label: str, hits: list[dict]) -> None:
    print(f"\n--- {label}")
    for i, h in enumerate(hits, 1):
        extra = h.get("ranks") or (f"bm25={h.get('bm25')}" if h.get("bm25") is not None
                                   else f"dist={h.get('distance')}")
        print(f"#{i} {h['source']}:{h['position']:03d} ({h['kind']}) {extra}")
        print(f"   {h['text'][:140]}…")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--compare", action="store_true",
                    help="show semantic, bm25, and hybrid side by side")
    args = ap.parse_args()

    if args.compare:
        _show("semantic (cosine)", retrieve(args.query, args.k))
        _show("BM25 (keyword)", retrieve_bm25(args.query, args.k))
        _show("hybrid (RRF)", retrieve_hybrid(args.query, args.k))
    else:
        _show("hybrid (RRF)", retrieve_hybrid(args.query, args.k))
