"""Document ingestion for The Unofficial Guide.

Loads the raw corpus (12 r/berkeley threads saved from the PullPush archive
API + 2 Berkeley Life HTML guides), cleans it, and writes structured document
records ready for chunking.

Input:   documents/raw/reddit_*.json, documents/raw/web_*.html
Output:  documents/processed/documents.jsonl   (one document per line)
         documents/processed/<doc_id>.txt      (human-readable, for inspection)

Cleaning rules (from planning.md / documents/SOURCES.md skim notes):
  * dedupe Reddit comments by id — the archive returns live/deleted duplicate
    records for the same comment in 3 files; keep the copy with a real author
  * drop [deleted]/[removed]/empty comment bodies
  * unescape HTML entities, strip zero-width chars and markdown link syntax
  * web guides: keep only the article body (entry-content), split into
    sections by heading; drop nav/related-posts/boilerplate

Usage:  python ingest.py            # writes documents/processed/
        python ingest.py --show reddit_landlords   # print one cleaned doc
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

RAW_DIR = Path("documents/raw")
OUT_DIR = Path("documents/processed")


# ---------------------------------------------------------------- text cleanup

def clean_text(text: str) -> str:
    """Normalize one block of Reddit/web text without rewriting its content."""
    text = html.unescape(html.unescape(text))          # &amp;#x200B; needs two passes
    text = re.sub(r"[​‌⁠﻿]", "", text)   # zero-width chars
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)   # image/gif embeds -> gone
    text = re.sub(r"\[([^\]]+)\]\([^)\s]+\)", r"\1", text)   # [label](url) -> label
    text = re.sub(r"&#x?[0-9a-fA-F]+;", " ", text)     # any entity the unescape missed
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------- reddit files

def load_reddit(path: Path) -> dict:
    raw = json.loads(path.read_text())
    sub = raw["submission"]
    year = datetime.fromtimestamp(int(sub["created_utc"]), tz=timezone.utc).year

    # Dedupe by comment id: the archive stores live/deleted pairs. Prefer the
    # record with a real author, then the longer body.
    by_id = {}
    for c in raw["comments"]:
        cid = c["id"]
        best = by_id.get(cid)
        if best is None:
            by_id[cid] = c
            continue
        c_live = c.get("author") not in (None, "[deleted]")
        best_live = best.get("author") not in (None, "[deleted]")
        if (c_live, len(c.get("body") or "")) > (best_live, len(best.get("body") or "")):
            by_id[cid] = c

    units = []
    selftext = clean_text(sub.get("selftext") or "")
    if selftext:
        units.append({"kind": "selftext", "text": selftext,
                      "score": sub.get("score"), "top_level": True})

    for c in sorted(by_id.values(), key=lambda c: c.get("score") or 0, reverse=True):
        body = c.get("body") or ""
        if body in ("[deleted]", "[removed]"):
            continue
        body = clean_text(body)
        if not body or re.fullmatch(r"https?://\S+", body):
            continue                                  # empty or bare-URL comments
        units.append({
            "kind": "comment",
            "text": body,
            "score": c.get("score"),
            "top_level": str(c.get("parent_id") or "").startswith("t3_"),
        })

    return {
        "doc_id": path.stem,                      # e.g. reddit_landlords
        "title": clean_text(sub["title"]),
        "source_type": "reddit_thread",
        "source_file": str(path),
        "url": "https://www.reddit.com" + sub.get("permalink", ""),
        "year": year,
        "units": units,
    }


# ------------------------------------------------------------------- web files

class ArticleExtractor(HTMLParser):
    """Pull heading/paragraph/list text out of the entry-content div."""

    BLOCK_TAGS = {"h2", "h3", "p", "li"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_article = False
        self.div_depth = 0
        self.current_tag = None
        self.buffer = []
        self.blocks = []                          # (tag, text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            if self.in_article:
                self.div_depth += 1
            elif "entry-content" in (attrs.get("class") or ""):
                self.in_article = True
                self.div_depth = 1
        elif self.in_article and tag in self.BLOCK_TAGS:
            if "wp-caption-text" in (attrs.get("class") or ""):
                return                                # image captions: skip
            self.current_tag = tag
            self.buffer = []

    def handle_endtag(self, tag):
        if tag == "div" and self.in_article:
            self.div_depth -= 1
            if self.div_depth == 0:
                self.in_article = False
        elif self.in_article and tag == self.current_tag:
            text = clean_text("".join(self.buffer))
            if text:
                self.blocks.append((self.current_tag, text))
            self.current_tag = None

    def handle_data(self, data):
        if self.in_article and self.current_tag:
            self.buffer.append(data)


def load_web(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    title = re.search(r"<title>(.*?)</title>", raw, re.S)
    title = clean_text(title.group(1)).removesuffix(" - Life") if title else path.stem
    canonical = re.search(r'rel="canonical" href="([^"]+)"', raw)
    published = re.search(r'article:published_time" content="(\d{4})', raw)

    parser = ArticleExtractor()
    parser.feed(raw)

    # Group paragraph/list blocks under the heading that precedes them.
    units, heading, paragraphs = [], "Introduction", []
    def flush():
        if paragraphs:
            units.append({"kind": "section", "heading": heading,
                          "text": "\n\n".join(paragraphs), "top_level": True})
    for tag, text in parser.blocks:
        if text.lower().startswith(("want more", "happy hunting")):
            break                                     # cross-promo outro: stop here
        if tag in ("h2", "h3"):
            flush()
            heading, paragraphs = text, []
        else:
            paragraphs.append(text)
    flush()

    return {
        "doc_id": path.stem,                      # e.g. web_offcampus_search_tips
        "title": title,
        "source_type": "web_guide",
        "source_file": str(path),
        "url": canonical.group(1) if canonical else "",
        "year": int(published.group(1)) if published else None,
        "units": units,
    }


# ------------------------------------------------------------------------ main

def load_documents() -> list[dict]:
    docs = [load_reddit(p) for p in sorted(RAW_DIR.glob("reddit_*.json"))]
    docs += [load_web(p) for p in sorted(RAW_DIR.glob("web_*.html"))]
    return docs


def write_outputs(docs: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "documents.jsonl", "w") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    for doc in docs:                              # readable copies for inspection
        lines = [f"# {doc['title']}  ({doc['source_type']}, {doc['year']})",
                 f"# {doc['url']}", ""]
        for u in doc["units"]:
            label = u["kind"] + (f" · {u['heading']}" if u.get("heading") else "")
            score = f" · score {u['score']}" if u.get("score") is not None else ""
            lines += [f"--- [{label}{score}]", u["text"], ""]
        (OUT_DIR / f"{doc['doc_id']}.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="print one cleaned document (doc_id) and exit")
    args = ap.parse_args()

    documents = load_documents()
    write_outputs(documents)

    if args.show:
        match = [d for d in documents if d["doc_id"] == args.show]
        if not match:
            sys.exit(f"unknown doc_id {args.show!r}")
        print((OUT_DIR / f"{args.show}.txt").read_text())
    else:
        total_units = sum(len(d["units"]) for d in documents)
        print(f"Ingested {len(documents)} documents, {total_units} units "
              f"-> {OUT_DIR}/documents.jsonl")
        for d in documents:
            print(f"  {d['doc_id']:32s} {d['year']}  {len(d['units']):3d} units  {d['title'][:60]}")
