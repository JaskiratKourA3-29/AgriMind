# AgriMind Week 10 — End-to-End Workflow Reliability & Integration Evaluation Report

**Document Version:** 1.0.0  
**Phase:** Week 10 (Final Multi-Agent Integration & Workflow Reliability Evaluation)  
**Author:** AI/ML Systems Engineer & Senior Software Testing Specialist  
**Evaluation Date:** October 27, 2026  
**Status:** Evaluation Verified — 17/17 Integration Tests Passing (118/118 Safe Regression Tests Passing)

---

## 1. Executive Summary

Week 10 evaluates the end-to-end integration and workflow reliability of the AgriMind multi-agent system. Following the Week 9 evaluation of the Critic/Verification Agent (which demonstrated a 100% flaw detection rate across 17 controlled agent audit tests, but identified that the Critic cannot independently recover from overconfident visual CNN misclassifications without external corroboration), Week 10 assesses how the entire integrated LangGraph pipeline behaves across state transitions, intermediate nodes, conditional edges, adaptive reassessments, and human-in-the-loop escalation paths.

### Key Evaluation Findings:
1. **End-to-End Orchestration Integrity (100.0% Agreement, 17/17 Scenarios):**  
   The compiled LangGraph workflow reliably orchestrates data movement across Image Validation, Vision Inference, RAG Extension Retrieval, Investigation Evidence Synthesis, Risk Assessment, Decision Planning, Critic Auditing, Manual Review, and Output Finalization.
2. **Defect Discovery & Resolution in Critic Error Routing:**  
   During automated failure testing (Scenario 6), a latent integration defect was identified in `route_after_critic` (`src/workflow/graph.py`): unexpected runtime exceptions in the Critic Agent were routed into `manual_review_node`, which overwrote the real failure diagnostic with `"Failed initializing manual review record."` A minimal, targeted fix was applied to check `state.get("workflow_status") == "error"` and route directly to `finalize_output`, preserving the exact diagnostic error message.
3. **Safety Gating & Unsafe Chemical Withholding (100.0%, 8/8 Scenarios):**  
   Under diagnostic conflict, ambiguous prediction margins, or out-of-scope pathogens, the integrated system strictly suppresses automated pesticide advice (`chemical_controls: []`, `pesticide_safety_notice: None`, `plan_urgency: DEFERRED`) and escalates to manual expert review.
4. **Adaptive Reassessment & Loop Ceiling Enforcement (100.0%):**  
   The adaptive reassessment loop safely updates case parameters, logs prior state snapshots in `case_history`, generates formal `ReassessmentRecord` audit logs, and halts at the configured 2-iteration ceiling by issuing a permanent `terminal_escalation` to extension clinics.
5. **Week 8 Visual Misclassification Boundary Characterization:**  
   Simulating the Week 8 finding where official test-split Bacterial Spot samples were misclassified as Early Blight or Late Blight with high confidence ($>0.99$), the evaluation verified that:
   - When no grower field notes are provided, downstream agents cannot detect CNN misclassification and accept the prediction as verified.
   - When grower notes report contradictory symptoms (e.g., hot/dry weather halting Late Blight sporulation, or concentric rings), the Investigation Agent flags the contradiction, withholds chemicals, and defers guidance.
   - Subsequent `LAB_DIAGNOSTIC_UPDATE` reassessments successfully override the misclassification with 1.0 confidence, revising the management plan to accredited Bacterial Spot IPM.

---

## 2. Actual Workflow Architecture Inspected

The implemented AgriMind workflow is orchestrated using **LangGraph** (`langgraph.graph.StateGraph`), passing a typed dictionary (`AgriMindState`) between modular nodes.

