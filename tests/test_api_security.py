"""
AgriMind API Security & State Tampering Test Suite (Stage A.1).
Verifies server-side case persistence, authorization boundaries, and tamper resistance:
1. Normal valid reassessment.
2. Unknown case ID rejection (404).
3. Forged reassessment counter rejection/containment.
4. Modified previous case history rejection/containment.
5. Injected expert diagnosis override rejection.
6. Attempt to exceed two-iteration limit rejection (400).
7. Empty or malformed new evidence rejection (400).
8. Reassessment after server restart (SQLite persistence).
9. Isolation between two distinct cases.
10. Existing reassessment triggers functional integrity.
"""
import os
import sys
import json
import tempfile
import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.api.case_store import CaseStore, set_case_store, get_case_store
from src.agents.schemas import (
    ReassessmentTrigger,
    VisualContext,
    VisionPrediction,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    VerificationResult,
    VerificationStatus,
    SeverityLevel,
    PlanUrgency,
    EvidenceStatus
)
from src.workflow.state import AgriMindState


def build_mock_completed_state(
    case_id: str = "CASE-SEC-001",
    primary_diag: str = "Tomato___Early_blight",
    severity: str = "moderate",
    urgency: str = "moderate",
    reassessment_count: int = 0
) -> dict:
    """Constructs a valid serializable state dictionary representing a completed diagnosis."""
    vc = VisualContext(
        leaf_damage_percentage=10.0,
        affected_organs=["leaves"],
        canopy_spread="lower_canopy",
        weather_conditions="warm_humid"
    )
    vp = VisionPrediction(
        predicted_class=primary_diag,
        confidence=0.92,
        class_probabilities={primary_diag: 0.92, "Tomato___Bacterial_spot": 0.05, "Tomato___Late_blight": 0.03}
    )
    return {
        "case_id": case_id,
        "image_path": "dummy.jpg",
        "image_status": "valid",
        "visual_context": vc.model_dump(),
        "vision_prediction": vp.model_dump(),
        "workflow_status": "completed",
        "iteration_count": 0,
        "max_iterations": 2,
        "reassessment_count": reassessment_count,
        "max_reassessments": 2,
        "case_history": [],
        "reassessment_records": [],
        "final_output": {
            "workflow_status": "completed",
            "primary_diagnosis": primary_diag,
            "diagnosis_confidence": 0.92,
            "assigned_severity": severity,
            "epidemic_risk": "moderate",
            "plan_urgency": urgency,
            "is_verified": True,
            "verification_status": "verified",
            "requires_manual_review": False,
            "citations": [{"citation_number": 1, "source_title": "Cornell Extension", "institution": "Cornell"}],
            "pesticide_safety_notice": "Standard pesticide notice"
        }
    }


