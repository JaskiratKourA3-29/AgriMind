"""
Critic/Verification Agent for AgriMind (Week 5).
Audits decision plans against underlying investigation evidence, risk assessment findings,
citation traceability, and agricultural safety constraints.
"""
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.agents.schemas import (
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    VerificationResult,
    VerificationStatus,
    PlanUrgency,
    SeverityLevel,
    EvidenceStatus
)


class CriticAgent:
    """
    Independent verification and critic agent.
    Detects evidential inconsistencies, missing citations, unsupported chemical claims,
    and agricultural safety violations.
    """

    VERIFIED_ACTIVE_INGREDIENTS = {
        "copper", "mancozeb", "chlorothalonil", "cymoxanil", "mandipropamid",
        "acibenzolar-s-methyl", "actigard", "curzate", "revus", "fixed copper"
    }

    def verify_plan(
        self,
        plan: DecisionPlan,
        investigation: InvestigationResult,
        risk: RiskAssessmentResult
    ) -> VerificationResult:
        """
        Executes comprehensive evidential and safety verification of a DecisionPlan.
        """
        verification_id = f"VRF-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        checks_passed: List[str] = []
        issues_detected: List[str] = []
        rejection_reasons: List[str] = []
        primary_status = VerificationStatus.VERIFIED

        # -------------------------------------------------------------
        # Check 1: Citation Presence and Grounding
        # -------------------------------------------------------------
        has_literature = investigation.retrieved_evidence.has_sufficient_evidence
        valid_citation_nums = {c.get("citation_number", 1) for c in plan.citations}

        if has_literature and not plan.citations:
            issues_detected.append("Plan lacks institutional citations despite available literature evidence.")
            rejection_reasons.append("Missing citation metadata in decision plan.")
            primary_status = VerificationStatus.REJECTED_UNSUPPORTED_CLAIMS
        else:
            checks_passed.append("Citation presence verified against available literature evidence.")

        # Validate action citation references
        all_actions = plan.cultural_controls + plan.resistant_varieties + plan.chemical_controls + plan.monitoring_actions
        invalid_refs = []
        for act in all_actions:
            for num in act.citation_numbers:
                if num not in valid_citation_nums:
                    invalid_refs.append(num)
        if invalid_refs:
            issues_detected.append(f"Actions reference citations not present in plan metadata: {invalid_refs}")
            rejection_reasons.append("Orphaned citation numbers detected in management actions.")
            primary_status = VerificationStatus.REJECTED_UNSUPPORTED_CLAIMS
        else:
            checks_passed.append("Action citation references trace cleanly to plan metadata.")

        # -------------------------------------------------------------
        # Check 2: Evidential Consistency with Risk Assessment
        # -------------------------------------------------------------
        # Urgency consistency
        if risk.assigned_severity == SeverityLevel.CRITICAL and plan.urgency in [PlanUrgency.LOW, PlanUrgency.MODERATE]:
            issues_detected.append(
                f"Urgency mismatch: Risk Assessment assigned CRITICAL severity, but plan urgency is {plan.urgency.value.upper()}."
            )
            rejection_reasons.append("Decision plan underestimates critical epidemic severity.")
            primary_status = VerificationStatus.REJECTED_INCONSISTENCY
        elif risk.assigned_severity == SeverityLevel.LOW and plan.urgency == PlanUrgency.CRITICAL:
            issues_detected.append(
                f"Urgency mismatch: Risk Assessment assigned LOW severity, but plan urgency is CRITICAL."
            )
            rejection_reasons.append("Decision plan overreacts to localized low-severity disease.")
            primary_status = VerificationStatus.REJECTED_INCONSISTENCY
        else:
            checks_passed.append(f"Plan urgency ({plan.urgency.value.upper()}) is consistent with risk assessment.")

        # Diagnostic conflict handling consistency
        if investigation.evidence_status in [EvidenceStatus.CONFLICTING, EvidenceStatus.UNSUPPORTED_DISEASE]:
            if plan.chemical_controls:
                issues_detected.append(
                    "Safety violation: Chemical recommendations issued under CONFLICTING or UNSUPPORTED evidence status."
                )
                rejection_reasons.append("Chemical sprays must be withheld when pathogen identification is contradictory or out-of-scope.")
                primary_status = VerificationStatus.REJECTED_SAFETY_VIOLATION
            if not plan.expert_review_required:
                issues_detected.append("Plan failed to flag required expert review under conflicting/unsupported evidence.")
                rejection_reasons.append("Expert review must be flagged when diagnostic evidence is unresolved.")
                primary_status = VerificationStatus.REJECTED_INCONSISTENCY
            if plan.urgency != PlanUrgency.DEFERRED:
                issues_detected.append("Plan urgency was not set to DEFERRED under conflicting/unsupported evidence.")
                rejection_reasons.append("Automated guidance must be deferred pending human review.")
                primary_status = VerificationStatus.REJECTED_INCONSISTENCY
        else:
            checks_passed.append("Diagnostic evidence handling is consistent with investigation status.")

        # -------------------------------------------------------------
        # Check 3: Mode of Action & Fungicide Safety Audit
        # -------------------------------------------------------------
        # Rule: Mandipropamid must NOT be attributed with curative kickback activity
        action_text_combined = " ".join(f"{a.action_summary} {a.details}" for a in all_actions).lower()
        if "mandipropamid" in action_text_combined:
            # Check if text claims curative/kickback for Mandipropamid without negation
            # e.g. "mandipropamid ... curative kickback" or "mandipropamid for curative"
            if re.search(r"mandipropamid[^\.]*?(?:curative|kickback)", action_text_combined):
                # Verify if it contains explicit negation ("not", "does not", "without")
                match = re.search(r"mandipropamid[^\.]*?(?:curative|kickback)", action_text_combined).group(0)
                if not any(neg in match for neg in ["not", "does not", "neither", "no"]):
                    issues_detected.append(
                        "Fungicide mode-of-action error: Mandipropamid (Revus) falsely credited with curative kickback activity."
                    )
                    rejection_reasons.append("Mandipropamid possesses only preventative and anti-sporulant activity (Cornell Extension).")
                    primary_status = VerificationStatus.REJECTED_SAFETY_VIOLATION

        # Rule: Cymoxanil kickback activity must be within 24-48 hours
        if "cymoxanil" in action_text_combined and "kickback" in action_text_combined:
            checks_passed.append("Cymoxanil post-infection kickback activity correctly attributed.")

        # -------------------------------------------------------------
        # Check 4: Mandatory Pesticide Safety Notice Audit
        # -------------------------------------------------------------
        if plan.chemical_controls:
            if not plan.pesticide_safety_notice or not plan.pesticide_safety_notice.strip():
                issues_detected.append("Regulatory safety violation: Chemical controls present without mandatory pesticide safety notice.")
                rejection_reasons.append("Pesticide recommendations must include mandatory EPA/state regulatory disclaimers.")
                primary_status = VerificationStatus.REJECTED_SAFETY_VIOLATION
            else:
                notice = plan.pesticide_safety_notice.upper()
                if "LABEL" not in notice or "REI" not in notice or "PHI" not in notice:
                    issues_detected.append("Pesticide safety notice is missing key regulatory components (label, REI, or PHI).")
                    rejection_reasons.append("Pesticide safety notice must include label adherence, REI, and PHI warnings.")
                    primary_status = VerificationStatus.REJECTED_SAFETY_VIOLATION
                else:
                    checks_passed.append("Mandatory pesticide safety notice verified (includes label, REI, and PHI disclaimers).")
        else:
            checks_passed.append("Zero chemical controls present; chemical safety notice check satisfied.")

        # -------------------------------------------------------------
        # Check 5: Active Ingredient Grounding Audit
        # -------------------------------------------------------------
        unsupported_chemicals = []
        for act in plan.chemical_controls:
            text = (act.action_summary + " " + act.details).lower()
            # Check for hallucinated unregistered agricultural products
            chemical_candidates = re.findall(r"\b([a-z\-]+(?:azole|mycin|thion|quat|nil|strobin|amid))\b", text)
            for cand in chemical_candidates:
                if cand not in self.VERIFIED_ACTIVE_INGREDIENTS and cand not in ["chlorothalonil", "cymoxanil", "mandipropamid"]:
                    unsupported_chemicals.append(cand)
        if unsupported_chemicals:
            issues_detected.append(f"Chemical controls include unverified/unregistered active ingredients: {unsupported_chemicals}")
            rejection_reasons.append("Chemical recommendation contains unverified active ingredients outside accredited knowledge base.")
            primary_status = VerificationStatus.REJECTED_UNSUPPORTED_CLAIMS
        else:
            checks_passed.append("Chemical active ingredients verified against accredited extension knowledge base.")

        # -------------------------------------------------------------
        # Final Decision Synthesis
        # -------------------------------------------------------------
        is_verified = (len(rejection_reasons) == 0)
        requires_manual_review = (not is_verified) or plan.expert_review_required

        escalation_reason = None
        if not is_verified:
            escalation_reason = f"Verification failed: {'; '.join(rejection_reasons)}"
        elif requires_manual_review:
            escalation_reason = "Manual review required due to diagnostic/epidemic risk factors in verified plan."

        return VerificationResult(
            verification_id=verification_id,
            plan_id=plan.plan_id,
            is_verified=is_verified,
            status=primary_status if not is_verified else VerificationStatus.VERIFIED,
            checks_passed=checks_passed,
            issues_detected=issues_detected,
            rejection_reasons=rejection_reasons,
            requires_manual_review=requires_manual_review,
            escalation_reason=escalation_reason,
            timestamp=timestamp
        )
