"""
Unit tests for AgriMind Language Detection Engine (Devanagari, Romanized Hinglish, and Dogri).
"""

import unittest
from src.rag.language_detector import detect_language


class TestLanguageDetector(unittest.TestCase):

    def test_english_query_detection(self):
        code, conf, method = detect_language("How do I control late blight on my tomato crop?")
        self.assertEqual(code, "en")
        self.assertGreaterEqual(conf, 0.90)

    def test_devanagari_hindi_detection(self):
        code, conf, method = detect_language("टमाटर के पौधों पर पछेती झुलसा का उपचार कैसे करें?")
        self.assertEqual(code, "hi")
        self.assertGreaterEqual(conf, 0.95)

    def test_romanized_hinglish_detection(self):
        """Verifies Romanized Hindi queries without Devanagari script are classified as 'hi'."""
        queries = [
            "tamatar ke patte sukh rahe hai kya kare",
            "kya dawai dale tamatar ki fasal me",
            "patte pile pad rahe hai kitna spray kare",
            "tamatar me rog lag gaya hai dawai batao"
        ]
        for q in queries:
            code, conf, method = detect_language(q)
            self.assertEqual(code, "hi", f"Failed for query: '{q}' (detected {code} via {method})")

    def test_dogri_vernacular_detection(self):
        """Verifies Dogri dialect markers trigger 'doi' code."""
        # Devanagari with Dogri markers
        code1, _, _ = detect_language("टमाटरै गी कीचन रोग लगी गेदा ऐ, तुस दस्सो की करिए?")
        self.assertEqual(code1, "doi")

        # Romanized Dogri
        code2, _, _ = detect_language("tusan dasso miggi tamatar ch kehn spray kareyo")
        self.assertEqual(code2, "doi")


if __name__ == "__main__":
    unittest.main()

