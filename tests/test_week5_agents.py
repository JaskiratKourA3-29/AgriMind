"""
Unit Tests for AgriMind Week 5: Decision Planning Agent, Critic Agent, and Manual Review Feedback Loop.
Tests evidential consistency, citation grounding, agricultural safety, and bounded review workflows.
"""
import unittest

from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    SeverityLevel,
    RiskAssessmentResult,
    PlanUrgency,
    ManagementAction,
    DecisionPlan,
    VerificationStatus,
    ReviewStatus
)
from src.agents.investigation import InvestigationAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.agents.decision_planning import DecisionPlanningAgent
from src.agents.critic import CriticAgent
from src.agents.feedback_loop import ManualReviewFeedbackLoop


class TestWeek5Agents(unittest.TestCase):
    """
    Test suite verifying Decision Planning, Critic Verification, and Feedback Loop functionality.
    """

    @classmethod
    def setUpClass(cls):
        cls.investigation_agent = InvestigationAgent()
        cls.risk_agent = RiskAssessmentAgent()
        cls.decision_planner = DecisionPlanningAgent()
        cls.critic_agent = CriticAgent()
        cls.feedback_loop = ManualReviewFeedbackLoop(max_iterations=2)

    def test_01_decision_planning_supported_guidance_with_citations(self):
        """Verify Decision Planning generates structured IPM guidance with traceable citations."""
        vision = VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.9600)
        context = VisualContext(
            leaf_damage_percentage=18.0,
            affected_organs=["leaves"],
            canopy_spread="mid_canopy"
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        self.assertIsInstance(plan, DecisionPlan)
        self.assertEqual(plan.disease, "Tomato___Early_blight")
        self.assertEqual(plan.urgency, PlanUrgency.MODERATE)
        self.assertGreater(len(plan.cultural_controls), 0)
        self.assertGreater(len(plan.resistant_varieties), 0)
        self.assertGreater(len(plan.chemical_controls), 0)
        self.assertGreater(len(plan.monitoring_actions), 0)
        self.assertGreater(len(plan.citations), 0)
        self.assertIsNotNone(plan.pesticide_safety_notice)

        # Verification by Critic must pass
        verif = self.critic_agent.verify_plan(plan, inv, risk)
        self.assertTrue(verif.is_verified)
        self.assertEqual(verif.status, VerificationStatus.VERIFIED)

    def test_02_critic_rejects_missing_citations_when_literature_available(self):
        """Verify Critic rejects a plan that strips out citations despite literature availability."""
        vision = VisionPrediction(predicted_class="Tomato___Bacterial_spot", confidence=0.9400)
        context = VisualContext(leaf_damage_percentage=8.0, canopy_spread="lower_canopy")
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        # Malform the plan by removing citations
        flawed_plan = plan.model_copy(update={"citations": []})
        verif = self.critic_agent.verify_plan(flawed_plan, inv, risk)

        self.assertFalse(verif.is_verified)
        self.assertEqual(verif.status, VerificationStatus.REJECTED_UNSUPPORTED_CLAIMS)
        self.assertTrue(any("Missing citation" in r for r in verif.rejection_reasons))

    def test_03_conflicting_evidence_defers_guidance_and_routes_to_review(self):
        """Verify conflicting evidence defers chemical advice, flags expert review, and routes to review loop."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9100)
        context = VisualContext(
            leaf_damage_percentage=25.0,
            field_notes="Concentric bullseye rings with yellow halo."  # Contradicts Late Blight
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        # Guidance must be deferred and contain zero chemical controls
        self.assertEqual(plan.urgency, PlanUrgency.DEFERRED)
        self.assertTrue(plan.expert_review_required)
        self.assertEqual(len(plan.chemical_controls), 0)
        self.assertIsNone(plan.pesticide_safety_notice)

        # Critic verifies the deferred plan
        verif = self.critic_agent.verify_plan(plan, inv, risk)
        self.assertTrue(verif.is_verified)
        self.assertTrue(verif.requires_manual_review)

        # Feedback loop routes to manual review
        record = self.feedback_loop.route_to_review(inv, risk, plan, verif)
        self.assertIsNotNone(record)
        self.assertEqual(record.status, ReviewStatus.PENDING)
        self.assertEqual(record.iteration_count, 1)

    def test_04_critic_rejects_urgency_inconsistency(self):
        """Verify Critic rejects a plan whose urgency contradicts severe risk assessment."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9800)
        context = VisualContext(
            leaf_damage_percentage=40.0,
            weather_conditions="cool_wet",
            field_notes="White sporulation on leaf undersides."
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        self.assertEqual(risk.assigned_severity, SeverityLevel.CRITICAL)

        plan = self.decision_planner.plan_decision(inv, risk)
        # Malform the plan by setting urgency to LOW
        flawed_plan = plan.model_copy(update={"urgency": PlanUrgency.LOW})
        verif = self.critic_agent.verify_plan(flawed_plan, inv, risk)

        self.assertFalse(verif.is_verified)
        self.assertEqual(verif.status, VerificationStatus.REJECTED_INCONSISTENCY)
        self.assertTrue(any("underestimates" in r for r in verif.rejection_reasons))

    def test_05_critic_rejects_mandipropamid_curative_kickback(self):
        """Verify Critic catches and rejects unsupported claim that Mandipropamid has curative kickback."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9500)
        context = VisualContext(leaf_damage_percentage=15.0, canopy_spread="lower_canopy")
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        # Inject flawed chemical recommendation falsely claiming Mandipropamid kickback
        flawed_action = ManagementAction(
            category="chemical",
            action_summary="Curative application of Mandipropamid",
            details="Apply Mandipropamid for curative kickback activity within 48 hours.",
            is_chemical=True,
            citation_numbers=[1]
        )
        flawed_plan = plan.model_copy(update={"chemical_controls": [flawed_action]})
        verif = self.critic_agent.verify_plan(flawed_plan, inv, risk)

        self.assertFalse(verif.is_verified)
        self.assertEqual(verif.status, VerificationStatus.REJECTED_SAFETY_VIOLATION)
        self.assertTrue(any("Mandipropamid" in r for r in verif.rejection_reasons))

    def test_06_critic_rejects_missing_pesticide_safety_notice(self):
        """Verify Critic rejects any plan recommending chemicals without the mandatory pesticide notice."""
        vision = VisionPrediction(predicted_class="Tomato___Bacterial_spot", confidence=0.9600)
        context = VisualContext(leaf_damage_percentage=20.0, canopy_spread="mid_canopy")
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        # Malform the plan by removing the notice
        flawed_plan = plan.model_copy(update={"pesticide_safety_notice": None})
        verif = self.critic_agent.verify_plan(flawed_plan, inv, risk)

        self.assertFalse(verif.is_verified)
        self.assertEqual(verif.status, VerificationStatus.REJECTED_SAFETY_VIOLATION)
        self.assertTrue(any("Pesticide" in r or "regulatory" in r for r in verif.rejection_reasons))

    def test_07_failed_verification_routes_to_manual_review(self):
        """Verify Critic rejection routes case directly to the Manual Review Feedback Loop."""
        vision = VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.9200)
        context = VisualContext(leaf_damage_percentage=10.0, canopy_spread="lower_canopy")
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        # Introduce flaw
        flawed_plan = plan.model_copy(update={"pesticide_safety_notice": "Incomplete note"})
        verif = self.critic_agent.verify_plan(flawed_plan, inv, risk)
        self.assertFalse(verif.is_verified)

        record = self.feedback_loop.route_to_review(inv, risk, flawed_plan, verif)
        self.assertIsNotNone(record)
        self.assertEqual(record.flagged_by, "CriticAgent")
        self.assertEqual(record.status, ReviewStatus.PENDING)
        self.assertGreater(len(record.trigger_reasons), 0)

    def test_08_feedback_loop_successful_resolution_and_reentry(self):
        """Verify an expert provides a diagnosis correction, which resolves the review and re-enters workflow."""
        # Initial case had conflict
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.8800)
        context = VisualContext(field_notes="Concentric target rings.")  # Early Blight symptom
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)
        verif = self.critic_agent.verify_plan(plan, inv, risk)

        record = self.feedback_loop.route_to_review(inv, risk, plan, verif)
        self.assertEqual(record.status, ReviewStatus.PENDING)

        # Expert inspects field, confirms Early Blight, and provides canopy context
        expert_context = VisualContext(
            leaf_damage_percentage=15.0,
            canopy_spread="lower_canopy",
            field_notes="Microscopic examination confirmed Alternaria solani conidia."
        )
        resolution = self.feedback_loop.resolve_review(
            record=record,
            investigation_agent=self.investigation_agent,
            risk_agent=self.risk_agent,
            decision_planner=self.decision_planner,
            critic_agent=self.critic_agent,
            expert_diagnosis="Tomato___Early_blight",
            corrected_context=expert_context,
            expert_notes="Confirmed Early Blight. Overriding misclassified Late Blight."
        )

        self.assertEqual(resolution["status"], ReviewStatus.APPROVED)
        self.assertEqual(record.status, ReviewStatus.APPROVED)
        self.assertIsNotNone(record.resolution_timestamp)
        self.assertEqual(resolution["plan"].disease, "Tomato___Early_blight")
        self.assertTrue(resolution["verification"].is_verified)

    def test_09_feedback_loop_bounded_iteration_terminal_escalation(self):
        """Verify bounded review ceiling prevents infinite loops and triggers terminal escalation."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.8500)
        context = VisualContext(field_notes="Concentric target rings.")
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)
        verif = self.critic_agent.verify_plan(plan, inv, risk)

        record = self.feedback_loop.route_to_review(inv, risk, plan, verif)
        self.assertEqual(record.iteration_count, 1)

        # First review cycle fails to resolve because expert submits conflicting notes again
        conflicting_context = VisualContext(field_notes="Concentric target rings.")
        res1 = self.feedback_loop.resolve_review(
            record=record,
            investigation_agent=self.investigation_agent,
            risk_agent=self.risk_agent,
            decision_planner=self.decision_planner,
            critic_agent=self.critic_agent,
            expert_diagnosis="Tomato___Late_blight",
            corrected_context=conflicting_context,
            expert_notes="Unsure, needs clinic re-testing."
        )
        self.assertEqual(record.iteration_count, 2)

        # Second review cycle exceeds max iterations (ceiling = 2)
        res2 = self.feedback_loop.resolve_review(
            record=record,
            investigation_agent=self.investigation_agent,
            risk_agent=self.risk_agent,
            decision_planner=self.decision_planner,
            critic_agent=self.critic_agent,
            expert_diagnosis="Tomato___Late_blight",
            corrected_context=conflicting_context,
            expert_notes="Still unresolved."
        )

        self.assertEqual(res2["status"], ReviewStatus.TERMINAL_ESCALATION)
        self.assertEqual(record.status, ReviewStatus.TERMINAL_ESCALATION)
        self.assertIn("TERMINAL ESCALATION", record.expert_notes)

    def test_10_late_blight_safety_sensitive_guidance(self):
        """Verify Late Blight under cool/wet weather generates urgent rogueing and grounded oomycides."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9850)
        context = VisualContext(
            leaf_damage_percentage=8.0,
            weather_conditions="cool_wet",
            field_notes="White cottony sporulation visible on leaf undersides."
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)
        plan = self.decision_planner.plan_decision(inv, risk)

        self.assertEqual(plan.urgency, PlanUrgency.CRITICAL)
        # Cultural controls must include Cornell rogueing procedure
        cultural_summaries = [c.action_summary for c in plan.cultural_controls]
        self.assertTrue(any("rogueing" in s.lower() for s in cultural_summaries))

        # Chemical controls must include Cymoxanil kickback and Mandipropamid anti-sporulant
        chem_details = " ".join(c.details for c in plan.chemical_controls)
        self.assertIn("Cymoxanil", chem_details)
        self.assertIn("kickback", chem_details.lower())
        self.assertIn("Mandipropamid", chem_details)
        self.assertIn("anti-sporulant", chem_details.lower())

        # Critic verification must pass cleanly
        verif = self.critic_agent.verify_plan(plan, inv, risk)
        self.assertTrue(verif.is_verified)


if __name__ == "__main__":
    unittest.main()