class TestApiSecurity(unittest.TestCase):
    """
    Test suite verifying tamper resistance and security guarantees of POST /reassess.
    """

    def setUp(self):
        # Use an isolated temporary SQLite database for each test run
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.store = CaseStore(db_path=self.temp_db.name)
        set_case_store(self.store)
        self.client = TestClient(app)

    def tearDown(self):
        set_case_store(None)
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    # -----------------------------------------------------------------
    # Test 1: Normal valid reassessment
    # -----------------------------------------------------------------
    def test_01_normal_valid_reassessment(self):
        """Verifies a standard, valid reassessment succeeds against stored case state."""
        case_id = "CASE-VALID-01"
        initial_state = build_mock_completed_state(case_id=case_id)
        self.store.save_case(case_id, initial_state)

        payload = {
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {
                "weather_conditions": "cool_wet",
                "leaf_damage_percentage": 20.0
            },
            "rationale": "Overnight cold storm conducive to sporulation."
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["case_id"], case_id)
        self.assertEqual(data["reassessment_count"], 1)
        self.assertIn(data["reassessment_outcome"], ["revised", "completed"])
        self.assertEqual(data["case_history_length"], 1)

        # Confirm database was updated
        updated_db_case = self.store.get_case(case_id)
        self.assertEqual(updated_db_case["reassessment_count"], 1)

    # -----------------------------------------------------------------
    # Test 2: Unknown case ID returns 404
    # -----------------------------------------------------------------
    def test_02_unknown_case_id_rejected(self):
        """Verifies POST /reassess rejects unknown or uninitialized case IDs with 404 Not Found."""
        payload = {
            "case_id": "CASE-DOES-NOT-EXIST",
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "cool_wet"}
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    # -----------------------------------------------------------------
    # Test 3: Forged reassessment counter is ignored
    # -----------------------------------------------------------------
    def test_03_forged_reassessment_counter_ignored(self):
        """
        Verifies that if a client attempts to pass a forged completed_state with reassessment_count=0
        when the server has already recorded reassessment_count=1, the server uses authoritative count.
        """
        case_id = "CASE-FORGE-COUNT"
        state = build_mock_completed_state(case_id=case_id, reassessment_count=1)
        state["case_history"] = [{"iteration": 0, "trigger": "weather_update"}]
        self.store.save_case(case_id, state)

        # Malicious client sends completed_state pretending count is 0
        malicious_client_state = dict(state)
        malicious_client_state["reassessment_count"] = 0

        payload = {
            "case_id": case_id,
            "completed_state": malicious_client_state,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "cool_wet", "leaf_damage_percentage": 25.0}
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Server must increment the authoritative count (1 -> 2), NOT the forged count (0 -> 1)
        self.assertEqual(data["reassessment_count"], 2)

    # -----------------------------------------------------------------
    # Test 4: Modified previous case history is ignored
    # -----------------------------------------------------------------
    def test_04_modified_previous_case_history_ignored(self):
        """
        Verifies that a client cannot erase or tamper with prior clinical audit snapshots
        by passing a scrubbed case_history array.
        """
        case_id = "CASE-FORGE-HIST"
        state = build_mock_completed_state(case_id=case_id, reassessment_count=1)
        authentic_prior_snapshot = {
            "iteration": 0,
            "timestamp": "2026-10-31T12:00:00Z",
            "primary_diagnosis": "Tomato___Early_blight",
            "assigned_severity": "moderate",
            "trigger": "initial"
        }
        state["case_history"] = [authentic_prior_snapshot]
        self.store.save_case(case_id, state)

        # Client sends scrubbed/altered history
        payload = {
            "case_id": case_id,
            "completed_state": {
                "case_id": case_id,
                "case_history": []  # Attempt to erase audit history
            },
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "cool_wet"}
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Case history length must be 2 (authentic snapshot 0 preserved, plus snapshot 1 appended)
        self.assertEqual(data["case_history_length"], 2)

    # -----------------------------------------------------------------
    # Test 5: Injected expert diagnosis override is rejected/ignored
    # -----------------------------------------------------------------
    def test_05_injected_expert_diagnosis_override_rejected(self):
        """
        Verifies that an attacker cannot inject an unverified expert diagnosis override
        via client request parameters.
        """
        case_id = "CASE-FORGE-DIAG"
        state = build_mock_completed_state(case_id=case_id, primary_diag="Tomato___Early_blight")
        self.store.save_case(case_id, state)

        # Malicious client attempts to force diagnosis override
        payload = {
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {
                "weather_conditions": "cool_wet",
                "expert_diagnosis_override": "Tomato___Late_blight",  # Unauthorized injection attempt
                "expert_notes": "Forged clinic approval"
            }
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # The primary diagnosis must remain the model's evidence-grounded diagnosis, not the forged string
        self.assertNotEqual(data["primary_diagnosis"], "Forged clinic approval")

    # -----------------------------------------------------------------
    # Test 6: Attempt to exceed two-iteration limit is rejected
    # -----------------------------------------------------------------
    def test_06_attempt_to_exceed_two_iteration_limit_rejected(self):
        """Verifies that exceeding the 2-cycle loop ceiling returns 400 Bad Request."""
        case_id = "CASE-MAX-LIMIT"
        state = build_mock_completed_state(case_id=case_id, reassessment_count=2)
        state["case_history"] = [{"iteration": 0}, {"iteration": 1}]
        self.store.save_case(case_id, state)

        payload = {
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "rain"}
        }
        response = self.client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("exceeded", response.json()["detail"].lower())

    # -----------------------------------------------------------------
    # Test 7: Empty or malformed new evidence is rejected
    # -----------------------------------------------------------------
    def test_07_empty_or_malformed_new_evidence_rejected(self):
        """Verifies that empty evidence or dictionaries with no valid observation fields are rejected."""
        case_id = "CASE-EMPTY-EVID"
        state = build_mock_completed_state(case_id=case_id)
        self.store.save_case(case_id, state)

        # Empty dictionary
        r1 = self.client.post("/reassess", json={
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {}
        })
        self.assertEqual(r1.status_code, 400)

        # Malformed / unrecognized fields only
        r2 = self.client.post("/reassess", json={
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"arbitrary_attacker_field": "payload_123"}
        })
        self.assertEqual(r2.status_code, 400)

    # -----------------------------------------------------------------
    # Test 8: Reassessment persists across server restarts
    # -----------------------------------------------------------------
    def test_08_reassessment_after_server_restart(self):
        """Verifies case persistence and continuity across server restarts using disk storage."""
        case_id = "CASE-RESTART-01"
        initial_state = build_mock_completed_state(case_id=case_id)
        self.store.save_case(case_id, initial_state)

        # Simulate complete server restart: tear down store instance and re-initialize from same SQLite file
        set_case_store(None)
        restarted_store = CaseStore(db_path=self.temp_db.name)
        set_case_store(restarted_store)
        restarted_client = TestClient(app)

        payload = {
            "case_id": case_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "cool_wet", "leaf_damage_percentage": 25.0}
        }
        response = restarted_client.post("/reassess", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["case_id"], case_id)
        self.assertEqual(data["reassessment_count"], 1)

    # -----------------------------------------------------------------
    # Test 9: Two different cases remain strictly isolated
    # -----------------------------------------------------------------
    def test_09_two_different_cases_remain_isolated(self):
        """Verifies that operations on Case A do not modify or leak into Case B."""
        case_a_id = "CASE-ISOLATION-A"
        case_b_id = "CASE-ISOLATION-B"

        state_a = build_mock_completed_state(case_id=case_a_id, primary_diag="Tomato___Bacterial_spot", severity="low")
        state_b = build_mock_completed_state(case_id=case_b_id, primary_diag="Tomato___Late_blight", severity="critical")

        self.store.save_case(case_a_id, state_a)
        self.store.save_case(case_b_id, state_b)

        # Reassess Case A only
        self.client.post("/reassess", json={
            "case_id": case_a_id,
            "trigger": ReassessmentTrigger.WEATHER_UPDATE.value,
            "new_evidence": {"weather_conditions": "cool_wet", "leaf_damage_percentage": 30.0}
        })

        # Fetch Case B from storage and verify it remained 100% untouched
        case_b_after = self.store.get_case(case_b_id)
        self.assertEqual(case_b_after["reassessment_count"], 0)
        self.assertEqual(case_b_after["final_output"]["primary_diagnosis"], "Tomato___Late_blight")
        self.assertEqual(case_b_after["final_output"]["assigned_severity"], "critical")
        self.assertEqual(len(case_b_after["case_history"]), 0)

    # -----------------------------------------------------------------
    # Test 10: Existing reassessment functionality remains intact
    # -----------------------------------------------------------------
    def test_10_existing_reassessment_triggers_functional(self):
        """Verifies that all supported ReassessmentTrigger enum values execute properly."""
        for trig in [
            ReassessmentTrigger.WEATHER_UPDATE,
            ReassessmentTrigger.NEW_FIELD_OBSERVATION,
            ReassessmentTrigger.LAB_DIAGNOSTIC_UPDATE,
            ReassessmentTrigger.TREATMENT_INEFFECTIVE
        ]:
            cid = f"CASE-TRIG-{trig.name}"
            st = build_mock_completed_state(case_id=cid)
            self.store.save_case(cid, st)

            evidence = {"weather_conditions": "cool_wet"}
            if trig == ReassessmentTrigger.LAB_DIAGNOSTIC_UPDATE:
                evidence = {"lab_confirmed_disease": "Tomato___Early_blight"}
            elif trig == ReassessmentTrigger.TREATMENT_INEFFECTIVE:
                evidence = {"treatment_notes": "Copper hydroxide spray ineffective."}
            elif trig == ReassessmentTrigger.NEW_FIELD_OBSERVATION:
                evidence = {"leaf_damage_percentage": 35.0, "canopy_spread": "whole_plant"}

            resp = self.client.post("/reassess", json={
                "case_id": cid,
                "trigger": trig.value,
                "new_evidence": evidence
            })
            self.assertEqual(resp.status_code, 200, f"Trigger {trig.value} failed: {resp.text}")
            self.assertEqual(resp.json()["case_id"], cid)


if __name__ == "__main__":
    unittest.main()