```mermaid
graph TD
    START([START]) --> RouteStart{route_from_start}
    RouteStart -->|reassessment_trigger| ReassessNode[reassessment]
    RouteStart -->|default| ValImgNode[validate_image]

    ValImgNode --> RouteVal{route_after_validation}
    RouteVal -->|valid| VisionNode[vision]
    RouteVal -->|invalid/error| FinalizeNode[finalize_output]

    VisionNode --> RouteVision{route_after_vision}
    RouteVision -->|success| RetrievalNode[retrieval]
    RouteVision -->|error| FinalizeNode

    RetrievalNode --> RouteRet{route_after_retrieval}
    RouteRet -->|success| InvNode[investigation]
    RouteRet -->|error| FinalizeNode

    InvNode --> RouteInv{route_after_investigation}
    RouteInv -->|success| RiskNode[risk_assessment]
    RouteInv -->|error| FinalizeNode

    RiskNode --> RouteRisk{route_after_risk_assessment}
    RouteRisk -->|success| PlanNode[decision_planning]
    RouteRisk -->|error| FinalizeNode

    PlanNode --> RoutePlan{route_after_decision_planning}
    RoutePlan -->|success| CriticNode[critic]
    RoutePlan -->|error| FinalizeNode

    CriticNode --> RouteCritic{route_after_critic}
    RouteCritic -->|verified & no review| FinalizeNode
    RouteCritic -->|rejected / requires review| ReviewNode[manual_review]
    RouteCritic -->|error (fixed)| FinalizeNode

    ReassessNode --> RouteReassess{route_after_reassessment}
    RouteReassess -->|error / terminal ceiling| FinalizeNode
    RouteReassess -->|new unvalidated image| ValImgNode
    RouteReassess -->|valid new evidence| RetrievalNode

    ReviewNode --> FinalizeNode
    FinalizeNode --> END([END])
```

### 2.1 Entry Points and Edge Routing Functions
1. **START (`route_from_start`):**
   - Routes to `reassessment` if `state.get("reassessment_trigger")` is populated.
   - Routes to `validate_image` for standard initial case evaluations.
2. **Image Validation (`validate_image_node` & `route_after_validation`):**
   - Checks presence, accessibility, and verifies magic bytes (`\xff\xd8` for JPEG, `\x89PNG` for PNG, `GIF`, `BM`).
   - Aborts directly to `finalize_output` on corrupt/missing files with `workflow_status="error"`.
3. **Vision Inference (`vision_node` & `route_after_vision`):**
   - Reuses pre-injected `VisionPrediction` (for tests/fixtures) or runs `VisionInferenceEngine.predict()`.
4. **Literature Retrieval (`retrieval_node` & `route_after_retrieval`):**
   - Queries the persistent ChromaDB knowledge base (50 chunks) using `sentence-transformers/all-MiniLM-L6-v2`.
5. **Investigation Synthesis (`investigation_node` & `route_after_investigation`):**
   - Cross-examines model predictions, grower canopy observations, and extension literature.
   - Identifies symptom conflicts, out-of-scope pathogens, low classification confidence ($<0.60$), and close class margins ($<0.15$).
