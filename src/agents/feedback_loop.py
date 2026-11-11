"""
Manual-Review Feedback Loop for AgriMind (Week 5).
Routes ambiguous, conflicting, high-risk, or verification-failed cases to a structured
manual-review state, and defines bounded re-entry into the decision workflow.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.agents.schemas import (
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    VerificationResult,
    ManualReviewRecord,
    ReviewStatus,
    VerificationStatus,
    EvidenceStatus,
    VisionPrediction,
    VisualContext
)
from src.agents.investigation import InvestigationAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.agents.decision_planning import DecisionPlanningAgent
from src.agents.critic import CriticAgent


class ManualReviewFeedbackLoop:
    """
    Orchestrates case routing to human agronomic review and bounded re-entry.
    Prevents infinite review loops via bounded iteration ceilings.
    """

    def __init__(self, max_iterations: int = 2):
        self.max_iterations = max_iterations

    def route_to_review(
        self,
        investigation: InvestigationResult,
        risk: Optional[RiskAssessmentResult] = None,
        plan: Optional[DecisionPlan] = None,
        verification: Optional[VerificationResult] = None
    ) -> Optional[ManualReviewRecord]:
        """
        Evaluates whether a case warrants manual expert review.
        Returns a ManualReviewRecord if triggered, otherwise None.
        """
        trigger_reasons: List[str] = []
        flagged_by = "InvestigationAgent"

        # 1. Investigation Triggers
        if investigation.evidence_status == EvidenceStatus.CONFLICTING:
            trigger_reasons.append("Diagnostic conflict detected between model predictions and field symptoms.")
        elif investigation.evidence_status == EvidenceStatus.UNSUPPORTED_DISEASE:
            trigger_reasons.append("Pathogen outside AgriMind 3-class verified tomato scope.")
        elif investigation.evidence_status == EvidenceStatus.INSUFFICIENT_LITERATURE:
            trigger_reasons.append("Insufficient verified extension literature in knowledge base.")

        # 2. Risk Assessment Triggers
        if risk is not None:
            flagged_by = "RiskAssessmentAgent"
            if risk.requires_human_expert_review:
                trigger_reasons.append("Risk assessment flagged mandatory human expert review.")

        # 3. Critic Verification Triggers
        if verification is not None:
            flagged_by = "CriticAgent"
            if not verification.is_verified:
                trigger_reasons.extend(verification.rejection_reasons)
            elif verification.requires_manual_review:
                if verification.escalation_reason:
                    trigger_reasons.append(verification.escalation_reason)

        if not trigger_reasons:
            return None

        review_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        evidence_summary = {
            "primary_diagnosis": investigation.primary_diagnosis,
            "diagnosis_confidence": investigation.diagnosis_confidence,
            "evidence_status": investigation.evidence_status.value,
            "conflicts": investigation.conflicts_detected,
            "assigned_severity": risk.assigned_severity.value if risk else None,
            "epidemic_risk": risk.epidemic_risk if risk else None
        }

        return ManualReviewRecord(
            review_id=review_id,
            plan_id=plan.plan_id if plan else None,
            investigation_id=investigation.investigation_id,
            assessment_id=risk.assessment_id if risk else None,
            flagged_by=flagged_by,
            trigger_reasons=trigger_reasons,
            evidence_summary=evidence_summary,
            status=ReviewStatus.PENDING,
            expert_notes=None,
            corrected_diagnosis=None,
            iteration_count=1,
            max_iterations=self.max_iterations,
            submission_timestamp=timestamp,
            resolution_timestamp=None
        )

    def resolve_review(
        self,
        record: ManualReviewRecord,
        investigation_agent: InvestigationAgent,
        risk_agent: RiskAssessmentAgent,
        decision_planner: DecisionPlanningAgent,
        critic_agent: CriticAgent,
        expert_diagnosis: Optional[str] = None,
        corrected_context: Optional[VisualContext] = None,
        expert_notes: Optional[str] = None,
        override_approve_plan: Optional[DecisionPlan] = None
    ) -> Dict[str, Any]:
        """
        Processes human expert review and re-enters the workflow with bounded retry control.
        """
        now = datetime.now(timezone.utc).isoformat()

        # Check iteration ceiling to prevent infinite loops
        if record.iteration_count >= record.max_iterations:
            record.status = ReviewStatus.TERMINAL_ESCALATION
            record.resolution_timestamp = now
            record.expert_notes = (expert_notes or "") + " [TERMINAL ESCALATION: Maximum review iterations reached. Refer sample to State Diagnostic Clinic.]"
            return {
                "status": ReviewStatus.TERMINAL_ESCALATION,
                "record": record,
                "plan": None,
                "verification": None,
                "message": "Maximum review iterations reached. Case permanently escalated to external diagnostic laboratory."
            }

        # Sub-case A: Direct expert override / approval
        if override_approve_plan is not None:
            record.status = ReviewStatus.OVERRIDDEN
            record.expert_notes = expert_notes
            record.resolution_timestamp = now
            return {
                "status": ReviewStatus.OVERRIDDEN,
                "record": record,
                "plan": override_approve_plan,
                "verification": None,
                "message": "Plan approved via direct expert override."
            }

        # Sub-case B: Corrected diagnosis or field context provided
        record.iteration_count += 1
        record.expert_notes = expert_notes
        record.corrected_diagnosis = expert_diagnosis

        # Formulate corrected vision prediction using expert confirmation
        diag = expert_diagnosis or record.evidence_summary.get("primary_diagnosis", "Tomato___Early_blight")
        corrected_vision = VisionPrediction(
            predicted_class=diag,
            confidence=1.0,  # Expert confirmed
            is_supported_disease=diag in ["Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight"]
        )

        # Re-run investigation with corrected context
        re_investigation = investigation_agent.investigate(
            vision_prediction=corrected_vision,
            visual_context=corrected_context
        )

        # Re-run risk assessment
        re_risk = risk_agent.assess_risk(re_investigation)

        # Re-run decision planning
        re_plan = decision_planner.plan_decision(re_investigation, re_risk)

        # Re-verify through Critic
        re_verification = critic_agent.verify_plan(re_plan, re_investigation, re_risk)

        if re_verification.is_verified:
            record.status = ReviewStatus.APPROVED
            record.resolution_timestamp = now
            return {
                "status": ReviewStatus.APPROVED,
                "record": record,
                "investigation": re_investigation,
                "risk": re_risk,
                "plan": re_plan,
                "verification": re_verification,
                "message": "Case successfully resolved and re-verified after expert review input."
            }
        else:
            # Re-verification failed after iteration increment
            if record.iteration_count > record.max_iterations:
                record.status = ReviewStatus.TERMINAL_ESCALATION
                record.resolution_timestamp = now
                return {
                    "status": ReviewStatus.TERMINAL_ESCALATION,
                    "record": record,
                    "plan": re_plan,
                    "verification": re_verification,
                    "message": "Re-verification failed and maximum iteration ceiling reached. Escalated to terminal state."
                }
            else:
                return {
                    "status": ReviewStatus.PENDING,
                    "record": record,
                    "plan": re_plan,
                    "verification": re_verification,
                    "message": "Re-verification failed. Case remains pending additional expert review."
                }
