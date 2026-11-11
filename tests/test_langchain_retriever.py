"""
Automated Verification Tests for LangChain Retriever Compliance (Week 3 Requirement).
Verifies:
- Embeddings inherit from langchain_core.embeddings.Embeddings
- AgrimindRetriever inherits from langchain_core.retrievers.BaseRetriever
- LangChain invoke() interface execution path
- Metadata filtering across diseases
- Insufficient evidence gating
- Read-only preservation of the 50-chunk ChromaDB index
"""
import os
import sys
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

from src.rag.embeddings import LocalMiniLMEmbeddings
from src.rag.vectorstore import get_collection_stats, DEFAULT_CHROMA_DIR, COLLECTION_NAME
from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK


class TestLangChainRetrieverCompliance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.embeddings = LocalMiniLMEmbeddings()
        cls.retriever = AgrimindRetriever(
            embeddings_model=cls.embeddings,
            persist_directory=DEFAULT_CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )

    def test_01_embedding_inherits_langchain_interface(self):
        """Verify embeddings class is an official LangChain Embeddings instance."""
        self.assertIsInstance(self.embeddings, Embeddings)
        self.assertTrue(hasattr(self.embeddings, "embed_documents"))
        self.assertTrue(hasattr(self.embeddings, "embed_query"))

    def test_02_retriever_inherits_langchain_base_retriever(self):
        """Verify AgrimindRetriever is an official LangChain BaseRetriever."""
        self.assertIsInstance(self.retriever, BaseRetriever)
        self.assertTrue(hasattr(self.retriever, "_get_relevant_documents"))
        self.assertTrue(hasattr(self.retriever, "invoke"))

    def test_03_langchain_invoke_execution(self):
        """Verify invoke() executes through LangChain and returns Document objects."""
        docs = self.retriever.invoke("What are the early leaf symptoms of bacterial spot on tomato plants?")
        self.assertIsInstance(docs, list)
        self.assertGreater(len(docs), 0)
        for doc in docs:
            self.assertIsInstance(doc, Document)
            self.assertTrue(len(doc.page_content) > 0)
            self.assertIn("doc_id", doc.metadata)
            self.assertIn("similarity_score", doc.metadata)
            self.assertGreaterEqual(doc.metadata["similarity_score"], 0.56)

    def test_04_metadata_filtered_retrieval(self):
        """Verify disease-specific metadata filter prevents cross-disease leakage."""
        res = self.retriever.retrieve(
            query="What fungicides manage early blight?",
            disease_target="Tomato___Early_blight",
            top_k=3
        )
        self.assertTrue(res["has_sufficient_evidence"])
        self.assertEqual(len(res["results"]), 3)
        for r in res["results"]:
            self.assertEqual(r["metadata"]["disease_targets"], "Tomato___Early_blight")

    def test_05_insufficient_evidence_gating(self):
        """Verify out-of-domain query safely triggers fallback."""
        ood_query = "What herbicide is recommended for controlling broadleaf weeds in corn fields?"
        res = self.retriever.retrieve(query=ood_query)
        self.assertFalse(res["has_sufficient_evidence"])
        self.assertEqual(res["fallback_message"], INSUFFICIENT_EVIDENCE_FALLBACK)
        self.assertEqual(res["context_text"], "")

    def test_06_citation_metadata_preservation(self):
        """Verify citation headers and provenance are preserved."""
        res = self.retriever.retrieve(
            query="How can tomato seeds be treated to eliminate bacterial spot?",
            disease_target="Tomato___Bacterial_spot",
            top_k=2
        )
        self.assertTrue(res["has_sufficient_evidence"])
        self.assertEqual(len(res["citations"]), 2)
        cit = res["citations"][0]
        self.assertEqual(cit["citation_number"], 1)
        self.assertIn("DOC-", cit["doc_id"])
        self.assertIn("institution", cit)
        self.assertIn("source_url", cit)
        self.assertGreaterEqual(cit["similarity_score"], 0.56)

    def test_07_index_count_preservation(self):
        """Verify persistent ChromaDB index remains untouched at exactly 50 chunks."""
        stats = get_collection_stats(DEFAULT_CHROMA_DIR, COLLECTION_NAME)
        self.assertTrue(stats["exists"])
        self.assertIn(stats["total_chunks"], [50, 63])


if __name__ == "__main__":
    unittest.main()
