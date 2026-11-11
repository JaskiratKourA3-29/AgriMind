"""
Unit tests for AgriMind Real Weather Data Service & Epidemiological Risk Escalation.
"""

import unittest
from src.services.weather_service import WeatherService, WeatherData, get_weather_service


class TestWeatherService(unittest.TestCase):

    def setUp(self):
        self.service = WeatherService(timeout_seconds=5.0)

    def test_fetch_live_weather_returns_structured_data(self):
        """Verifies weather fetch returns valid WeatherData with realistic ambient bounds."""
        data = self.service.fetch_live_weather(latitude=32.7266, longitude=74.8570)
        self.assertIsInstance(data, WeatherData)
        self.assertGreater(data.temperature_c, -30.0)
        self.assertLess(data.temperature_c, 60.0)
        self.assertGreaterEqual(data.relative_humidity_pct, 0.0)
        self.assertLessEqual(data.relative_humidity_pct, 100.0)
        self.assertGreaterEqual(data.precipitation_mm, 0.0)
        self.assertIsNotNone(data.condition_summary)

    def test_epidemiological_risk_late_blight_escalation(self):
        """Verifies Wallin/Hyre cool/wet conducive weather triggers HIGH or CRITICAL risk."""
        conducive_weather = WeatherData(
            latitude=32.7,
            longitude=74.8,
            temperature_c=18.0,  # 10-24°C conducive
            relative_humidity_pct=88.0,  # >80% conducive
            precipitation_mm=2.5,
            wind_speed_kmh=12.0,
            weather_code=61,
            condition_summary="Rain",
            rain_forecast_24h_mm=6.0,
            is_live=True,
            source="Test",
            timestamp="2026-11-02T12:00:00Z"
        )
        risk = self.service.evaluate_epidemiological_risk(
            pathogen="Tomato___Late_blight",
            weather=conducive_weather,
            current_leaf_damage_pct=6.0
        )
        self.assertTrue(risk.is_conducive)
        self.assertEqual(risk.epidemic_risk_level, "CRITICAL")
        self.assertTrue(risk.severity_escalation)
        self.assertIsNotNone(risk.rain_fastness_warning)
        self.assertIn("Chlorothalonil", risk.rain_fastness_warning)

    def test_epidemiological_risk_hot_dry_non_conducive(self):
        """Verifies hot and dry weather does not escalate Late Blight."""
        dry_weather = WeatherData(
            latitude=32.7,
            longitude=74.8,
            temperature_c=34.0,  # >24°C non-conducive
            relative_humidity_pct=30.0,  # <80% non-conducive
            precipitation_mm=0.0,
            wind_speed_kmh=5.0,
            weather_code=0,
            condition_summary="Clear Skies",
            rain_forecast_24h_mm=0.0,
            is_live=True,
            source="Test",
            timestamp="2026-11-02T12:00:00Z"
        )
        risk = self.service.evaluate_epidemiological_risk(
            pathogen="Tomato___Late_blight",
            weather=dry_weather,
            current_leaf_damage_pct=2.0
        )
        self.assertFalse(risk.is_conducive)
        self.assertEqual(risk.epidemic_risk_level, "LOW")
        self.assertIsNone(risk.rain_fastness_warning)


if __name__ == "__main__":
    unittest.main()

