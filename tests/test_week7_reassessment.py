"""
Automated Isolated Unit and Integration Tests for AgriMind Week 7:
Adaptive Reassessment Mechanism Implementation.
Verifies all 4 triggers, missing/invalid evidence rejection, context preservation,
history tracking, the 2-iteration loop ceiling, decision revisions, and backward compatibility.
"""
import os
import sys
import unittest
from typing import Dict, Any

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.workflow.state import AgriMindState
from src.workflow.graph import build_agrimind_workflow
from src.workflow.nodes import reassess_case
from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    ReassessmentTrigger,
    ReassessmentOutcome,
    ReassessmentRecord,
    SeverityLevel,
    PlanUrgency
)

SAMPLE_REAL_IMAGE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"


class TestWeek7Reassessment(unittest.TestCase):
    """
    Test suite for Week 7 Adaptive Reassessment Mechanism.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = build_agrimind_workflow()

    def _create_initial_completed_case(
        self,
        disease: str = "Tomato___Late_blight",
        damage: float = 3.0,
        weather: str = "mild_overcast"
    ) -> AgriMindState:
        """Helper to run and produce an initial verified completed case state."""
        probs = {
            "Tomato___Bacterial_spot": 0.02,
            "Tomato___Early_blight": 0.02,
            "Tomato___Late_blight": 0.02
        }
        probs[disease] = 0.9600

        initial_state: AgriMindState = {
            "case_id": "CASE-LB-TEST-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class=disease,
                confidence=0.9600,
                class_probabilities=probs
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=damage,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                weather_conditions=weather
            )
        }
        return self.app.invoke(initial_state)

    def test_01_trigger_weather_update_revises_decision(self):
        """
        Verify WEATHER_UPDATE trigger adaptively escalates Late Blight risk
        when weather shifts from mild_overcast to cool_wet.
        """
        initial_case = self._create_initial_completed_case(
            disease="Tomato___Late_blight",
            damage=3.0,
            weather="mild_overcast"
        )
        self.assertEqual(initial_case.get("workflow_status"), "completed")
        initial_sev = initial_case.get("final_output", {}).get("assigned_severity")
        self.assertEqual(initial_sev, "moderate")  # < 5% damage under non-conducive mild weather = moderate for LB

        # Reassess with sudden cool/wet weather (conducive to epidemic sporulation)
        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=initial_case,
            trigger=ReassessmentTrigger.WEATHER_UPDATE,
            new_evidence={"weather_conditions": "cool_wet", "leaf_damage_percentage": 12.0},
            rationale="Heavy rain event followed by temperatures dropping to 65F."
        )

        self.assertIn(revised_case.get("workflow_status"), ["completed", "pending_manual_review"])
        self.assertEqual(revised_case.get("reassessment_status"), "revised")
        final = revised_case.get("final_output", {})
        self.assertTrue(final.get("is_verified"))
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        self.assertEqual(final.get("reassessment_count"), 1)
        self.assertEqual(final.get("case_history_length"), 1)

        # Severity should escalate to critical due to cool_wet + damage >= 5%
        self.assertEqual(final.get("assigned_severity"), "critical")
        self.assertEqual(final.get("plan_urgency"), "critical")

        # Verify audit record
        records = revised_case.get("reassessment_records", [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].trigger, ReassessmentTrigger.WEATHER_UPDATE)
        self.assertEqual(records[0].prior_severity, "moderate")
        self.assertEqual(records[0].revised_severity, "critical")
        self.assertEqual(records[0].outcome, ReassessmentOutcome.REVISED)

    def test_02_trigger_new_field_observation_updates_damage(self):
        """
        Verify NEW_FIELD_OBSERVATION updates foliar damage % and canopy spread.
        """
        initial_case = self._create_initial_completed_case(
            disease="Tomato___Early_blight",
            damage=8.0,
            weather="mild_overcast"
        )
        initial_sev = initial_case.get("final_output", {}).get("assigned_severity")
        self.assertEqual(initial_sev, "low")  # < 10% damage for EB = low

        # Reassess with updated field scouting: damage increased to 38% progressing upward
        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=initial_case,
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={"leaf_damage_percentage": 38.0, "canopy_spread": "upper_canopy"}
        )

        final = revised_case.get("final_output", {})
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        self.assertEqual(final.get("assigned_severity"), "high")
        self.assertEqual(final.get("reassessment_count"), 1)

    def test_03_trigger_lab_diagnostic_update_overrides_pathogen(self):
        """
        Verify LAB_DIAGNOSTIC_UPDATE updates diagnosis to lab-confirmed pathogen with 1.0 confidence.
        """
        initial_case = self._create_initial_completed_case(
            disease="Tomato___Bacterial_spot",
            damage=10.0,
            weather="mild_overcast"
        )
        self.assertEqual(initial_case.get("final_output", {}).get("primary_diagnosis"), "Tomato___Bacterial_spot")

        # Lab microscopic examination confirms Late Blight oospores/conidia
        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=initial_case,
            trigger=ReassessmentTrigger.LAB_DIAGNOSTIC_UPDATE,
            new_evidence={"lab_confirmed_disease": "Tomato___Late_blight"},
            rationale="University Plant Disease Diagnostic Clinic PCR confirmation."
        )

        final = revised_case.get("final_output", {})
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Late_blight")
        self.assertEqual(final.get("diagnosis_confidence"), 1.0)
        self.assertEqual(final.get("reassessment_outcome"), "revised")

    def test_04_trigger_treatment_ineffective_appends_alert(self):
        """
        Verify TREATMENT_INEFFECTIVE notes ongoing symptoms and refreshes IPM recommendations.
        """
        initial_case = self._create_initial_completed_case(
            disease="Tomato___Early_blight",
            damage=15.0,
            weather="mild_overcast"
        )

        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=initial_case,
            trigger=ReassessmentTrigger.TREATMENT_INEFFECTIVE,
            new_evidence={
                "treatment_notes": "Chlorothalonil application 7 days ago failed to arrest lesion spread",
                "leaf_damage_percentage": 25.0
            }
        )

        final = revised_case.get("final_output", {})
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        # Field context should record treatment alert
        updated_context = revised_case.get("visual_context")
        self.assertIn("Treatment alert", updated_context.field_notes)

    def test_05_missing_or_empty_new_evidence_rejected(self):
        """
        Verify reassessment request with empty new evidence is safely rejected with error.
        """
        initial_case = self._create_initial_completed_case()

        bad_state = dict(initial_case)
        bad_state["reassessment_trigger"] = "weather_update"
        bad_state["reassessment_new_evidence"] = {}  # Empty dictionary!

        result = self.app.invoke(bad_state)

        self.assertEqual(result.get("workflow_status"), "error")
        self.assertEqual(result.get("reassessment_status"), "unresolved")
        self.assertIn("non-empty dictionary", result.get("error_message", ""))

    def test_06_invalid_trigger_rejected(self):
        """
        Verify invalid reassessment trigger string is rejected cleanly.
        """
        initial_case = self._create_initial_completed_case()

        bad_state = dict(initial_case)
        bad_state["reassessment_trigger"] = "unsupported_alien_trigger"
        bad_state["reassessment_new_evidence"] = {"leaf_damage_percentage": 20.0}

        result = self.app.invoke(bad_state)

        self.assertEqual(result.get("workflow_status"), "error")
        self.assertIn("Invalid trigger", result.get("error_message", ""))

    def test_07_loop_prevention_two_iteration_ceiling(self):
        """
        Verify strict enforcement of the maximum 2-iteration reassessment ceiling.
        Cycle 1 -> Allowed.
        Cycle 2 -> Allowed.
        Cycle 3 -> Terminal escalation to diagnostic clinic, halting infinite loops.
        """
        initial_case = self._create_initial_completed_case()

        # Reassessment Cycle 1
        case_v1 = reassess_case(
            self.app,
            initial_case,
            trigger=ReassessmentTrigger.WEATHER_UPDATE,
            new_evidence={"weather_conditions": "cool_wet", "leaf_damage_percentage": 10.0}
        )
        self.assertEqual(case_v1.get("reassessment_count"), 1)
        self.assertEqual(case_v1.get("reassessment_status"), "revised")

        # Reassessment Cycle 2
        case_v2 = reassess_case(
            self.app,
            case_v1,
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={"canopy_spread": "whole_plant", "leaf_damage_percentage": 30.0}
        )
        self.assertEqual(case_v2.get("reassessment_count"), 2)
        self.assertEqual(case_v2.get("reassessment_status"), "revised")

        # Reassessment Cycle 3 (Exceeds maximum ceiling of 2)
        case_v3 = reassess_case(
            self.app,
            case_v2,
            trigger=ReassessmentTrigger.TREATMENT_INEFFECTIVE,
            new_evidence={"treatment_notes": "Copper spray failed."}
        )

        self.assertEqual(case_v3.get("workflow_status"), "terminal_escalation")
        self.assertEqual(case_v3.get("reassessment_status"), "escalated")
        self.assertIn("Maximum reassessment limit (2) exceeded", case_v3.get("error_message"))

        # Verify terminal record created
        records = case_v3.get("reassessment_records", [])
        self.assertEqual(len(records), 3)
        self.assertTrue(records[-1].is_terminal)
        self.assertEqual(records[-1].outcome, ReassessmentOutcome.ESCALATED)

    def test_08_context_and_history_preservation_across_cycles(self):
        """
        Verify case_history accurately snapshots and preserves state across multiple iterations.
        """
        initial_case = self._create_initial_completed_case(
            disease="Tomato___Late_blight",
            damage=2.0,
            weather="mild_overcast"
        )

        case_v1 = reassess_case(
            self.app,
            initial_case,
            trigger=ReassessmentTrigger.WEATHER_UPDATE,
            new_evidence={"weather_conditions": "cool_wet", "leaf_damage_percentage": 15.0}
        )

        case_history = case_v1.get("case_history", [])
        self.assertEqual(len(case_history), 1)
        snap0 = case_history[0]
        self.assertEqual(snap0.get("iteration"), 0)
        self.assertEqual(snap0.get("primary_diagnosis"), "Tomato___Late_blight")
        self.assertEqual(snap0.get("assigned_severity"), "moderate")
        self.assertEqual(snap0.get("visual_context", {}).get("weather_conditions"), "mild_overcast")
        self.assertEqual(snap0.get("trigger"), "weather_update")

    def test_09_initial_workflow_backward_compatibility(self):
        """
        Verify standard initial investigation workflow remains 100% functional
        when reassessment_trigger is None.
        """
        clean_state: AgriMindState = {
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9200,
                class_probabilities={"Tomato___Early_blight": 0.9200, "Tomato___Bacterial_spot": 0.05, "Tomato___Late_blight": 0.03}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=12.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy"
            )
        }

        output = self.app.invoke(clean_state)
        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertTrue(final.get("is_verified"))
        self.assertEqual(final.get("reassessment_count"), 0)
        self.assertEqual(final.get("reassessment_outcome"), "none")

    def test_10_reassessment_record_schema_validation(self):
        """
        Verify ReassessmentRecord validation helper rules.
        """
        # Valid
        errs = ReassessmentRecord.validate_reassessment_payload(
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={"leaf_damage_percentage": 10.0},
            current_count=0,
            max_reassessments=2
        )
        self.assertEqual(len(errs), 0)

        # Missing trigger
        errs = ReassessmentRecord.validate_reassessment_payload(
            trigger=None,
            new_evidence={"leaf_damage_percentage": 10.0},
            current_count=0
        )
        self.assertIn("trigger is required", errs[0])

        # Empty evidence
        errs = ReassessmentRecord.validate_reassessment_payload(
            trigger="weather_update",
            new_evidence={},
            current_count=0
        )
        self.assertIn("non-empty dictionary", errs[0])

        # Exceeded limit
        errs = ReassessmentRecord.validate_reassessment_payload(
            trigger="weather_update",
            new_evidence={"leaf_damage_percentage": 10.0},
            current_count=2,
            max_reassessments=2
        )
        self.assertIn("Maximum reassessment limit", errs[0])


if __name__ == "__main__":
    unittest.main()
