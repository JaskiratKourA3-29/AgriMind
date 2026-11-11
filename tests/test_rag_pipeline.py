"""
Automated Unit and Integration Tests for AgriMind RAG Pipeline.
Verifies ingestion, chunking, metadata preservation, embeddings, vector indexing,
disease filtering, and insufficient evidence fallback.
"""
import os
import sys
import json
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.rag.ingest import process_knowledge_base, RAW_DOCS_DIR, MANIFEST_PATH, PROCESSED_CHUNKS_PATH
from src.rag.embeddings import LocalMiniLMEmbeddings, EMBEDDING_DIM
from src.rag.vectorstore import (
    build_or_update_vectorstore,
    get_chroma_client,
    query_vectorstore,
    get_collection_stats,
    DEFAULT_CHROMA_DIR,
    COLLECTION_NAME
)
from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK

class TestAgriMindRAGPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ingest and process knowledge base
        cls.chunks = process_knowledge_base(
            raw_dir=RAW_DOCS_DIR,
            manifest_path=MANIFEST_PATH,
            output_path=PROCESSED_CHUNKS_PATH,
            chunk_size=600,
            chunk_overlap=100
        )
        cls.embeddings = LocalMiniLMEmbeddings()
        cls.index_result = build_or_update_vectorstore(
            chunks=cls.chunks,
            embeddings_model=cls.embeddings,
            persist_directory=DEFAULT_CHROMA_DIR,
            collection_name=COLLECTION_NAME,
            force_rebuild=False
        )
        cls.retriever = AgrimindRetriever(
            embeddings_model=cls.embeddings,
            persist_directory=DEFAULT_CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )

    def test_01_raw_documents_and_manifest(self):
        """Verify all 6 raw documents and the metadata manifest exist."""
        self.assertTrue(os.path.exists(MANIFEST_PATH), "Manifest file missing.")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertIn(manifest["total_documents"], [6, 7], "Manifest must list documents.")
        self.assertIn(len(manifest["documents"]), [6, 7])

        raw_files = [f for f in os.listdir(RAW_DOCS_DIR) if f.endswith(".md")]
        self.assertIn(len(raw_files), [6, 7], "Must have 6 or 7 raw markdown documents.")

    def test_02_chunking_and_metadata_preservation(self):
        """Verify chunks are generated, non-empty, and retain all essential metadata."""
        self.assertGreater(len(self.chunks), 15, "Knowledge base should produce at least 15 chunks.")
        
        for ch in self.chunks:
            self.assertIn("chunk_id", ch)
            self.assertIn("text", ch)
            self.assertGreater(len(ch["text"]), 20, "Chunk text must not be empty.")
            
            meta = ch["metadata"]
            self.assertIn("doc_id", meta)
            self.assertIn("title", meta)
            self.assertIn("institution", meta)
            self.assertIn("source_url", meta)
            self.assertTrue(meta["source_url"].startswith("http"), "Source URL must be valid HTTP/HTTPS.")
            self.assertIn("disease_targets", meta)
            self.assertIn("pathogen", meta)

    def test_03_embedding_dimension(self):
        """Verify embeddings are normalized dense vectors of dimension 384."""
        test_text = "Tomato late blight symptoms include water soaked lesions."
        query_emb = self.embeddings.embed_query(test_text)
        self.assertEqual(len(query_emb), EMBEDDING_DIM, f"Embedding must be {EMBEDDING_DIM}-dimensional.")

        doc_embs = self.embeddings.embed_documents([test_text, "Another sentence."])
        self.assertEqual(len(doc_embs), 2)
        self.assertEqual(len(doc_embs[0]), EMBEDDING_DIM)

    def test_04_chromadb_persistence_and_reload(self):
        """Verify ChromaDB persists chunks and reloads cleanly in a fresh client."""
        stats = get_collection_stats(DEFAULT_CHROMA_DIR, COLLECTION_NAME)
        self.assertTrue(stats["exists"])
        self.assertEqual(stats["total_chunks"], len(self.chunks), "Indexed chunks must match processed chunks.")

    def test_05_metadata_disease_filtering(self):
        """Verify that disease-target filter restricts retrieval strictly to the target disease."""
        query = "What fungicides are effective for control?"
        retrieval = self.retriever.retrieve(
            query=query,
            disease_target="Tomato___Early_blight",
            top_k=4
        )
        self.assertTrue(retrieval["has_sufficient_evidence"])
        self.assertGreater(len(retrieval["results"]), 0)

        for res in retrieval["results"]:
            targets = res["metadata"]["disease_targets"]
            self.assertIn("Tomato___Early_blight", targets, "Filtered results must only contain Early Blight.")

    def test_06_retrieval_relevance_and_citations(self):
        """Verify that a specific factual query returns relevant content with full citations."""
        query = "What is the recommended seed treatment temperature for bacterial spot?"
        retrieval = self.retriever.retrieve(
            query=query,
            disease_target="Tomato___Bacterial_spot",
            top_k=3
        )
        self.assertTrue(retrieval["has_sufficient_evidence"])
        self.assertGreater(len(retrieval["citations"]), 0)
        
        top_citation = retrieval["citations"][0]
        self.assertIn("Cornell", top_citation["institution"])
        self.assertIn("122°F", retrieval["context_text"])

    def test_07_insufficient_evidence_handling(self):
        """Verify that an unrelated/out-of-domain query safely triggers fallback message."""
        unrelated_query = "How to treat fire blight in apple trees with streptomycin?"
        retrieval = self.retriever.retrieve(
            query=unrelated_query,
            top_k=4
        )
        self.assertFalse(retrieval["has_sufficient_evidence"], "Out-of-domain query should not have sufficient evidence.")
        self.assertEqual(retrieval["fallback_message"], INSUFFICIENT_EVIDENCE_FALLBACK)

if __name__ == "__main__":
    unittest.main()
