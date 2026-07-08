"""Gradio web UI for The Unofficial Guide.

Run:   python app.py       then open http://localhost:7860

Input:  a plain-language question about UC Berkeley housing.
Output: a grounded answer with [Source N] citations, the source list
        (document, thread title, year, URL), and a collapsible view of the
        raw retrieved chunks with their distances.
"""

import gradio as gr

from query import ask

EXAMPLES = [
    "When should I start looking for an apartment for the fall?",
    "Which property management companies do students warn about?",
    "Is living in a co-op worth it?",
    "How much does a room in a shared apartment cost?",
    "Is BART a viable commute option from Oakland?",
]


def handle_query(question, mode):
    if not question.strip():
        return "Ask a question first.", "", ""
    result = ask(question, mode=mode)
    sources = "\n".join(f"• {s}" for s in result["sources"])
    chunks = "\n\n".join(
        f"#{i} ({h['source']}, {h['year']}, "
        + (f"ranks {h['ranks']}" if "ranks" in h else f"distance {h['distance']}")
        + f")\n{h['text']}"
        for i, h in enumerate(result["hits"], 1)
    )
    return result["answer"], sources, chunks


with gr.Blocks(title="The Unofficial Guide — UC Berkeley Housing") as demo:
    gr.Markdown(
        "# 🐻 The Unofficial Guide: UC Berkeley Housing\n"
        "Answers come **only** from 12 r/berkeley threads (2019–2025) and 2 "
        "student guides — real student experiences, cited. Not official advice."
    )
    inp = gr.Textbox(label="Your question",
                     placeholder="e.g. What happens if I decline my housing offer?")
    mode = gr.Radio(["semantic", "hybrid"], value="semantic",
                    label="Retrieval mode",
                    info="hybrid = BM25 keyword + semantic, fused by "
                         "reciprocal rank (Stretch A)")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)
    with gr.Accordion("Retrieved chunks (what the model actually saw)", open=False):
        chunks = gr.Textbox(label="Top-5 chunks with distances", lines=14)
    gr.Examples(EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=[inp, mode], outputs=[answer, sources, chunks])
    inp.submit(handle_query, inputs=[inp, mode], outputs=[answer, sources, chunks])

if __name__ == "__main__":
    demo.launch()
