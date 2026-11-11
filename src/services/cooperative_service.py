"""
AgriMind Cooperative Insights & Aggregated Disease Intelligence Service.
Synthesizes shared diagnostic data into regional epidemic alerts,
pathogen distribution analytics, and collective IPM guidance.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from src.services.case_sharing_service import get_case_sharing_service

logger = logging.getLogger(__name__)


@dataclass
class CooperativeInsights:
    region: str
    total_cases_analyzed: int
    disease_distribution: Dict[str, Dict[str, Any]]
    severity_distribution: Dict[str, int]
    risk_level_distribution: Dict[str, int]
    dominant_pathogen: Optional[str]
    regional_risk_level: str  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    outbreak_alerts: List[str]
    collective_ipm_actions: List[str]
    generated_at: str


class CooperativeService:
    """Computes aggregated cooperative-level analytics across shared farmer cases."""

    def __init__(self, sharing_service=None):
        self.sharing_service = sharing_service or get_case_sharing_service()

    def generate_insights(
        self,
        target_entity: str = "cooperative_all",
        region_name: str = "Regional Farmer Cooperative"
    ) -> CooperativeInsights:
        """Aggregates all shared cases for the cooperative and produces actionable insights."""
        shared_list = self.sharing_service.list_shared_cases(target_entity=target_entity, limit=200)

        total = len(shared_list)
        now_iso = datetime.now(timezone.utc).isoformat()

        if total == 0:
            return CooperativeInsights(
                region=region_name,
                total_cases_analyzed=0,
                disease_distribution={},
                severity_distribution={"low": 0, "moderate": 0, "high": 0, "critical": 0},
                risk_level_distribution={"low": 0, "moderate": 0, "high": 0, "critical": 0},
                dominant_pathogen=None,
                regional_risk_level="LOW",
                outbreak_alerts=["No shared cases recorded in cooperative surveillance pool yet."],
                collective_ipm_actions=[
                    "Encourage participating farmers to upload leaf assessments.",
                    "Maintain baseline preventive scouting twice weekly across all holdings."
                ],
                generated_at=now_iso
            )

        disease_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        risk_counts: Dict[str, int] = {"low": 0, "moderate": 0, "high": 0, "critical": 0}

        for item in shared_list:
            summary = item.get("case_summary", {})
            pathogen = summary.get("primary_diagnosis") or "Unknown"
            severity = (summary.get("assigned_severity") or "moderate").lower()
            risk = (summary.get("epidemic_risk") or "moderate").lower()

            disease_counts[pathogen] = disease_counts.get(pathogen, 0) + 1
            if severity in severity_counts:
                severity_counts[severity] += 1
            if risk in risk_counts:
                risk_counts[risk] += 1

        # Format distribution with percentages
        disease_dist: Dict[str, Dict[str, Any]] = {}
        dominant_disease = None
        max_count = -1
        for path, count in disease_counts.items():
            pct = round((count / total) * 100, 1)
            disease_dist[path] = {"count": count, "percentage": pct}
            if count > max_count:
                max_count = count
                dominant_disease = path

        # Determine regional risk level
        crit_count = severity_counts.get("critical", 0) + risk_counts.get("critical", 0)
        high_count = severity_counts.get("high", 0) + risk_counts.get("high", 0)

        if crit_count > 0:
            regional_risk = "CRITICAL"
        elif high_count >= 2 or (high_count / max(total, 1)) >= 0.3:
            regional_risk = "HIGH"
        elif severity_counts.get("moderate", 0) > 0:
            regional_risk = "MODERATE"
        else:
            regional_risk = "LOW"

        # Outbreak alerts
        alerts: List[str] = []
        late_blight_count = sum(c for p, c in disease_counts.items() if "late_blight" in p.lower())
        bacterial_count = sum(c for p, c in disease_counts.items() if "bacterial" in p.lower())

        if late_blight_count > 0:
            alerts.append(
                f"LATE BLIGHT WARNING: {late_blight_count} confirmed case(s) reported in cooperative pool. "
                "Cool/moist weather poses high regional transmission risk. Synchronize protective spraying."
            )
        if bacterial_count > 0:
            alerts.append(
                f"BACTERIAL SPOT ALERT: {bacterial_count} case(s) reported. Avoid overhead watering and sanitise machinery between fields."
            )
        if crit_count > 0:
            alerts.append(
                f"CRITICAL SEVERITY ESCALATION: {severity_counts.get('critical', 0)} case(s) marked critical. Immediate agronomic intervention required."
            )
        if not alerts:
            alerts.append("Cooperative pathogen incidence is currently within normal seasonal thresholds.")

        # Collective IPM recommendations based on dominant pathogen
        ipm_actions: List[str] = [
            "Coordinated Chemical Timing: Coordinate protectant spray cycles (Mancozeb / Chlorothalonil) within 48h across neighboring plots.",
            "Field Sanitation Protocol: Bag and remove severely infected solanaceous biomass during hot midday hours to prevent spore drift.",
            "Drip Irrigation Uniformity: Ensure all cooperative members eliminate overhead sprinklers to minimize leaf wetness duration.",
            "Shared Machine Decontamination: Wash and sanitize tractors, crates, and harvesting shears with 10% bleach between farm visits."
        ]

        return CooperativeInsights(
            region=region_name,
            total_cases_analyzed=total,
            disease_distribution=disease_dist,
            severity_distribution=severity_counts,
            risk_level_distribution=risk_counts,
            dominant_pathogen=dominant_disease,
            regional_risk_level=regional_risk,
            outbreak_alerts=alerts,
            collective_ipm_actions=ipm_actions,
            generated_at=now_iso
        )

    def generate_regional_comparison(self) -> Dict[str, Any]:
        """
        Produces a multi-regional comparative view (Jammu vs neighboring agricultural belts).
        Explicitly distinguishes local live surveillance data from demonstration partner grids.
        """
        jammu_insights = self.generate_insights(
            target_entity="cooperative_all",
            region_name="Jammu (R.S. Pura Pilot)"
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        # Simulated partner regions for multi-cooperative interoperability demo
        comparison = {
            "generated_at": now_iso,
            "is_live_partnership": False,
            "disclaimer": (
                "Multi-cooperative comparison presents local live pilot cases alongside "
                "simulated regional partner nodes for demonstration of multi-cooperative interoperability. "
                "Formal inter-state data exchange requires approved data governance protocols."
            ),
            "regions": [
                {
                    "region_name": "Jammu & Kashmir (R.S. Pura Hub)",
                    "cooperative_id": "coop_jammu_rspura",
                    "is_local_pilot": True,
                    "data_status": "Live Community Pilot",
                    "total_cases": jammu_insights.total_cases_analyzed,
                    "dominant_pathogen": jammu_insights.dominant_pathogen or "Late Blight (Phytophthora infestans)",
                    "regional_risk_level": jammu_insights.regional_risk_level,
                    "outbreak_alerts": jammu_insights.outbreak_alerts,
                    "disease_distribution": jammu_insights.disease_distribution
                },
                {
                    "region_name": "Punjab Border Grid (Gurdaspur Cluster)",
                    "cooperative_id": "coop_punjab_gurdaspur_sim",
                    "is_local_pilot": False,
                    "data_status": "Simulated Partner Node",
                    "total_cases": 42,
                    "dominant_pathogen": "Early Blight (Alternaria solani)",
                    "regional_risk_level": "MODERATE",
                    "outbreak_alerts": [
                        "Elevated Early Blight foliar lesions reported in canal-irrigated acreage."
                    ],
                    "disease_distribution": {
                        "Tomato___Early_blight": {"count": 26, "percentage": 61.9},
                        "Tomato___Late_blight": {"count": 10, "percentage": 23.8},
                        "Tomato___Bacterial_spot": {"count": 6, "percentage": 14.3}
                    }
                },
                {
                    "region_name": "Himachal Foothills (Kangra Sub-Valley)",
                    "cooperative_id": "coop_himachal_kangra_sim",
                    "is_local_pilot": False,
                    "data_status": "Simulated Partner Node",
                    "total_cases": 35,
                    "dominant_pathogen": "Bacterial Spot (Xanthomonas)",
                    "regional_risk_level": "HIGH",
                    "outbreak_alerts": [
                        "High morning leaf wetness and warm afternoon winds accelerating Bacterial Spot transmission."
                    ],
                    "disease_distribution": {
                        "Tomato___Bacterial_spot": {"count": 20, "percentage": 57.1},
                        "Tomato___Late_blight": {"count": 11, "percentage": 31.4},
                        "Tomato___Early_blight": {"count": 4, "percentage": 11.4}
                    }
                }
            ]
        }
        return comparison


# Singleton
_COOPERATIVE_SERVICE = None


def get_cooperative_service() -> CooperativeService:
    global _COOPERATIVE_SERVICE
    if _COOPERATIVE_SERVICE is None:
        _COOPERATIVE_SERVICE = CooperativeService()
    return _COOPERATIVE_SERVICE

