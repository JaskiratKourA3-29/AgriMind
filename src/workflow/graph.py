"""
LangGraph Workflow Architecture for AgriMind (Week 6).
Builds and compiles the StateGraph connecting Vision, RAG Retrieval, Investigation,
Risk Assessment, Decision Planning, Critic Verification, and Manual Review.
"""
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, START, END

from src.workflow.state import AgriMindState
from src.workflow.nodes import (
    validate_image_node,
    vision_node,
    retrieval_node,
    investigation_node,
    risk_assessment_node,
    decision_planning_node,
    critic_node,
    manual_review_node,
    finalize_output_node,
    reassessment_node
)


# =====================================================================
# Conditional Edge Routing Functions
# =====================================================================

def route_from_start(state: AgriMindState) -> str:
    """
    Routes from workflow START:
    If reassessment_trigger is provided -> adaptive reassessment flow.
    Otherwise -> initial image validation flow.
    """
    if state.get("reassessment_trigger"):
        return "reassessment"
    return "validate_image"


def route_after_reassessment(state: AgriMindState) -> str:
    """
    Routes from reassessment node:
    If validation error or terminal loop limit -> finalize_output.
    If new unvalidated image provided -> validate_image.
    Otherwise re-enters at retrieval to ground updated context in extension literature.
    """
    status = state.get("workflow_status")
    if status in ["error", "terminal_escalation"]:
        return "finalize_output"
    if state.get("image_status") == "unvalidated" and state.get("image_path"):
        return "validate_image"
    return "retrieval"


def route_after_validation(state: AgriMindState) -> str:
    """Routes to vision inference if image is valid, otherwise aborts to output."""
    if state.get("image_status") == "valid":
        return "vision"
    return "finalize_output"


def route_after_vision(state: AgriMindState) -> str:
    """Routes to retrieval if vision succeeded, otherwise aborts to output."""
    if state.get("workflow_status") == "error":
        return "finalize_output"
    return "retrieval"


def route_after_retrieval(state: AgriMindState) -> str:
    """Routes to investigation if retrieval succeeded, otherwise aborts."""
    if state.get("workflow_status") == "error":
        return "finalize_output"
    return "investigation"


def route_after_investigation(state: AgriMindState) -> str:
    """Routes to risk assessment if investigation succeeded, otherwise aborts."""
    if state.get("workflow_status") == "error":
        return "finalize_output"
    return "risk_assessment"


def route_after_risk_assessment(state: AgriMindState) -> str:
    """Routes to decision planning if risk assessment succeeded, otherwise aborts."""
    if state.get("workflow_status") == "error":
        return "finalize_output"
    return "decision_planning"


def route_after_decision_planning(state: AgriMindState) -> str:
    """Routes to critic verification if plan was generated, otherwise aborts."""
    if state.get("workflow_status") == "error":
        return "finalize_output"
    return "critic"


def route_after_critic(state: AgriMindState) -> str:
    """
    Evaluates verification result.
    If workflow encountered an error -> aborts directly to finalize output.
    If fully verified without manual review requirement -> finalize output.
    If rejected or requires human review -> manual_review node.
    """
    if state.get("workflow_status") == "error":
        return "finalize_output"
    verif = state.get("verification_result")
    if verif is not None and verif.is_verified and not verif.requires_manual_review:
        return "finalize_output"
    return "manual_review"


# =====================================================================
# Graph Construction and Compilation
# =====================================================================

def build_agrimind_workflow() -> Any:
    """
    Constructs and compiles the end-to-end AgriMind LangGraph workflow.
    """
    workflow = StateGraph(AgriMindState)

    # 1. Register Nodes
    workflow.add_node("validate_image", validate_image_node)
    workflow.add_node("vision", vision_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("investigation", investigation_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("decision_planning", decision_planning_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("manual_review", manual_review_node)
    workflow.add_node("finalize_output", finalize_output_node)
    workflow.add_node("reassessment", reassessment_node)

    # 2. Add Transitions & Conditional Edges
    workflow.add_conditional_edges(
        START,
        route_from_start,
        {
            "validate_image": "validate_image",
            "reassessment": "reassessment"
        }
    )

    workflow.add_conditional_edges(
        "reassessment",
        route_after_reassessment,
        {
            "finalize_output": "finalize_output",
            "validate_image": "validate_image",
            "retrieval": "retrieval"
        }
    )

    workflow.add_conditional_edges(
        "validate_image",
        route_after_validation,
        {
            "vision": "vision",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "vision",
        route_after_vision,
        {
            "retrieval": "retrieval",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "investigation": "investigation",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "investigation",
        route_after_investigation,
        {
            "risk_assessment": "risk_assessment",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "risk_assessment",
        route_after_risk_assessment,
        {
            "decision_planning": "decision_planning",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "decision_planning",
        route_after_decision_planning,
        {
            "critic": "critic",
            "finalize_output": "finalize_output"
        }
    )

    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "finalize_output": "finalize_output",
            "manual_review": "manual_review"
        }
    )

    workflow.add_edge("manual_review", "finalize_output")
    workflow.add_edge("finalize_output", END)

    # Compile the LangGraph application
    return workflow.compile()
