"""
Unit and Integration Tests for Regional Multi-Crop RAG Guidance (Wheat, Rice, Potato, Mustard, Chili)
and Transparency Boundary Validation in AgriMind.
"""
import unittest
from src.rag.generator import AgrimindAnswerGenerator, check_multi_crop_guidance


class TestMultiCropRAGGuidance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = AgrimindAnswerGenerator()

    def test_direct_wheat_guidance_english(self):
        resp = check_multi_crop_guidance("What is the best sowing time and irrigation for wheat?", language="en")
        self.assertIsNotNone(resp)
        self.assertTrue(resp["has_sufficient_evidence"])
        self.assertIn("Wheat", resp["disease_target"])
        self.assertIn("Crown Root Initiation", resp["answer"])
        self.assertIn("Vision Scanner Note", resp["answer"])
        self.assertIn("tomato foliage", resp["answer"])
        self.assertEqual(resp["citations"][0]["institution"], "Indian Council of Agricultural Research (ICAR)")

    def test_direct_rice_guidance_hindi(self):
        resp = check_multi_crop_guidance("धान की फसल में पानी का प्रबंधन और ब्लास्ट रोग कैसे रोकें?", language="hi")
        self.assertIsNotNone(resp)
        self.assertTrue(resp["has_sufficient_evidence"])
        self.assertEqual(resp["language"], "hi")
        self.assertIn("भाकृअनुप", resp["answer"])
        self.assertIn("कैमरा विज़न स्कैनर सूचना", resp["answer"])
        self.assertIn("टमाटर की फसल", resp["answer"])

    def test_direct_potato_guidance(self):
        resp = check_multi_crop_guidance("How to prevent late blight in potato crop?", language="en")
        self.assertIsNotNone(resp)
        self.assertTrue(resp["has_sufficient_evidence"])
        self.assertIn("Potato", resp["disease_target"])
        self.assertIn("Earthing Up", resp["answer"])

    def test_direct_mustard_guidance(self):
        resp = check_multi_crop_guidance("सरसों की बुवाई और माहू कीट नियंत्रण", language="hi")
        self.assertIsNotNone(resp)
        self.assertTrue(resp["has_sufficient_evidence"])
        self.assertIn("माहू", resp["answer"])
        self.assertIn("पीले स्टिकी ट्रैप", resp["answer"])

    def test_direct_chili_guidance(self):
        resp = check_multi_crop_guidance("How to control chili leaf curl virus?", language="en")
        self.assertIsNotNone(resp)
        self.assertTrue(resp["has_sufficient_evidence"])
        self.assertIn("Chili", resp["disease_target"])
        self.assertIn("Neem Seed Kernel Extract", resp["answer"])

    def test_adversarial_non_agronomic_tractor_filtered(self):
        # Queries regarding mechanical repairs must NOT return crop guidance
        resp = check_multi_crop_guidance("How to repair tractor gearbox in wheat field?", language="en")
        self.assertIsNone(resp)

    def test_adversarial_fabricated_chemical_filtered(self):
        resp = check_multi_crop_guidance("Spray crypto-solanidine-XYZ99 on wheat crop", language="en")
        self.assertIsNone(resp)

    def test_end_to_end_generate_answer_wheat(self):
        result = self.generator.generate_answer(
            query="When should I sow wheat in North India and what are the irrigation stages?",
            language="en"
        )
        self.assertTrue(result["has_sufficient_evidence"])
        self.assertEqual(result["generation_mode"], "multi_crop_institutional_advisory")
        self.assertIn("Vision Scanner Note", result["answer"])
        self.assertIn("tomato", result["answer"].lower())

    def test_end_to_end_generate_answer_tractor_fallback(self):
        result = self.generator.generate_answer(
            query="How to repair tractor engine gearbox?",
            language="en"
        )
        self.assertFalse(result["has_sufficient_evidence"])
        self.assertEqual(result["generation_mode"], "insufficient_evidence_fallback")
        self.assertIn("Insufficient agricultural evidence", result["answer"])


if __name__ == "__main__":
    unittest.main()
