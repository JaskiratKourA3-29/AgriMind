# AgriMind — Week 4 Implementation Report: Investigation and Risk Assessment Agent Logic (Audited Safety Corrections Applied)

**Date:** October 13, 2026  
**Stage:** Week 4 — Core Reasoning Agents (Investigation Agent & Risk Assessment Agent)  
**Execution Environment:** Dedicated virtual environment `/home/jaskirat/agrimind-rag-env` (Python 3.13.16)  
**Status:** **WEEK 4 AUDITED SAFETY CORRECTIONS COMPLETED AND EMPIRICALLY VERIFIED (17/17 UNIT TESTS PASSED; 33/33 TOTAL SUITE PASSED)**  
**Lead Architecture:** Antigravity Pair-Programming Assistant  

---

## Executive Summary

Pursuant to the official Week 4 project assignment, master prompt specifications, and the completed **Week 4 Evidence Audit of the Risk Assessment Severity Rubric**, the core reasoning agents responsible for evidence synthesis and severity characterization have been implemented, audited, corrected for agronomic safety, and empirically benchmarked within the dedicated AgriMind environment:

1. **Investigation Agent (`src/agents/investigation.py`):** Organizes, cross-examines, and synthesizes visual model predictions (Week 2 ResNet-50), physical field/canopy observations, and accredited agricultural extension literature (Week 3 LangChain RAG). It enforces strict separation between model predictions and retrieved facts, detects symptomological and epidemiological contradictions, and explicitly surfaces evidence gaps.
2. **Risk Assessment Agent (`src/agents/risk_assessment.py`):** Maps supported disease findings to standardized severity levels (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`, `INDETERMINATE`). **Crucially, all five categories and associated percentage cutoffs are explicitly documented as project-defined engineering heuristics**, calibrated from qualitative Land-Grant extension descriptions rather than official university numerical standards. It decouples model identification confidence from physical disease severity, implements conservative Late Blight epidemiological gating, corrects fungicide mode-of-action distinctions, and attaches mandatory pesticide safety disclaimers.
3. **Typed Schemas & Shared State (`src/agents/schemas.py`):** Enforces Pydantic v2 data validation across `VisionPrediction`, `VisualContext`, `RetrievedEvidence`, `InvestigationResult`, and `RiskAssessmentResult`. Added `pesticide_safety_notice` field to mandate regulatory notices.
4. **Prompt Architecture (`src/agents/prompts.py`):** Establishes anti-hallucination prompt definitions and structured synthesis templates, explicitly framing severity categories as project-defined heuristics.
5. **Empirical Verification (`tests/test_agents.py`):** 17 comprehensive unit tests verify evidence synthesis, conflict detection, missing context handling, out-of-scope disease handling, severity assignment, conservative Late Blight gating under low damage and missing context, fungicide mode-of-action attribution, pesticide safety notice attachment, and project heuristic transparency (100% pass rate). Combined with existing Week 3 suites, **33 total unit tests pass cleanly**.

All protected artifacts (Week 2 ResNet-50 checkpoint `outputs/week2_vision/best_model.pth` and Week 3 50-chunk Chroma collection `agrimind_tomato_diseases`) remain 100% intact with zero overwrites or modifications.

---

## 1. Master Prompt Requirements & Audited Safety Corrections

The master prompt (sections 13 & 14) and the Week 4 safety audit mandate the following corrections:

### 1.1 Provenance of Severity Rubrics (Project-Defined Engineering Heuristics)
- **Finding:** The six curated extension fact sheets (Cornell, UF/IFAS, Purdue, UC IPM) describe disease symptoms qualitatively (e.g. "lower leaves first", "bullseye rings", "sunscald exposure", "rapid defoliation"). They do *not* define an official numerical rubric with 10%, 25%, 35%, or 50% cutoffs.
- **Correction Applied:** All code comments, schema docstrings (`SeverityLevel`), prompt instructions (`RISK_ASSESSMENT_SYSTEM_PROMPT`), and agent output entries (`rubric_basis`) explicitly identify the five categories and percentage bands as **project-defined engineering heuristics**. The extension institutions are cited for qualitative pathogen biology (e.g., rapid cycle time, vascular collar rot, fruit loss), without claiming university endorsement of the numerical cutoffs.

### 1.2 Conservative Late Blight Epidemiological Gating
- **Finding:** *Phytophthora infestans* is an explosive oomycete pathogen capable of complete crop destruction in 7–10 days under cool, humid conditions. UC IPM (`DOC-UCIPM-TOM-LB-02:38`) states that once late blight reaches 5% to 10% canopy infection, chemical control is ineffective. An unsupported 25% threshold or generic foliar percentage bands could dangerously downgrade Late Blight to LOW or MODERATE under conducive weather.
- **Correction Applied:**
  - **Threshold Elimination:** Removed the unsupported 25% damage threshold.
  - **Active Sporulation or $\ge 5\%$ Damage under Conducive Weather:** Triggers `CRITICAL` severity, `epidemic_risk="critical"`, `requires_immediate_action=True`, and `requires_human_expert_review=True`. Recommends immediate rogueing of initial hot-spot plants (bagging on dry sunny midday per Cornell Extension) and emergency consultation.
  - **Early Infection ($< 5\%$ Damage) under Conducive Weather:** Escalates to `HIGH` severity, `epidemic_risk="high"`, and `requires_immediate_action=True`. It is **never downgraded to LOW or MODERATE** when weather is cool/wet/humid.
  - **Single Cropped Leaf (Missing Canopy Context):** Assigns physical severity as `INDETERMINATE`, but elevates `epidemic_risk="high"`, `requires_immediate_action=True`, and `requires_human_expert_review=True`, warning growers that a single leaf lesion under field conditions warrants urgent whole-planting inspection.
  - **Model Prediction vs Confirmed Diagnosis:** Clearly separates computer vision classification from agronomic field confirmation.

### 1.3 Fungicide Mode-of-Action Attribution & Curative Claims
- **Finding:** Cornell Extension (`DOC-CORNELL-TOM-LB-01:49-50`) distinguishes between specific targeted oomycides. Cymoxanil (Curzate) provides 24–48 hours of post-infection/curative "kickback" activity when tank-mixed with protectants. Mandipropamid (Revus) provides preventative and anti-sporulant activity. Mandipropamid does *not* possess curative kickback activity.
- **Correction Applied:**
  - Attributed 24–48-hour post-infection kickback activity exclusively to Cymoxanil (tank-mixed with protectant per Cornell Extension).
  - Described Mandipropamid (Revus) strictly for preventative and anti-sporulant protection.
  - Prohibited unsubstantiated product-specific treatment directions.

### 1.4 Calibrated Scouting Guidance
- **Finding:** Instructions such as "scout 20 plants in a W/Z pattern", "scout twice-weekly", or "re-scout in 4–5 days" were not stated in the six curated fact sheets.
- **Correction Applied:**
  - Removed arbitrary, ungrounded sampling commands.
  - Labeled canopy sampling recommendations as general IPM suggestions rather than institutional requirements from the curated fact sheets.

### 1.5 Mandatory Pesticide Safety Safeguards
- **Finding:** Recommendations referencing chemical fungicides must never appear without prominent regulatory, legal, and safety disclaimers.
- **Correction Applied:**
  - Added `pesticide_safety_notice` to `RiskAssessmentResult`.
  - Added `MANDATORY_PESTICIDE_SAFETY_NOTICE` to all risk assessment outputs:
    > "MANDATORY PESTICIDE SAFETY NOTICE: Any pesticide or fungicide application must strictly adhere to the manufacturer's product label, which is a legally binding document under federal and state/provincial pesticide regulations. Applicators must verify current product registration, approved target crops, application rates, spray volume, Worker Protection Standard requirements, Restricted-Entry Intervals (REI), Pre-Harvest Intervals (PHI), and resistance management (FRAC code) guidelines. If label directions or local regulations are unclear, consult your county agricultural extension office, state department of agriculture, or a certified crop advisor prior to application."

---

## 2. Pre-Implementation Audit & Baseline Architecture

Prior to Week 4 implementation, the project state was verified:
- **Vision Baseline (Week 2):** ResNet-50 checkpoint at `outputs/week2_vision/best_model.pth` achieving Macro-F1 of 0.9828 across 3 classes:
  - `Tomato___Bacterial_spot`
  - `Tomato___Early_blight`
  - `Tomato___Late_blight`
- **LangChain RAG Pipeline (Week 3):** Persistent local ChromaDB collection `agrimind_tomato_diseases` containing 50 verified chunks embedded with local `sentence-transformers/all-MiniLM-L6-v2`. `AgrimindRetriever` subclasses `langchain_core.retrievers.BaseRetriever` and implements similarity threshold gating (`0.56`) with institutional citations.
- **Existing Agent Modules:** No multi-agent reasoning modules existed in `src/agents/`.
- **Agricultural Pathology Literature:** 6 curated Land-Grant extension guides in `data/knowledge_base/raw/` providing documented symptom progression, environmental epidemiology, and management practices for the 3 target diseases.

---

## 3. Investigation Agent Design (`src/agents/investigation.py`)

### 3.1 Responsibilities & Workflow
The Investigation Agent receives visual predictions, optional grower canopy observations, and agricultural extension literature:
1. **Scope Validation:** Verifies whether the predicted pathogen is within AgriMind's 3 verified tomato classes. Unsupported diseases are flagged immediately.
2. **Dynamic / Supplied Retrieval:** If literature evidence is not pre-supplied, queries `AgrimindRetriever` with metadata filtering and similarity score gating.
3. **Conflict Detection Engine:**
   - *Classification Ambiguity:* Flags predictions with confidence < 0.60 or top-class probability margins < 0.15.
   - *Symptom Inconsistencies:* Flags contradictions between model predictions and grower field notes (e.g. vision predicts Late Blight, but notes describe concentric bullseye target rings characteristic of Early Blight; or vision predicts Bacterial Spot, but notes describe white cottony mold).
   - *Epidemiological Mismatches:* Flags environmental conflicts (e.g. Late Blight reported in hot, dry weather > 30°C, which halts *Phytophthora infestans* sporulation).
4. **Evidence Completeness Status:** Categorizes overall diagnostic standing:
   - `sufficient`: Visual, contextual, and literature evidence are verified and aligned.
   - `insufficient_context`: Visual prediction exists, but canopy vertical spread or leaf damage percentage is missing.
   - `insufficient_literature`: Retrieved agricultural literature falls below calibrated similarity threshold (`0.56`).
   - `conflicting`: Severe discrepancy detected between visual prediction, field symptoms, or weather.
   - `unsupported_disease`: Pathogen is outside the verified 3-class scope.
5. **Structured Synthesis Narrative:** Produces a markdown diagnostic brief with sectioned headers clearly distinguishing `[VISUAL MODEL FINDINGS]`, `[FIELD OBSERVATIONS]`, `[EXTENSION LITERATURE EVIDENCE]`, and `[STATUS & LIMITATIONS]`.

### 3.2 Prompt Design (`src/agents/prompts.py`)
- `INVESTIGATION_SYSTEM_PROMPT`: Directs the reasoning system to maintain strict evidence boundaries, preserve citation provenance `[1]`, `[2]`, detect conflicts, and prevent hallucination.
- `INVESTIGATION_USER_PROMPT_TEMPLATE`: Injects formatted visual probabilities, damage metrics, organ involvement, canopy spread, weather, and retrieved literature blocks.

---

## 4. Risk Assessment Agent Design (`src/agents/risk_assessment.py`)

### 4.1 Agronomic Severity Rubric (Project-Defined Heuristics)
Calibrated from extension literature descriptions (Cornell CALS, UF/IFAS, Purdue, and UC IPM) into transparent project engineering heuristics:

| Severity Level | Heuristic Criteria & Field Thresholds | Epidemic Risk | Required Action |
| :--- | :--- | :---: | :---: |
| **`INDETERMINATE`** | • Single cropped leaf image without canopy context.<br>• Conflicting evidence detected between model and notes.<br>• Unsupported pathogen outside 3-class scope.<br>• Missing quantitative damage data.<br>*(For Late Blight: escalates urgency while keeping severity indeterminate)* | Dependent on pathogen (High if Late Blight) | Re-scout canopy; reconcile symptoms; urgent human expert review if Late Blight or conflicting. |
| **`LOW`** | • Foliar damage < 10% leaf area.<br>• Confined to lower canopy.<br>• Leaves only (zero stem cankers, zero fruit rot).<br>• Incipient lesions (< 1/8" spots, no sporulation).<br>*(Does NOT apply to Late Blight under conducive weather)* | Low | Preventative sanitation; prune lower leaves; general IPM re-scouting. |
| **`MODERATE`** | • Foliar damage 10% – 35% leaf area.<br>• Progressing to mid-canopy.<br>• Leaves predominantly; zero fruit or girdling stem lesions.<br>• Established concentric bullseye rings or coalescing greasy lesions.<br>*(Late Blight localized <5% under non-conducive hot/dry weather)* | Moderate | Preventative protectant spray (chlorothalonil, mancozeb); regular IPM scouting. |
| **`HIGH`** | • Foliar damage > 35% leaf area.<br>• Disease reached upper canopy or whole plant.<br>• Direct economic fruit involvement (scabs/rot).<br>• Stem cankers / collar rot present; sunscald exposure.<br>• **Late Blight under conducive weather even at < 5% damage.** | High | Immediate action; targeted protectant/systemic fungicide spray; restrict field entry. |
| **`CRITICAL`** | • Systemic canopy collapse ($\ge 50\%$ damage across whole plant/field).<br>• **Late Blight with active sporulation or $\ge 5\%$ damage under cool/wet weather.**<br>• Chemical control ineffective beyond 5–10% canopy infection (UC IPM). | Critical | Immediate rogueing of initial hot-spot plants (bagging on dry midday per Cornell); emergency oomycide intervention; notify extension. |

### 4.2 Decoupling Identification Confidence from Disease Severity
A central design requirement of Week 4 is preventing false certainty:
```python
# Cropped single leaf with 99.5% classification confidence:
risk_result = risk_agent.assess_risk(investigation)
assert risk_result.identification_confidence == 0.995  # Model is certain of pathogen
assert risk_result.assigned_severity == SeverityLevel.INDETERMINATE  # Severity cannot be known
assert risk_result.requires_immediate_action is True  # Escalates if Late Blight suspected
```
This ensures AgriMind does not present ungrounded conclusions to growers.

---

## 5. Verification and Test Results

The full agent test suite (`tests/test_agents.py`) and Week 3 regression suites were executed in the dedicated `/home/jaskirat/agrimind-rag-env` virtual environment:

```bash
# Agent tests (including audited safety corrections)
wsl -d Ubuntu -e /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_agents.py

# Week 3 regression tests (safe execution without index rebuild)
wsl -d Ubuntu -e /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_langchain_retriever.py tests/test_rag_generation.py
```

### 5.1 Real Execution Results for `tests/test_agents.py` (17/17 PASSED)
- `test_01_investigation_sufficient_evidence`: **PASSED** (Full visual + context + RAG synthesis verified; citations preserved).
- `test_02_investigation_missing_canopy_context`: **PASSED** (Cropped leaf correctly flagged as `INSUFFICIENT_CONTEXT`).
- `test_03_investigation_conflicting_symptoms`: **PASSED** (Late Blight vs Early Blight bullseye rings detected as `CONFLICTING`).
- `test_04_investigation_unsupported_disease`: **PASSED** (`Septoria_leaf_spot` flagged as `UNSUPPORTED_DISEASE`).
- `test_05_investigation_insufficient_literature`: **PASSED** (Out-of-domain query triggers `INSUFFICIENT_LITERATURE`).
- `test_06_risk_assessment_indeterminate_when_context_missing`: **PASSED** (99.5% confidence decoupled from `INDETERMINATE` severity).
- `test_07_risk_assessment_low_severity`: **PASSED** (<10% lower canopy maps to `LOW`).
- `test_08_risk_assessment_moderate_severity`: **PASSED** (22% mid-canopy maps to `MODERATE`).
- `test_09_risk_assessment_high_severity`: **PASSED** (40% damage with fruit involvement maps to `HIGH`).
- `test_10_risk_assessment_critical_severity`: **PASSED** (Late Blight under cool/wet weather maps to `CRITICAL`).
- `test_11_risk_assessment_indeterminate_on_conflict`: **PASSED** (Conflict triggers `INDETERMINATE` and `requires_human_expert_review=True`).
- `test_12_risk_assessment_indeterminate_on_unsupported_disease`: **PASSED** (Unsupported disease safely triggers `INDETERMINATE`).
- `test_13_late_blight_low_damage_conducive_weather_escalation`: **PASSED** (Late Blight at 3% damage under cool/wet weather escalates to `HIGH`, avoiding unsafe downgrading).
- `test_14_late_blight_active_sporulation_critical`: **PASSED** (Active sporulation triggers `CRITICAL` severity and immediate rogueing recommendation).
- `test_15_late_blight_missing_context_urgent_escalation`: **PASSED** (Single leaf Late Blight keeps physical severity `INDETERMINATE` but flags urgent action and high epidemic risk).
- `test_16_fungicide_activity_descriptions_and_pesticide_safety_notice`: **PASSED** (Cymoxanil verified for curative kickback, Mandipropamid verified for preventative/anti-sporulant, pesticide safety notice verified).
- `test_17_project_heuristic_transparency_in_rubric_basis`: **PASSED** (Rubric basis explicitly labels percentage bands as "Project heuristic").

**Test Execution Time:** 37.209s  
**Status:** `Ran 17 tests in 37.209s, OK`

### 5.2 Full Regression Suite (33/33 PASSED)
- `tests/test_langchain_retriever.py`: 7 passed (LangChain compliance, `invoke()`, metadata filtering, 50-chunk count).
- `tests/test_rag_generation.py`: 9 passed (Answer generation, fallback, citation schema, mock LLM).
- `tests/test_agents.py`: 17 passed (Investigation and Risk Assessment Agent logic with audited safety corrections).
- **Cumulative Test Pass Rate:** **33/33 tests passed (100%)**.

---

## 6. Protection of Completed Work and Deliverables

| Protected Artifact | Location | Verification Method | Status |
| :--- | :--- | :--- | :---: |
| Week 2 Vision Model | `outputs/week2_vision/best_model.pth` | File integrity / SHA check (282,626,785 bytes) | **UNTOUCHED & VERIFIED** |
| Week 2 Metrics | `outputs/week2_vision/final_evaluation.json` | Read-only check | **UNTOUCHED** |
| ChromaDB Collection | `data/vectorstore/chroma/` | `collection.count() == 50` | **PRESERVED (50 chunks)** |
| Knowledge Chunks | `data/knowledge_base/processed_chunks.json` | Read-only inspection | **UNTOUCHED** |
| Metadata Manifest | `data/knowledge_base/metadata_manifest.json` | Read-only inspection | **UNTOUCHED** |
| Data Splits | `data_splits/` (train/val CSVs) | Read-only inspection | **UNTOUCHED** |
| PlantDoc Dataset | Local dataset directories | Restricted access policy | **STRICTLY UNACCESSED** |
| Environments | `agrimind-eda`, `fiftyone-env`, `agrimind-vision-env` | Process isolation | **UNTOUCHED** |

---

## 7. Remaining Limitations and Next Steps

1. **Canopy Context Acquisition:** In production, single smartphone photos of tomato leaves only provide visual classification. For accurate severity scoring, the user interface (Week 5/6) must prompt growers for secondary observations (e.g. estimated defoliation percentage, canopy location, or fruit involvement).
2. **Multi-Organ Vision:** Current vision baseline operates solely on single leaf images. Expanding visual detection to fruit and stem cankers remains future scope (Semester 8).
3. **Pesticide Product Registrations:** Because EPA and state pesticide registrations vary by state, year, and formulation, AgriMind does not provide legal application rates or chemical prescriptions; growers are explicitly guided to consult their local extension office and official product labels.
4. **Next Phase (Week 5):** Decision Planning and Critic Agent logic to synthesize actionable management recommendations, chemical safety guidelines, and hallucination critiques.
