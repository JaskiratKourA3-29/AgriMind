"""
Unit and Integration Tests for AgriMind Investigation and Risk Assessment Agents (Week 4).
Tests:
- Sufficient visual and contextual evidence handling
- Missing canopy context handling (single cropped leaf)
- Conflicting visual vs symptomological evidence handling
- Unknown / unsupported disease handling
- Severity rubric mapping across LOW, MODERATE, HIGH, CRITICAL, and INDETERMINATE
- Decoupling of identification confidence from disease severity
- Prevention of unsupported conclusions
- Output schema integrity and citation provenance preservation
Strictly read-only against the active vector database (zero index rebuilds).
"""
import os
import sys
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.agents.schemas import (
    VisionPrediction,
    VisualContext,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    SeverityLevel,
    EvidenceStatus
)
from src.agents.investigation import InvestigationAgent
from src.agents.risk_assessment import RiskAssessmentAgent
from src.rag.retriever import AgrimindRetriever, DEFAULT_CHROMA_DIR, COLLECTION_NAME


class TestAgriMindAgents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Read-only retriever reusing persistent 50-chunk ChromaDB
        cls.retriever = AgrimindRetriever(
            persist_directory=DEFAULT_CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )
        cls.investigation_agent = InvestigationAgent(retriever=cls.retriever)
        cls.risk_agent = RiskAssessmentAgent()

    def test_01_investigation_sufficient_evidence(self):
        """Verify complete visual + contextual + literature inputs synthesize cleanly."""
        vision = VisionPrediction(
            predicted_class="Tomato___Early_blight",
            confidence=0.9841,
            class_probabilities={
                "Tomato___Bacterial_spot": 0.0050,
                "Tomato___Early_blight": 0.9841,
                "Tomato___Late_blight": 0.0109
            }
        )
        context = VisualContext(
            leaf_damage_percentage=15.0,
            affected_organs=["leaves"],
            canopy_spread="lower_canopy",
            weather_conditions="warm_humid",
            field_notes="Concentric target rings observed on lower leaves."
        )

        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)

        self.assertIsInstance(inv, InvestigationResult)
        self.assertEqual(inv.primary_diagnosis, "Tomato___Early_blight")
        self.assertEqual(inv.diagnosis_confidence, 0.9841)
        self.assertEqual(inv.evidence_status, EvidenceStatus.SUFFICIENT)
        self.assertEqual(len(inv.conflicts_detected), 0)
        self.assertGreater(len(inv.citations), 0)
        
        # Verify provenance preservation
        top_cit = inv.citations[0]
        self.assertIn("DOC-", top_cit["doc_id"])
        self.assertTrue(top_cit["source_url"].startswith("http"))
        self.assertIn("Purdue", top_cit["institution"] + inv.synthesis_narrative)

    def test_02_investigation_missing_canopy_context(self):
        """Verify cropped leaf image without canopy metadata is flagged as insufficient context."""
        vision = VisionPrediction(
            predicted_class="Tomato___Bacterial_spot",
            confidence=0.9910
        )
        # No canopy context provided
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=None)

        self.assertEqual(inv.evidence_status, EvidenceStatus.INSUFFICIENT_CONTEXT)
        self.assertTrue(any("single cropped leaf" in lim for lim in inv.limitations))

    def test_03_investigation_conflicting_symptoms(self):
        """Verify symptom contradiction between vision prediction and field notes is detected."""
        vision = VisionPrediction(
            predicted_class="Tomato___Late_blight",
            confidence=0.9200
        )
        context = VisualContext(
            leaf_damage_percentage=20.0,
            affected_organs=["leaves"],
            field_notes="Distinctive concentric bullseye target spots on leaves."  # Contradicts Late Blight
        )

        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)

        self.assertEqual(inv.evidence_status, EvidenceStatus.CONFLICTING)
        self.assertGreater(len(inv.conflicts_detected), 0)
        self.assertTrue(any("Early Blight" in c for c in inv.conflicts_detected))

    def test_04_investigation_unsupported_disease(self):
        """Verify out-of-scope disease label is safely flagged."""
        vision = VisionPrediction(
            predicted_class="Tomato___Septoria_leaf_spot",
            confidence=0.8800
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision)

        self.assertFalse(inv.visual_prediction.is_supported_disease)
        self.assertEqual(inv.evidence_status, EvidenceStatus.UNSUPPORTED_DISEASE)
        self.assertTrue(any("outside AgriMind's 3-class" in c for c in inv.conflicts_detected))

    def test_05_investigation_insufficient_literature(self):
        """Verify out-of-domain literature failure is transparently handled."""
        vision = VisionPrediction(
            predicted_class="Tomato___Early_blight",
            confidence=0.9500
        )
        # Simulated out-of-domain retrieval result
        retrieved = RetrievedEvidence(
            has_sufficient_evidence=False,
            query="Broadleaf weed control in corn",
            citations=[],
            retrieved_count=0,
            fallback_message="Insufficient agricultural evidence in the knowledge base."
        )

        inv = self.investigation_agent.investigate(
            vision_prediction=vision,
            retrieved_evidence=retrieved
        )

        self.assertEqual(inv.evidence_status, EvidenceStatus.INSUFFICIENT_LITERATURE)
        self.assertTrue(any("peer-reviewed agricultural literature" in lim for lim in inv.limitations))

    def test_06_risk_assessment_indeterminate_when_context_missing(self):
        """Verify high model confidence alone does NOT produce an arbitrary severity assignment."""
        vision = VisionPrediction(
            predicted_class="Tomato___Early_blight",
            confidence=0.9950  # High vision confidence
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=None)
        risk = self.risk_agent.assess_risk(inv)

        self.assertIsInstance(risk, RiskAssessmentResult)
        # CRUCIAL: Identification confidence is high (0.995), but severity is INDETERMINATE!
        self.assertEqual(risk.identification_confidence, 0.9950)
        self.assertEqual(risk.assigned_severity, SeverityLevel.INDETERMINATE)
        self.assertEqual(risk.severity_confidence, "none")
        self.assertGreater(len(risk.scouting_recommendations), 0)
        self.assertTrue(any("single cropped leaf" in b for b in risk.rubric_basis))

    def test_07_risk_assessment_low_severity(self):
        """Verify <10% lower canopy damage maps to LOW severity."""
        vision = VisionPrediction(predicted_class="Tomato___Bacterial_spot", confidence=0.9400)
        context = VisualContext(
            leaf_damage_percentage=4.5,
            affected_organs=["leaves"],
            canopy_spread="lower_canopy"
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.LOW)
        self.assertEqual(risk.epidemic_risk, "low")
        self.assertFalse(risk.requires_immediate_action)
        self.assertTrue(any("Early, localized" in b for b in risk.rubric_basis))

    def test_08_risk_assessment_moderate_severity(self):
        """Verify 10-35% mid-canopy foliar damage maps to MODERATE severity."""
        vision = VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.9600)
        context = VisualContext(
            leaf_damage_percentage=22.0,
            affected_organs=["leaves"],
            canopy_spread="mid_canopy"
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.MODERATE)
        self.assertEqual(risk.epidemic_risk, "moderate")
        self.assertFalse(risk.requires_immediate_action)

    def test_09_risk_assessment_high_severity(self):
        """Verify >35% damage or fruit involvement maps to HIGH severity."""
        vision = VisionPrediction(predicted_class="Tomato___Bacterial_spot", confidence=0.9700)
        context = VisualContext(
            leaf_damage_percentage=40.0,
            affected_organs=["leaves", "fruit"],
            canopy_spread="upper_canopy"
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.HIGH)
        self.assertTrue(risk.requires_immediate_action)
        self.assertTrue(any("fruit involvement" in b for b in risk.rubric_basis))

    def test_10_risk_assessment_critical_severity(self):
        """Verify Late Blight under cool/wet weather with extensive canopy damage maps to CRITICAL."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9850)
        context = VisualContext(
            leaf_damage_percentage=30.0,
            affected_organs=["leaves", "stems"],
            canopy_spread="whole_plant",
            weather_conditions="cool_wet",
            field_notes="White cottony sporulation on leaf undersides after heavy rain."
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.CRITICAL)
        self.assertEqual(risk.epidemic_risk, "critical")
        self.assertTrue(risk.requires_immediate_action)
        self.assertTrue(risk.requires_human_expert_review)
        self.assertTrue(any("Cornell Extension" in b for b in risk.rubric_basis))

    def test_11_risk_assessment_indeterminate_on_conflict(self):
        """Verify conflicting evidence leads to INDETERMINATE severity and flags human review."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9100)
        context = VisualContext(
            leaf_damage_percentage=25.0,
            field_notes="Concentric bullseye rings with yellow halo."  # Contradicts Late Blight
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.INDETERMINATE)
        self.assertTrue(risk.requires_human_expert_review)
        self.assertTrue(any("diagnostic conflict" in b for b in risk.rubric_basis))

    def test_12_risk_assessment_indeterminate_on_unsupported_disease(self):
        """Verify unsupported disease leads to INDETERMINATE severity and human review."""
        vision = VisionPrediction(predicted_class="Corn___Common_rust", confidence=0.9500)
        inv = self.investigation_agent.investigate(vision_prediction=vision)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.INDETERMINATE)
        self.assertTrue(risk.requires_human_expert_review)

    def test_13_late_blight_low_damage_conducive_weather_escalation(self):
        """Verify Late Blight at low damage (3%) under cool/wet weather escalates to HIGH, not LOW."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9600)
        context = VisualContext(
            leaf_damage_percentage=3.0,  # Low damage
            affected_organs=["leaves"],
            canopy_spread="lower_canopy",
            weather_conditions="cool_wet"  # Conducive weather
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        # Must NOT be downgraded to LOW!
        self.assertEqual(risk.assigned_severity, SeverityLevel.HIGH)
        self.assertEqual(risk.epidemic_risk, "high")
        self.assertTrue(risk.requires_immediate_action)
        self.assertTrue(risk.requires_human_expert_review)

    def test_14_late_blight_active_sporulation_critical(self):
        """Verify active sporulation on leaf undersides triggers CRITICAL severity."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9700)
        context = VisualContext(
            leaf_damage_percentage=12.0,
            affected_organs=["leaves"],
            canopy_spread="lower_canopy",
            weather_conditions="cool_wet",
            field_notes="Active white cottony sporulation visible on leaf undersides."
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.CRITICAL)
        self.assertEqual(risk.epidemic_risk, "critical")
        self.assertTrue(risk.requires_immediate_action)
        self.assertTrue(any("rogueing" in r.lower() for r in risk.scouting_recommendations))

    def test_15_late_blight_missing_context_urgent_escalation(self):
        """Verify single-leaf Late Blight prediction has INDETERMINATE severity but urgent action."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9900)
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=None)
        risk = self.risk_agent.assess_risk(inv)

        self.assertEqual(risk.assigned_severity, SeverityLevel.INDETERMINATE)
        self.assertEqual(risk.epidemic_risk, "high")
        self.assertTrue(risk.requires_immediate_action)
        self.assertTrue(risk.requires_human_expert_review)
        self.assertTrue(any("URGENT" in r for r in risk.scouting_recommendations))

    def test_16_fungicide_activity_descriptions_and_pesticide_safety_notice(self):
        """Verify accurate fungicide mode-of-action attribution and presence of pesticide notice."""
        vision = VisionPrediction(predicted_class="Tomato___Late_blight", confidence=0.9800)
        context = VisualContext(
            leaf_damage_percentage=20.0,
            affected_organs=["leaves", "stems"],
            canopy_spread="whole_plant",
            weather_conditions="cool_wet",
            field_notes="White cottony mold on undersides."
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        # 1. Pesticide safety notice is present and non-empty
        self.assertIsNotNone(risk.pesticide_safety_notice)
        self.assertIn("MANDATORY PESTICIDE SAFETY NOTICE", risk.pesticide_safety_notice)
        self.assertIn("REI", risk.pesticide_safety_notice)
        self.assertIn("PHI", risk.pesticide_safety_notice)

        # 2. Cymoxanil has curative kickback and Mandipropamid has anti-sporulant
        rec_text = " ".join(risk.scouting_recommendations)
        self.assertIn("Cymoxanil", rec_text)
        self.assertIn("kickback", rec_text.lower())
        self.assertIn("Mandipropamid", rec_text)
        self.assertIn("anti-sporulant", rec_text.lower())

        # 3. Mandipropamid is NOT credited with curative kickback
        for r in risk.scouting_recommendations:
            if "Mandipropamid" in r:
                self.assertNotIn("curative kickback activity (e.g. Mandipropamid", r)

    def test_17_project_heuristic_transparency_in_rubric_basis(self):
        """Verify project-defined cutoffs are explicitly labeled as project heuristics."""
        vision = VisionPrediction(predicted_class="Tomato___Early_blight", confidence=0.9500)
        context = VisualContext(
            leaf_damage_percentage=15.0,
            canopy_spread="mid_canopy"
        )
        inv = self.investigation_agent.investigate(vision_prediction=vision, visual_context=context)
        risk = self.risk_agent.assess_risk(inv)

        self.assertTrue(any("Project heuristic" in b for b in risk.rubric_basis))


if __name__ == "__main__":
    unittest.main()
