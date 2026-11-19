"""
Risk Assessment Agent for AgriMind (Week 4).
Maps supported disease findings and canopy contextual evidence to standardized
severity and epidemic risk levels using project-defined heuristics synthesized
from qualitative university extension pathology literature (Cornell CALS, UF/IFAS, Purdue, UC IPM).
"""
import uuid
from typing import Dict, Any, List, Optional

from src.agents.schemas import (
    InvestigationResult,
    RiskAssessmentResult,
    SeverityLevel,
    EvidenceStatus
)

MANDATORY_PESTICIDE_SAFETY_NOTICE = (
    "MANDATORY PESTICIDE SAFETY NOTICE: Any chemical pesticide or bactericide application must strictly follow "
    "the registered EPA and state product label, including personal protective equipment (PPE), restricted-entry "
    "intervals (REI), and pre-harvest intervals (PHI). Consult your local university agricultural extension service "
    "or a certified crop advisor for legally registered, site-specific treatment recommendations."
)


class RiskAssessmentAgent:
    """
    Evaluates agricultural disease severity and epidemic risk.
    Strictly decouples model classification confidence from physical disease severity.
    """
    def assess_risk(self, investigation: InvestigationResult) -> RiskAssessmentResult:
        """
        Assesses severity and epidemic risk from an InvestigationResult.
        """
        assessment_id = f"RSK-{uuid.uuid4().hex[:8].upper()}"
        disease = investigation.primary_diagnosis
        id_confidence = investigation.diagnosis_confidence
        context = investigation.visual_context
        status = investigation.evidence_status

        rubric_basis: List[str] = []
        uncertainty_factors: List[str] = []
        scouting_recs: List[str] = []
        requires_immediate_action = False
        requires_human_expert_review = False

        is_late_blight = "Late_blight" in disease
        is_early_blight = "Early_blight" in disease
        is_bacterial_spot = "Bacterial_spot" in disease

        # Rule 0: Healthy tomato foliage
        if "healthy" in disease.lower():
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                identification_confidence=id_confidence,
                assigned_severity=SeverityLevel.LOW,
                severity_confidence="high",
                rubric_basis=["Tomato foliage exhibits healthy laminar structure with no active pathogen lesions."],
                epidemic_risk="low",
                uncertainty_factors=[],
                scouting_recommendations=["Continue routine weekly crop scouting."],
                requires_immediate_action=False,
                requires_human_expert_review=False,
                pesticide_safety_notice=None
            )

        # Rule 1: Guard against conflicting or unsupported evidence
        if status == EvidenceStatus.UNSUPPORTED_DISEASE:
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                identification_confidence=id_confidence,
                assigned_severity=SeverityLevel.INDETERMINATE,
                severity_confidence="none",
                rubric_basis=["Disease pathogen is outside the 3 verified in-scope tomato diseases."],
                epidemic_risk="unknown",
                uncertainty_factors=["Unsupported pathogen classification outside AgriMind scope."],
                scouting_recommendations=["Submit sample to university diagnostic laboratory for professional identification."],
                requires_immediate_action=False,
                requires_human_expert_review=True,
                pesticide_safety_notice=MANDATORY_PESTICIDE_SAFETY_NOTICE
            )

        if status == EvidenceStatus.CONFLICTING:
            return RiskAssessmentResult(
                assessment_id=assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                identification_confidence=id_confidence,
                assigned_severity=SeverityLevel.INDETERMINATE,
                severity_confidence="none",
                rubric_basis=["Diagnostic conflict detected between visual model prediction and field observations (diagnostic conflict)."],
                epidemic_risk="unknown",
                uncertainty_factors=investigation.conflicts_detected,
                scouting_recommendations=[
                    "Conduct in-field physical inspection to reconcile contradictory symptoms.",
                    "Review lower vs upper canopy symptoms and verify lesion morphology."
                ],
                requires_immediate_action=True if is_late_blight else False,
                requires_human_expert_review=True,
                pesticide_safety_notice=MANDATORY_PESTICIDE_SAFETY_NOTICE
            )

        # Rule 2: Single-leaf image without canopy context cannot establish severity
        if context is None or (
            context.leaf_damage_percentage is None and
            context.canopy_spread is None
        ):
            # Safe handling: If Late Blight is suspected, escalate urgency even while severity is INDETERMINATE!
            if is_late_blight:
                epidemic_risk = "high"
                requires_immediate_action = True
                requires_human_expert_review = True
                rubric_basis = [
                    "Evidence restricted to single cropped leaf image. "
                    "Project heuristics require whole-canopy context to establish physical severity.",
                    "CRITICAL SAFETY WARNING: Suspected Late Blight (Phytophthora infestans) is an explosive epidemic pathogen "
                    "capable of complete crop destruction within 7-10 days (Cornell Extension). Urgent whole-field scouting is required."
                ]
                scouting_recs = [
                    "URGENT: Immediately scout entire tomato planting for foliar water-soaking or stem lesions.",
                    "Check leaf undersides in early morning for white cottony sporulation (Cornell Extension).",
                    "Consult local agricultural extension immediately if symptoms are observed across the planting."
                ]
            else:
                epidemic_risk = "low"
                requires_immediate_action = False
                requires_human_expert_review = False
                rubric_basis = [
                    "Evidence restricted to single cropped leaf image. "
                    "Project heuristics require canopy spread and leaf area coverage to establish physical disease severity."
                ]
                scouting_recs = [
                    "General IPM suggestion: scout representative tomato plants across the field.",
                    "Estimate average percentage of canopy foliage exhibiting lesions.",
                    "Inspect stems and developing fruit for sunken cankers or water-soaked lesions."
                ]

            return RiskAssessmentResult(
                assessment_id=assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                identification_confidence=id_confidence,
                assigned_severity=SeverityLevel.INDETERMINATE,
                severity_confidence="none",
                rubric_basis=rubric_basis,
                epidemic_risk=epidemic_risk,
                uncertainty_factors=[
                    "Missing foliar damage percentage.",
                    "Missing whole-canopy vertical spread observation.",
                    "Missing organ involvement data (stems/fruit)."
                ],
                scouting_recommendations=scouting_recs,
                requires_immediate_action=requires_immediate_action,
                requires_human_expert_review=requires_human_expert_review,
                pesticide_safety_notice=MANDATORY_PESTICIDE_SAFETY_NOTICE
            )

        # Rule 3: Agronomic Rubric Evaluation using available physical evidence
        damage_pct = context.leaf_damage_percentage if context.leaf_damage_percentage is not None else 0.0
        canopy = context.canopy_spread or "lower_canopy"
        organs = set(context.affected_organs or ["leaves"])
        has_stem_involvement = "stems" in organs or "stem" in organs
        has_fruit_involvement = "fruit" in organs or "fruits" in organs
        weather = (context.weather_conditions or "").lower()
        notes = (context.field_notes or "").lower()
        has_active_sporulation = "sporulation" in notes or "white mold" in notes or "white cottony" in notes
        is_conducive_late_blight_weather = any(w in weather for w in ["cool", "wet", "humid", "fog", "rain"])

        # LATE BLIGHT CONSERVATIVE SAFETY GATING:
        # Never downgrade Late Blight to LOW or MODERATE under conducive weather or active sporulation.
        # UC IPM (DOC-UCIPM-TOM-LB-02:38): Once late blight reaches 5% to 10% of canopy, chemical control is ineffective.
        if is_late_blight:
            if has_active_sporulation or (is_conducive_late_blight_weather and (damage_pct >= 5.0 or canopy != "lower_canopy" or has_stem_involvement or has_fruit_involvement)):
                severity = SeverityLevel.CRITICAL
                severity_conf = "high"
                epidemic_risk = "critical"
                requires_immediate_action = True
                requires_human_expert_review = True
                rubric_basis.append(
                    "Late Blight (Phytophthora infestans) with active sporulation or conducive weather (cool/wet) "
                    "with established canopy spread (>=5% damage or stem/canopy progression). "
                    "Pathogen capable of 100% crop loss within 7-10 days; chemical control fails beyond 5-10% canopy infection (Cornell Extension & UC IPM)."
                )
                scouting_recs.extend([
                    "Immediate rogueing: When an initial hot-spot plant is detected, bag plant in plastic on dry sunny midday, cut at base, and remove (Cornell Extension).",
                    "Fungicide intervention: Consult extension recommendations for targeted systemic oomycides: apply Cymoxanil for post-infection kickback activity (24-48 hours post-infection, tank-mixed with protectant per Cornell Extension), or Mandipropamid (Revus) for preventative anti-sporulant protection.",
                    "Alert regional agricultural extension office / USABlight network of potential late blight outbreak."
                ])
            elif is_conducive_late_blight_weather or damage_pct >= 5.0 or has_stem_involvement or has_fruit_involvement:
                # Early Late Blight under conducive weather or >=5% damage without sporulation
                severity = SeverityLevel.HIGH
                severity_conf = "high"
                epidemic_risk = "high"
                requires_immediate_action = True
                requires_human_expert_review = True
                rubric_basis.append(
                    "Late Blight (Phytophthora infestans) detected under conducive cool/wet weather or early canopy spread. "
                    "Escalated to HIGH severity due to acute epidemic potential and rapid generation time (Cornell Extension)."
                )
                scouting_recs.extend([
                    "Apply protectant fungicides (chlorothalonil, mancozeb, or fixed copper) on strict 5-day interval under cool, overcast, rainy conditions (UC IPM).",
                    "Avoid overhead irrigation to eliminate leaf wetness duration (UC IPM).",
                    "Daily canopy scouting for white sporulation on leaf undersides."
                ])
            else:
                # Late Blight in non-conducive weather (e.g. hot/dry) with <5% damage
                severity = SeverityLevel.MODERATE
                severity_conf = "medium"
                epidemic_risk = "moderate"
                requires_immediate_action = True
                requires_human_expert_review = False
                rubric_basis.append(
                    f"Late Blight lesions localized (<5% damage in {canopy}) under non-conducive weather. "
                    "Retains elevated epidemic risk compared to other foliar diseases."
                )
                scouting_recs.extend([
                    "Scout planting daily; if weather shifts to cool/wet, escalate protective sprays immediately.",
                    "Avoid overhead irrigation to keep foliage dry."
                ])

        # GENERAL PATHOGENS (Early Blight, Bacterial Spot):
        else:
            # CRITICAL LEVEL: Systemic canopy collapse (>=50% damage across whole plant/field)
            if (canopy in ["field_scale", "whole_plant"] and damage_pct >= 50.0):
                severity = SeverityLevel.CRITICAL
                severity_conf = "high"
                epidemic_risk = "critical"
                requires_immediate_action = True
                requires_human_expert_review = True
                rubric_basis.append(
                    f"Project heuristic CRITICAL: Severe systemic canopy collapse ({damage_pct:.1f}% foliar damage across {canopy})."
                )
                scouting_recs.extend([
                    "Evaluate economic feasibility of continued harvest versus crop termination.",
                    "Destroy and deeply plow under heavily infected crop residues following harvest to eliminate bacterial/fungal overwintering inoculum (UF/IFAS & UC IPM)."
                ])
            # HIGH LEVEL: >35% foliar damage, stem cankers/collar rot, or fruit lesions
            elif (
                damage_pct > 35.0 or
                has_fruit_involvement or
                has_stem_involvement or
                canopy in ["upper_canopy", "whole_plant"]
            ):
                severity = SeverityLevel.HIGH
                severity_conf = "high" if context.leaf_damage_percentage is not None else "medium"
                epidemic_risk = "moderate"
                requires_immediate_action = True
                requires_human_expert_review = False

                if has_fruit_involvement:
                    rubric_basis.append("Direct economic fruit involvement / lesions detected (marketable yield loss; Cornell & Purdue Extension).")
                if has_stem_involvement:
                    rubric_basis.append("Stem cankers / collar rot detected, threatening vascular transport (Purdue & UC IPM Extension).")
                if damage_pct > 35.0:
                    rubric_basis.append(f"Project heuristic HIGH: Extensive foliar defoliation ({damage_pct:.1f}% leaf area) exposing developing fruit to sunscald.")
                if canopy in ["upper_canopy", "whole_plant"]:
                    rubric_basis.append(f"Disease has progressed vertically into {canopy}.")

                scouting_recs.extend([
                    "Maintain strict 5- to 7-day preventative protectant spray coverage during warm, wet weather (Cornell & Purdue Extension).",
                    "Avoid overhead irrigation; use drip irrigation beneath mulch to keep foliage dry (Purdue & Cornell Extension).",
                    "Sanitize tools and never work in fields when foliage is wet from dew or rain (Cornell Extension)."
                ])
            # MODERATE LEVEL: 10% - 35% damage, or mid-canopy progression
            elif (
                10.0 <= damage_pct <= 35.0 or
                canopy == "mid_canopy"
            ):
                severity = SeverityLevel.MODERATE
                severity_conf = "high" if context.leaf_damage_percentage is not None else "medium"
                epidemic_risk = "moderate"
                requires_immediate_action = False
                requires_human_expert_review = False

                rubric_basis.append(
                    f"Project heuristic MODERATE: Established foliar lesions ({damage_pct:.1f}% damage) progressing to {canopy}. "
                    "Infection is established but remains confined to vegetative foliage without stem/fruit invasion."
                )
                scouting_recs.extend([
                    "Monitor canopy regularly (recommended: 3-5 days) for upward progression.",
                    "Ensure balanced nitrogen nutrition; avoid plant stress that accelerates early blight defoliation (UC IPM).",
                    "Apply protectant spray (e.g. chlorothalonil or copper/mancozeb tank-mix) prior to forecast rain events (Cornell & Purdue Extension)."
                ])
            # LOW LEVEL: < 10% damage, lower canopy only, leaves only
            else:
                severity = SeverityLevel.LOW
                severity_conf = "high" if context.leaf_damage_percentage is not None else "medium"
                epidemic_risk = "low"
                requires_immediate_action = False
                requires_human_expert_review = False

                rubric_basis.append(
                    f"Project heuristic LOW: Early, localized foliar lesions restricted to {damage_pct:.1f}% of leaf area in {canopy}. "
                    "No stem cankers, fruit lesions, or mid-canopy progression observed."
                )
                scouting_recs.extend([
                    "Prune infected lowermost leaves and suckers up to 12 inches above mulch line to improve air circulation and reduce inoculum (Purdue Extension).",
                    "Maintain preventative cultural sanitation, weed elimination, and drip irrigation.",
                    "Re-scout canopy in 4-5 days to verify absence of upward vertical progression."
                ])

        # Record uncertainty factors if identification confidence is modest
        if id_confidence < 0.85:
            uncertainty_factors.append(
                f"Model disease identification confidence is moderate ({id_confidence:.2%}). "
                "Verify pathogen diagnosis with a diagnostic laboratory or extension specialist."
            )
        if context.leaf_damage_percentage is None:
            uncertainty_factors.append(
                "Leaf damage percentage was not quantitatively supplied; severity estimated from canopy spread."
            )

        return RiskAssessmentResult(
            assessment_id=assessment_id,
            investigation_id=investigation.investigation_id,
            disease=disease,
            identification_confidence=id_confidence,
            assigned_severity=severity,
            severity_confidence=severity_conf,
            rubric_basis=rubric_basis,
            epidemic_risk=epidemic_risk,
            uncertainty_factors=uncertainty_factors,
            scouting_recommendations=scouting_recs,
            requires_immediate_action=requires_immediate_action,
            requires_human_expert_review=requires_human_expert_review,
            pesticide_safety_notice=MANDATORY_PESTICIDE_SAFETY_NOTICE
        )
