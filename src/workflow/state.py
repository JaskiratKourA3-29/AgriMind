"""
State schema definitions for AgriMind LangGraph Orchestration (Week 6).
Carries typed diagnostic state across Vision, RAG Retrieval, Investigation,
Risk Assessment, Decision Planning, Critic Verification, and Manual Review.
"""
from typing import TypedDict, Optional, Dict, Any, List

from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    VerificationResult,
    ManualReviewRecord,
    ReassessmentRecord
)


class AgriMindState(TypedDict, total=False):
    """
    Typed, LangGraph-compatible state dictionary passed across the multi-agent workflow.
    Reuses existing Pydantic models from Weeks 2-5.
    """
    # 0. Case Identification
    case_id: Optional[str]

    # 1. Input Image Reference & Validation Status
    image_path: Optional[str]
    image_status: str  # "unvalidated", "valid", "invalid", "missing", "error"
    image_error: Optional[str]

    # 2. Contextual Metadata & Query
    visual_context: Optional[VisualContext]
    user_query: Optional[str]

    # 3. Intermediate Agent Outputs
    vision_prediction: Optional[VisionPrediction]
    retrieved_evidence: Optional[RetrievedEvidence]
    investigation_result: Optional[InvestigationResult]
    risk_assessment: Optional[RiskAssessmentResult]
    decision_plan: Optional[DecisionPlan]
    verification_result: Optional[VerificationResult]
    manual_review_record: Optional[ManualReviewRecord]

    # 4. Workflow Lifecycle Tracking
    workflow_status: str
    # Possible values:
    # "initialized", "image_validated", "vision_complete", "retrieval_complete",
    # "investigation_complete", "risk_assessed", "plan_generated", "verified",
    # "pending_manual_review", "review_resolved", "terminal_escalation",
    # "completed", "error", "reassessment_in_progress"
    error_message: Optional[str]

    # 5. Human-in-the-Loop Re-entry Parameters
    expert_diagnosis_override: Optional[str]
    expert_context_override: Optional[VisualContext]
    expert_notes: Optional[str]
    iteration_count: int
    max_iterations: int

    # 6. Adaptive Reassessment Mechanism (Week 7)
    reassessment_trigger: Optional[str]                  # E.g. "weather_update", "new_field_observation", etc.
    reassessment_new_evidence: Optional[Dict[str, Any]]  # New observations/context dictionary
    reassessment_rationale: Optional[str]                # Contextual explanation of the trigger
    reassessment_count: int                              # Iteration count of reassessments for this case
    max_reassessments: int                               # Maximum allowable reassessments (default 2)
    case_history: List[Dict[str, Any]]                   # Preserved history snapshots of prior iterations
    reassessment_records: List[ReassessmentRecord]       # Formal audit records of each reassessment cycle
    reassessment_status: Optional[str]                   # "none", "in_progress", "revised", "unresolved", "escalated"

    # 7. Final Structured Decision Output
    final_output: Optional[Dict[str, Any]]

