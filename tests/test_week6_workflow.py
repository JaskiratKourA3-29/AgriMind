"""
Unit and End-to-End Tests for AgriMind Week 6: LangGraph Orchestration and Workflow Integration.
Verifies state passing, conditional transitions, manual-review routing, error handling,
citation/pesticide notice retention, and actual-image smoke testing.
"""
import os
import unittest
from typing import Dict, Any

from src.workflow.state import AgriMindState
from src.workflow.graph import build_agrimind_workflow
from src.workflow.nodes import get_node_registry, set_node_registry, WorkflowNodeRegistry
from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    SeverityLevel,
    PlanUrgency,
    ReviewStatus,
    VerificationStatus,
    EvidenceStatus
)


SAMPLE_REAL_IMAGE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"


class TestWeek6Workflow(unittest.TestCase):
    """
    Test suite for Week 6 LangGraph multi-agent workflow.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = build_agrimind_workflow()

    def test_01_valid_workflow_end_to_end_verified_decision(self):
        """Verify a valid image fixture progresses through all nodes to a completed, verified decision."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9600,
                class_probabilities={"Tomato___Early_blight": 0.9600, "Tomato___Bacterial_spot": 0.02, "Tomato___Late_blight": 0.02}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=15.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy"
            )
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertTrue(final.get("is_verified"))
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Early_blight")
        self.assertEqual(final.get("assigned_severity"), "moderate")
        self.assertEqual(final.get("plan_urgency"), "moderate")
        self.assertGreater(len(final.get("citations", [])), 0)
        self.assertIsNotNone(final.get("pesticide_safety_notice"))

    def test_02_invalid_image_path_handling(self):
        """Verify invalid/missing image path aborts gracefully without throwing unhandled exceptions."""
        initial_state: AgriMindState = {
            "image_path": "/nonexistent/path/to/missing_leaf.jpg"
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("image_status"), "invalid")
        self.assertEqual(output.get("workflow_status"), "error")
        final = output.get("final_output", {})
        self.assertIn("not found", final.get("error_message", "").lower())
        self.assertFalse(final.get("is_verified"))

    def test_03_non_image_file_handling(self):
        """Verify non-image file is caught by header validation and aborts safely."""
        # Use an existing text file as input
        text_file = os.path.abspath("docs/week5_agent_logic_report.md")
        initial_state: AgriMindState = {
            "image_path": text_file
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("image_status"), "invalid")
        self.assertEqual(output.get("workflow_status"), "error")
        final = output.get("final_output", {})
        self.assertIn("unsupported or corrupted", final.get("error_message", "").lower())

    def test_04_insufficient_evidence_handling(self):
        """Verify insufficient literature evidence is flagged and routes to manual review."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9200
            ),
            "retrieved_evidence": RetrievedEvidence(
                has_sufficient_evidence=False,
                query="Unknown query",
                citations=[],
                fallback_message="Insufficient agricultural evidence."
            )
        }

        output = self.app.invoke(initial_state)

        # Insufficient literature triggers review routing
        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))
        self.assertEqual(final.get("manual_review_status"), "pending")

    def test_05_conflicting_diagnostic_evidence_routes_to_manual_review(self):
        """Verify symptom contradiction routes case to pending manual review with deferred guidance."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9100
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=20.0,
                field_notes="Concentric bullseye rings with yellow halo."  # Contradicts Late Blight
            )
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))
        self.assertEqual(final.get("plan_urgency"), "deferred")
        # Chemical advice must be withheld
        self.assertIsNone(final.get("pesticide_safety_notice"))

    def test_06_late_blight_urgent_escalation_in_workflow(self):
        """Verify Late Blight under conducive cool/wet weather escalates to CRITICAL urgency."""
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9850
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=12.0,
                canopy_spread="lower_canopy",
                weather_conditions="cool_wet",
                field_notes="White cottony sporulation on leaf undersides."
            )
        }

        output = self.app.invoke(initial_state)

        # Late Blight with sporulation is high risk and requires expert alert, routed to manual review
        final = output.get("final_output", {})
        self.assertEqual(final.get("assigned_severity"), "critical")
        self.assertEqual(final.get("plan_urgency"), "critical")
        self.assertTrue(final.get("is_verified"))
        self.assertIsNotNone(final.get("pesticide_safety_notice"))

    def test_07_critic_rejection_routes_to_manual_review(self):
        """Verify that a Critic verification failure transitions directly to manual review."""
        # Force a critic rejection by providing an unsupported disease that was misrouted
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Corn___Common_rust",  # Out of scope
                confidence=0.9500,
                is_supported_disease=False
            )
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))

    def test_08_manual_review_resolution_and_reentry(self):
        """Verify human expert correction re-enters workflow and successfully completes."""
        # Initial conflict state with expert correction provided
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.8800
            ),
            "visual_context": VisualContext(field_notes="Concentric bullseye rings."),
            # Human expert provides resolution
            "expert_diagnosis_override": "Tomato___Early_blight",
            "expert_context_override": VisualContext(
                leaf_damage_percentage=15.0,
                canopy_spread="lower_canopy",
                field_notes="Lab confirmed Alternaria solani."
            ),
            "expert_notes": "Diagnostic conflict resolved: confirmed Early Blight."
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertTrue(final.get("is_verified"))
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Early_blight")
        self.assertEqual(final.get("manual_review_status"), "approved")

    def test_09_manual_review_bounded_retry_terminal_escalation(self):
        """Verify bounded review iteration ceiling prevents infinite loops and reaches terminal escalation."""
        # State with review record already at iteration ceiling
        from src.agents.schemas import ManualReviewRecord
        import uuid
        from datetime import datetime, timezone

        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.8500
            ),
            "visual_context": VisualContext(field_notes="Concentric bullseye rings."),
            "manual_review_record": ManualReviewRecord(
                review_id=f"REV-{uuid.uuid4().hex[:8].upper()}",
                investigation_id="INV-TEST",
                flagged_by="InvestigationAgent",
                trigger_reasons=["Persistent conflict"],
                status=ReviewStatus.PENDING,
                iteration_count=2,  # Already at ceiling
                max_iterations=2,
                submission_timestamp=datetime.now(timezone.utc).isoformat()
            ),
            "expert_notes": "Unresolvable in field."
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "terminal_escalation")
        final = output.get("final_output", {})
        self.assertEqual(final.get("manual_review_status"), "terminal_escalation")
        self.assertIn("escalat", final.get("error_message", "").lower())

    def test_10_real_sample_image_actual_model_smoke_test(self):
        """Smoke test executing end-to-end workflow with an ACTUAL PlantVillage image and trained ResNet-50."""
        self.assertTrue(os.path.exists(SAMPLE_REAL_IMAGE), f"Sample image must exist: {SAMPLE_REAL_IMAGE}")

        # Run with zero mock predictions: ResNet-50 model will classify the actual image!
        initial_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "visual_context": VisualContext(
                leaf_damage_percentage=8.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy"
            )
        }

        output = self.app.invoke(initial_state)

        # 1. Vision prediction was genuinely executed by the ResNet-50 baseline
        vision_pred = output.get("vision_prediction")
        self.assertIsNotNone(vision_pred)
        self.assertEqual(vision_pred.predicted_class, "Tomato___Bacterial_spot")
        self.assertGreater(vision_pred.confidence, 0.90)

        # 2. Entire workflow succeeded through to final output
        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Bacterial_spot")
        self.assertTrue(final.get("is_verified"))
        self.assertGreater(len(final.get("citations", [])), 0)
        self.assertIsNotNone(final.get("pesticide_safety_notice"))


if __name__ == "__main__":
    unittest.main()
