"""
Investigation Agent for AgriMind (Week 4).
Responsible for organizing, cross-referencing, and synthesizing visual predictions,
canopy observations, and retrieved agricultural extension literature.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    EvidenceStatus,
    SupportedTomatoDisease
)
from src.agents.prompts import (
    INVESTIGATION_SYSTEM_PROMPT,
    INVESTIGATION_USER_PROMPT_TEMPLATE
)
from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK


class InvestigationAgent:
    """
    Evidence synthesis agent. Integrates computer vision classifications with
    grower canopy observations and accredited extension literature.
    """
    def __init__(
        self,
        retriever: Optional[AgrimindRetriever] = None,
        llm: Optional[Any] = None
    ):
        self.retriever = retriever or AgrimindRetriever()
        self.llm = llm

    def investigate(
        self,
        vision_prediction: VisionPrediction,
        visual_context: Optional[VisualContext] = None,
        retrieved_evidence: Optional[RetrievedEvidence] = None,
        user_query: Optional[str] = None
    ) -> InvestigationResult:
        """
        Executes diagnostic evidence cross-examination and structures the investigation result.
        """
        investigation_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Scope & Disease Support Validation
        supported_classes = [d.value for d in SupportedTomatoDisease]
        is_supported = vision_prediction.predicted_class in supported_classes
        vision_prediction.is_supported_disease = is_supported

        # 2. Retrieve literature evidence if not explicitly supplied
        if retrieved_evidence is None:
            query = user_query or f"Management and diagnostic symptoms of {vision_prediction.predicted_class}"
            disease_filter = vision_prediction.predicted_class if is_supported else None
            
            raw_retrieval = self.retriever.retrieve(
                query=query,
                disease_target=disease_filter,
                top_k=4
            )
            retrieved_evidence = RetrievedEvidence(
                has_sufficient_evidence=raw_retrieval.get("has_sufficient_evidence", False),
                query=query,
                citations=raw_retrieval.get("citations", []),
                retrieved_count=raw_retrieval.get("retrieved_count", 0),
                context_text=raw_retrieval.get("context_text", ""),
                fallback_message=raw_retrieval.get("fallback_message")
            )

        # 3. Detect Conflicts and Anomalies
        conflicts_detected: List[str] = []
        limitations: List[str] = []

        if not is_supported:
            conflicts_detected.append(
                f"Pathogen '{vision_prediction.predicted_class}' is outside AgriMind's 3-class verified tomato scope."
            )

        # Vision prediction confidence checks
        if vision_prediction.confidence < 0.60:
            conflicts_detected.append(
                f"Low model classification confidence ({vision_prediction.confidence:.2%}). "
                "Prediction is ambiguous and requires physical scouting confirmation."
            )

        # Multi-class distribution ambiguity check
        if vision_prediction.class_probabilities:
            sorted_probs = sorted(vision_prediction.class_probabilities.values(), reverse=True)
            if len(sorted_probs) >= 2 and (sorted_probs[0] - sorted_probs[1]) < 0.15:
                conflicts_detected.append(
                    f"Ambiguous classification margin: Top class margin is only {(sorted_probs[0] - sorted_probs[1]):.2%}. "
                    "Close runner-up class detected."
                )

        # Symptomological cross-checks with field notes
        if visual_context and visual_context.field_notes:
            notes_lower = visual_context.field_notes.lower()
            pred = vision_prediction.predicted_class

            # Early Blight vs Late Blight confusion check
            if "Tomato___Late_blight" in pred and ("concentric" in notes_lower or "target" in notes_lower or "bullseye" in notes_lower):
                conflicts_detected.append(
                    "Symptom conflict: Field notes describe concentric target rings typical of Early Blight (Alternaria solani), "
                    "conflicting with visual prediction of Late Blight (Phytophthora infestans)."
                )
            # Bacterial Spot vs Late Blight confusion check
            if "Tomato___Bacterial_spot" in pred and ("white sporulation" in notes_lower or "cottony" in notes_lower):
                conflicts_detected.append(
                    "Symptom conflict: Field notes report white sporulation/mold typical of Late Blight, "
                    "conflicting with visual prediction of Bacterial Spot (bacterial disease)."
                )
            # Weather epidemiology mismatch check
            if visual_context.weather_conditions:
                weather_lower = visual_context.weather_conditions.lower()
                if "Tomato___Late_blight" in pred and ("hot" in weather_lower or "dry" in weather_lower or ">30" in weather_lower):
                    conflicts_detected.append(
                        "Epidemiological conflict: Hot/dry weather (>30°C) reported, which halts Phytophthora infestans "
                        "sporulation and spread. Late Blight thrives strictly in cool, humid weather."
                    )

        # 4. Context completeness audit
        if visual_context is None or (
            visual_context.leaf_damage_percentage is None and
            visual_context.canopy_spread is None
        ):
            limitations.append(
                "Visual evidence restricted to single cropped leaf; lacks canopy spread and damage percentage metadata."
            )

        if not retrieved_evidence.has_sufficient_evidence:
            limitations.append(
                "Knowledge base contains insufficient peer-reviewed agricultural literature for this query."
            )

        # 5. Determine Overall Evidence Status
        if not is_supported:
            evidence_status = EvidenceStatus.UNSUPPORTED_DISEASE
        elif conflicts_detected:
            evidence_status = EvidenceStatus.CONFLICTING
        elif not retrieved_evidence.has_sufficient_evidence:
            evidence_status = EvidenceStatus.INSUFFICIENT_LITERATURE
        elif visual_context is None or (
            visual_context.leaf_damage_percentage is None and
            visual_context.canopy_spread is None
        ):
            evidence_status = EvidenceStatus.INSUFFICIENT_CONTEXT
        else:
            evidence_status = EvidenceStatus.SUFFICIENT

        # 6. Format Synthesis Narrative (Deterministic Grounded Synthesis)
        synthesis = self._build_deterministic_synthesis(
            vision_prediction=vision_prediction,
            visual_context=visual_context,
            retrieved_evidence=retrieved_evidence,
            evidence_status=evidence_status,
            conflicts=conflicts_detected,
            limitations=limitations
        )

        return InvestigationResult(
            investigation_id=investigation_id,
            timestamp=timestamp,
            primary_diagnosis=vision_prediction.predicted_class,
            diagnosis_confidence=vision_prediction.confidence,
            visual_prediction=vision_prediction,
            visual_context=visual_context,
            retrieved_evidence=retrieved_evidence,
            evidence_status=evidence_status,
            synthesis_narrative=synthesis,
            conflicts_detected=conflicts_detected,
            limitations=limitations,
            citations=retrieved_evidence.citations
        )

    def _build_deterministic_synthesis(
        self,
        vision_prediction: VisionPrediction,
        visual_context: Optional[VisualContext],
        retrieved_evidence: RetrievedEvidence,
        evidence_status: EvidenceStatus,
        conflicts: List[str],
        limitations: List[str]
    ) -> str:
        """
        Generates a transparent, structured diagnostic narrative delineating
        model predictions, field observations, and literature citations.
        """
        lines = []
        lines.append("### AGRI-MIND INVESTIGATION BRIEF\n")

        # Section 1: Visual Model Findings
        lines.append("#### 1. Visual Model Classification")
        lines.append(f"- **Primary Pathogen Predicted:** `{vision_prediction.predicted_class}`")
        lines.append(f"- **Classification Confidence:** `{vision_prediction.confidence:.2%}` (Model: {vision_prediction.model_name})")
        if vision_prediction.class_probabilities:
            prob_str = ", ".join(f"{k.split('___')[-1]}: {v:.2%}" for k, v in vision_prediction.class_probabilities.items())
            lines.append(f"- **Class Probability Distribution:** {prob_str}")
        lines.append(f"- **Scope Status:** {'In-Scope Tomato Pathogen' if vision_prediction.is_supported_disease else 'OUT-OF-SCOPE / UNSUPPORTED'}")

        # Section 2: Canopy & Field Observations
        lines.append("\n#### 2. Field & Canopy Observations")
        if visual_context:
            dmg = f"{visual_context.leaf_damage_percentage:.1f}%" if visual_context.leaf_damage_percentage is not None else "Not specified"
            lines.append(f"- **Estimated Leaf Area Damaged:** {dmg}")
            lines.append(f"- **Organs Involved:** {', '.join(visual_context.affected_organs)}")
            lines.append(f"- **Canopy Spread Level:** {visual_context.canopy_spread or 'Unspecified'}")
            lines.append(f"- **Microclimate Weather:** {visual_context.weather_conditions or 'Unrecorded'}")
            if visual_context.field_notes:
                lines.append(f"- **Grower Notes:** \"{visual_context.field_notes}\"")
        else:
            lines.append("- *No field context provided. Diagnosis based solely on cropped leaf image.*")

        # Section 3: Extension Literature Corroboration
        lines.append("\n#### 3. Extension Literature Evidence")
        if retrieved_evidence.has_sufficient_evidence and retrieved_evidence.citations:
            lines.append(f"- **Corroborating Sources ({len(retrieved_evidence.citations)}):**")
            for cit in retrieved_evidence.citations:
                c_num = cit.get("citation_number", 1)
                title = cit.get("title", "Extension Guide")
                inst = cit.get("institution", "Agricultural Extension")
                sim = cit.get("similarity_score", 0.0)
                url = cit.get("source_url", "")
                lines.append(f"  - [{c_num}] *{title}* ({inst}, Sim: {sim:.4f}) - [Source]({url})")
        else:
            fallback = retrieved_evidence.fallback_message or INSUFFICIENT_EVIDENCE_FALLBACK
            lines.append(f"- *{fallback}*")

        # Section 4: Conflict & Evidence Status
        lines.append(f"\n#### 4. Diagnostic Assessment Status: `{evidence_status.value.upper()}`")
        if conflicts:
            lines.append("**Identified Discrepancies:**")
            for c in conflicts:
                lines.append(f"- ⚠️ {c}")
        if limitations:
            lines.append("**Known Limitations:**")
            for lim in limitations:
                lines.append(f"- ℹ️ {lim}")

        return "\n".join(lines)
