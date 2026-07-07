"""Evaluation runner: the 5 test questions from planning.md, end to end.

Runs each question through ask(), and records the full trace (answer, source
list, retrieved chunk ids + distances) to documents/processed/eval_results.json
so the README evaluation report is reproducible. Accuracy judgments are made
by hand against the expected answers in planning.md — not by the model.

Usage:   python evaluate.py
"""

import json
from pathlib import Path

from query import ask

OUT = Path("documents/processed/eval_results.json")

QUESTIONS = [
    ("How much does a one-way BART ride from Oakland to Berkeley cost, "
     "and which transit is free for Cal students?"),
    "Which other company names do students say Raj Properties operates under?",
    ("What do students warn will happen if you decline your UC Berkeley "
     "on-campus housing offer?"),
    "How do students compare Blackwell Hall and Unit 3 as freshman dorms?",
    ("What does a room in a shared apartment near campus typically cost, "
     "according to students?"),
]

if __name__ == "__main__":
    results = []
    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n{'=' * 70}\nQ{i}: {question}\n")
        result = ask(question)
        print(result["answer"])
        print("\nRetrieved:")
        for hit in result["hits"]:
            print(f"  {hit['distance']:.3f}  {hit['source']}:{hit['position']:03d} "
                  f"({hit['kind']}, {hit['year']})")
        results.append({
            "n": i,
            "question": question,
            "answer": result["answer"],
            "sources": result["sources"],
            "retrieved": [
                {"chunk": f"{h['source']}:{h['position']:03d}", "kind": h["kind"],
                 "year": h["year"], "distance": h["distance"],
                 "text": h["text"]}
                for h in result["hits"]
            ],
        })

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote full traces -> {OUT}")
