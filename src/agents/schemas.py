"""
Typed data schemas for AgriMind Agent Logic (Week 4).
Enforces structured, validated data exchange across Vision, Investigation, and Risk Assessment.
"""
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class SupportedTomatoDisease(str, Enum):
    """Supported tomato disease classes from Week 1-3 scope."""
    BACTERIAL_SPOT = "Tomato___Bacterial_spot"
    EARLY_BLIGHT = "Tomato___Early_blight"
    LATE_BLIGHT = "Tomato___Late_blight"


class SeverityLevel(str, Enum):
    """
    Project-defined disease severity classification levels.
    Synthesized as engineering categories from qualitative extension pathology literature
    (Cornell CALS, UF/IFAS, Purdue, UC IPM). These categories are project-specific
    operational heuristics and are not officially published standardized rubrics of those institutions.
    """
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    INDETERMINATE = "indeterminate"


class EvidenceStatus(str, Enum):
    """Evidence validity status characterizing confidence and data completeness."""
    SUFFICIENT = "sufficient"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    INSUFFICIENT_LITERATURE = "insufficient_literature"
    CONFLICTING = "conflicting"
    UNSUPPORTED_DISEASE = "unsupported_disease"


class VisionPrediction(BaseModel):
    """
    Structured output from AgriMind Vision Model (Week 2 ResNet-50).
    Separates predicted classification from disease severity.
    """
    predicted_class: str
    confidence: float = Field(ge=0.0, le=1.0)
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    model_name: str = "ResNet-50-Tomato3-Baseline"
    is_supported_disease: bool = True

    model_config = ConfigDict(extra="ignore")


class VisualContext(BaseModel):
    """
    Contextual agronomic metadata observed in the canopy or provided by grower.
    Fills the crucial gap between single-leaf classification and whole-plant severity.
    """
    leaf_damage_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    affected_organs: List[str] = Field(default_factory=lambda: ["leaves"])
    canopy_spread: Optional[str] = Field(
        default=None,
        description="Observed spread: 'lower_canopy', 'mid_canopy', 'upper_canopy', 'whole_plant', 'field_scale'"
    )
    weather_conditions: Optional[str] = Field(
        default=None,
        description="Conducive conditions: 'cool_wet', 'warm_humid', 'hot_dry', etc."
    )
    field_notes: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class RetrievedEvidence(BaseModel):
    """
    Structured agricultural extension literature retrieved by Week 3 LangChain RAG.
    """
    has_sufficient_evidence: bool = True
    query: str = ""
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_count: int = 0
    context_text: str = ""
    fallback_message: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class InvestigationResult(BaseModel):
    """
    Structured investigation synthesis produced by the Investigation Agent.
    Strictly separates model predictions, retrieved facts, and diagnostic conclusions.
    """
    investigation_id: str
    timestamp: str
    primary_diagnosis: str
    diagnosis_confidence: float
    visual_prediction: VisionPrediction
    visual_context: Optional[VisualContext] = None
    retrieved_evidence: RetrievedEvidence
    evidence_status: EvidenceStatus
    synthesis_narrative: str
    conflicts_detected: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class RiskAssessmentResult(BaseModel):
    """
    Structured severity and epidemic risk evaluation produced by the Risk Assessment Agent.
    Strictly decouples model identification confidence from agronomic severity.
    """
    assessment_id: str
    investigation_id: str
    disease: str
    identification_confidence: float
    assigned_severity: SeverityLevel
    severity_confidence: str  # "high", "medium", "low", "none"
    rubric_basis: List[str] = Field(default_factory=list)
    epidemic_risk: str  # "low", "moderate", "high", "critical", "unknown"
    uncertainty_factors: List[str] = Field(default_factory=list)
    scouting_recommendations: List[str] = Field(default_factory=list)
    requires_immediate_action: bool = False
    requires_human_expert_review: bool = False
    pesticide_safety_notice: Optional[str] = Field(
        default=(
            "MANDATORY PESTICIDE SAFETY NOTICE: Any chemical pesticide or bactericide application must strictly follow "
            "the registered EPA and state product label, including personal protective equipment (PPE), restricted-entry "
            "intervals (REI), and pre-harvest intervals (PHI). Consult your local university agricultural extension service "
            "or a certified crop advisor for legally registered, site-specific treatment recommendations."
        ),
        description="Mandatory regulatory and legal safety disclaimer accompanying chemical recommendations."
    )

    model_config = ConfigDict(extra="ignore")


class PlanUrgency(str, Enum):
    """Urgency level for agronomic management response."""
    LOW = "low"            # Preventative sanitation, normal cultivation
    MODERATE = "moderate"  # Routine scouting, preventative protectant sprays
    HIGH = "high"          # Immediate action, protectant/systemic coverage
    CRITICAL = "critical"  # Emergency intervention, rogueing, containment
    DEFERRED = "deferred"  # Automated guidance deferred pending expert review


