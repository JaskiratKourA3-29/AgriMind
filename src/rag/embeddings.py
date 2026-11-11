"""
Local Embedding Wrapper for AgriMind RAG Agent.
Uses sentence-transformers/all-MiniLM-L6-v2.
"""
from typing import List, Optional
import numpy as np
from langchain_core.embeddings import Embeddings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

class LocalMiniLMEmbeddings(Embeddings):
    """
    Wrapper for all-MiniLM-L6-v2 local sentence embeddings.
    Compatible with LangChain and direct ChromaDB embedding function interface.
    """
    def __init__(self, model_name: str = MODEL_NAME, device: Optional[str] = None):
        self.model_name = model_name
        self._model = None
        self._device = device

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading local embedding model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name, device=self._device)
            print("Embedding model loaded successfully.")
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of document chunks.
        """
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single search query.
        """
        embedding = self.model.encode([text], show_progress_bar=False, normalize_embeddings=True)[0]
        return embedding.tolist()

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        ChromaDB EmbeddingFunction protocol compliance.
        """
        return self.embed_documents(input)

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM
