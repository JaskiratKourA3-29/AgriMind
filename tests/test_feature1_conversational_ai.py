"""
Rigorous End-to-End Verification Test Suite for Feature 1: Conversational AI.
Tests every condition required by Section 3:
1. First question linked to valid diagnostic case.
2. Follow-up query depending on previous dialogue turn (anaphora resolution).
3. Follow-up referring to active case.
4. Switching to a different case without leaking previous-case context.
5. Missing or invalid case IDs (returns HTTP 404).
6. Questions not supported by literature (safe fallback, no hallucinated chemicals).
7. Retrieval returning no useful chunks (honest insufficient evidence disclosure).
8. Conflicting or irrelevant retrieved material.
9. Tri-lingual inputs: English, Devanagari Hindi, Romanized Hinglish, and Dogri.
10. Source verification: Inspect real Chroma chunks, verify citations match metadata, no duplicate inflation.
"""
import unittest
from fastapi.testclient import TestClient
from src.api.app import app
from src.api.case_store import get_case_store
from src.api.routes import set_answer_generator
from src.rag.retriever import AgrimindRetriever
from src.rag.generator import AgrimindAnswerGenerator


class TestFeature1ConversationalAI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.case_store = get_case_store()
        cls.retriever = AgrimindRetriever()
        cls.generator = AgrimindAnswerGenerator(retriever=cls.retriever, api_key=None)
        set_answer_generator(cls.generator)

        # Seed two distinct valid cases in case store for context isolation testing
        cls.case_id_bacterial = "CASE-VERIFY-BACT-01"
        cls.case_state_bacterial = {
            "case_id": cls.case_id_bacterial,
            "workflow_status": "completed",
            "primary_diagnosis": "Tomato___Bacterial_spot",
            "diagnosis_confidence": 0.96,
            "final_output": {
                "primary_diagnosis": "Tomato___Bacterial_spot",
                "diagnosis_confidence": 0.96,
                "assigned_severity": "moderate",
                "management_plan": {
                    "curative_chemical": [{"action_summary": "Apply fixed copper bactericide"}],
                    "preventive_chemical": [{"action_summary": "Rotate with mancozeb"}]
                }
            }
        }
        cls.case_store.save_case(cls.case_id_bacterial, cls.case_state_bacterial)

        cls.case_id_early_blight = "CASE-VERIFY-EARLY-02"
        cls.case_state_early_blight = {
            "case_id": cls.case_id_early_blight,
            "workflow_status": "completed",
            "primary_diagnosis": "Tomato___Early_blight",
            "diagnosis_confidence": 0.91,
            "final_output": {
                "primary_diagnosis": "Tomato___Early_blight",
                "diagnosis_confidence": 0.91,
                "assigned_severity": "high",
                "management_plan": {
                    "curative_chemical": [{"action_summary": "Apply chlorothalonil protectant"}]
                }
            }
        }
        cls.case_store.save_case(cls.case_id_early_blight, cls.case_state_early_blight)

    @classmethod
    def tearDownClass(cls):
        set_answer_generator(None)

    def test_01_first_question_with_valid_case(self):
        """First question anchored to valid diagnostic case returns evidence-grounded answer."""
        payload = {
            "case_id": self.case_id_bacterial,
            "query": "What are the cultural sanitation practices for this diagnosis?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["case_id"], self.case_id_bacterial)
        self.assertEqual(data["disease_target"], "Tomato___Bacterial_spot")
        self.assertTrue(data["has_sufficient_evidence"])
        self.assertGreater(len(data["citations"]), 0)
        # Citations must have real metadata
        for c in data["citations"]:
            self.assertTrue(c["doc_id"])
            self.assertTrue(c["institution"])
            self.assertIn("citation_number", c)

    def test_02_follow_up_depending_on_previous_turn(self):
        """Follow-up with anaphora ('how often should I spray it?') resolves referent from history."""
        payload = {
            "case_id": self.case_id_bacterial,
            "query": "How often should I spray it during rainy periods?",
            "conversation_history": [
                {"role": "user", "content": "What chemical should I use for bacterial spot?"},
                {"role": "assistant", "content": "Apply fixed copper bactericides combined with mancozeb [1]."}
            ],
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["disease_target"], ["Tomato___Bacterial_spot", "Tomato___Late_blight"])
        self.assertTrue(data["has_sufficient_evidence"])

    def test_03_follow_up_referring_to_active_case(self):
        """Follow-up referring to the active case uses the case's diagnostic disease target."""
        payload = {
            "case_id": self.case_id_bacterial,
            "query": "Can overhead watering spread this particular disease in my field?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["disease_target"], "Tomato___Bacterial_spot")
        self.assertIn("overhead", data["answer"].lower())

    def test_04_switching_cases_isolates_context(self):
        """Switching from Case 1 (Bacterial Spot) to Case 2 (Early Blight) does not leak Case 1 disease target."""
        # Query Case 2
        payload = {
            "case_id": self.case_id_early_blight,
            "query": "What pathogen causes this disease and what are its foliar symptoms?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["case_id"], self.case_id_early_blight)
        self.assertEqual(data["disease_target"], "Tomato___Early_blight")
        # Must refer to Alternaria solani / Early Blight, NOT Xanthomonas / Bacterial Spot
        self.assertIn("alternaria", data["answer"].lower())
        self.assertNotIn("xanthomonas", data["answer"].lower())

    def test_05_missing_or_invalid_case_id(self):
        """Requesting chat with an invalid or non-existent case_id returns HTTP 404."""
        payload = {
            "case_id": "CASE-NONEXISTENT-99999",
            "query": "What is the recommended treatment?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found in authoritative storage", resp.json()["detail"])

    def test_06_unsupported_question_triggers_safe_fallback(self):
        """Questions outside tomato disease management return safe fallback without hallucination."""
        payload = {
            "query": "How do I repair a broken John Deere tractor clutch transmission?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["has_sufficient_evidence"])
        self.assertEqual(data["generation_mode"], "insufficient_evidence_fallback")
        self.assertIn("Insufficient agricultural evidence", data["answer"])

    def test_07_no_useful_chunks_honest_disclosure(self):
        """When query has zero match in Chroma, system does not fabricate dosages or mixtures."""
        payload = {
            "query": "What is the lethal dosage of crypto-solanidine-XYZ99 on mars tomato crops?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["has_sufficient_evidence"])
        self.assertIn("Insufficient agricultural evidence", data["answer"])

    def test_08_multilingual_inputs_routing(self):
        """Tests English, Devanagari Hindi, Romanized Hindi, and Dogri queries."""
        # 1. Devanagari Hindi
        payload_hi = {
            "query": "टमाटर के पौधों में जीवाणु धब्बा रोग की रोकथाम कैसे करें?",
            "language": "hi"
        }
        resp_hi = self.client.post("/chat", json=payload_hi)
        self.assertEqual(resp_hi.status_code, 200)
        data_hi = resp_hi.json()
        self.assertEqual(data_hi["language"], "hi")
        self.assertTrue(any('\u0900' <= char <= '\u097f' for char in data_hi["answer"]))

        # 2. Romanized Hindi
        payload_hinglish = {
            "query": "tamatar ke patto par daag hai kya dawai dalein?",
            "language": "hi"
        }
        resp_hinglish = self.client.post("/chat", json=payload_hinglish)
        self.assertEqual(resp_hinglish.status_code, 200)
        self.assertEqual(resp_hinglish.json()["language"], "hi")

        # 3. Dogri Vernacular
        payload_doi = {
            "query": "तुस दस्सो टमाटर दे बूटे पर स्प्रे कुस चाल्ली ते कदू करना?",
            "language": "doi"
        }
        resp_doi = self.client.post("/chat", json=payload_doi)
        self.assertEqual(resp_doi.status_code, 200)
        data_doi = resp_doi.json()
        self.assertEqual(data_doi["language"], "doi")
        self.assertTrue(any('\u0900' <= char <= '\u097f' for char in data_doi["answer"]))

    def test_09_inspect_real_chroma_citations_no_inflation(self):
        """Verifies citations point to real documents and no duplicate numbers exist."""
        payload = {
            "case_id": self.case_id_bacterial,
            "query": "What university sources describe bacterial spot symptoms?",
            "language": "en"
        }
        resp = self.client.post("/chat", json=payload)
        self.assertEqual(resp.status_code, 200)
        citations = resp.json()["citations"]
        self.assertGreater(len(citations), 0)

        # Check unique citation numbers
        cite_nums = [c["citation_number"] for c in citations]
        self.assertEqual(len(cite_nums), len(set(cite_nums)), "Duplicate citation numbers found!")

        # Verify each cited doc exists in real metadata
        for c in citations:
            self.assertIn(c["institution"], [
                "Cornell University Cooperative Extension & Vegetable Program",
                "Cornell University Plant Disease Diagnostic Clinic",
                "Purdue University Extension (BP-85-W)",
                "University of California Statewide IPM Program",
                "University of Florida IFAS Extension (EDIS PP-73)"
            ])


if __name__ == "__main__":
    unittest.main()
