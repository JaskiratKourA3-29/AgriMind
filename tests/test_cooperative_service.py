"""
Unit tests for AgriMind Cooperative Aggregated Disease Intelligence Service & Multi-Region Comparisons.
"""

import unittest
import tempfile
import os
from src.services.case_sharing_service import CaseSharingService
from src.services.cooperative_service import CooperativeService, CooperativeInsights


class TestCooperativeService(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.sharing_svc = CaseSharingService(db_path=self.temp_db.name)
        self.coop_svc = CooperativeService(sharing_service=self.sharing_svc)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    def test_empty_cooperative_insights(self):
        """Verifies baseline low-risk insights when pool has no cases."""
        insights = self.coop_svc.generate_insights(target_entity="cooperative_all")
        self.assertEqual(insights.total_cases_analyzed, 0)
        self.assertEqual(insights.regional_risk_level, "LOW")
        self.assertIsNotNone(insights.outbreak_alerts)

    def test_aggregated_insights_with_multiple_cases(self):
        """Verifies disease prevalence, outbreak alerts, and risk level escalation."""
        # Share 2 Late Blight (1 critical, 1 high) and 1 Early Blight (moderate)
        self.sharing_svc.share_case(
            case_data={
                "case_id": "C1",
                "primary_diagnosis": "Tomato___Late_blight",
                "assigned_severity": "critical",
                "epidemic_risk": "critical"
            },
            owner_farmer_id="F1"
        )
        self.sharing_svc.share_case(
            case_data={
                "case_id": "C2",
                "primary_diagnosis": "Tomato___Late_blight",
                "assigned_severity": "high",
                "epidemic_risk": "high"
            },
            owner_farmer_id="F2"
        )
        self.sharing_svc.share_case(
            case_data={
                "case_id": "C3",
                "primary_diagnosis": "Tomato___Early_blight",
                "assigned_severity": "moderate",
                "epidemic_risk": "moderate"
            },
            owner_farmer_id="F3"
        )

        insights = self.coop_svc.generate_insights(target_entity="cooperative_all")
        self.assertEqual(insights.total_cases_analyzed, 3)
        self.assertEqual(insights.dominant_pathogen, "Tomato___Late_blight")
        self.assertEqual(insights.regional_risk_level, "CRITICAL")
        self.assertEqual(insights.disease_distribution["Tomato___Late_blight"]["count"], 2)
        self.assertEqual(insights.disease_distribution["Tomato___Late_blight"]["percentage"], 66.7)

        # Alerts should mention Late Blight and Critical severity
        alerts_str = " ".join(insights.outbreak_alerts)
        self.assertIn("LATE BLIGHT WARNING", alerts_str)
        self.assertIn("CRITICAL SEVERITY ESCALATION", alerts_str)

    def test_regional_comparison_and_disclaimer(self):
        """
        Verifies multi-region comparison returns live pilot alongside transparently
        disclosed simulated partner nodes, strictly adhering to truth-in-advertising guidelines.
        """
        comparison = self.coop_svc.generate_regional_comparison()
        self.assertFalse(comparison["is_live_partnership"], "Must honestly disclose unratified partnerships")
        self.assertIn("disclaimer", comparison)
        self.assertIn("simulated regional partner nodes", comparison["disclaimer"].lower())

        regions = comparison["regions"]
        self.assertEqual(len(regions), 3)

        # Region 1: Jammu local pilot
        jammu = regions[0]
        self.assertTrue(jammu["is_local_pilot"])
        self.assertEqual(jammu["data_status"], "Live Community Pilot")
        self.assertIn("Jammu", jammu["region_name"])

        # Region 2 & 3: Simulated partner grids
        punjab = regions[1]
        self.assertFalse(punjab["is_local_pilot"])
        self.assertEqual(punjab["data_status"], "Simulated Partner Node")

        himachal = regions[2]
        self.assertFalse(himachal["is_local_pilot"])
        self.assertEqual(himachal["data_status"], "Simulated Partner Node")


if __name__ == "__main__":
    unittest.main()
