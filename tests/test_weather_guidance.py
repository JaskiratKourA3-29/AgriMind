"""
Unit & Integration Test Suite for Weather-Aware Crop Care & Decision Support (Stage E).
Verifies:
1. Heat stress advisories for temperatures >= 32°C in English and Hindi.
2. Heavy rainfall & waterlogging warnings for rain >= 10mm.
3. High foliar humidity advisories for RH >= 75%.
4. Regulatory disclaimer disclaiming chemical auto-prescription based solely on weather.
5. GET /weather/guidance FastAPI endpoint routing.
"""
import os
import sys
import unittest
from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.services.weather_service import WeatherService, WeatherData


class TestWeatherCropGuidance(unittest.TestCase):

    def setUp(self):
        self.svc = WeatherService()
        self.client = TestClient(app)

    def _make_dummy_weather(self, temp=24.0, rh=60.0, rain=0.0):
        return WeatherData(
            latitude=32.72,
            longitude=74.85,
            temperature_c=temp,
            relative_humidity_pct=rh,
            precipitation_mm=rain,
            wind_speed_kmh=10.0,
            weather_code=1,
            condition_summary="Test Conditions",
            rain_forecast_24h_mm=rain,
            is_live=True,
            source="Test Provider",
            timestamp="2026-11-03T12:00:00Z"
        )

    def test_01_heat_stress_advisory_en_and_hi(self):
        """High temperatures (>=32C) trigger heat stress advisory in EN and HI."""
        hot_weather = self._make_dummy_weather(temp=35.0, rh=45.0, rain=0.0)

        # English
        g_en = self.svc.get_weather_crop_care_guidance(hot_weather, crop="tomato", language="en")
        self.assertIsNotNone(g_en["heat_advisory"])
        self.assertIn("Heat Stress Alert", g_en["heat_advisory"])
        self.assertIn("blossom drop", g_en["heat_advisory"])
        self.assertIn("mulch", g_en["heat_advisory"])

        # Hindi
        g_hi = self.svc.get_weather_crop_care_guidance(hot_weather, crop="tomato", language="hi")
        self.assertIsNotNone(g_hi["heat_advisory"])
        self.assertIn("उच्च तापमान", g_hi["heat_advisory"])
        self.assertIn("मल्चिंग", g_hi["heat_advisory"])

    def test_02_heavy_rainfall_and_drainage_advisory(self):
        """Rainfall >= 10mm triggers drainage and waterlogging alert."""
        wet_weather = self._make_dummy_weather(temp=22.0, rh=85.0, rain=15.0)

        g = self.svc.get_weather_crop_care_guidance(wet_weather, crop="tomato", language="en")
        self.assertIsNotNone(g["rain_advisory"])
        self.assertIn("Rainfall & Drainage Alert", g["rain_advisory"])
        self.assertIn("Clear drainage ditches", g["rain_advisory"])

    def test_03_high_humidity_foliar_advisory(self):
        """Humidity >= 75% triggers foliar moisture warning."""
        humid_weather = self._make_dummy_weather(temp=23.0, rh=88.0, rain=0.0)

        g = self.svc.get_weather_crop_care_guidance(humid_weather, crop="tomato", language="en")
        self.assertIsNotNone(g["humidity_advisory"])
        self.assertIn("High Atmospheric Humidity", g["humidity_advisory"])
        self.assertIn("Avoid overhead sprinkler", g["humidity_advisory"])

    def test_04_regulatory_disclaimer_present(self):
        """Ensures safety disclaimer disclaiming chemical prescription based solely on weather."""
        weather = self._make_dummy_weather()
        g_en = self.svc.get_weather_crop_care_guidance(weather, language="en")
        self.assertIn("Do not apply synthetic chemical fungicides", g_en["regulatory_disclaimer"])

        g_hi = self.svc.get_weather_crop_care_guidance(weather, language="hi")
        self.assertIn("रासायनिक कीटनाशकों", g_hi["regulatory_disclaimer"])

    def test_05_endpoint_get_weather_guidance(self):
        """Verifies GET /weather/guidance returns HTTP 200 with structured decision support."""
        resp = self.client.get("/weather/guidance?crop=tomato&language=en")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("temperature_c", data)
        self.assertIn("relative_humidity_pct", data)
        self.assertIn("regulatory_disclaimer", data)
        self.assertEqual(data["crop"], "tomato")


if __name__ == "__main__":
    unittest.main()

