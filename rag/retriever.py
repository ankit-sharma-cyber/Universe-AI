from dataclasses import dataclass
from pathlib import Path

import chromadb

from rag.seed import COLLECTION_NAME, PERSIST_DIR


@dataclass
class ChunkResult:
    text: str
    source: str
    heading: str
    distance: float


class Retriever:
    """Semantic retrieval over the seeded policy collection."""

    def __init__(
        self,
        persist_dir: Path | None = None,
        collection_name: str = COLLECTION_NAME,
        k: int = 3,
    ) -> None:
        self.client = chromadb.PersistentClient(path=str(persist_dir or PERSIST_DIR))
        self.collection_name = collection_name
        self.collection = None
        self.k = k

    def _get_collection(self):
        if self.collection is None:
            self.collection = self.client.get_collection(self.collection_name)
        return self.collection

    @property
    def available(self) -> bool:
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False

    def search(self, query: str, k: int | None = None) -> list[ChunkResult]:
        collection = self._get_collection()
        result = collection.query(
            query_texts=[query],
            n_results=k or self.k,
            include=["documents", "metadatas", "distances"],
        )
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        distances = result["distances"][0]
        return [
            ChunkResult(
                text=doc,
                source=meta["source"],
                heading=meta["heading"],
                distance=distance,
            )
            for doc, meta, distance in zip(docs, metas, distances)
        ]
