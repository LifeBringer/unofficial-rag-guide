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


def _where(source_type: str | None, min_year: int | None) -> dict | None:
    """Build a ChromaDB metadata filter (Stretch C)."""
    clauses = []
    if source_type:
        clauses.append({"source_type": source_type})
    if min_year:
        clauses.append({"year": {"$gte": min_year}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def retrieve(query: str, k: int = TOP_K, source_type: str | None = None,
             min_year: int | None = None) -> list[dict]:
    """Return the top-k chunks for a query: [{text, distance, ...metadata}].

    source_type ("reddit_thread"/"web_guide") and min_year filter by chunk
    metadata before ranking (Stretch C).
    """
    embedding = _model().encode([query], normalize_embeddings=True)
    result = _collection().query(
        query_embeddings=embedding.tolist(),
        n_results=k,
        where=_where(source_type, min_year),
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


def _rewrite_query(question: str, history: list[tuple[str, str]]) -> str:
    """Rewrite a follow-up into a standalone question (Stretch D).

    Retrieval can't resolve pronouns — "what other names do THEY use?" has no
    semantic signal — so the conversation history is used to produce a
    self-contained query before embedding it.
    """
    transcript = "\n".join(f"User: {q}\nAssistant: {a}" for q, a in history)
    rewritten = _chat([
        {"role": "system", "content":
            "Rewrite the user's follow-up question as a single standalone "
            "question that makes sense with no conversation context, replacing "
            "pronouns and references with what they refer to. Keep it short. "
            "Output ONLY the rewritten question."},
        {"role": "user", "content": f"Conversation so far:\n{transcript}\n\n"
                                    f"Follow-up question: {question}"},
    ])
    return rewritten.strip().strip('"')


def ask(question: str, k: int = TOP_K, mode: str = "semantic",
        source_type: str | None = None, min_year: int | None = None,
        history: list[tuple[str, str]] | None = None) -> dict:
    """Answer a question grounded in retrieved chunks.

    mode: "semantic" (default) or "hybrid" (BM25 + semantic RRF — Stretch A).
    source_type / min_year: metadata filters (Stretch C).
    history: prior (user, assistant) turns; enables follow-up questions via
        query rewriting + history-aware generation (Stretch D).
    Returns {"answer", "sources", "hits", "search_query"}.
    """
    search_query = _rewrite_query(question, history) if history else question

    if mode == "hybrid":
        from hybrid import retrieve_hybrid          # lazy: rank-bm25 optional
        hits = retrieve_hybrid(search_query, k, source_type=source_type,
                               min_year=min_year)
    else:
        hits = retrieve(search_query, k, source_type=source_type,
                        min_year=min_year)
    if not hits:
        return {"answer": "No documents match those filters.", "sources": [],
                "hits": [], "search_query": search_query}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_turn, assistant_turn in history or []:
        messages.append({"role": "user", "content": user_turn})
        messages.append({"role": "assistant", "content": assistant_turn})
    messages.append({"role": "user",
                     "content": f"Sources:\n\n{_context_block(hits)}\n\n"
                                f"Question: {question}"})
    answer = _chat(messages)

    # Attribution is guaranteed in code: list every source that was in the
    # context, numbered exactly as the model saw it, regardless of what the
    # model chose to cite.
    sources = [
        f'[Source {i}] {hit["source"]} — "{hit["title"]}" ({hit["year"]}) {hit["url"]}'
        for i, hit in enumerate(hits, 1)
    ]
    return {"answer": answer, "sources": sources, "hits": hits,
            "search_query": search_query}


def chat_repl(mode: str) -> None:
    """Interactive multi-turn session (Stretch D). Ctrl-D or 'quit' to exit."""
    history: list[tuple[str, str]] = []
    print("Multi-turn chat — follow-ups like 'what about X?' work. "
          "'quit' to exit.")
    while True:
        try:
            question = input("\nyou> ").strip()
        except EOFError:
            break
        if question.lower() in ("quit", "exit", ""):
            break
        result = ask(question, mode=mode, history=history)
        if result["search_query"] != question:
            print(f"    (searched as: {result['search_query']})")
        print(f"\n{result['answer']}")
        for s in result["sources"]:
            print(f"  • {s}")
        history.append((question, result["answer"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default=None)
    ap.add_argument("--k", type=int, default=TOP_K)
    ap.add_argument("--retrieve-only", action="store_true",
                    help="show retrieved chunks without calling the LLM")
    ap.add_argument("--mode", choices=["semantic", "hybrid"], default="semantic",
                    help="retrieval mode (hybrid = BM25 + semantic, Stretch A)")
    ap.add_argument("--source-type", choices=["reddit_thread", "web_guide"],
                    help="only retrieve from this source type (Stretch C)")
    ap.add_argument("--min-year", type=int,
                    help="only retrieve from documents this year or newer (Stretch C)")
    ap.add_argument("--chat", action="store_true",
                    help="interactive multi-turn session (Stretch D)")
    args = ap.parse_args()

    if args.chat:
        chat_repl(args.mode)
        raise SystemExit
    if args.query is None:
        ap.error("provide a query, or use --chat")

    if args.retrieve_only:
        for i, hit in enumerate(retrieve(args.query, args.k, args.source_type,
                                         args.min_year), 1):
            print(f"\n#{i}  distance={hit['distance']}  source={hit['source']} "
                  f"({hit['kind']}, {hit['year']})")
            print(hit["text"])
    else:
        result = ask(args.query, args.k, mode=args.mode,
                     source_type=args.source_type, min_year=args.min_year)
        print(result["answer"])
        print("\nRetrieved from:")
        for s in result["sources"]:
            print(f"  • {s}")
