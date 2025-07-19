from dataclasses import dataclass, field
import numpy as np


@dataclass
class VectorStoreItem:
    vec: list[int | float] = field(default_factory=list)
    documents: str = ""


@dataclass
class VectorStore:
    items: list[VectorStoreItem] = field(default_factory=list)

    def add_item(self, vec: list[int | float], documents: str):
        self.items.append(VectorStoreItem(vec, documents))

    def search_items(self, query: list[int | float], top_k: int = 3) -> list[VectorStoreItem]:
        query_vec = np.array(query, dtype=np.float32)
        scores = [self._get_cosine_similarity(np.array(item.vec, dtype=np.float32), query_vec) for item in self.items]
        # arr: [3,2,11]
        # sorted_idx:[1,0,2]
        sorted_idx = np.argsort(scores)
        return [self.items[idx] for idx in sorted_idx[-top_k:]]

    def _get_cosine_similarity(self, vec1, vec2):
        return np.dot(vec1, vec2) / np.sqrt(np.dot(vec1, vec1) * np.dot(vec2, vec2))
