"""
AgriMind Real Weather Data & Epidemiological Risk Escalation Service.
Integrates the Open-Meteo REST API (open-access, non-commercial/commercial friendly, no API key required)
to retrieve real-time ambient meteorological data and calculate evidence-based disease risks.
"""

import logging
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Default coordinates for regional Jammu & Kashmir tomato agricultural zone
DEFAULT_LATITUDE = 32.7266
DEFAULT_LONGITUDE = 74.8570


@dataclass
class WeatherData:
    latitude: float
    longitude: float
    temperature_c: float
    relative_humidity_pct: float
    precipitation_mm: float
    wind_speed_kmh: float
    weather_code: int
    condition_summary: str
    rain_forecast_24h_mm: float
    is_live: bool
    source: str
    timestamp: str


@dataclass
class EpidemiologicalRiskAssessment:
    pathogen: str
    is_conducive: bool
    epidemic_risk_level: str  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    severity_escalation: bool
    risk_factors: list[str]
    rain_fastness_warning: Optional[str]
    recommended_spray_window: str


class WeatherService:
    """Provides real-time weather fetching and agricultural epidemiological risk models."""

    def __init__(self, timeout_seconds: float = 6.0):
        self.timeout = timeout_seconds

    def fetch_live_weather(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> WeatherData:
        """
        Fetches current weather and 24h precipitation forecast from Open-Meteo API.
        If network is unavailable or request fails, provides a structured offline fallback.
        """
        lat = latitude if latitude is not None else DEFAULT_LATITUDE
        lon = longitude if longitude is not None else DEFAULT_LONGITUDE

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lon:.4f}&"
            f"current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&"
            f"hourly=precipitation&forecast_days=2&timezone=auto"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AgriMind-Crop-Health-System/1.0"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data.get("current", {})
            hourly = data.get("hourly", {})
            hourly_precip = hourly.get("precipitation", [])
            rain_24h = sum(hourly_precip[:24]) if hourly_precip else 0.0

            temp = float(current.get("temperature_2m", 22.0))
            rh = float(current.get("relative_humidity_2m", 65.0))
            precip = float(current.get("precipitation", 0.0))
            wind = float(current.get("wind_speed_10m", 5.0))
            wcode = int(current.get("weather_code", 0))
            time_str = current.get("time", "")

            condition_desc = self._wmo_code_to_text(wcode, temp, rh, precip)

            return WeatherData(
                latitude=lat,
                longitude=lon,
                temperature_c=temp,
                relative_humidity_pct=rh,
                precipitation_mm=precip,
                wind_speed_kmh=wind,
                weather_code=wcode,
                condition_summary=condition_desc,
                rain_forecast_24h_mm=round(rain_24h, 2),
                is_live=True,
                source="Open-Meteo Global Meteorological API",
                timestamp=time_str
            )
        except Exception as e:
            logger.warning("Live weather fetch failed (%s). Utilizing edge fallback context.", str(e))
            return WeatherData(
                latitude=lat,
                longitude=lon,
                temperature_c=22.0,
                relative_humidity_pct=65.0,
                precipitation_mm=0.0,
                wind_speed_kmh=8.0,
                weather_code=1,
                condition_summary="Clear / Moderate (Offline Fallback)",
                rain_forecast_24h_mm=0.0,
                is_live=False,
                source="Offline Default Context",
                timestamp=""
            )

    def evaluate_epidemiological_risk(
        self,
        pathogen: str,
        weather: WeatherData,
        current_leaf_damage_pct: float = 3.0
    ) -> EpidemiologicalRiskAssessment:
        """
        Calculates pathogen-specific epidemiological risk escalation based on real weather.
        Implements Wallin/Hyre Late Blight criteria, alternating moisture models for Early Blight,
        and wind/splash models for Bacterial Spot.
        """
        temp = weather.temperature_c
        rh = weather.relative_humidity_pct
        precip = weather.precipitation_mm
        rain_24h = weather.rain_forecast_24h_mm
        wind = weather.wind_speed_kmh

        risk_factors: list[str] = []
        is_conducive = False
        risk_level = "LOW"
        escalate_severity = False

        norm_pathogen = pathogen.lower()

        if "late_blight" in norm_pathogen:
            # Wallin / Hyre criteria: Temp 10-24°C with RH > 80% or free moisture
            temp_conducive = 10.0 <= temp <= 24.0
            moisture_conducive = rh >= 80.0 or precip > 0.0 or rain_24h > 1.0

            if temp_conducive:
                risk_factors.append(f"Temperature ({temp:.1f}°C) is in optimal Phytophthora infestans sporulation range (10-24°C)")
            if moisture_conducive:
                risk_factors.append(f"High atmospheric humidity ({rh:.1f}%) and moisture facilitate rapid sporangia germination within 2-3 hours")

            if temp_conducive and moisture_conducive:
                is_conducive = True
                escalate_severity = True
                if current_leaf_damage_pct >= 5.0 or rain_24h >= 5.0:
                    risk_level = "CRITICAL"
                else:
                    risk_level = "HIGH"
            elif temp_conducive or moisture_conducive:
                risk_level = "MODERATE"
            else:
                risk_level = "LOW"

        elif "early_blight" in norm_pathogen:
            # Alternaria solani: Temp 24-32°C with alternating wet/dry conditions
            temp_conducive = 24.0 <= temp <= 32.0
            moisture_conducive = rh >= 70.0 or precip > 0.0

            if temp_conducive:
                risk_factors.append(f"Warm temperature ({temp:.1f}°C) favors Alternaria conidia development (24-32°C)")
            if moisture_conducive:
                risk_factors.append(f"Elevated humidity ({rh:.1f}%) promotes foliar lesion expansion")

            if temp_conducive and moisture_conducive:
                is_conducive = True
                escalate_severity = current_leaf_damage_pct >= 4.0
                risk_level = "HIGH" if current_leaf_damage_pct >= 6.0 else "MODERATE"
            else:
                risk_level = "MODERATE" if (temp_conducive or moisture_conducive) else "LOW"

        elif "bacterial_spot" in norm_pathogen:
            # Xanthomonas: Temp 24-30°C with high humidity and driving rain/wind
            temp_conducive = 24.0 <= temp <= 30.0
            splash_conducive = (rh >= 80.0 or precip > 0.0) and wind >= 10.0

            if temp_conducive:
                risk_factors.append(f"Warm temperature ({temp:.1f}°C) ideal for Xanthomonas bacterial multiplication")
            if splash_conducive:
                risk_factors.append(f"Wind ({wind:.1f} km/h) combined with moisture drives bacterial ingress through stomata and wounds")

            if temp_conducive and splash_conducive:
                is_conducive = True
                escalate_severity = True
                risk_level = "HIGH"
            else:
                risk_level = "MODERATE" if (temp_conducive or rh >= 75.0) else "LOW"

        else:
            risk_level = "LOW"

        # Rain-fastness warning logic
        rain_warning = None
        spray_window = "Optimal spray window: Morning hours with low wind (<10 km/h) and no imminent rain."
        if rain_24h >= 1.0:
            rain_warning = (
                f"Rainfall alert: Approximately {rain_24h:.1f} mm precipitation forecast within next 24 hours. "
                "Foliar contact protectants (e.g. Chlorothalonil or Mancozeb) risk wash-off unless applied at least "
                "2 to 3 hours prior to precipitation. Consider adding an approved non-ionic spreader/sticker or using "
                "locally systemic translaminar fungicides (e.g. Mandipropamid) if curative action is required."
            )
            spray_window = "Spray window constrained: Apply only if clear dry interval of 3+ hours is assured before rain."

        return EpidemiologicalRiskAssessment(
            pathogen=pathogen,
            is_conducive=is_conducive,
            epidemic_risk_level=risk_level,
            severity_escalation=escalate_severity,
            risk_factors=risk_factors,
            rain_fastness_warning=rain_warning,
            recommended_spray_window=spray_window
        )

    def _wmo_code_to_text(self, code: int, temp: float, rh: float, precip: float) -> str:
        """Converts WMO weather interpretation code to agronomic condition text."""
        if code == 0:
            return "Clear Skies"
        elif code in (1, 2, 3):
            return "Partly Cloudy"
        elif code in (45, 48):
            return "Fog / High Humidity"
        elif code in (51, 53, 55):
            return "Drizzle / Light Moisture"
        elif code in (61, 63, 65):
            return "Rain / Free Moisture"
        elif code in (80, 81, 82):
            return "Rain Showers"
        elif code >= 95:
            return "Thunderstorm / Wind & Rain"
        elif precip > 0:
            return "Active Precipitation"
        elif rh > 80:
            return "Humid / Overcast"
        elif temp > 28:
            return "Warm & Dry"
        else:
            return "Mild Agricultural Weather"

    def get_weather_crop_care_guidance(
        self,
        weather: WeatherData,
        crop: str = "tomato",
        growth_stage: Optional[str] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Produces crop-specific agricultural care guidance based on ambient weather,
        addressing heat stress, rainfall, humidity/leaf wetness, and disease risks
        in English and Hindi.
        """
        lang = "hi" if language.lower() in ("hi", "hindi") else "en"
        temp = weather.temperature_c
        rh = weather.relative_humidity_pct
        rain_24h = weather.rain_forecast_24h_mm
        crop_clean = crop.strip().lower()

        # 1. Heat Stress Guidance
        heat_advisory = None
        if temp >= 32.0:
            if lang == "en":
                heat_advisory = (
                    f"Heat Stress Alert ({temp:.1f}°C): High temperatures can cause blossom drop, "
                    f"pollen sterility, and poor fruit set in {crop_clean}. "
                    f"Action: Irrigate deeply during early morning or late evening. Apply straw/organic mulch "
                    f"to retain root-zone soil moisture and cool root temperatures."
                )
            else:
                heat_advisory = (
                    f"उच्च तापमान एवं लू की चेतावनी ({temp:.1f}°C): अत्यधिक गर्मी से {crop_clean} में फूल झड़ने, "
                    f"पराग सूखने और फल न बनने का खतरा रहता है। "
                    f"सलाह: सुबह या शाम के समय ड्रिप से सिंचाई करें। मिट्टी की नमी बनाए रखने और जड़ों को ठंडा रखने के लिए "
                    f"पुआल या सूखी घास से मल्चिंग (आच्छादन) करें।"
                )
        elif temp <= 10.0:
            if lang == "en":
                heat_advisory = (
                    f"Low Temperature Notice ({temp:.1f}°C): Chilling temperatures slow plant metabolism and nutrient uptake. "
                    f"Action: Avoid excessive irrigation; ensure protective row covers if frost is expected."
                )
            else:
                heat_advisory = (
                    f"कम तापमान की सूचना ({temp:.1f}°C): अत्यधिक ठंड से पौधे की वृद्धि धीमी हो जाती है। "
                    f"सलाह: अतिरिक्त सिंचाई से बचें; पाला पड़ने की संभावना होने पर खेत में हल्की नमी रखें या पौधों को ढकें।"
                )

        # 2. Heavy Rainfall & Waterlogging Guidance
        rain_advisory = None
        if rain_24h >= 10.0 or weather.precipitation_mm > 0:
            if lang == "en":
                rain_advisory = (
                    f"Rainfall & Drainage Alert (Forecast: {rain_24h:.1f} mm): Saturated soil causes root oxygen depletion "
                    f"and promotes Pythium/Phytophthora root rots. "
                    f"Action: Halt all scheduled irrigation immediately. Clear drainage ditches and field trenches "
                    f"to evacuate standing water rapidly. Inspect field within 24h after rain for eroded roots."
                )
            else:
                rain_advisory = (
                    f"वर्षा एवं जलभराव चेतावनी (अनुमान: {rain_24h:.1f} मिमी): जलभराव से जड़ों में ऑक्सीजन की कमी और जड़ सड़न "
                    f"(Damping-off/Root rot) का खतरा बढ़ जाता है। "
                    f"सलाह: सभी सिंचाई तुरंत रोकें। जल निकासी की नालियों को साफ करें ताकि पानी खेत में खड़ा न रहे। "
                    f"बारिश के बाद खेत का निरीक्षण करें।"
                )

        # 3. Humidity & Leaf Wetness Guidance
        humidity_advisory = None
        if rh >= 75.0:
            if lang == "en":
                humidity_advisory = (
                    f"High Atmospheric Humidity ({rh:.1f}%): Prolonged leaf surface moisture creates optimal conditions "
                    f"for foliar fungal sporulation and bacterial entry. "
                    f"Action: Avoid overhead sprinkler irrigation; strictly use ground drip. Prune lower senescent leaves "
                    f"to enhance airflow through the crop canopy. Do not cultivate wet foliage."
                )
            else:
                humidity_advisory = (
                    f"उच्च नमी चेतावनी ({rh:.1f}%): पत्तों पर लंबे समय तक नमी रहने से फफूंद और जीवाणु धब्बा रोग पनपते हैं। "
                    f"सलाह: ऊपर से फव्वारे से पानी न दें, केवल जड़ों में ड्रिप से पानी दें। हवा के संचार के लिए नीचे की पीली पत्तियां "
                    f"हटाएं। भीगे पौधों पर काम करने से बचें ताकि रोग न फैले।"
                )

        # 4. Safety Disclaimer
        if lang == "en":
            disclaimer = (
                "IMPORTANT NOTICE: Meteorological risk assessments evaluate environmental disease favorability only. "
                "Weather alone does not confirm pathogen infection. Do not apply synthetic chemical fungicides without "
                "identifying physical symptoms and consulting a certified agricultural extension officer."
            )
        else:
            disclaimer = (
                "महत्वपूर्ण सूचना: मौसम आधारित जोखिम केवल बीमारियों के अनुकूल मौसम का आकलन करता है, बीमारी की पुष्टि नहीं करता। "
                "केवल मौसम देखकर रासायनिक कीटनाशकों या फफूंदनाशकों का छिड़काव न करें। फसल में लक्षण दिखने पर ही स्थानीय "
                "कृषि विशेषज्ञ से परामर्श लें।"
            )

        return {
            "crop": crop,
            "growth_stage": growth_stage or "vegetative_to_fruiting",
            "temperature_c": temp,
            "relative_humidity_pct": rh,
            "rain_forecast_24h_mm": rain_24h,
            "condition_summary": weather.condition_summary,
            "heat_advisory": heat_advisory,
            "rain_advisory": rain_advisory,
            "humidity_advisory": humidity_advisory,
            "regulatory_disclaimer": disclaimer,
            "source": weather.source,
            "timestamp": weather.timestamp,
            "is_live": weather.is_live
        }


# Global singleton instance
_WEATHER_SERVICE_INSTANCE = None


def get_weather_service() -> WeatherService:
    global _WEATHER_SERVICE_INSTANCE
    if _WEATHER_SERVICE_INSTANCE is None:
        _WEATHER_SERVICE_INSTANCE = WeatherService()
    return _WEATHER_SERVICE_INSTANCE

