"""
Comprehensive 10-Scenario End-to-End Multi-Agent Workflow Verification Suite for AgriMind.
Verifies all 10 core integration scenarios:
1. Valid tomato image produces a valid three-class ResNet-50 prediction.
2. A prediction proceeds through investigation and risk assessment.
3. Retrieved evidence reaches the final decision plan with institutional citations.
4. A coherent IPM plan passes critic verification.
5. A deliberately flawed plan is rejected/flagged by Critic.
6. Missing Gemini credentials executes grounded extractive fallback cleanly.
7. Simulated Gemini API failure catches exception, sanitizes, and falls back to extractive mode.
8. Supported adaptive reassessment trigger updates case and preserves prior history.
9. Insufficient or conflicting evidence withholds autonomous certainty and defers to human expert.
10. Invalid inputs, non-image files, and missing state contracts terminate safely in error.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.workflow.state import AgriMindState
from src.workflow.graph import build_agrimind_workflow
from src.workflow.nodes import reassess_case
from src.vision.inference import VisionInferenceEngine
from src.rag.retriever import AgrimindRetriever
from src.rag.generator import AgrimindAnswerGenerator
from src.agents.investigation import InvestigationAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.agents.critic import CriticAgent
from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    ManagementAction,
    SeverityLevel,
    PlanUrgency,
    EvidenceStatus,
    VerificationStatus,
    ReassessmentTrigger
)

# Standard PlantVillage sample used across AgriMind test fixtures
SAMPLE_REAL_IMAGE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"
if not os.path.exists(SAMPLE_REAL_IMAGE):
    # Windows native path fallback
    SAMPLE_REAL_IMAGE = "C:/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"


class TestAgriMindEndToEnd10Scenarios(unittest.TestCase):
    """
    Direct verification of all 10 end-to-end integration scenarios.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = build_agrimind_workflow()
        cls.vision_engine = VisionInferenceEngine()
        cls.retriever = AgrimindRetriever()

    # -------------------------------------------------------------------------
    # Case 1: Valid tomato image produces valid 3-class prediction
    # -------------------------------------------------------------------------
    def test_case_01_valid_tomato_image_prediction(self):
        """Case 1: Valid tomato image produces a valid three-class model prediction."""
        self.assertTrue(os.path.exists(SAMPLE_REAL_IMAGE), f"Test image missing: {SAMPLE_REAL_IMAGE}")
        pred = self.vision_engine.predict(SAMPLE_REAL_IMAGE)

        self.assertIsInstance(pred, VisionPrediction)
        self.assertIn(pred.predicted_class, [
            "Tomato___Bacterial_spot",
            "Tomato___Early_blight",
            "Tomato___Late_blight"
        ])
        self.assertTrue(pred.is_supported_disease)
        self.assertGreater(pred.confidence, 0.50)
        self.assertEqual(len(pred.class_probabilities), 3)
        self.assertIn("Tomato___Bacterial_spot", pred.class_probabilities)
        self.assertIn("Tomato___Early_blight", pred.class_probabilities)
        self.assertIn("Tomato___Late_blight", pred.class_probabilities)

    # -------------------------------------------------------------------------
    # Case 2: Prediction proceeds through investigation and risk assessment
    # -------------------------------------------------------------------------
    def test_case_02_prediction_through_investigation_and_risk(self):
        """Case 2: A prediction proceeds through investigation and risk assessment."""
        pred = VisionPrediction(
            predicted_class="Tomato___Early_blight",
            confidence=0.9600,
            class_probabilities={"Tomato___Early_blight": 0.96, "Tomato___Bacterial_spot": 0.02, "Tomato___Late_blight": 0.02}
        )
        context = VisualContext(
            leaf_damage_percentage=12.0,
            affected_organs=["leaves"],
            canopy_spread="lower_canopy",
            weather_conditions="warm_dry"
        )
        inv_agent = InvestigationAgent(retriever=self.retriever)
        inv_result = inv_agent.investigate(vision_prediction=pred, visual_context=context)

        self.assertEqual(inv_result.primary_diagnosis, "Tomato___Early_blight")
        self.assertEqual(inv_result.evidence_status, EvidenceStatus.SUFFICIENT)
        self.assertEqual(len(inv_result.conflicts_detected), 0)

        risk_agent = RiskAssessmentAgent()
        risk_result = risk_agent.assess_risk(inv_result)

        self.assertIsInstance(risk_result, RiskAssessmentResult)
        self.assertEqual(risk_result.assigned_severity, SeverityLevel.MODERATE)
        self.assertEqual(risk_result.epidemic_risk, "moderate")
        # Ensure confidence is strictly decoupled from physical severity
        self.assertNotEqual(str(risk_result.assigned_severity.value), str(inv_result.diagnosis_confidence))

    # -------------------------------------------------------------------------
    # Case 3: Retrieved evidence reaches final decision plan
    # -------------------------------------------------------------------------
    def test_case_03_retrieved_evidence_reaches_decision_plan(self):
        """Case 3: Retrieved evidence reaches the final decision plan with institutional citations."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Bacterial_spot",
                confidence=0.9500,
                class_probabilities={"Tomato___Bacterial_spot": 0.95, "Tomato___Early_blight": 0.03, "Tomato___Late_blight": 0.02}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=8.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy"
            )
        }
        res = self.app.invoke(initial_state)
        final = res.get("final_output", {})

        self.assertIn(res.get("workflow_status"), ["completed", "verified"])
        plan = res.get("decision_plan")
        self.assertIsNotNone(plan)
        self.assertGreater(len(plan.citations), 0)
        # Citations must be accredited extension sources
        institutions = [c.get("institution", "") for c in plan.citations]
        self.assertTrue(any("Cornell" in inst or "UC" in inst or "Florida" in inst or "NC State" in inst or "Extension" in inst for inst in institutions))
        # Citations must reach final output
        self.assertEqual(final.get("citations"), plan.citations)

    # -------------------------------------------------------------------------
    # Case 4: Plan that passes critic verification
    # -------------------------------------------------------------------------
    def test_case_04_plan_passes_critic_verification(self):
        """Case 4: A coherent, cited IPM plan passes critic verification."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9400,
                class_probabilities={"Tomato___Early_blight": 0.94, "Tomato___Bacterial_spot": 0.03, "Tomato___Late_blight": 0.03}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=15.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                weather_conditions="mild_warm"
            )
        }
        res = self.app.invoke(initial_state)
        verif = res.get("verification_result")

        self.assertIsNotNone(verif)
        self.assertTrue(verif.is_verified)
        self.assertFalse(verif.requires_manual_review)
        self.assertEqual(verif.status, VerificationStatus.VERIFIED)
        self.assertEqual(res.get("workflow_status"), "completed")

    # -------------------------------------------------------------------------
    # Case 5: Deliberately flawed plan that critic rejects/flags
    # -------------------------------------------------------------------------
    def test_case_05_flawed_plan_rejected_by_critic(self):
        """Case 5: A deliberately flawed plan (unauthorized pesticide / urgency mismatch) is rejected by Critic."""
        critic = CriticAgent()
        flawed_plan = DecisionPlan(
            plan_id="PLN-FLAWED-001",
            assessment_id="RSK-001",
            investigation_id="INV-001",
            disease="Tomato___Early_blight",
            urgency=PlanUrgency.LOW,  # Mismatch with critical severity
            cultural_controls=[],
            resistant_varieties=[],
            chemical_controls=[
                ManagementAction(
                    category="chemical",
                    action_summary="Apply unauthorized restricted organophosphate pesticide",
                    details="Spray Paraquat or Methyl Parathion on tomatoes.",
                    is_chemical=True,
                    citation_numbers=[1]
                )
            ],
            monitoring_actions=[],
            citations=[{"citation_number": 1, "title": "Guide", "institution": "Ext", "source_url": "http://ext.edu"}],
            pesticide_safety_notice="Use PPE."
        )
        fake_pred = VisionPrediction(
            predicted_class="Tomato___Early_blight",
            confidence=0.95,
            class_probabilities={"Tomato___Early_blight": 0.95, "Tomato___Bacterial_spot": 0.05}
        )
        fake_inv = InvestigationResult(
            investigation_id="INV-001",
            timestamp="2026-10-29T12:00:00Z",
            primary_diagnosis="Tomato___Early_blight",
            diagnosis_confidence=0.95,
            visual_prediction=fake_pred,
            evidence_status=EvidenceStatus.SUFFICIENT,
            retrieved_evidence=RetrievedEvidence(has_sufficient_evidence=True, citations=[{"citation_number": 1}]),
            synthesis_narrative="Test synthesis",
            citations=[{"citation_number": 1}]
        )
        fake_risk = RiskAssessmentResult(
            assessment_id="RSK-001",
            investigation_id="INV-001",
            disease="Tomato___Early_blight",
            identification_confidence=0.95,
            assigned_severity=SeverityLevel.CRITICAL,  # Severe mismatch with LOW urgency
            severity_confidence="high",
            epidemic_risk="high",
            rubric_basis=["Critical defoliation"],
            scouting_recommendations=["Inspect"],
            requires_immediate_action=True,
            pesticide_safety_notice="Notice"
        )

        verif = critic.verify_plan(flawed_plan, fake_inv, fake_risk)

        self.assertFalse(verif.is_verified)
        self.assertIn(verif.status, [
            VerificationStatus.REJECTED_INCONSISTENCY,
            VerificationStatus.REJECTED_UNSUPPORTED_CLAIMS
        ])
        self.assertGreater(len(verif.rejection_reasons), 0)

    # -------------------------------------------------------------------------
    # Case 6: Missing Gemini credentials -> grounded extractive fallback
    # -------------------------------------------------------------------------
    def test_case_06_missing_credentials_extractive_fallback(self):
        """Case 6: Missing Gemini credentials executes grounded extractive fallback cleanly."""
        with patch("src.rag.generator.get_gemini_api_key", return_value=None):
            gen = AgrimindAnswerGenerator(retriever=self.retriever)
            res = gen.generate_answer(
                query="What temperature water is used for tomato seed treatment?",
                disease_target="Tomato___Bacterial_spot"
            )

            self.assertEqual(res.get("generation_mode"), "grounded_extractive")
            self.assertTrue(res.get("has_sufficient_evidence"))
            self.assertGreater(len(res.get("citations")), 0)
            self.assertIn("122", res.get("answer"))

    # -------------------------------------------------------------------------
    # Case 7: Simulated Gemini API failure -> graceful fallback
    # -------------------------------------------------------------------------
    def test_case_07_simulated_api_failure_graceful_fallback(self):
        """Case 7: Simulated Gemini API failure catches exception, sanitizes, and falls back to extractive mode."""
        failing_mock_llm = MagicMock()
        failing_mock_llm.invoke.side_effect = RuntimeError("503 Service Unavailable: High load on Google servers")

        with patch("src.rag.generator.get_gemini_api_key", return_value="AQ.Ab8FakeKeyForTestOnly123456"):
            gen = AgrimindAnswerGenerator(retriever=self.retriever)
            gen.llm = failing_mock_llm

            res = gen.generate_answer(
                query="How to control late blight in tomatoes?",
                disease_target="Tomato___Late_blight"
            )

            self.assertEqual(res.get("generation_mode"), "grounded_extractive_fallback")
            self.assertTrue(res.get("has_sufficient_evidence"))
            self.assertGreater(len(res.get("citations")), 0)
            self.assertFalse("AQ.Ab8FakeKeyForTestOnly123456" in res.get("answer"))

    # -------------------------------------------------------------------------
    # Case 8: Supported adaptive reassessment trigger with preserved history
    # -------------------------------------------------------------------------
    def test_case_08_adaptive_reassessment_preserves_history(self):
        """Case 8: A supported adaptive reassessment trigger updates case and preserves prior history."""
        initial_state: AgriMindState = {
            "case_id": "CASE-HIST-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9500,
                class_probabilities={"Tomato___Late_blight": 0.95, "Tomato___Early_blight": 0.03, "Tomato___Bacterial_spot": 0.02}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=3.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                weather_conditions="mild_overcast"
            )
        }
        initial_case = self.app.invoke(initial_state)
        self.assertEqual(initial_case.get("workflow_status"), "completed")
        self.assertEqual(initial_case.get("final_output", {}).get("assigned_severity"), "moderate")

        # Adaptive Reassessment via WEATHER_UPDATE
        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=initial_case,
            trigger=ReassessmentTrigger.WEATHER_UPDATE,
            new_evidence={"weather_conditions": "cool_wet", "leaf_damage_percentage": 15.0},
            rationale="Sudden cold rainstorm overnight."
        )

        final = revised_case.get("final_output", {})
        self.assertEqual(final.get("reassessment_count"), 1)
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        self.assertEqual(final.get("case_history_length"), 1)
        self.assertEqual(len(revised_case.get("case_history", [])), 1)

        prior = revised_case.get("case_history")[0]
        self.assertEqual(prior.get("iteration"), 0)
        self.assertEqual(prior.get("primary_diagnosis"), "Tomato___Late_blight")
        self.assertEqual(prior.get("assigned_severity"), "moderate")
        self.assertEqual(prior.get("trigger"), "weather_update")

    # -------------------------------------------------------------------------
    # Case 9: Insufficient or conflicting evidence does not invent certainty
    # -------------------------------------------------------------------------
    def test_case_09_conflicting_evidence_withholds_certainty(self):
        """Case 9: Conflicting field symptoms prevent autonomous chemical action and defer to human expert."""
        conflict_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9200,
                class_probabilities={"Tomato___Late_blight": 0.92, "Tomato___Early_blight": 0.05, "Tomato___Bacterial_spot": 0.03}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=10.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                field_notes="Leaf lesions exhibit dark concentric target rings and bullseye pattern."  # Early Blight morphology!
            )
        }
        res = self.app.invoke(conflict_state)

        # Must route to pending_manual_review
        self.assertEqual(res.get("workflow_status"), "pending_manual_review")
        final = res.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))
        self.assertEqual(final.get("assigned_severity"), "indeterminate")
        self.assertEqual(final.get("plan_urgency"), "deferred")
        self.assertEqual(final.get("manual_review_status"), "pending")

        plan = res.get("decision_plan")
        self.assertIsNotNone(plan)
        # Chemical guidance must be strictly withheld
        self.assertEqual(len(plan.chemical_controls), 0)
        self.assertTrue(plan.expert_review_required)

    # -------------------------------------------------------------------------
    # Case 10: Invalid input or component failure -> safe error handling
    # -------------------------------------------------------------------------
    def test_case_10_invalid_input_and_safe_error_handling(self):
        """Case 10: Invalid input paths, non-image files, and missing state contracts terminate safely in error."""
        # Subcase 10A: Nonexistent image path
        state_nonexistent: AgriMindState = {
            "image_path": "/nonexistent/test/path/nonexistent_tomato_leaf.jpg"
        }
        res_nonexistent = self.app.invoke(state_nonexistent)
        self.assertEqual(res_nonexistent.get("workflow_status"), "error")
        self.assertEqual(res_nonexistent.get("image_status"), "invalid")
        self.assertIn("not found", res_nonexistent.get("error_message", "").lower())

        # Subcase 10B: Non-image file (e.g. text file)
        state_text: AgriMindState = {
            "image_path": os.path.join(WORKSPACE_DIR, "docs", "data_preparation_proposal.md")
        }
        res_text = self.app.invoke(state_text)
        self.assertEqual(res_text.get("workflow_status"), "error")
        self.assertEqual(res_text.get("image_status"), "invalid")
        self.assertIn("unsupported or corrupted", res_text.get("error_message", "").lower())

        # Subcase 10C: Missing contract state in intermediate node
        empty_state: AgriMindState = {}
        res_empty = self.app.invoke(empty_state)
        self.assertEqual(res_empty.get("workflow_status"), "error")
        self.assertEqual(res_empty.get("image_status"), "missing")


if __name__ == "__main__":
    unittest.main()

