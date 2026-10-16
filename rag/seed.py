import re
from pathlib import Path

import chromadb

POLICY_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"
PERSIST_DIR = Path(__file__).resolve().parent / ".chroma"
COLLECTION_NAME = "policies"


def chunk_markdown(path: Path) -> list[tuple[str, str]]:
    """Split a markdown policy doc into (heading, text) chunks by '##' sections."""
    text = path.read_text(encoding="utf-8")
    chunks: list[tuple[str, str]] = []
    for section in re.split(r"(?m)^##\s+", text):
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if not body:
            continue
        title = heading or path.stem
        chunks.append((title, f"{title}\n\n{body}"))
    return chunks


def seed(persist_dir: Path | None = None, force: bool = False) -> int:
    """Build the ChromaDB collection from data/policies/*.md. Returns chunk count."""
    persist_dir = persist_dir or PERSIST_DIR
    client = chromadb.PersistentClient(path=str(persist_dir))
    if force:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    collection = client.get_or_create_collection(COLLECTION_NAME)
    ids, docs, metadatas = [], [], []
    for path in sorted(POLICY_DIR.glob("*.md")):
        for index, (title, chunk) in enumerate(chunk_markdown(path)):
            ids.append(f"{path.stem}:{index}")
            docs.append(chunk)
            metadatas.append({"source": path.name, "heading": title})
    collection.upsert(ids=ids, documents=docs, metadatas=metadatas)
    return len(ids)


if __name__ == "__main__":
    count = seed(force=True)
    print(f"Seeded {count} chunks into {PERSIST_DIR}")
