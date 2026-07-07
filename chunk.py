"""Chunking for The Unofficial Guide — structure-aware, per planning.md.

Rules:
  * 1 Reddit comment = 1 chunk. Comments are independent utterances by
    different authors and are never merged across authors. The handful of
    comments longer than MAX_CHARS (12 in this corpus) are split like long
    prose — each piece still belongs to a single author.
  * Long continuous prose (submission selftexts, web-guide sections, oversized
    comments) is split on paragraph boundaries into pieces of at most
    MAX_CHARS, with the last OVERLAP characters of each piece repeated at the
    start of the next so a fact straddling a split survives in at least one
    piece.
  * Comments shorter than MIN_CHARS are dropped (mostly jokes/one-line
    agreement) unless they are top-level replies of at least MIN_TOP_LEVEL
    chars — a top-level "800 single 2 blocks" directly answers the rent
    thread's title and must be kept.
  * Every chunk is prefixed with its thread/guide title so referential
    comments ("avoid them at all costs") embed with their topic attached.

Input:   documents/processed/documents.jsonl   (from ingest.py)
Output:  documents/processed/chunks.jsonl

Usage:   python chunk.py                 # write chunks + print stats
         python chunk.py --sample 5     # also print N random chunks
"""

import argparse
import json
import random
import re
from pathlib import Path

IN_FILE = Path("documents/processed/documents.jsonl")
OUT_FILE = Path("documents/processed/chunks.jsonl")

MAX_CHARS = 900        # cap per chunk body (~225 tokens, fits MiniLM's window)
OVERLAP = 120          # carried between pieces when splitting long prose only
MIN_CHARS = 120        # drop shorter comments...
MIN_TOP_LEVEL = 15     # ...unless top-level and at least this long


def split_long(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Split prose on paragraph (then sentence) boundaries with overlap."""
    if len(text) <= max_chars:
        return [text]

    # Prefer paragraph boundaries; fall back to sentences for giant paragraphs.
    parts = []
    for para in text.split("\n\n"):
        if len(para) <= max_chars:
            parts.append(para)
        else:
            parts += re.split(r"(?<=[.!?])\s+", para)

    pieces, current = [], ""
    for part in parts:
        candidate = f"{current}\n\n{part}" if current else part
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            pieces.append(current)
            tail = current[-overlap:]
            tail = tail[tail.find(" ") + 1:]            # snap to a word boundary
            current = f"…{tail} {part}"
    if current:
        pieces.append(current)
    return pieces


def chunk_document(doc: dict) -> list[dict]:
    chunks = []
    for pos, unit in enumerate(doc["units"]):
        text = unit["text"]

        if unit["kind"] == "comment":
            if len(text) < MIN_CHARS and not (unit["top_level"] and len(text) >= MIN_TOP_LEVEL):
                continue
            pieces = split_long(text) if len(text) > MAX_CHARS else [text]
        else:                                           # selftext or guide section
            pieces = split_long(text)

        heading = unit.get("heading")
        prefix = f"[{doc['title']} — {heading}]" if heading else f"[{doc['title']}]"

        for i, piece in enumerate(pieces):
            chunks.append({
                "chunk_id": f"{doc['doc_id']}:{pos:03d}{f'.{i}' if len(pieces) > 1 else ''}",
                "text": f"{prefix} {piece}",
                "source": doc["doc_id"],
                "title": doc["title"],
                "source_type": doc["source_type"],
                "url": doc["url"],
                "year": doc["year"] or 0,
                "score": unit.get("score") if unit.get("score") is not None else 0,
                "kind": unit["kind"],
                "position": pos,
            })
    return chunks


def build_chunks() -> list[dict]:
    docs = [json.loads(line) for line in open(IN_FILE)]
    chunks = [c for doc in docs for c in chunk_document(doc)]
    with open(OUT_FILE, "w") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    return chunks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="print N random chunks")
    ap.add_argument("--seed", type=int, default=201, help="sampling seed")
    args = ap.parse_args()

    chunks = build_chunks()
    sizes = sorted(len(c["text"]) for c in chunks)
    by_doc = {}
    for c in chunks:
        by_doc[c["source"]] = by_doc.get(c["source"], 0) + 1

    print(f"{len(chunks)} chunks -> {OUT_FILE}")
    print(f"chars/chunk: min {sizes[0]}, median {sizes[len(sizes)//2]}, max {sizes[-1]}")
    for doc_id, n in sorted(by_doc.items()):
        print(f"  {doc_id:32s} {n:3d} chunks")

    if args.sample:
        print(f"\n--- {args.sample} random chunks (seed {args.seed}) ---")
        for c in random.Random(args.seed).sample(chunks, args.sample):
            print(f"\n[{c['chunk_id']}] source={c['source']} kind={c['kind']} "
                  f"year={c['year']} score={c['score']}")
            print(c["text"])
