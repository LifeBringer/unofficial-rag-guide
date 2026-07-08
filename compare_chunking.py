"""Stretch B — Compare two chunking strategies on the same query set.

Strategy A (production): structure-aware chunks from chunk.py
    (1 comment = 1 chunk, <=900 chars, title prefix, short-comment filter).
Strategy B (naive): each document's cleaned text concatenated in order and
    sliced into fixed 500-char windows with 100-char overlap — exactly the
    "split every 500 characters" approach the project instructions warn about.

Both sets are embedded with the same model (all-MiniLM-L6-v2) and ranked by
cosine similarity for the 5 evaluation questions. Metric: hit@5 — does any
top-5 chunk contain the known answer marker — plus the rank of the first
answering chunk (searched to rank 20).

Usage:   python compare_chunking.py
"""

import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DOCS_FILE = Path("documents/processed/documents.jsonl")
CHUNKS_FILE = Path("documents/processed/chunks.jsonl")

FIXED_SIZE = 500
FIXED_OVERLAP = 100

# (question, answer-marker regex, marker description)
QUERIES = [
    ("How much does a one-way BART ride from Oakland to Berkeley cost, "
     "and which transit is free for Cal students?",
     r"2\.25", '"2.25" (the fare)'),
    ("Which other company names do students say Raj Properties operates under?",
     r"URSA|Everest Properties", "the alias list"),
    ("What do students warn will happen if you decline your UC Berkeley "
     "on-campus housing offer?",
     r"DO NOT DECLINE", "the decline warning"),
    ("How do students compare Blackwell Hall and Unit 3 as freshman dorms?",
     r"objectively the best dorm", "the canonical comparison"),
    ("What does a room in a shared apartment near campus typically cost, "
     "according to students?",
     r"\$?1[,]?[0-5]\d\d\b.{0,60}(room|single)|(room|single).{0,60}\$?1[,]?[0-5]\d\d\b",
     "a single-room price point"),
]


def fixed_chunks() -> list[dict]:
    """Strategy B: naive fixed-size windows over concatenated document text."""
    chunks = []
    for line in open(DOCS_FILE):
        doc = json.loads(line)
        text = "\n\n".join([doc["title"]] + [u["text"] for u in doc["units"]])
        step = FIXED_SIZE - FIXED_OVERLAP
        for i, start in enumerate(range(0, max(len(text) - FIXED_OVERLAP, 1), step)):
            piece = text[start:start + FIXED_SIZE]
            if piece.strip():
                chunks.append({"chunk_id": f'{doc["doc_id"]}#f{i:03d}',
                               "source": doc["doc_id"], "text": piece})
    return chunks


def rank_of_first_hit(query_vec, chunk_vecs, chunks, marker, depth=20):
    """Return (rank, chunk) of the first chunk matching marker, else (None, None)."""
    order = np.argsort(-chunk_vecs @ query_vec)
    for rank, idx in enumerate(order[:depth], 1):
        if re.search(marker, chunks[idx]["text"], re.IGNORECASE):
            return rank, chunks[idx]
    return None, None


if __name__ == "__main__":
    strategy_a = [json.loads(l) for l in open(CHUNKS_FILE)]
    strategy_b = fixed_chunks()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Strategy A (structure-aware): {len(strategy_a)} chunks")
    print(f"Strategy B (fixed {FIXED_SIZE}/{FIXED_OVERLAP}): {len(strategy_b)} chunks")
    vecs = {
        "A": model.encode([c["text"] for c in strategy_a], normalize_embeddings=True),
        "B": model.encode([c["text"] for c in strategy_b], normalize_embeddings=True),
    }
    sets = {"A": strategy_a, "B": strategy_b}

    wins = {"A": 0, "B": 0}
    for question, marker, desc in QUERIES:
        q_vec = model.encode([question], normalize_embeddings=True)[0]
        print(f"\nQ: {question[:74]}…\n   answer marker: {desc}")
        ranks = {}
        for name in ("A", "B"):
            rank, chunk = rank_of_first_hit(q_vec, vecs[name], sets[name], marker)
            ranks[name] = rank
            status = (f"rank {rank} {'(hit@5)' if rank and rank <= 5 else '(MISS top-5)'}"
                      if rank else "not in top 20")
            print(f"   {name}: {status}"
                  + (f"  [{chunk['source']}]" if chunk else ""))
        a, b = ranks["A"] or 99, ranks["B"] or 99
        if a < b:
            wins["A"] += 1
        elif b < a:
            wins["B"] += 1

    print(f"\nFirst-hit wins — structure-aware: {wins['A']}, fixed-500: {wins['B']}, "
          f"ties: {len(QUERIES) - wins['A'] - wins['B']}")