class ManagementAction(BaseModel):
    """Structured individual agronomic management recommendation."""
    category: str  # "cultural", "resistant_variety", "chemical", "monitoring"
    action_summary: str
    details: str
    is_chemical: bool = False
    citation_numbers: List[int] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class DecisionPlan(BaseModel):
    """
    Structured agronomic decision plan produced by the Decision Planning Agent (Week 5).
    Organized strictly along the Integrated Pest Management (IPM) hierarchy.
    """
    plan_id: str
    assessment_id: str
    investigation_id: str
    disease: str
    urgency: PlanUrgency
    cultural_controls: List[ManagementAction] = Field(default_factory=list)
    resistant_varieties: List[ManagementAction] = Field(default_factory=list)
    chemical_controls: List[ManagementAction] = Field(default_factory=list)
    monitoring_actions: List[ManagementAction] = Field(default_factory=list)
    uncertainty_disclosures: List[str] = Field(default_factory=list)
    expert_review_required: bool = False
    pesticide_safety_notice: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class VerificationStatus(str, Enum):
    """Verification outcome produced by Critic/Verification Agent."""
    VERIFIED = "verified"
    REJECTED_UNSUPPORTED_CLAIMS = "rejected_unsupported_claims"
    REJECTED_SAFETY_VIOLATION = "rejected_safety_violation"
    REJECTED_INCONSISTENCY = "rejected_inconsistency"
    ESCALATED_MANUAL_REVIEW = "escalated_manual_review"


class VerificationResult(BaseModel):
    """
    Structured verification output produced by Critic/Verification Agent (Week 5).
    Enforces evidential consistency, citation grounding, and agricultural safety.
    """
    verification_id: str
    plan_id: str
    is_verified: bool
    status: VerificationStatus
    checks_passed: List[str] = Field(default_factory=list)
    issues_detected: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    requires_manual_review: bool = False
    escalation_reason: Optional[str] = None
    timestamp: str

    model_config = ConfigDict(extra="ignore")


class ReviewStatus(str, Enum):
    """State of a case in the manual-review feedback loop."""
    PENDING = "pending"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"
    TERMINAL_ESCALATION = "terminal_escalation"


class ManualReviewRecord(BaseModel):
    """
    Record of a case routed to the manual-review feedback loop (Week 5).
    Defines bounded re-entry into the decision workflow.
    """
    review_id: str
    plan_id: Optional[str] = None
    investigation_id: str
    assessment_id: Optional[str] = None
    flagged_by: str  # "RiskAssessmentAgent", "CriticAgent", "InvestigationAgent"
    trigger_reasons: List[str] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    status: ReviewStatus = ReviewStatus.PENDING
    expert_notes: Optional[str] = None
    corrected_diagnosis: Optional[str] = None
    iteration_count: int = 1
    max_iterations: int = 2
    submission_timestamp: str
    resolution_timestamp: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ReassessmentTrigger(str, Enum):
    """
    Triggers that warrant adaptive case re-evaluation in the AgriMind workflow (Week 7).
    """
    NEW_FIELD_OBSERVATION = "new_field_observation"      # E.g., follow-up photo, change in canopy spread or damage %
    WEATHER_UPDATE = "weather_update"                    # E.g., sudden cool/wet weather conducive to sporulation
    LAB_DIAGNOSTIC_UPDATE = "lab_diagnostic_update"      # E.g., laboratory microscopic spore/conidia confirmation
    TREATMENT_INEFFECTIVE = "treatment_ineffective"      # E.g., symptoms continuing/worsening after treatment


class ReassessmentOutcome(str, Enum):
    """Outcome of an adaptive reassessment cycle."""
    REVISED = "revised"                     # Successfully re-examined and revised decision produced
    UNRESOLVED = "unresolved"               # Reassessment inconclusive or conflicted, requires manual review
    ESCALATED = "escalated"                 # Exceeded iteration limit or critical pathogen safety alert


class ReassessmentRecord(BaseModel):
    """
    Audit record of an adaptive case reassessment cycle (Week 7).
    Preserves prior decisions, evidence updates, triggers, and outcomes.
    """
    reassessment_id: str
    case_id: str = "CASE-DEFAULT"
    reassessment_count: int = Field(ge=1, description="Iteration number of this reassessment cycle")
    max_reassessments: int = Field(default=2, description="Upper bound on reassessments per case")
    trigger: ReassessmentTrigger
    trigger_rationale: Optional[str] = None
    new_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Newly supplied agronomic observations (e.g. updated VisualContext fields, lab result, weather)"
    )
    prior_severity: Optional[str] = None
    revised_severity: Optional[str] = None
    prior_urgency: Optional[str] = None
    revised_urgency: Optional[str] = None
    prior_diagnosis: Optional[str] = None
    revised_diagnosis: Optional[str] = None
    outcome: ReassessmentOutcome = ReassessmentOutcome.REVISED
    is_terminal: bool = False
    notes: Optional[str] = None
    timestamp: str

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def validate_reassessment_payload(
        cls,
        trigger: Any,
        new_evidence: Any,
        current_count: int,
        max_reassessments: int = 2
    ) -> List[str]:
        """
        Validates input payload before launching a reassessment cycle.
        Returns a list of validation error messages (empty if valid).
        """
        errors: List[str] = []
        if not trigger:
            errors.append("Reassessment trigger is required.")
        elif isinstance(trigger, str):
            valid_values = [t.value for t in ReassessmentTrigger]
            if trigger not in valid_values:
                errors.append(f"Invalid trigger '{trigger}'. Must be one of: {valid_values}")
        elif not isinstance(trigger, ReassessmentTrigger):
            errors.append(f"Invalid trigger type: {type(trigger)}")

        if not isinstance(new_evidence, dict) or not new_evidence:
            errors.append("New evidence must be a non-empty dictionary containing agronomic observations.")

        if current_count >= max_reassessments:
            errors.append(
                f"Maximum reassessment limit ({max_reassessments}) exceeded. Further automated reassessments prohibited."
            )

        return errors

