"""
Graph Node definitions for AgriMind LangGraph Orchestration (Week 6).
Implements robust node execution for image validation, vision inference, RAG retrieval,
investigation, risk assessment, decision planning, critic verification, manual review,
and final output synthesis.
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from src.workflow.state import AgriMindState
from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    VerificationResult,
    ManualReviewRecord,
    ReviewStatus,
    VerificationStatus,
    EvidenceStatus,
    ReassessmentTrigger,
    ReassessmentOutcome,
    ReassessmentRecord
)
from src.vision.inference import VisionInferenceEngine
from src.rag.retriever import AgrimindRetriever
from src.agents.investigation import InvestigationAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.agents.decision_planning import DecisionPlanningAgent
from src.agents.critic import CriticAgent
from src.agents.feedback_loop import ManualReviewFeedbackLoop


class WorkflowNodeRegistry:
    """
    Container providing singleton access or dependency injection for workflow agents.
    """
    def __init__(
        self,
        vision_engine: Optional[VisionInferenceEngine] = None,
        retriever: Optional[AgrimindRetriever] = None,
        investigation_agent: Optional[InvestigationAgent] = None,
        risk_agent: Optional[RiskAssessmentAgent] = None,
        decision_planner: Optional[DecisionPlanningAgent] = None,
        critic_agent: Optional[CriticAgent] = None,
        feedback_loop: Optional[ManualReviewFeedbackLoop] = None
    ):
        self.vision_engine = vision_engine or VisionInferenceEngine()
        self.retriever = retriever or AgrimindRetriever()
        self.investigation_agent = investigation_agent or InvestigationAgent(retriever=self.retriever)
        self.risk_agent = risk_agent or RiskAssessmentAgent()
        self.decision_planner = decision_planner or DecisionPlanningAgent()
        self.critic_agent = critic_agent or CriticAgent()
        self.feedback_loop = feedback_loop or ManualReviewFeedbackLoop(max_iterations=2)


# Default module-level registry
_DEFAULT_REGISTRY: Optional[WorkflowNodeRegistry] = None

def get_node_registry() -> WorkflowNodeRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = WorkflowNodeRegistry()
    return _DEFAULT_REGISTRY

def set_node_registry(registry: WorkflowNodeRegistry):
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = registry


# =====================================================================
# Node 1: Image Validation Node
# =====================================================================
def validate_image_node(state: AgriMindState) -> Dict[str, Any]:
    """Validates that image input reference exists, is accessible, and has a valid image format."""
    image_path = state.get("image_path")

    if not image_path or not isinstance(image_path, str) or not image_path.strip():
        return {
            "image_status": "missing",
            "workflow_status": "error",
            "error_message": "Input image path was not provided or is empty."
        }

    clean_path = image_path.strip()
    if not os.path.exists(clean_path):
        return {
            "image_status": "invalid",
            "workflow_status": "error",
            "error_message": f"Image file not found at path: {clean_path}"
        }

    # Verify image magic bytes without loading full library
    try:
        with open(clean_path, "rb") as f:
            header = f.read(16)
        if not header:
            return {
                "image_status": "invalid",
                "workflow_status": "error",
                "error_message": f"Image file is empty (0 bytes): {clean_path}"
            }
        is_jpeg = header.startswith(b"\xff\xd8")
        is_png = header.startswith(b"\x89PNG")
        is_gif = header.startswith(b"GIF")
        is_bmp = header.startswith(b"BM")
        if not (is_jpeg or is_png or is_gif or is_bmp):
            return {
                "image_status": "invalid",
                "workflow_status": "error",
                "error_message": f"Unsupported or corrupted image file format: {clean_path}"
            }

        # Verify image integrity (detect corrupt or unreadable bitstream)
        from src.vision.inference import verify_image_integrity
        if not verify_image_integrity(clean_path):
            return {
                "image_status": "invalid",
                "workflow_status": "error",
                "error_message": f"Corrupted or unreadable image file: {clean_path}"
            }
    except Exception as e:
        return {
            "image_status": "error",
            "workflow_status": "error",
            "error_message": f"Failed reading image file: {str(e)}"
        }

    return {
        "image_status": "valid",
        "workflow_status": "image_validated"
    }


# =====================================================================
# Node 2: Vision Inference Node
# =====================================================================
def vision_node(state: AgriMindState) -> Dict[str, Any]:
    """Executes ResNet-50 vision classification or preserves injected prediction."""
    # If prediction was already injected (e.g. by a test fixture)
    if state.get("vision_prediction") is not None:
        return {"workflow_status": "vision_complete"}

    image_path = state.get("image_path")
    registry = get_node_registry()

    try:
        prediction = registry.vision_engine.predict(image_path)
        return {
            "vision_prediction": prediction,
            "workflow_status": "vision_complete"
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Vision classification failed: {str(e)}"
        }


# =====================================================================
# Node 3: Agricultural Evidence Retrieval Node
# =====================================================================
def retrieval_node(state: AgriMindState) -> Dict[str, Any]:
    """Retrieves relevant extension literature using LangChain RAG pipeline."""
    # If retrieved evidence was pre-injected
    if state.get("retrieved_evidence") is not None:
        return {"workflow_status": "retrieval_complete"}

    vision_pred = state.get("vision_prediction")
    if not vision_pred:
        return {
            "workflow_status": "error",
            "error_message": "Vision prediction missing prior to evidence retrieval."
        }

    registry = get_node_registry()
    if "healthy" in vision_pred.predicted_class.lower():
        query = state.get("user_query") or "Agronomic practices and preventative maintenance for healthy tomato foliage"
        disease_filter = None
    else:
        disease_filter = vision_pred.predicted_class if vision_pred.is_supported_disease else None
        query = state.get("user_query") or f"Management and diagnostic symptoms of {vision_pred.predicted_class}"

    try:
        raw_retrieval = registry.retriever.retrieve(
            query=query,
            disease_target=disease_filter,
            top_k=4
        )
        evidence = RetrievedEvidence(
            has_sufficient_evidence=raw_retrieval.get("has_sufficient_evidence", False),
            query=query,
            citations=raw_retrieval.get("citations", []),
            retrieved_count=raw_retrieval.get("retrieved_count", 0),
            context_text=raw_retrieval.get("context_text", ""),
            fallback_message=raw_retrieval.get("fallback_message")
        )
        return {
            "retrieved_evidence": evidence,
            "workflow_status": "retrieval_complete"
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Knowledge base retrieval failed: {str(e)}"
        }


# =====================================================================
# Node 4: Investigation Agent Node
# =====================================================================
def investigation_node(state: AgriMindState) -> Dict[str, Any]:
    """Synthesizes visual classification, canopy observations, and extension literature."""
    vision_pred = state.get("vision_prediction")
    visual_context = state.get("visual_context")
    retrieved_evidence = state.get("retrieved_evidence")

    if not vision_pred or not retrieved_evidence:
        return {
            "workflow_status": "error",
            "error_message": "Investigation node requires vision prediction and retrieved evidence."
        }

    registry = get_node_registry()
    try:
        inv_result = registry.investigation_agent.investigate(
            vision_prediction=vision_pred,
            visual_context=visual_context,
            retrieved_evidence=retrieved_evidence,
            user_query=state.get("user_query")
        )
        return {
            "investigation_result": inv_result,
            "workflow_status": "investigation_complete"
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Investigation agent failed: {str(e)}"
        }


# =====================================================================
# Node 5: Risk Assessment Agent Node
# =====================================================================
def risk_assessment_node(state: AgriMindState) -> Dict[str, Any]:
    """Characterizes physical disease severity, epidemic velocity, and urgency."""
    inv_result = state.get("investigation_result")
    if not inv_result:
        return {
            "workflow_status": "error",
            "error_message": "Risk assessment requires completed investigation result."
        }

    registry = get_node_registry()
    try:
        risk_result = registry.risk_agent.assess_risk(inv_result)
        return {
            "risk_assessment": risk_result,
            "workflow_status": "risk_assessed"
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Risk assessment agent failed: {str(e)}"
        }


# =====================================================================
# Node 6: Decision Planning Agent Node
# =====================================================================
def decision_planning_node(state: AgriMindState) -> Dict[str, Any]:
    """Generates structured IPM management guidance with citation traceability."""
    inv_result = state.get("investigation_result")
    risk_result = state.get("risk_assessment")

    if not inv_result or not risk_result:
        return {
            "workflow_status": "error",
            "error_message": "Decision planning requires investigation and risk assessment results."
        }

    registry = get_node_registry()
    try:
        plan = registry.decision_planner.plan_decision(inv_result, risk_result)
        return {
            "decision_plan": plan,
            "workflow_status": "plan_generated"
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Decision planning agent failed: {str(e)}"
        }


# =====================================================================
# Node 7: Critic/Verification Agent Node
# =====================================================================
def critic_node(state: AgriMindState) -> Dict[str, Any]:
    """Audits decision plan for evidential consistency, citations, and chemical safety."""
    plan = state.get("decision_plan")
    inv_result = state.get("investigation_result")
    risk_result = state.get("risk_assessment")

    if not plan or not inv_result or not risk_result:
        return {
            "workflow_status": "error",
            "error_message": "Critic verification requires plan, investigation, and risk assessment."
        }

    registry = get_node_registry()
    try:
        verif = registry.critic_agent.verify_plan(plan, inv_result, risk_result)
        status = "verified" if verif.is_verified and not verif.requires_manual_review else "critic_rejected"
        return {
            "verification_result": verif,
            "workflow_status": status
        }
    except Exception as e:
        return {
            "workflow_status": "error",
            "error_message": f"Critic verification agent failed: {str(e)}"
        }


# =====================================================================
# Node 8: Manual Review & Feedback Loop Node
# =====================================================================
def manual_review_node(state: AgriMindState) -> Dict[str, Any]:
    """
    Manages routing of ambiguous/rejected cases to manual review and bounded re-entry.
    Returns explicit pending status if no reviewer is actively connected.
    """
    inv_result = state.get("investigation_result")
    risk_result = state.get("risk_assessment")
    plan = state.get("decision_plan")
    verif = state.get("verification_result")

    registry = get_node_registry()

    # Retrieve or create ManualReviewRecord
    record = state.get("manual_review_record")
    if record is None and inv_result is not None:
        record = registry.feedback_loop.route_to_review(inv_result, risk_result, plan, verif)

    if record is None:
        return {
            "workflow_status": "error",
            "error_message": "Failed initializing manual review record."
        }

    # Check if expert inputs are provided for re-entry
    expert_diag = state.get("expert_diagnosis_override")
    expert_context = state.get("expert_context_override")
    expert_notes = state.get("expert_notes")

    if expert_diag or expert_context or expert_notes:
        resolution = registry.feedback_loop.resolve_review(
            record=record,
            investigation_agent=registry.investigation_agent,
            risk_agent=registry.risk_agent,
            decision_planner=registry.decision_planner,
            critic_agent=registry.critic_agent,
            expert_diagnosis=expert_diag,
            corrected_context=expert_context,
            expert_notes=expert_notes
        )

        res_status = resolution.get("status")
        if res_status == ReviewStatus.APPROVED:
            return {
                "manual_review_record": record,
                "investigation_result": resolution.get("investigation"),
                "risk_assessment": resolution.get("risk"),
                "decision_plan": resolution.get("plan"),
                "verification_result": resolution.get("verification"),
                "workflow_status": "review_resolved"
            }
        elif res_status == ReviewStatus.TERMINAL_ESCALATION:
            return {
                "manual_review_record": record,
                "workflow_status": "terminal_escalation",
                "error_message": resolution.get("message")
            }
        else:
            return {
                "manual_review_record": record,
                "workflow_status": "pending_manual_review",
                "error_message": resolution.get("message")
            }

    # No expert connected: Return explicit pending review state
    return {
        "manual_review_record": record,
        "workflow_status": "pending_manual_review"
    }


# =====================================================================
# Node 9: Final Output Node
# =====================================================================
def finalize_output_node(state: AgriMindState) -> Dict[str, Any]:
    """Compiles the final structured decision summary and preserves citations/pesticide notices."""
    status = state.get("workflow_status", "unknown")
    plan = state.get("decision_plan")
    verif = state.get("verification_result")
    review = state.get("manual_review_record")
    inv = state.get("investigation_result")
    risk = state.get("risk_assessment")
    vision = state.get("vision_prediction")

    final_output = {
        "workflow_status": status,
        "image_path": state.get("image_path"),
        "primary_diagnosis": inv.primary_diagnosis if inv else (vision.predicted_class if vision else None),
        "diagnosis_confidence": inv.diagnosis_confidence if inv else (vision.confidence if vision else None),
        "assigned_severity": risk.assigned_severity.value if risk else None,
        "epidemic_risk": risk.epidemic_risk if risk else None,
        "plan_urgency": plan.urgency.value if plan else None,
        "is_verified": verif.is_verified if verif else False,
        "verification_status": verif.status.value if verif else None,
        "requires_manual_review": (review is not None) or (verif.requires_manual_review if verif else False),
        "manual_review_status": review.status.value if review else None,
        "citations": plan.citations if plan else (inv.citations if inv else []),
        "pesticide_safety_notice": plan.pesticide_safety_notice if plan else None,
        "error_message": state.get("error_message")
    }

    # Determine final workflow status
    if status in ["verified", "review_resolved"]:
        final_workflow_status = "completed"
    else:
        final_workflow_status = status

    # Check if this state went through an adaptive reassessment cycle
    reassessment_trigger_val = state.get("reassessment_trigger")
    reassessment_count = state.get("reassessment_count", 0)
    case_history = list(state.get("case_history") or [])
    reassessment_records = list(state.get("reassessment_records") or [])

    if reassessment_trigger_val and case_history and status != "terminal_escalation":
        prior = case_history[-1]
        prior_sev = prior.get("assigned_severity")
        prior_urg = prior.get("plan_urgency")
        prior_diag = prior.get("primary_diagnosis")

        revised_sev = risk.assigned_severity.value if risk else None
        revised_urg = plan.urgency.value if plan else None
        revised_diag = inv.primary_diagnosis if inv else (vision.predicted_class if vision else None)

        # Determine reassessment outcome
        if status == "terminal_escalation":
            outcome = ReassessmentOutcome.ESCALATED
            is_term = True
        elif verif and verif.is_verified:
            outcome = ReassessmentOutcome.REVISED
            is_term = False
        else:
            outcome = ReassessmentOutcome.UNRESOLVED
            is_term = False

        try:
            trigger_enum = ReassessmentTrigger(reassessment_trigger_val)
        except Exception:
            trigger_enum = ReassessmentTrigger.NEW_FIELD_OBSERVATION

        record = ReassessmentRecord(
            reassessment_id=f"REASSESS-{uuid.uuid4().hex[:8].upper()}",
            case_id=state.get("case_id", "CASE-DEFAULT"),
            reassessment_count=reassessment_count,
            max_reassessments=state.get("max_reassessments", 2),
            trigger=trigger_enum,
            trigger_rationale=state.get("reassessment_rationale"),
            new_evidence=state.get("reassessment_new_evidence") or {},
            prior_severity=prior_sev,
            revised_severity=revised_sev,
            prior_urgency=prior_urg,
            revised_urgency=revised_urg,
            prior_diagnosis=prior_diag,
            revised_diagnosis=revised_diag,
            outcome=outcome,
            is_terminal=is_term,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        reassessment_records.append(record)
        state_reassessment_status = outcome.value
    elif state.get("reassessment_status"):
        state_reassessment_status = state.get("reassessment_status")
    else:
        state_reassessment_status = "none"

    final_output["reassessment_count"] = reassessment_count
    final_output["reassessment_outcome"] = state_reassessment_status
    final_output["case_history_length"] = len(case_history)
    final_output["reassessment_records"] = [
        r.model_dump() if hasattr(r, "model_dump") else r for r in reassessment_records
    ]

    return {
        "final_output": final_output,
        "workflow_status": final_workflow_status,
        "reassessment_records": reassessment_records,
        "reassessment_status": state_reassessment_status,
        # Clear transient trigger to ensure clean next execution
        "reassessment_trigger": None
    }


# =====================================================================
# Node 10: Adaptive Reassessment Node (Week 7)
# =====================================================================
def reassessment_node(state: AgriMindState) -> Dict[str, Any]:
    """
    Evaluates new evidence or feedback to resume/re-examine a case adaptively.
    Validates triggers, snapshots prior context into case_history, updates
    contextual evidence, enforces the 2-iteration loop ceiling, and routes
    to workflow re-examination or terminal escalation.
    """
    trigger_raw = state.get("reassessment_trigger")
    new_evidence = state.get("reassessment_new_evidence")
    current_count = state.get("reassessment_count", 0)
    max_reassessments = state.get("max_reassessments", 2)
    case_history = list(state.get("case_history") or [])
    reassessment_records = list(state.get("reassessment_records") or [])

    # Validate trigger and new evidence payload
    errors = ReassessmentRecord.validate_reassessment_payload(
        trigger=trigger_raw,
        new_evidence=new_evidence,
        current_count=current_count,
        max_reassessments=max_reassessments
    )

    if errors:
        # Check if error is due to loop limit exceeded
        if current_count >= max_reassessments:
            try:
                trig = ReassessmentTrigger(trigger_raw)
            except Exception:
                trig = ReassessmentTrigger.NEW_FIELD_OBSERVATION

            terminal_record = ReassessmentRecord(
                reassessment_id=f"REASSESS-{uuid.uuid4().hex[:8].upper()}",
                case_id=state.get("case_id", "CASE-DEFAULT"),
                reassessment_count=current_count,
                max_reassessments=max_reassessments,
                trigger=trig,
                trigger_rationale="Loop ceiling reached; automated reassessment prohibited.",
                new_evidence=new_evidence if isinstance(new_evidence, dict) else {},
                outcome=ReassessmentOutcome.ESCALATED,
                is_terminal=True,
                notes="Maximum reassessment iterations (2) reached for this case. Permanent escalation to extension clinic.",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            reassessment_records.append(terminal_record)
            return {
                "workflow_status": "terminal_escalation",
                "reassessment_status": "escalated",
                "error_message": f"Maximum reassessment limit ({max_reassessments}) exceeded. Permanent escalation required.",
                "reassessment_records": reassessment_records
            }
        else:
            return {
                "workflow_status": "error",
                "reassessment_status": "unresolved",
                "error_message": "; ".join(errors)
            }

    # Normalize trigger enum
    trigger = ReassessmentTrigger(trigger_raw) if isinstance(trigger_raw, str) else trigger_raw

    # Capture prior snapshot to preserve in case_history
    inv = state.get("investigation_result")
    risk = state.get("risk_assessment")
    plan = state.get("decision_plan")
    verif = state.get("verification_result")
    vision = state.get("vision_prediction")
    final = state.get("final_output") or {}

    prior_snapshot = {
        "iteration": current_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "primary_diagnosis": inv.primary_diagnosis if inv else (final.get("primary_diagnosis") or (vision.predicted_class if vision else None)),
        "diagnosis_confidence": inv.diagnosis_confidence if inv else (final.get("diagnosis_confidence") or (vision.confidence if vision else None)),
        "assigned_severity": risk.assigned_severity.value if risk else final.get("assigned_severity"),
        "epidemic_risk": risk.epidemic_risk if risk else final.get("epidemic_risk"),
        "plan_urgency": plan.urgency.value if plan else final.get("plan_urgency"),
        "is_verified": verif.is_verified if verif else final.get("is_verified", False),
        "visual_context": state.get("visual_context").model_dump() if state.get("visual_context") else None,
        "trigger": trigger.value
    }
    case_history.append(prior_snapshot)

    # Increment iteration count
    next_count = current_count + 1

    # Update visual context with new evidence
    old_context = state.get("visual_context")
    context_dict = old_context.model_dump() if old_context else {}

    # Merge new evidence fields
    for field in ["leaf_damage_percentage", "affected_organs", "canopy_spread", "weather_conditions", "field_notes"]:
        if field in new_evidence and new_evidence[field] is not None:
            context_dict[field] = new_evidence[field]

    # Specific trigger handling
    updated_vision = vision
    if trigger == ReassessmentTrigger.LAB_DIAGNOSTIC_UPDATE:
        lab_disease = new_evidence.get("lab_confirmed_disease") or new_evidence.get("confirmed_pathogen")
        if lab_disease:
            if "bacterial" in lab_disease.lower() or "xanthomonas" in lab_disease.lower():
                norm_disease = "Tomato___Bacterial_spot"
            elif "early" in lab_disease.lower() or "alternaria" in lab_disease.lower():
                norm_disease = "Tomato___Early_blight"
            elif "late" in lab_disease.lower() or "phytophthora" in lab_disease.lower():
                norm_disease = "Tomato___Late_blight"
            else:
                norm_disease = lab_disease

            updated_vision = VisionPrediction(
                predicted_class=norm_disease,
                confidence=1.0,
                class_probabilities={norm_disease: 1.0},
                model_name="Laboratory-Diagnostic-Confirmation",
                is_supported_disease=norm_disease in [
                    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___Late_blight"
                ]
            )
            context_dict["field_notes"] = (context_dict.get("field_notes") or "") + f" [Lab confirmation: {norm_disease}]"

    elif trigger == ReassessmentTrigger.TREATMENT_INEFFECTIVE:
        t_notes = new_evidence.get("treatment_notes") or "Previous treatment yielded no reduction in foliar lesions."
        context_dict["field_notes"] = (context_dict.get("field_notes") or "") + f" [Treatment alert: {t_notes}]"

    elif trigger == ReassessmentTrigger.WEATHER_UPDATE:
        w_update = new_evidence.get("weather_conditions")
        if w_update:
            context_dict["weather_conditions"] = w_update
            context_dict["field_notes"] = (context_dict.get("field_notes") or "") + f" [Weather update: {w_update}]"

    updated_context = VisualContext(**context_dict)

    # Check if a new image was provided
    new_image_path = new_evidence.get("image_path") or new_evidence.get("new_image_path")
    image_status = "unvalidated" if new_image_path else state.get("image_status", "valid")
    image_path = new_image_path if new_image_path else state.get("image_path")

    return {
        "reassessment_count": next_count,
        "max_reassessments": max_reassessments,
        "case_history": case_history,
        "reassessment_records": reassessment_records,
        "visual_context": updated_context,
        "vision_prediction": updated_vision,
        "image_path": image_path,
        "image_status": image_status,
        "workflow_status": "reassessment_in_progress",
        "reassessment_status": "in_progress",
        # Clear transient outputs to ensure fresh downstream agent execution
        "decision_plan": None,
        "verification_result": None
    }


def reassess_case(
    workflow_app: Any,
    completed_state: AgriMindState,
    trigger: Any,
    new_evidence: Dict[str, Any],
    rationale: Optional[str] = None
) -> AgriMindState:
    """
    Convenience function to trigger an adaptive reassessment on a previously completed case.
    Accepts the compiled LangGraph workflow, the previous state, new evidence, and trigger.
    """
    trigger_str = trigger.value if isinstance(trigger, ReassessmentTrigger) else str(trigger)
    reassess_input = dict(completed_state)
    reassess_input["reassessment_trigger"] = trigger_str
    reassess_input["reassessment_new_evidence"] = new_evidence
    reassess_input["reassessment_rationale"] = rationale
    return workflow_app.invoke(reassess_input)

