from llm.client import complete
from rag.retriever import Retriever

NAME = "knowledge"


def run(request: str, student_id: str, **ctx) -> dict:
    try:
        retriever = Retriever()
        if not retriever.available:
            return {
                "output": None,
                "error": "Knowledge base is not seeded. Run `python -m rag.seed` first.",
                "confidence": 0.3,
                "trace": "RAG store unavailable",
            }
        chunks = retriever.search(request, k=3)
        output = [
            {
                "source": c.source,
                "heading": c.heading,
                "text": c.text,
                "distance": round(c.distance, 3),
            }
            for c in chunks
        ]
        summary = _summarize(request, output)
        if summary:
            for item in output:
                item["summary"] = summary
            # attach once at top-level via first chunk to keep schema simple for merge
            output = [{"summary": summary, **output[0]}, *output[1:]] if output else output

        return {
            "output": output,
            "error": None,
            "confidence": 0.95 if output else 0.5,
            "trace": f"Retrieved {len(output)} relevant policy chunks from the knowledge base"
                     + (" (LLM summarized)." if summary else "."),
        }
    except Exception as exc:
        return {"output": None, "error": f"RAG retrieval failed: {exc}", "confidence": 0.3, "trace": "RAG retrieval failed"}


def _summarize(request: str, chunks: list[dict]) -> str | None:
    if not chunks:
        return None
    evidence = "\n\n".join(
        f"[{c['source']} / {c['heading']}]\n{c['text'][:600]}" for c in chunks
    )
    return complete(
        f"Student question: {request}\n\nPolicy excerpts:\n{evidence}\n\n"
        "Write a concise 3-5 bullet summary answering the student. Use only the excerpts.",
        system="You summarize campus policy documents for students. Be precise and cite headings.",
        max_tokens=350,
    )