6. **Risk Assessment (`risk_assessment_node` & `route_after_risk_assessment`):**
   - Evaluates physical severity (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`, `INDETERMINATE`) and epidemic risk.
   - Enforces conservative gating: Late Blight under conducive weather cannot be downgraded.
7. **Decision Planning (`decision_planning_node` & `route_after_decision_planning`):**
   - Structures IPM management actions along the hierarchy: Cultural $\rightarrow$ Resistant Varieties $\rightarrow$ Chemical $\rightarrow$ Monitoring.
   - Under `CONFLICTING` or `UNSUPPORTED_DISEASE` status, withholds all chemicals, sets `PlanUrgency.DEFERRED`, and requires human review.
8. **Critic Auditing (`critic_node` & `route_after_critic`):**
   - Verifies citation grounding, severity-urgency consistency, fungicide mode of action, EPA/state regulatory pesticide notices, and registered active ingredient names.
   - Routes to `finalize_output` if fully verified and not flagged for review; otherwise routes to `manual_review` (or `finalize_output` on runtime error).
9. **Manual Review Feedback Loop (`manual_review_node`):**
   - Creates a `ManualReviewRecord` and returns `workflow_status="pending_manual_review"` when no expert is connected.
10. **Adaptive Reassessment (`reassessment_node` & `route_after_reassessment`):**
    - Validates triggers (`NEW_FIELD_OBSERVATION`, `WEATHER_UPDATE`, `LAB_DIAGNOSTIC_UPDATE`, `TREATMENT_INEFFECTIVE`), merges evidence into `VisualContext`, snapshots history, increments loop count, and enforces the 2-iteration limit.
11. **Output Finalization (`finalize_output_node`):**
    - Compiles the final structured summary, converts `verified` / `review_resolved` to `completed`, appends formal `ReassessmentRecord` objects, and clears transient trigger flags.

---

## 3. Test Scenarios and Expected vs. Actual Results

The evaluation suite `tests/test_week10_workflow_integration.py` covers 17 granular scenarios across 10 core integration categories.

| Test ID | Scenario Description | Initial Inputs & Injected Conditions | Expected Transition & Terminal State | Observed Terminal State | Verified? | Result |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **TC-01** | Normal workflow end-to-end execution | Valid image, Early Blight (conf=0.965), 15% damage, lower canopy | validate $\rightarrow$ vision $\rightarrow$ retrieval $\rightarrow$ inv $\rightarrow$ risk $\rightarrow$ plan $\rightarrow$ critic $\rightarrow$ finalize (`completed`) | `completed` | True | **PASS** |
| **TC-02** | Diagnostic symptom conflict handling | Late Blight (conf=0.94), grower notes: "concentric bullseye rings" | inv flags `CONFLICTING` $\rightarrow$ risk `INDETERMINATE` $\rightarrow$ plan `DEFERRED` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True (safe deferral) | **PASS** |
| **TC-03a** | Low-confidence vision classification | Early Blight (conf=0.52 < 0.60), 10% damage | inv flags low confidence conflict $\rightarrow$ urgency `DEFERRED` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True (safe deferral) | **PASS** |
| **TC-03b** | Ambiguous multi-class prediction margin | Top class: 0.48, Runner-up: 0.42 (margin 0.06 < 0.15) | inv flags margin conflict $\rightarrow$ urgency `DEFERRED` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True (safe deferral) | **PASS** |
| **TC-04a** | Unsupported pathogen scope | Predicted `Tomato___Tomato_Yellow_Leaf_Curl_Virus` (conf=0.98) | inv flags `UNSUPPORTED_DISEASE` $\rightarrow$ urgency `DEFERRED` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True (safe deferral) | **PASS** |
| **TC-04b** | Insufficient peer-reviewed literature | `RetrievedEvidence(has_sufficient_evidence=False, citations=[])` | inv flags `INSUFFICIENT_LITERATURE` $\rightarrow$ plan lacks citations $\rightarrow$ `pending_manual_review` | `pending_manual_review` | False (review triggered) | **PASS** |
| **TC-05** | Critic rejection of unverified chemical | Injected plan recommending unverified active ingredient `propiconazole` | Critic rejects with `REJECTED_UNSUPPORTED_CLAIMS` $\rightarrow$ `manual_review` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | False | **PASS** |
| **TC-06** | Critic unexpected runtime exception | Mock Critic raises `RuntimeError("Simulated out-of-memory")` | `critic_node` catches error $\rightarrow$ `route_after_critic` $\rightarrow$ `finalize_output` (`error`) | `error` | False | **PASS** |
| **TC-07** | Adaptive reassessment weather escalation | Completed mild Late Blight case $\rightarrow$ `WEATHER_UPDATE` with `cool_wet` | `reassessment` $\rightarrow$ `retrieval` $\rightarrow$ risk escalates to `CRITICAL` $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True | **PASS** |
| **TC-08** | Reassessment loop ceiling enforcement | Completed case at count=2 $\rightarrow$ attempt 3rd reassessment | payload validation detects count $\ge$ 2 $\rightarrow$ terminal record $\rightarrow$ `terminal_escalation` | `terminal_escalation` | False (terminal halt) | **PASS** |
| **TC-09** | Reassessment with conflicting evidence | Completed Late Blight $\rightarrow$ `NEW_FIELD_OBSERVATION` with concentric rings | Reassessment $\rightarrow$ inv flags symptom conflict $\rightarrow$ chemicals withheld $\rightarrow$ `pending_manual_review` | `pending_manual_review` | True (safe deferral) | **PASS** |
| **TC-10** | State and history schema integrity | Case undergoes reassessment cycle; assert typed schemas | `case_history` snapshots prior severity; `ReassessmentRecord` populated with valid fields | `completed` | True | **PASS** |
| **TC-11a** | Image path input validation | Empty string, nonexistent file, non-image text file | `validate_image_node` detects corrupt/missing file $\rightarrow$ `finalize_output` with `workflow_status="error"` | `error` | False | **PASS** |
| **TC-11b** | Mid-workflow missing state contracts | Intermediate nodes invoked without prerequisite inputs | Nodes return `workflow_status="error"` and descriptive diagnostics | `error` | False | **PASS** |
| **TC-12** | Terminal-state mutual exclusivity | Evaluate completed, review, and error states | States exhibit mutually exclusive property invariants without conflation | `completed` / `pending_manual_review` / `error` | True / True / False | **PASS** |
| **TC-13a** | Week 8 vision limitation: uncontradicted | Bacterial Spot misclassified as Early Blight (conf=0.9999), no notes | Workflow faithfully accepts prediction because evidence is internally consistent | `completed` | True (Early Blight) | **PASS** |
| **TC-13b** | Week 8 vision limitation: lab recovery | Bacterial Spot misclassified as Late Blight (conf=1.0) with hot/dry notes $\rightarrow$ Lab PCR | Initial deferral $\rightarrow$ `LAB_DIAGNOSTIC_UPDATE` overrides pathogen with 1.0 conf $\rightarrow$ `completed` | `pending_manual_review` $\rightarrow$ `completed` | True (Bacterial Spot) | **PASS** |

---

## 4. Quantitative Metrics and Performance Measurements

The quantitative evaluation was computed using `scratch/analyze_week10_performance.py`:

```
======================================================================
AGRIMIND WEEK 10 WORKFLOW INTEGRATION EVALUATION METRICS
======================================================================
Total Controlled Scenarios Tested : 17
Scenarios Fully Passing Criteria  : 17 / 17 (100.0%)
Terminal-State Agreement Rate     : 17 / 17 (100.0%)
Conflict Cases Correctly Deferred : 6 / 6 (100.0%)
Unsafe Chemical Advice Blocked    : 8 / 8 (100.0%)
Reassessment Limit Enforced       : 1 / 1 (100.0%)
History & State Preserved         : 3 / 3 (100.0%)
Exception Gracefully Handled      : 3 / 3 (100.0%)
======================================================================
```

### Metric Definitions and Denominators:
1. **Scenarios Fully Passing Criteria (17 / 17, 100.0%):**  
   - *Numerator:* Test cases meeting all assertion invariants (status, schema integrity, citations, notices).  
   - *Denominator:* Total number of integration scenarios executed ($N=17$).
2. **Terminal-State Agreement Rate (17 / 17, 100.0%):**  
   - *Numerator:* Cases where the observed terminal workflow status matched the formally specified architectural expectation.  
   - *Denominator:* Total number of integration scenarios executed ($N=17$).
3. **Conflict Deferral Rate (6 / 6, 100.0%):**  
   - *Numerator:* Cases presenting contradictory diagnostic symptoms, ambiguous runner-up margins, low confidence, or out-of-scope pathogens that correctly routed to `pending_manual_review` with `plan_urgency: DEFERRED`.  
   - *Denominator:* Total conflict/ambiguity scenarios (TC-02, TC-03a, TC-03b, TC-04a, TC-09, TC-13b; $N=6$).
4. **Unsafe Chemical Advice Suppression Rate (8 / 8, 100.0%):**  
   - *Numerator:* Controlled scenarios involving contradictory evidence, unverified chemicals, or ceiling limits where automated chemical recommendations were completely suppressed (`len(chemical_controls) == 0` or rejected by Critic).  
   - *Denominator:* Total candidate scenarios requiring chemical withholding (TC-02, TC-03a, TC-03b, TC-04a, TC-05, TC-08, TC-09, TC-13b; $N=8$).
5. **Reassessment Limit Enforcement (1 / 1, 100.0%):**  
   - *Numerator:* Cases attempting to exceed the 2-cycle loop ceiling that were successfully halted with a terminal audit record.  
   - *Denominator:* Total ceiling test cases (TC-08; $N=1$).
6. **State & Case History Preservation Rate (3 / 3, 100.0%):**  
   - *Numerator:* Reassessment cases where `case_history` snapshots and `ReassessmentRecord` objects matched typed Pydantic models with non-empty timestamps and valid triggers.  
   - *Denominator:* Reassessment state tracking test cases (TC-07, TC-08, TC-10; $N=3$).
7. **Exception Resilience Rate (3 / 3, 100.0%):**  
   - *Numerator:* Cases simulating runtime faults or malformed inputs that aborted safely to `workflow_status="error"` without unhandled Python exceptions crashing the process.  
   - *Denominator:* Total failure-injection test cases (TC-06, TC-11a, TC-11b; $N=3$).

> [!NOTE]
> These metrics represent deterministic synthetic unit and integration tests under controlled laboratory fixtures. They do not constitute real-world agricultural field trials, clinical validation, or mathematical proof of defect freedom across all unconstrained user inputs.

---

## 5. Integration Defects Found and Fixed

During the evaluation of Scenario 6 (Critic exception handling), one reproducible integration defect was identified and resolved.

### Defect 1: Critic Exception Error Masking in `route_after_critic`
- **Symptom:**  
  When `CriticAgent.verify_plan` encountered an unexpected runtime exception (e.g., `RuntimeError("Simulated Critic out-of-memory fault")`), `critic_node` caught the exception and set `workflow_status="error"` with a descriptive error message. However, the workflow terminated with `workflow_status="error"` but with `error_message="Failed initializing manual review record."` instead of the original Critic diagnostic.
- **Root Cause Analysis:**  
  In `src/workflow/graph.py`, line 97:
  ```python
  def route_after_critic(state: AgriMindState) -> str:
      """Evaluates verification result."""
      verif = state.get("verification_result")
      if verif is not None and verif.is_verified and not verif.requires_manual_review:
          return "finalize_output"
      return "manual_review"
  ```
  Every other post-node routing function in `graph.py` (`route_after_vision`, `route_after_retrieval`, `route_after_investigation`, `route_after_risk_assessment`, `route_after_decision_planning`) begins with:
  ```python
  if state.get("workflow_status") == "error":
      return "finalize_output"
  ```
  `route_after_critic` omitted this error check. Consequently, when `critic_node` failed, the error state fell through to `manual_review`. Inside `manual_review_node`, because no review record existed and `investigation_result` had sufficient evidence, `route_to_review` returned `None`, which triggered line 340:
  ```python
  return {
      "workflow_status": "error",
      "error_message": "Failed initializing manual review record."
  }
  ```
  This masked the real root cause of the Critic failure.
- **Minimal Code Correction:**  
  In `src/workflow/graph.py`, added the standard error guard to `route_after_critic`:
  ```python
  def route_after_critic(state: AgriMindState) -> str:
      if state.get("workflow_status") == "error":
          return "finalize_output"
      verif = state.get("verification_result")
      if verif is not None and verif.is_verified and not verif.requires_manual_review:
          return "finalize_output"
      return "manual_review"
  ```
- **Regression Verification:**  
  Re-running `test_06` confirmed that `final_output["error_message"]` preserves `"Critic verification agent failed: Simulated Critic out-of-memory fault"`. All 118 tests in the regression suite passed cleanly.

---

## 6. Analysis of Week 8 Vision Limitations in the Integrated System

In Week 8, evaluation of the PlantDoc dataset revealed that all 9 official test-split Bacterial Spot images were misclassified by the baseline ResNet-50 visual model (5 misclassified as Early Blight, 4 as Late Blight) with high average confidence (0.9416).

Week 10 specifically evaluated how the integrated multi-agent system behaves when confronted with such misclassifications:

1. **Uncontradicted Overconfident Classification (TC-13a):**  
   - When a Bacterial Spot image is predicted as Early Blight with 0.9999 confidence and the user provides only a cropped leaf image without field scouting observations, the entire downstream workflow (Investigation, Risk Assessment, Decision Planning, and Critic) operates consistently on the premise of Early Blight.
   - **Architectural Boundary:** The multi-agent workflow contains no magical oracle capable of overturning an overconfident convolutional feature extraction without independent evidence. Downstream agents verify *internal evidential coherence*, not absolute biological ground truth.
2. **Discrepancy Catch & Diagnostic Recovery via Field Observations and Reassessment (TC-13b):**  
   - When an overconfident misclassification occurs (e.g. Bacterial Spot sample SMPL-00011 predicted as Late Blight with 1.0 confidence), but the grower supplies field scouting observations reporting hot/dry weather ($>32^\circ\text{C}$) or concentric target rings, the Investigation Agent flags the contradiction:
     `"Epidemiological conflict: Hot/dry weather (>30°C) reported, which halts Phytophthora infestans sporulation and spread."`
   - The workflow suppresses all automated chemical recommendations and defers the case to manual expert review.
   - When the grower subsequently obtains a university diagnostic laboratory PCR confirmation (`Tomato___Bacterial_spot`), an adaptive reassessment (`LAB_DIAGNOSTIC_UPDATE`) is invoked.
   - The `reassessment_node` overrides the visual prediction with 1.0 confidence, allowing the workflow to generate and verify an accredited Bacterial Spot IPM decision plan.

---

## 7. Protected Resource Integrity Checks

Strict non-destructive constraints were verified before and after test execution:

| Protected Resource | Path | Verification Method | Initial State / Baseline | Final State After Testing | Integrity Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Vision Model Checkpoint** | `outputs/week2_vision/best_model.pth` | SHA-256 Checksum & File Size | `eb40b4d9ff9bc8278b63392809702fc17dbe701b05974c8a620588ab56c196d5`<br>(282,626,785 bytes) | `eb40b4d9ff9bc8278b63392809702fc17dbe701b05974c8a620588ab56c196d5`<br>(282,626,785 bytes) | **MATCH / INTACT** |
| **Persistent ChromaDB Store** | `data/vectorstore/chroma/` | Collection Document Count | Exactly 50 chunks | Exactly 50 chunks | **MATCH / INTACT** |
| **Week 8 PlantDoc Evaluation** | `outputs/week8_plantdoc_evaluation/` | Directory Verification | Predictions & reports intact | Predictions & reports untouched | **UNTOUCHED** |
| **API Keys & Secrets** | Workspace & Environment | Git Status / Grep | No `.env` committed; keys masked | No secrets committed or logged | **PROTECTED** |
| **Virtual Environments** | `agrimind-rag-env` & `agrimind-vision-env` | Interpreter verification | Unmodified | Unmodified | **INTACT** |

---

## 8. Summary of Files Created and Modified

### 8.1 Files Created:
1. `tests/test_week10_workflow_integration.py`:  
   Comprehensive test module (17 test cases, 715 lines) evaluating all 13 Week 10 scenarios.
2. `scratch/analyze_week10_performance.py`:  
   Quantitative analysis script measuring scenario pass rates, terminal agreement, conflict deferrals, and safety gating.
3. `docs/week10_workflow_integration_report.md`:  
   Formal Week 10 engineering report (this document).

### 8.2 Files Modified:
1. `src/workflow/graph.py`:  
   Added error check `if state.get("workflow_status") == "error": return "finalize_output"` to `route_after_critic` to fix Critic runtime exception masking.
2. `scratch/run_safe_tests.py`:  
   Added `tests.test_week10_workflow_integration` to `SAFE_TEST_FILES`, expanding safe regression coverage from 101 to 118 tests.

---

## 9. Verification Commands and Actual Terminal Outputs

### 9.1 Focused Week 10 Test Suite
Command executed:
```bash
/home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_week10_workflow_integration.py -v
```
Actual output:
```
test_01_normal_workflow_end_to_end_verified_completion ... ok
test_02_conflicting_diagnostic_symptoms_withholds_chemicals ... ok
test_03a_low_confidence_vision_routes_to_deferred_review ... ok
test_03b_inadequate_class_margin_routes_to_deferred_review ... ok
test_04a_unsupported_disease_scope_routes_to_expert_review ... ok
test_04b_insufficient_literature_evidence_routes_to_review ... ok
test_05_critic_rejection_routes_through_manual_review ... ok
test_06_critic_runtime_exception_aborts_to_error_terminal_state ... ok
test_07_adaptive_reassessment_updates_case_and_preserves_history ... ok
test_08_repeated_reassessment_enforces_ceiling_terminal_escalation ... ok
test_09_reassessment_with_conflicting_evidence_requires_expert_review ... ok
test_10_state_and_history_integrity_preservation ... ok
test_11a_malformed_image_paths_handled_gracefully ... ok
test_11b_intermediate_nodes_missing_state_contracts_abort_safely ... ok
test_12_terminal_state_integrity_and_mutual_exclusivity ... ok
test_13a_week8_vision_limitation_uncontradicted_misclassification ... ok
test_13b_week8_vision_limitation_resolved_by_scouting_and_lab_reassessment ... ok

----------------------------------------------------------------------
Ran 17 tests in 46.038s

OK
```

### 9.2 Safe Regression Test Suite (Weeks 1–10)
Command executed:
```bash
/home/jaskirat/agrimind-rag-env/bin/python scratch/run_safe_tests.py
```
Actual output:
```
Total safe test cases loaded: 118
...
----------------------------------------------------------------------
Ran 118 tests in 109.333s

OK

==================================================
Tests run: 118
Failures : 0
Errors   : 0
Skipped  : 0
==================================================
```

---

## 10. Unresolved Design Questions and Remaining Limitations

1. **Active Reviewer Disconnection Assumption:**  
   In the current implementation, `manual_review_node` assumes no interactive human reviewer is synchronously connected during batch execution, defaulting immediately to `pending_manual_review`. In a production deployment with asynchronous UI or webhook integrations, an interactive human-in-the-loop pause/resume primitive (such as LangGraph's `interrupt()`) would be required.
2. **Symptom Cross-Check Rule Lexicon:**  
   The symptomological conflict rules in `InvestigationAgent` currently detect:
   - Concentric target rings vs. Late Blight
   - White sporulation vs. Bacterial Spot
   - Hot/dry weather ($>30^\circ\text{C}$) vs. Late Blight  
   Expanding this rule base to cover bacterial speck morphology vs. Early Blight lesions directly in text without requiring lab updates would further improve discrepancy detection.
3. **Dual Virtual Environment Boundary:**  
   PyTorch ResNet-50 vision inference resides in `agrimind-vision-env`, while LangGraph RAG and multi-agent coordination reside in `agrimind-rag-env`. In the current workflow integration tests, synthetic or pre-injected `VisionPrediction` objects are used to isolate agent logic deterministically. End-to-end multi-process bridge invocation between the two environments remains a design consideration for future user-facing deployment.

---

## 11. Stop Condition and Next Steps

Week 10 evaluation, bug fixing, and safe regression verification are fully complete. Development has ceased in accordance with the Phase Objective and Stop Condition. No Week 11 work will begin until explicit instruction is received from the user.
