"""Retrieval + grounded generation for The Unofficial Guide.

retrieve(query, k=5)  -> top-k chunks by cosine similarity, with metadata.
ask(question, k=5)    -> grounded answer from Groq llama-3.3-70b-versatile,
                         using ONLY the retrieved chunks as context, plus a
                         programmatically-built source list.

Grounding is enforced two ways:
  1. The system prompt allows answers only from the numbered sources in the
     context block and requires the exact refusal phrase when they don't
     contain the answer.
  2. Source attribution is NOT left to the model: the "sources" list returned
     by ask() is built in code from the retrieval metadata of the chunks that
     were actually in the context window.

Usage:   python query.py --retrieve-only "is BART viable?"   # retrieval only
         python query.py "when should I start looking for an apartment?"
"""

import argparse
import os
from functools import lru_cache
from pathlib import Path

import chromadb
import groq
import httpx
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

DB_DIR = "chroma_db"
COLLECTION = "unofficial_guide"
MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"          # Groq (course default)
HF_LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"   # same model, HF router
HF_ROUTER = "https://router.huggingface.co/v1/chat/completions"
TOP_K = 5

REFUSAL = "I don't have enough information on that in my documents."

SYSTEM_PROMPT = f"""\
You are The Unofficial Guide, answering questions about housing at UC Berkeley
using ONLY the numbered sources provided in the user message. The sources are
excerpts from real r/berkeley threads and student-written guides.

Hard rules:
1. Use only information stated in the sources. Never add facts from your
   general knowledge, even if you are confident they are true.
2. If the sources do not contain enough information to answer the question,
   reply with exactly: "{REFUSAL}" — do not attempt a partial guess from
   general knowledge.
3. Cite every claim with its source number in brackets, e.g. [Source 2].
4. These are student opinions, not verified facts: attribute them ("one
   commenter reports…", "the top comment says…") and mention the year when
   the sources span different years or the info could be dated (e.g. prices).
5. If sources disagree, present both sides with their citations.
Keep answers to a few sentences or a short list — direct and concrete."""


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def _collection():
    return chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION)


def _hf_token() -> str:
    token_file = Path.home() / ".cache/huggingface/token"
    return os.environ.get("HF_TOKEN") or (
        token_file.read_text().strip() if token_file.exists() else ""
    )


def _chat(messages: list[dict]) -> str:
    """Call the LLM. Default: Groq llama-3.3-70b-versatile (course setup).

    Fallback: the identical model (Llama-3.3-70B-Instruct) via Hugging Face's
    OpenAI-compatible Inference Providers router — added because the network
    this project was built on blocks api.groq.com at the IP level. With a
    GROQ_API_KEY in .env, the Groq path is used and the fallback never runs.
    """
    load_dotenv()
    key = os.environ.get("GROQ_API_KEY", "")
    if key and key != "your_key_here":
        try:
            response = Groq(api_key=key).chat.completions.create(
                model=LLM_MODEL, temperature=0.2, max_tokens=600, messages=messages
            )
            return response.choices[0].message.content.strip()
        except groq.PermissionDeniedError as err:
            # 403 "check your network settings" = Groq blocks this IP (VPN);
            # not a key problem. Fall through to the HF router if possible.
            if not _hf_token():
                raise
            print(f"[query] Groq unreachable from this network ({err.status_code}); "
                  f"falling back to HF router with {HF_LLM_MODEL}", flush=True)

    if token := _hf_token():
        response = httpx.post(
            HF_ROUTER,
            headers={"Authorization": f"Bearer {token}"},
            json={"model": HF_LLM_MODEL, "temperature": 0.2,
                  "max_tokens": 600, "messages": messages},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    raise RuntimeError(
        "No LLM credentials. Copy .env.example to .env and add a free Groq "
        "key from https://console.groq.com (or set HF_TOKEN)."
    )


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k chunks for a query: [{text, distance, ...metadata}]."""
    embedding = _model().encode([query], normalize_embeddings=True)
    result = _collection().query(
        query_embeddings=embedding.tolist(),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"chunk_id": cid, "text": doc, "distance": round(dist, 3), **meta}
        for cid, doc, dist, meta in zip(
            result["ids"][0], result["documents"][0],
            result["distances"][0], result["metadatas"][0]
        )
    ]


def _context_block(hits: list[dict]) -> str:
    lines = []
    for i, hit in enumerate(hits, 1):
        kind = "r/berkeley thread" if hit["source_type"] == "reddit_thread" else "student guide"
        lines.append(f'[Source {i}] ({kind} "{hit["title"]}", {hit["year"]})\n{hit["text"]}')
    return "\n\n".join(lines)


def ask(question: str, k: int = TOP_K, mode: str = "semantic") -> dict:
    """Answer a question grounded in retrieved chunks.

    mode: "semantic" (default) or "hybrid" (BM25 + semantic RRF — Stretch A).
    Returns {"answer": str, "sources": [str], "hits": [chunk dicts]}.
    """
    if mode == "hybrid":
        from hybrid import retrieve_hybrid          # lazy: rank-bm25 optional
        hits = retrieve_hybrid(question, k)
    else:
        hits = retrieve(question, k)
    answer = _chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Sources:\n\n{_context_block(hits)}\n\n"
                                    f"Question: {question}"},
    ])

    # Attribution is guaranteed in code: list every source that was in the
    # context, numbered exactly as the model saw it, regardless of what the
    # model chose to cite.
    sources = [
        f'[Source {i}] {hit["source"]} — "{hit["title"]}" ({hit["year"]}) {hit["url"]}'
        for i, hit in enumerate(hits, 1)
    ]
    return {"answer": answer, "sources": sources, "hits": hits}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=TOP_K)
    ap.add_argument("--retrieve-only", action="store_true",
                    help="show retrieved chunks without calling the LLM")
    ap.add_argument("--mode", choices=["semantic", "hybrid"], default="semantic",
                    help="retrieval mode (hybrid = BM25 + semantic, Stretch A)")
    args = ap.parse_args()

    if args.retrieve_only:
        for i, hit in enumerate(retrieve(args.query, args.k), 1):
            print(f"\n#{i}  distance={hit['distance']}  source={hit['source']} "
                  f"({hit['kind']}, {hit['year']})")
            print(hit["text"])
    else:
        result = ask(args.query, args.k, mode=args.mode)
        print(result["answer"])
        print("\nRetrieved from:")
        for s in result["sources"]:
            print(f"  • {s}")
