"""
Unit and End-to-End Integration Tests for AgriMind Week 10:
End-to-End Workflow Reliability & Integration Evaluation.

Evaluates workflow transitions, state schema preservation, conflict deferrals,
low confidence handling, Critic rejections, runtime exceptions, adaptive reassessment,
reassessment iteration ceilings, terminal-state integrity, and Week 8 visual CNN limitations.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.workflow.state import AgriMindState
from src.workflow.graph import build_agrimind_workflow, route_after_critic
from src.workflow.nodes import (
    get_node_registry,
    set_node_registry,
    WorkflowNodeRegistry,
    reassess_case,
    retrieval_node,
    investigation_node,
    risk_assessment_node,
    decision_planning_node,
    critic_node
)
from src.agents.decision_planning import DecisionPlanningAgent
from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    ManagementAction,
    VerificationResult,
    ManualReviewRecord,
    SeverityLevel,
    PlanUrgency,
    EvidenceStatus,
    VerificationStatus,
    ReviewStatus,
    ReassessmentTrigger,
    ReassessmentOutcome,
    ReassessmentRecord
)

SAMPLE_REAL_IMAGE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"


class TestWeek10WorkflowIntegration(unittest.TestCase):
    """
    Comprehensive Week 10 evaluation test suite for AgriMind multi-agent workflow integration.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = build_agrimind_workflow()

    # -------------------------------------------------------------------------
    # Scenario 1: Normal Workflow End-to-End Execution
    # -------------------------------------------------------------------------
    def test_01_normal_workflow_end_to_end_verified_completion(self):
        """
        Scenario 1: Normal workflow with valid evidence proceeds through all stages
        and terminates with workflow_status='completed' and is_verified=True.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-NORM-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9650,
                class_probabilities={
                    "Tomato___Early_blight": 0.9650,
                    "Tomato___Bacterial_spot": 0.0200,
                    "Tomato___Late_blight": 0.0150
                }
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=15.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                weather_conditions="mild_warm"
            )
        }

        output = self.app.invoke(initial_state)

        # Terminal state assertions
        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertIn(final.get("workflow_status"), ["completed", "verified"])
        self.assertTrue(final.get("is_verified"))
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Early_blight")
        self.assertEqual(final.get("assigned_severity"), "moderate")
        self.assertEqual(final.get("plan_urgency"), "moderate")
        self.assertFalse(final.get("requires_manual_review"))
        self.assertGreater(len(final.get("citations", [])), 0)
        self.assertIsNotNone(final.get("pesticide_safety_notice"))
        self.assertIsNone(output.get("error_message"))

    # -------------------------------------------------------------------------
    # Scenario 2: Conflicting Diagnostic Evidence Handling
    # -------------------------------------------------------------------------
    def test_02_conflicting_diagnostic_symptoms_withholds_chemicals(self):
        """
        Scenario 2: When field observations directly contradict visual classification,
        the workflow must flag CONFLICTING evidence, set DEFERRED urgency, withhold all chemical
        recommendations (0 chemical controls, no pesticide notice), and route to pending manual review.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-CONFLICT-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9400,
                class_probabilities={"Tomato___Late_blight": 0.94, "Tomato___Early_blight": 0.06}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=22.0,
                field_notes="Concentric bullseye rings with dark target-like halos on lower foliage."
            )
        }

        output = self.app.invoke(initial_state)

        # Must route to pending_manual_review
        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))
        self.assertEqual(final.get("plan_urgency"), "deferred")
        self.assertEqual(final.get("manual_review_status"), "pending")

        # Crucial safety invariants: chemical advice must be withheld
        plan: DecisionPlan = output.get("decision_plan")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.chemical_controls), 0)
        self.assertIsNone(final.get("pesticide_safety_notice"))
        self.assertTrue(plan.expert_review_required)

        # Investigation result must record the diagnostic discrepancy
        inv: InvestigationResult = output.get("investigation_result")
        self.assertEqual(inv.evidence_status, EvidenceStatus.CONFLICTING)
        self.assertGreater(len(inv.conflicts_detected), 0)

    # -------------------------------------------------------------------------
    # Scenario 3: Low-Confidence and Ambiguous Vision Result
    # -------------------------------------------------------------------------
    def test_03a_low_confidence_vision_routes_to_deferred_review(self):
        """
        Scenario 3A: When visual prediction confidence is low (< 0.60), the workflow
        must detect evidence conflict, assign INDETERMINATE severity, and defer management.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-LOWCONF-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.5200,
                class_probabilities={
                    "Tomato___Early_blight": 0.5200,
                    "Tomato___Late_blight": 0.3500,
                    "Tomato___Bacterial_spot": 0.1300
                }
            ),
            "visual_context": VisualContext(leaf_damage_percentage=10.0)
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertEqual(final.get("plan_urgency"), "deferred")
        self.assertTrue(final.get("requires_manual_review"))

        inv: InvestigationResult = output.get("investigation_result")
        self.assertEqual(inv.evidence_status, EvidenceStatus.CONFLICTING)
        self.assertTrue(any("low model classification confidence" in c.lower() for c in inv.conflicts_detected))

    def test_03b_inadequate_class_margin_routes_to_deferred_review(self):
        """
        Scenario 3B: When top two predicted class probabilities are separated by < 0.15 margin,
        multi-class distribution ambiguity must be flagged, routing the case to review.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-MARGIN-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.4800,
                class_probabilities={
                    "Tomato___Early_blight": 0.4800,
                    "Tomato___Late_blight": 0.4200,
                    "Tomato___Bacterial_spot": 0.1000
                }
            ),
            "visual_context": VisualContext(leaf_damage_percentage=8.0)
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        inv: InvestigationResult = output.get("investigation_result")
        self.assertEqual(inv.evidence_status, EvidenceStatus.CONFLICTING)
        self.assertTrue(any("ambiguous classification margin" in c.lower() for c in inv.conflicts_detected))

    # -------------------------------------------------------------------------
    # Scenario 4: Unsupported Disease Scope and Insufficient Literature
    # -------------------------------------------------------------------------
    def test_04a_unsupported_disease_scope_routes_to_expert_review(self):
        """
        Scenario 4A: When classification predicts an out-of-scope pathogen,
        the workflow must flag UNSUPPORTED_DISEASE, withhold chemicals, and defer to lab review.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-UNSUPPORTED-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Tomato_Yellow_Leaf_Curl_Virus",
                confidence=0.9800,
                is_supported_disease=False
            ),
            "visual_context": VisualContext(leaf_damage_percentage=15.0)
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertEqual(final.get("plan_urgency"), "deferred")
        self.assertTrue(final.get("requires_manual_review"))

        inv: InvestigationResult = output.get("investigation_result")
        self.assertEqual(inv.evidence_status, EvidenceStatus.UNSUPPORTED_DISEASE)
        plan: DecisionPlan = output.get("decision_plan")
        self.assertEqual(len(plan.chemical_controls), 0)

    def test_04b_insufficient_literature_evidence_routes_to_review(self):
        """
        Scenario 4B: When RAG retrieval returns insufficient peer-reviewed literature,
        the workflow must flag INSUFFICIENT_LITERATURE and route to manual review.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-NOLIT-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",
                confidence=0.9100
            ),
            "retrieved_evidence": RetrievedEvidence(
                has_sufficient_evidence=False,
                query="Rare exotic tomato pathogen",
                citations=[],
                fallback_message="No peer-reviewed extension documents found."
            )
        }

        output = self.app.invoke(initial_state)

        self.assertEqual(output.get("workflow_status"), "pending_manual_review")
        final = output.get("final_output", {})
        self.assertTrue(final.get("requires_manual_review"))
        inv: InvestigationResult = output.get("investigation_result")
        self.assertEqual(inv.evidence_status, EvidenceStatus.INSUFFICIENT_LITERATURE)

    # -------------------------------------------------------------------------
    # Scenario 5: Critic Rejection Routing
    # -------------------------------------------------------------------------
    def test_05_critic_rejection_routes_through_manual_review(self):
        """
        Scenario 5: When Critic rejects an unsafe or unverified decision plan,
        the workflow must transition through manual_review and terminate in pending_manual_review
        with is_verified=False and rejection reasons populated.
        """
        registry = get_node_registry()
        original_planner = registry.decision_planner

        # Create a mock planner that injects an unsafe active ingredient into the plan
        class FlawedPlanner(DecisionPlanningAgent):
            def plan_decision(self, investigation, risk):
                plan = original_planner.plan_decision(investigation, risk)
                # Inject unverified active ingredient
                unsafe_action = ManagementAction(
                    category="chemical",
                    action_summary="Spray unverified experimental systemic propiconazole",
                    details="Apply propiconazole at 1 pint per acre.",
                    is_chemical=True,
                    citation_numbers=[1]
                )
                return plan.model_copy(update={"chemical_controls": [unsafe_action]})

        registry.decision_planner = FlawedPlanner()
        try:
            initial_state: AgriMindState = {
                "case_id": "CASE-REJECT-001",
                "image_path": SAMPLE_REAL_IMAGE,
                "vision_prediction": VisionPrediction(
                    predicted_class="Tomato___Early_blight",
                    confidence=0.9500
                ),
                "visual_context": VisualContext(leaf_damage_percentage=12.0)
            }

            output = self.app.invoke(initial_state)

            self.assertEqual(output.get("workflow_status"), "pending_manual_review")
            final = output.get("final_output", {})
            self.assertFalse(final.get("is_verified"))
            self.assertEqual(final.get("verification_status"), "rejected_unsupported_claims")
            self.assertTrue(final.get("requires_manual_review"))

            verif: VerificationResult = output.get("verification_result")
            self.assertFalse(verif.is_verified)
            self.assertIn("propiconazole", str(verif.issues_detected).lower())
        finally:
            registry.decision_planner = original_planner

    # -------------------------------------------------------------------------
    # Scenario 6: Critic Exception Handling in Workflow
    # -------------------------------------------------------------------------
    def test_06_critic_runtime_exception_aborts_to_error_terminal_state(self):
        """
        Scenario 6: When CriticAgent raises an unexpected unhandled exception,
        the workflow must handle it gracefully, transition to error state,
        and preserve the original diagnostic error message in final_output.
        """
        registry = get_node_registry()
        original_critic = registry.critic_agent

        mock_critic = MagicMock()
        mock_critic.verify_plan.side_effect = RuntimeError("Simulated Critic out-of-memory fault")
        registry.critic_agent = mock_critic

        try:
            initial_state: AgriMindState = {
                "case_id": "CASE-CRITIC-ERR-001",
                "image_path": SAMPLE_REAL_IMAGE,
                "vision_prediction": VisionPrediction(
                    predicted_class="Tomato___Early_blight",
                    confidence=0.9500
                ),
                "visual_context": VisualContext(leaf_damage_percentage=10.0)
            }

            output = self.app.invoke(initial_state)

            # Workflow must terminate with error status and preserve Critic's exception message
            self.assertEqual(output.get("workflow_status"), "error")
            final = output.get("final_output", {})
            self.assertEqual(final.get("workflow_status"), "error")
            self.assertFalse(final.get("is_verified"))
            self.assertIn("critic verification agent failed", final.get("error_message", "").lower())
            self.assertIn("simulated critic out-of-memory fault", final.get("error_message", "").lower())
        finally:
            registry.critic_agent = original_critic

    # -------------------------------------------------------------------------
    # Scenario 7: Adaptive Reassessment Mechanism
    # -------------------------------------------------------------------------
    def test_07_adaptive_reassessment_updates_case_and_preserves_history(self):
        """
        Scenario 7: Supported reassessment trigger (WEATHER_UPDATE) updates the case correctly,
        escalates Late Blight severity to critical, and preserves prior decision snapshot in case_history.
        """
        # Step 1: Run initial mild Late Blight case
        initial_state: AgriMindState = {
            "case_id": "CASE-ADAPT-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9600,
                class_probabilities={"Tomato___Late_blight": 0.96, "Tomato___Early_blight": 0.04}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=3.0,
                canopy_spread="lower_canopy",
                weather_conditions="mild_overcast"
            )
        }
        case1 = self.app.invoke(initial_state)
        self.assertEqual(case1.get("workflow_status"), "completed")
        self.assertEqual(case1.get("final_output", {}).get("assigned_severity"), "moderate")

        # Step 2: Trigger WEATHER_UPDATE reassessment with cool_wet weather and increased damage
        revised_case = reassess_case(
            workflow_app=self.app,
            completed_state=case1,
            trigger=ReassessmentTrigger.WEATHER_UPDATE,
            new_evidence={"weather_conditions": "cool_wet", "leaf_damage_percentage": 10.0},
            rationale="Sudden cold rainstorm overnight."
        )

        final = revised_case.get("final_output", {})
        self.assertEqual(final.get("reassessment_count"), 1)
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        self.assertEqual(final.get("assigned_severity"), "critical")
        self.assertEqual(final.get("plan_urgency"), "critical")

        # State history assertions
        history = revised_case.get("case_history", [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["assigned_severity"], "moderate")
        self.assertEqual(history[0]["trigger"], "weather_update")

        records = revised_case.get("reassessment_records", [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].trigger, ReassessmentTrigger.WEATHER_UPDATE)
        self.assertEqual(records[0].outcome, ReassessmentOutcome.REVISED)

    # -------------------------------------------------------------------------
    # Scenario 8: Repeated Reassessment Loop Ceiling Enforcement
    # -------------------------------------------------------------------------
    def test_08_repeated_reassessment_enforces_ceiling_terminal_escalation(self):
        """
        Scenario 8: When reassessment count reaches the configured limit (max 2),
        a subsequent reassessment attempt must be blocked and transition permanently
        to workflow_status='terminal_escalation' with an audit record marked is_terminal=True.
        """
        # Build a completed case that has already undergone 2 reassessments
        prior_state: AgriMindState = {
            "case_id": "CASE-CEILING-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "workflow_status": "completed",
            "reassessment_count": 2,
            "max_reassessments": 2,
            "case_history": [{"iteration": 0}, {"iteration": 1}],
            "reassessment_records": [],
            "vision_prediction": VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.90),
            "visual_context": VisualContext(leaf_damage_percentage=15.0)
        }

        # Attempt 3rd reassessment (exceeding limit)
        escalated_case = reassess_case(
            workflow_app=self.app,
            completed_state=prior_state,
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={"leaf_damage_percentage": 45.0},
            rationale="Attempting 3rd automated reassessment"
        )

        self.assertEqual(escalated_case.get("workflow_status"), "terminal_escalation")
        self.assertEqual(escalated_case.get("reassessment_status"), "escalated")
        final = escalated_case.get("final_output", {})
        self.assertEqual(final.get("workflow_status"), "terminal_escalation")
        self.assertIn("maximum reassessment limit (2) exceeded", final.get("error_message", "").lower())

        # Audit record verification
        records = escalated_case.get("reassessment_records", [])
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].is_terminal)
        self.assertEqual(records[0].outcome, ReassessmentOutcome.ESCALATED)

    # -------------------------------------------------------------------------
    # Scenario 9: Reassessment with Conflicting Evidence
    # -------------------------------------------------------------------------
    def test_09_reassessment_with_conflicting_evidence_requires_expert_review(self):
        """
        Scenario 9: If new evidence during reassessment introduces a diagnostic conflict
        (e.g. concentric target rings reported on suspected Late Blight),
        the workflow must withhold chemical actions, set urgency to DEFERRED, and route to
        pending_manual_review requiring human expert examination.
        """
        # Step 1: Initial Late Blight case under mild weather
        initial_state: AgriMindState = {
            "case_id": "CASE-REASSESS-CONF-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",
                confidence=0.9500
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=4.0,
                canopy_spread="lower_canopy",
                weather_conditions="mild_overcast"
            )
        }
        case1 = self.app.invoke(initial_state)
        self.assertEqual(case1.get("workflow_status"), "completed")

        # Step 2: Reassess with field scouting notes describing concentric target rings (Early Blight symptoms)
        reassessed = reassess_case(
            workflow_app=self.app,
            completed_state=case1,
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={
                "leaf_damage_percentage": 20.0,
                "field_notes": "Concentric bullseye rings with target halos on lower canopy foliage."
            }
        )

        self.assertEqual(reassessed.get("workflow_status"), "pending_manual_review")
        final = reassessed.get("final_output", {})
        self.assertEqual(final.get("plan_urgency"), "deferred")
        self.assertTrue(final.get("requires_manual_review"))

        # Chemical recommendations must be withheld
        plan: DecisionPlan = reassessed.get("decision_plan")
        self.assertEqual(len(plan.chemical_controls), 0)
        self.assertIsNone(final.get("pesticide_safety_notice"))

        records = reassessed.get("reassessment_records", [])
        self.assertEqual(len(records), 1)

    # -------------------------------------------------------------------------
    # Scenario 10: State and History Integrity Preservation
    # -------------------------------------------------------------------------
    def test_10_state_and_history_integrity_preservation(self):
        """
        Scenario 10: Verifies schema integrity across reassessment cycles. Confirms that
        case_id, original evidence, prior severity/urgency, and audit records conform to typed schemas.
        """
        initial_state: AgriMindState = {
            "case_id": "CASE-INTEG-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Bacterial_spot",
                confidence=0.9700
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=5.0,
                affected_organs=["leaves"],
                canopy_spread="lower_canopy",
                weather_conditions="warm_dry"
            )
        }
        case1 = self.app.invoke(initial_state)

        reassessed = reassess_case(
            workflow_app=self.app,
            completed_state=case1,
            trigger=ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            new_evidence={"leaf_damage_percentage": 25.0, "canopy_spread": "mid_canopy"}
        )

        # Schema and attribute type checks
        self.assertEqual(reassessed.get("case_id"), "CASE-INTEG-001")
        history = reassessed.get("case_history", [])
        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 1)
        self.assertIn("iteration", history[0])
        self.assertIn("primary_diagnosis", history[0])
        self.assertIn("assigned_severity", history[0])
        self.assertIn("plan_urgency", history[0])
        self.assertIn("timestamp", history[0])

        records = reassessed.get("reassessment_records", [])
        self.assertIsInstance(records, list)
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], ReassessmentRecord)
        self.assertTrue(records[0].reassessment_id.startswith("REASSESS-"))
        self.assertEqual(records[0].prior_severity, "low")
        self.assertEqual(records[0].revised_severity, "moderate")

    # -------------------------------------------------------------------------
    # Scenario 11: Malformed and Incomplete State Handling
    # -------------------------------------------------------------------------
    def test_11a_malformed_image_paths_handled_gracefully(self):
        """
        Scenario 11A: Workflow handles empty, missing, nonexistent, and non-image files
        gracefully without unhandled crashes.
        """
        # Empty path
        res_empty = self.app.invoke({"image_path": ""})
        self.assertEqual(res_empty.get("workflow_status"), "error")
        self.assertEqual(res_empty.get("image_status"), "missing")

        # Nonexistent path
        res_missing = self.app.invoke({"image_path": "/nonexistent/fake_leaf.jpg"})
        self.assertEqual(res_missing.get("workflow_status"), "error")
        self.assertEqual(res_missing.get("image_status"), "invalid")

        # Non-image file (README.md)
        text_file = os.path.abspath("README.md")
        res_nonimg = self.app.invoke({"image_path": text_file})
        self.assertEqual(res_nonimg.get("workflow_status"), "error")
        self.assertEqual(res_nonimg.get("image_status"), "invalid")

    def test_11b_intermediate_nodes_missing_state_contracts_abort_safely(self):
        """
        Scenario 11B: Intermediate nodes safely return workflow_status='error'
        when invoked with states missing required prerequisite inputs.
        """
        # retrieval_node missing vision_prediction
        ret_out = retrieval_node({"image_status": "valid"})
        self.assertEqual(ret_out.get("workflow_status"), "error")

        # investigation_node missing retrieved_evidence
        inv_out = investigation_node({"vision_prediction": VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.9)})
        self.assertEqual(inv_out.get("workflow_status"), "error")

        # risk_assessment_node missing investigation_result
        rsk_out = risk_assessment_node({})
        self.assertEqual(rsk_out.get("workflow_status"), "error")

        # decision_planning_node missing risk_assessment
        dec_out = decision_planning_node({})
        self.assertEqual(dec_out.get("workflow_status"), "error")

        # critic_node missing decision_plan
        crt_out = critic_node({})
        self.assertEqual(crt_out.get("workflow_status"), "error")

    # -------------------------------------------------------------------------
    # Scenario 12: Terminal-State Integrity and Mutual Exclusivity
    # -------------------------------------------------------------------------
    def test_12_terminal_state_integrity_and_mutual_exclusivity(self):
        """
        Scenario 12: Verifies that terminal states ('completed', 'pending_manual_review',
        'terminal_escalation', 'error') have distinct, non-overlapping property invariants.
        """
        # 1. 'completed' state
        comp_state = self.app.invoke({
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.95),
            "visual_context": VisualContext(leaf_damage_percentage=5.0)
        })
        self.assertEqual(comp_state.get("workflow_status"), "completed")
        self.assertTrue(comp_state.get("final_output", {}).get("is_verified"))
        self.assertFalse(comp_state.get("final_output", {}).get("requires_manual_review"))

        # 2. 'pending_manual_review' state (via conflict)
        review_state = self.app.invoke({
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.95),
            "visual_context": VisualContext(leaf_damage_percentage=10.0, field_notes="Target bullseye spots.")
        })
        self.assertEqual(review_state.get("workflow_status"), "pending_manual_review")
        self.assertTrue(review_state.get("final_output", {}).get("requires_manual_review"))

        # 3. 'error' state
        err_state = self.app.invoke({"image_path": ""})
        self.assertEqual(err_state.get("workflow_status"), "error")
        self.assertFalse(err_state.get("final_output", {}).get("is_verified"))
        self.assertIsNotNone(err_state.get("final_output", {}).get("error_message"))

    # -------------------------------------------------------------------------
    # Scenario 13: Week 8 Visual Misclassification Limitation & Recovery
    # -------------------------------------------------------------------------
    def test_13a_week8_vision_limitation_uncontradicted_misclassification(self):
        """
        Scenario 13A: When ResNet-50 visual model misclassifies a Bacterial Spot sample
        as Early Blight with 0.9999 confidence and no field notes contradict it,
        the workflow accepts the prediction as verified Early Blight.
        Demonstrates the documented boundary that downstream agents cannot detect visual errors
        without independent external evidence.
        """
        # Simulates Week 8 PlantDoc Bacterial Spot sample misclassified as Early Blight
        synthetic_misclassification: AgriMindState = {
            "case_id": "CASE-WK8-MISCLASS-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Early_blight",  # True Ground Truth: Bacterial Spot
                confidence=0.9999,
                class_probabilities={"Tomato___Early_blight": 0.9999, "Tomato___Bacterial_spot": 0.0001}
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=10.0,
                canopy_spread="lower_canopy"
                # No grower notes to contradict
            )
        }

        output = self.app.invoke(synthetic_misclassification)

        # System faithfully accepts the overconfident prediction because evidence is internally consistent
        self.assertEqual(output.get("workflow_status"), "completed")
        final = output.get("final_output", {})
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Early_blight")
        self.assertTrue(final.get("is_verified"))

    def test_13b_week8_vision_limitation_resolved_by_scouting_and_lab_reassessment(self):
        """
        Scenario 13B: Simulates Week 8 sample SMPL-00011 (true Bacterial Spot misclassified as Late Blight).
        When grower provides field observations reporting hot/dry weather (>30C) or concentric rings,
        the Investigation Agent catches the epidemiological discrepancy, withholds chemical advice, and defers.
        Subsequent LAB_DIAGNOSTIC_UPDATE reassessment successfully overrides the diagnosis
        with 1.0 confidence, producing an accredited Bacterial Spot decision plan.
        """
        # Step 1: Initial investigation with grower notes reporting hot/dry conditions or symptom conflict
        case_with_notes: AgriMindState = {
            "case_id": "CASE-WK8-RECOVERY-001",
            "image_path": SAMPLE_REAL_IMAGE,
            "vision_prediction": VisionPrediction(
                predicted_class="Tomato___Late_blight",  # Week 8 SMPL-00011 misclassification
                confidence=1.0000
            ),
            "visual_context": VisualContext(
                leaf_damage_percentage=12.0,
                weather_conditions="hot_dry (>32C)",
                field_notes="Concentric bullseye rings with small dark specks; dry hot weather."
            )
        }
        case1 = self.app.invoke(case_with_notes)

        # Investigation Agent catches the discrepancy (Late Blight cannot sporulate in hot/dry >30C)
        self.assertEqual(case1.get("workflow_status"), "pending_manual_review")
        self.assertEqual(case1.get("final_output", {}).get("plan_urgency"), "deferred")
        self.assertIsNone(case1.get("final_output", {}).get("pesticide_safety_notice"))

        # Step 2: Lab diagnostic clinic confirms Bacterial Spot via PCR
        corrected_case = reassess_case(
            workflow_app=self.app,
            completed_state=case1,
            trigger=ReassessmentTrigger.LAB_DIAGNOSTIC_UPDATE,
            new_evidence={"lab_confirmed_disease": "Tomato___Bacterial_spot"},
            rationale="PCR confirmation from University Extension Pathology Clinic."
        )

        final = corrected_case.get("final_output", {})
        self.assertEqual(final.get("primary_diagnosis"), "Tomato___Bacterial_spot")
        self.assertEqual(final.get("reassessment_outcome"), "revised")
        self.assertTrue(final.get("is_verified"))
        self.assertIn("bacterial_spot", final.get("primary_diagnosis").lower())


if __name__ == "__main__":
    unittest.main()
