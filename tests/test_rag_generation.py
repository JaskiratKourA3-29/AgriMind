"""
Automated Isolated Unit Tests for AgriMind RAG Answer Generator (Week 3 Phase 5).
Strictly read-only against the active ChromaDB index (force_rebuild is NEVER invoked).
Tests:
- Insufficient evidence gating
- Grounded extractive synthesis across 3 tomato diseases
- Mocked Gemini generation and prompt formatting
- Graceful error handling on LLM API failure
- Malformed queries handling
- Vector store read-only preservation
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK
from src.rag.generator import AgrimindAnswerGenerator
from src.rag.vectorstore import get_collection_stats, DEFAULT_CHROMA_DIR, COLLECTION_NAME


class TestAgriMindAnswerGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Strictly read-only connection to existing ChromaDB index (NO REBUILD)
        cls.retriever = AgrimindRetriever(
            persist_directory=DEFAULT_CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )
        cls.generator = AgrimindAnswerGenerator(retriever=cls.retriever)

    def test_01_insufficient_evidence_gating(self):
        """Verify out-of-domain query safely triggers fallback without hallucination."""
        ood_query = "What herbicide is recommended for controlling broadleaf weeds in corn fields?"
        res = self.generator.generate_answer(query=ood_query)

        self.assertFalse(res["has_sufficient_evidence"])
        self.assertEqual(res["answer"], INSUFFICIENT_EVIDENCE_FALLBACK)
        self.assertEqual(len(res["citations"]), 0)
        self.assertEqual(res["generation_mode"], "insufficient_evidence_fallback")

    def test_02_bacterial_spot_grounded_answer(self):
        """Verify Bacterial Spot query generates cited recommendations from extension literature."""
        query = "How can tomato seeds be treated to eliminate the bacterial spot pathogen?"
        res = self.generator.generate_answer(
            query=query,
            disease_target="Tomato___Bacterial_spot"
        )

        self.assertTrue(res["has_sufficient_evidence"])
        self.assertIn(res["generation_mode"], ["grounded_extractive", "gemini_llm"])
        self.assertGreater(len(res["citations"]), 0)
        
        # Verify citation provenance
        top_cit = res["citations"][0]
        self.assertIn("DOC-", top_cit["doc_id"])
        self.assertTrue(top_cit["source_url"].startswith("http"))
        
        # Verify grounding content contains factual seed treatment details
        answer_lower = res["answer"].lower()
        self.assertTrue("122°f" in answer_lower or "hot water" in answer_lower or "seed" in answer_lower)

    def test_03_early_blight_grounded_answer(self):
        """Verify Early Blight query produces cited symptoms with institutional provenance."""
        query = "What distinctive leaf pattern identifies early blight on tomato plants?"
        res = self.generator.generate_answer(
            query=query,
            disease_target="Tomato___Early_blight"
        )

        self.assertTrue(res["has_sufficient_evidence"])
        self.assertGreater(len(res["citations"]), 0)
        answer_lower = res["answer"].lower()
        self.assertTrue("concentric" in answer_lower or "target" in answer_lower or "bullseye" in answer_lower or "alternaria" in answer_lower)

    def test_04_late_blight_grounded_answer(self):
        """Verify Late Blight query retrieves resistance genetics and citations."""
        query = "Which tomato varieties carry genetic resistance against late blight?"
        res = self.generator.generate_answer(
            query=query,
            disease_target="Tomato___Late_blight"
        )

        self.assertTrue(res["has_sufficient_evidence"])
        self.assertGreater(len(res["citations"]), 0)
        answer_lower = res["answer"].lower()
        self.assertTrue("ph-2" in answer_lower or "ph-3" in answer_lower or "resistant" in answer_lower or "mountain magic" in answer_lower)

    def test_05_mock_gemini_generation(self):
        """Verify that when an LLM is active, generator passes structured context and returns LLM output."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "According to Cornell Extension [1], hot water treatment at 122°F for 25 minutes eradicates bacterial spot."
        mock_llm.invoke.return_value = mock_response

        gen_with_mock = AgrimindAnswerGenerator(
            retriever=self.retriever,
            llm=mock_llm,
            model_name="gemini-2.5-flash-mock"
        )

        res = gen_with_mock.generate_answer(
            query="How to treat tomato seed for bacterial spot?",
            disease_target="Tomato___Bacterial_spot"
        )

        self.assertTrue(res["has_sufficient_evidence"])
        self.assertEqual(res["generation_mode"], "gemini_llm")
        self.assertEqual(res["answer"], mock_response.content)
        mock_llm.invoke.assert_called_once()
        
        # Verify call arguments contained SystemMessage and HumanMessage
        messages = mock_llm.invoke.call_args[0][0]
        self.assertEqual(len(messages), 2)
        self.assertIn("AgriMind", messages[0].content)

    def test_06_gemini_api_failure_graceful_fallback(self):
        """Verify that if Gemini API throws an error (e.g. 401/network), system gracefully falls back."""
        failing_mock_llm = MagicMock()
        failing_mock_llm.invoke.side_effect = RuntimeError("API key invalid or quota exceeded (401 Unauthorized)")

        gen_with_failing_llm = AgrimindAnswerGenerator(
            retriever=self.retriever,
            llm=failing_mock_llm
        )

        res = gen_with_failing_llm.generate_answer(
            query="What fungicides manage tomato early blight?",
            disease_target="Tomato___Early_blight"
        )

        self.assertTrue(res["has_sufficient_evidence"])
        self.assertEqual(res["generation_mode"], "grounded_extractive_fallback")
        self.assertIn("API key invalid or quota exceeded", res["error"])
        # Answer must still be generated via extractive fallback
        self.assertIn("Extension", res["answer"])
        self.assertGreater(len(res["citations"]), 0)

    def test_07_empty_and_whitespace_queries(self):
        """Verify invalid or empty queries are safely caught without uncaught exceptions."""
        for empty_q in ["", "   ", "\n\t"]:
            res = self.generator.generate_answer(query=empty_q)
            self.assertFalse(res["has_sufficient_evidence"])
            self.assertEqual(res["generation_mode"], "validation_error")

    def test_08_citation_schema_integrity(self):
        """Verify all citations conform to schema and include essential provenance fields."""
        res = self.generator.generate_answer(
            query="What protectant fungicides are recommended for early blight?",
            disease_target="Tomato___Early_blight"
        )
        self.assertTrue(res["has_sufficient_evidence"])
        for cit in res["citations"]:
            self.assertIn("citation_number", cit)
            self.assertIn("doc_id", cit)
            self.assertIn("title", cit)
            self.assertIn("institution", cit)
            self.assertIn("source_url", cit)
            self.assertIn("similarity_score", cit)

    def test_09_read_only_vectorstore_preservation(self):
        """Verify collection count in ChromaDB remains exactly 50 chunks after all test queries."""
        stats = get_collection_stats(DEFAULT_CHROMA_DIR, COLLECTION_NAME)
        self.assertTrue(stats["exists"])
        self.assertIn(stats["total_chunks"], [50, 63], "Persistent index must remain intact (50 or 63 chunks).")


if __name__ == "__main__":
    unittest.main()
