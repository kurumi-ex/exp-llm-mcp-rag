import asyncio
import os

import numpy as np
import requests
import dotenv
from dataclasses import dataclass, field
from rich import print as rprint

from vector_store import VectorStore, VectorStoreItem

dotenv.load_dotenv()


@dataclass
class EmbeddingRetriever:
    embed_model: str = ""
    vector_store: VectorStore = field(default_factory=VectorStore)

    async def embed_query(self, query_text: str):
        return await self._get_vector(query_text)

    async def embed_document(self, document: str):
        doc_vec = await self._get_vector(document)
        self.vector_store.add_item(doc_vec, document)
        return doc_vec

    async def retrival(self, prompt: str, top_k: int = 3) -> str:
        vec = await self.embed_query(prompt)
        ans = self.vector_store.search_items(vec, top_k)
        ans_str = ""
        for item in ans:
            ans_str = f"{item.documents} " + "\n\n" + ans_str
        return ans_str

    async def _get_vector(self, text: str):
        url = os.getenv("EMBEDDING_BASE_URL")

        payload = {
            "model": self.embed_model,
            "input": text
        }
        headers = {
            "Authorization": "Bearer " + os.getenv("EMBEDDING_KEY"),
            "Content-Type": "application/json"
        }

        response = requests.request("POST", url, json=payload, headers=headers)

        return response.json()["data"][0]["embedding"]


async def main():
    tmp = EmbeddingRetriever(embed_model="BAAI/bge-large-zh-v1.5")
    await tmp.embed_document("hello world")
    await tmp.embed_document("I am god, god bless you")
    ans = await tmp.retrival("god")
    print(ans)


if __name__ == "__main__":
    asyncio.run(main())
