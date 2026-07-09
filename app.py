"""Gradio web UI for The Unofficial Guide.

Run:   python app.py       then open http://localhost:7860

Input:  a plain-language question about UC Berkeley housing, with optional
        retrieval-mode (Stretch A) and metadata-filter (Stretch C) controls.
        The chat remembers previous turns (Stretch D): follow-ups like
        "how much does it cost?" are rewritten into standalone questions
        before retrieval.
Output: a chat transcript of grounded answers with [Source N] citations,
        the source list for the latest turn, and a collapsible view of the
        raw retrieved chunks. When a follow-up was rewritten, the standalone
        search query is shown under the answer.
"""

import gradio as gr

from query import ask

EXAMPLES = [
    "When should I start looking for an apartment for the fall?",
    "Which property management companies do students warn about?",
    "Is living in a co-op worth it?",
    "Is BART a viable commute option from Oakland?",
    "How much does it cost?",   # follow-up: works after the BART question
]

SOURCE_MAP = {"Reddit threads": "reddit_thread", "Student guides": "web_guide"}


def respond(question, pairs, mode, source_filter, year_filter):
    """One chat turn. `pairs` is the raw (user, assistant) history state."""
    question = question.strip()
    if not question:
        return "", pairs, _render(pairs), "", ""

    result = ask(
        question, mode=mode,
        source_type=SOURCE_MAP.get(source_filter),
        min_year=None if year_filter == "any" else int(year_filter),
        history=[(q, a) for q, a, _ in pairs] or None,
    )
    pairs = pairs + [(question, result["answer"], result["search_query"])]

    sources = "\n".join(f"• {s}" for s in result["sources"])
    chunks = "\n\n".join(
        f"#{i} ({h['source']}, {h['year']}, "
        + (f"ranks {h['ranks']}" if "ranks" in h else f"distance {h['distance']}")
        + f")\n{h['text']}"
        for i, h in enumerate(result["hits"], 1)
    )
    return "", pairs, _render(pairs), sources, chunks


def _render(pairs):
    """History tuples -> Chatbot messages, showing rewritten search queries."""
    messages = []
    for user_turn, answer, search_query in pairs:
        messages.append({"role": "user", "content": user_turn})
        note = (f"\n\n*(searched as: “{search_query}”)*"
                if search_query != user_turn else "")
        messages.append({"role": "assistant", "content": answer + note})
    return messages


def clear():
    return [], [], "", ""


with gr.Blocks(title="The Unofficial Guide — UC Berkeley Housing") as demo:
    gr.Markdown(
        "# 🐻 The Unofficial Guide: UC Berkeley Housing\n"
        "Answers come **only** from 12 r/berkeley threads (2019–2025) and 2 "
        "student guides — real student experiences, cited. Not official advice. "
        "Follow-up questions work: the chat remembers context."
    )
    chat = gr.Chatbot(label="Conversation", height=380)
    inp = gr.Textbox(label="Your question",
                     placeholder="e.g. What happens if I decline my housing offer?")
    with gr.Row():
        mode = gr.Radio(["semantic", "hybrid"], value="semantic",
                        label="Retrieval mode",
                        info="hybrid = BM25 keyword + semantic, fused by "
                             "reciprocal rank")
        source_filter = gr.Dropdown(
            ["All sources", "Reddit threads", "Student guides"],
            value="All sources", label="Source filter")
        year_filter = gr.Dropdown(
            ["any", "2022", "2023", "2024", "2025"], value="any",
            label="From year",
            info="only documents from this year or newer")
    with gr.Row():
        btn = gr.Button("Ask", variant="primary")
        reset = gr.Button("New conversation")
    sources = gr.Textbox(label="Retrieved from (latest turn)", lines=6, max_lines=10)
    with gr.Accordion("Retrieved chunks (what the model actually saw)", open=False):
        chunks = gr.Textbox(label="Top-5 chunks", lines=18, max_lines=18)
    gr.Examples(EXAMPLES, inputs=inp)

    pairs = gr.State([])
    turn = dict(fn=respond, inputs=[inp, pairs, mode, source_filter, year_filter],
                outputs=[inp, pairs, chat, sources, chunks])
    btn.click(**turn)
    inp.submit(**turn)
    reset.click(clear, outputs=[pairs, chat, sources, chunks])

if __name__ == "__main__":
    demo.launch()
