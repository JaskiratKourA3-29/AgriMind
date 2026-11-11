"""
Unit Test Suite for Image Quality & Foliar Validation Engine (Stage D).
Verifies:
1. Valid plant leaf images pass validation.
2. Severely dark images produce localized TOO_DARK advisory.
3. Overexposed images produce localized OVEREXPOSED advisory.
4. Blurred images produce localized BLURRY advisory.
5. Non-plant images (e.g. blue sky, red car) produce localized NO_PLANT_DETECTED advisory.
6. Localized Hindi error messages match expected Devanagari guidance.
"""
import io
import unittest
from PIL import Image, ImageDraw

from src.vision.image_validator import validate_image_suitability


def create_test_image(color=(34, 139, 34), width=200, height=200, draw_pattern=True) -> bytes:
    """Generates a test JPEG image with optional high-frequency edge patterns."""
    img = Image.new("RGB", (width, height), color=color)
    if draw_pattern:
        draw = ImageDraw.Draw(img)
        # Add high-contrast lines and dots to simulate leaf veins and disease lesions
        for i in range(10, width - 10, 20):
            draw.line([(i, 10), (i + 15, height - 10)], fill=(139, 69, 19), width=2)
            draw.ellipse([(i, 50), (i + 15, 65)], fill=(160, 82, 45))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestImageValidator(unittest.TestCase):

    def test_01_valid_plant_leaf_passes(self):
        """A well-lit, sharp image containing green foliage passes suitability checks."""
        # Forest green background with simulated leaf veins/spots
        valid_bytes = create_test_image(color=(34, 139, 34), draw_pattern=True)
        is_ok, reason, msg, metrics = validate_image_suitability(valid_bytes, preferred_language="en")

        self.assertTrue(is_ok)
        self.assertIsNone(reason)
        self.assertIsNone(msg)
        self.assertGreater(metrics["foliar_ratio"], 0.04)
        self.assertGreater(metrics["laplacian_variance"], 25.0)

    def test_02_too_dark_rejected_with_guidance(self):
        """An underexposed/black image is rejected with localized guidance."""
        dark_bytes = create_test_image(color=(5, 5, 5), draw_pattern=False)

        # English
        is_ok_en, reason_en, msg_en, _ = validate_image_suitability(dark_bytes, preferred_language="en")
        self.assertFalse(is_ok_en)
        self.assertEqual(reason_en, "TOO_DARK")
        self.assertIn("too dark", msg_en)

        # Hindi
        is_ok_hi, reason_hi, msg_hi, _ = validate_image_suitability(dark_bytes, preferred_language="hi")
        self.assertFalse(is_ok_hi)
        self.assertEqual(reason_hi, "TOO_DARK")
        self.assertIn("अंधेरा", msg_hi)

    def test_03_overexposed_rejected_with_guidance(self):
        """A washed-out/overexposed image is rejected with localized guidance."""
        bright_bytes = create_test_image(color=(250, 250, 250), draw_pattern=False)
        is_ok, reason, msg, _ = validate_image_suitability(bright_bytes, preferred_language="en")

        self.assertFalse(is_ok)
        self.assertEqual(reason, "OVEREXPOSED")
        self.assertIn("overexposed", msg)

    def test_04_blurry_image_rejected(self):
        """A flat/blurry image lacking high-frequency edges is rejected with BLURRY guidance."""
        # Flat green without edges has very low Laplacian variance (< 25)
        flat_bytes = create_test_image(color=(40, 150, 40), draw_pattern=False)
        is_ok, reason, msg, metrics = validate_image_suitability(flat_bytes, preferred_language="en")

        self.assertFalse(is_ok)
        self.assertEqual(reason, "BLURRY")
        self.assertIn("blurry", msg)

    def test_05_non_plant_image_rejected(self):
        """A sharp image with no green foliar content (e.g. red tractor, brick wall) is rejected."""
        # Red-orange brick background with black lines (sharp, mean luminance ~100, but 0% green foliage)
        brick_bytes = create_test_image(color=(180, 70, 40), draw_pattern=True)
        is_ok, reason, msg, metrics = validate_image_suitability(brick_bytes, preferred_language="en")

        self.assertFalse(is_ok)
        self.assertEqual(reason, "NO_PLANT_DETECTED")
        self.assertIn("could not identify a plant or leaf", msg)
        self.assertLess(metrics["foliar_ratio"], 0.04)


if __name__ == "__main__":
    unittest.main()
