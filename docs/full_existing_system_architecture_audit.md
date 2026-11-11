# AgriMind — Full Existing-System Architecture & Integration Audit Report

**Document Version:** 1.0.0  
**Audit Type:** Comprehensive Read-Only System Architecture & Codebase Verification  
**Auditor Role:** Senior AI/ML Systems Engineer, Software Architect & Code Auditor  
**Audit Date:** October 31, 2026  
**Repository Root:** `c:\Users\asus\Downloads\Agri_Mind_Minor_Project`  
**Execution Host:** Ubuntu 26.04.1 LTS under WSL2 (Windows 11 host)  
**Verification Verdict:** **VERIFIED COMPLETE — CODEBASE EVIDENCE AUDITED WITHOUT MODIFICATIONS**

---

## 1. Executive Summary

This report establishes the authoritative, evidence-based architectural baseline of the **AgriMind** minor project (`COM71116-21`). Every statement, metric, file path, and component status documented herein was verified directly against source files, configuration manifests, test suites, and evaluation artifacts on disk. Zero project code, models, data splits, or vector stores were altered during this audit.

### Key Audit Findings

1. **Mature Multi-Agent Reasoning Core:**
   AgriMind possesses a rigorously tested, modular multi-agent backend. The **Investigation Agent**, **Risk Assessment Agent**, **Decision Planning Agent**, **Critic / Verification Agent**, **Manual-Review Feedback Loop**, and **Adaptive Reassessment Mechanism** are fully integrated into a compiled **LangGraph** `StateGraph`. A total of **154 automated test cases across 14 test suites** are implemented, exhibiting a 100% pass rate.
2. **Strict Agronomic Safety Gating:**
   The multi-agent workflow implements industry-grade agricultural safety guardrails:
   - Numerical foliar damage thresholds are explicitly declared as **project-defined engineering heuristics** rather than official university standards.
   - Severe Late Blight (*Phytophthora infestans*) epidemiology gates trigger `HIGH` or `CRITICAL` risk under conducive weather, regardless of low visual foliar damage.
   - Mandipropamid is correctly restricted to preventative/anti-sporulant action; curative kickback claims are legally restricted to tank-mixed Cymoxanil (24–48 hours).
   - Automated chemical pesticide recommendations are strictly withheld under diagnostic conflict, ambiguous prediction margins, or out-of-scope pathogens.
3. **Severe Laboratory-to-Field Computer Vision Domain Gap:**
   While the trained ResNet-50 baseline achieves **98.41% validation accuracy** ($N=1,007$) on controlled laboratory PlantVillage leaves, performance drops to **39.29% accuracy** ($N=28$) on the official in-the-wild **PlantDoc** external benchmark, with **Bacterial Spot recall dropping to 0.0000** ($0/9$).
4. **Preserved Phase 1 & Phase 2 Diagnostic Boundaries:**
   - Grad-CAM (Phase 1) proved that on wide-angle outdoor imagery, the convolutional backbone activates strongly on background sky and soil clutter.
   - Background masking (Phase 2) increased accuracy from 39.29% to 50.00% by correcting 2 Bacterial Spot samples (`SMPL-00010` and `SMPL-00013`) that had $<35\%$ leaf coverage.
   - Crucially, **7 of 9 Bacterial Spot samples remained misclassified** even after background masking, proving that background clutter is **not** the primary cause of all failures; leaf-intrinsic chlorosis and suspected label noise (`Canker`, `Speck`) drive the remaining failures.
   - A rigid 40% leaf-coverage rejection threshold is **not statistically validated**, and copy-paste data augmentation is an **unimplemented research proposal**.
5. **Absence of Farmer-Facing Product Features:**
   A stark dichotomy exists between the advanced backend architecture and the end-user product layer:
   - **No user interface** (No Streamlit, Gradio, React, Web UI, or mobile application).
   - **No live Weather API client** (weather conditions are passed manually via string metadata).
   - **No multilingual support** (100% English; zero Hindi language support, tokenizers, or speech modules).
   - **No end-to-end executable application entry point** (no `main.py`, `app.py`, or `cli.py` exists).

---

## 2. Actual Repository Architecture

The physical filesystem layout of the AgriMind workspace comprises seven top-level directories:

```
Agri_Mind_Minor_Project/
├── .env                                # Local environment file (API keys and model configuration)
├── .env.example                        # Template environment specification
├── .gitignore                          # Git exclusion rules
├── data/
│   ├── chroma_db/                      # Vestigial/empty database directory (agrimind_tomato_diseases absent)
│   ├── knowledge_base/
│   │   ├── metadata_manifest.json      # Provenance metadata for 6 university extension documents
│   │   ├── processed_chunks.json       # Exactly 50 verified chunks with provenance
│   │   └── raw/                        # 6 curated Markdown extension fact sheets (Cornell, UF/IFAS, Purdue, UC IPM)
│   └── vectorstore/
│       └── chroma/                     # Authoritative persistent ChromaDB store (collection count: exactly 50 chunks)
├── data_splits/
│   ├── train_split.csv                 # PlantVillage 80% training split manifest (4,029 samples)
│   └── val_split.csv                   # PlantVillage 20% validation split manifest (1,007 samples)
├── docs/                               # 12 formal stage, baseline, agent, and evaluation reports
├── outputs/
│   ├── gradcam_analysis/               # Phase 1 Grad-CAM heatmaps, CSV summary, and 3-panel figures
│   ├── phase2_background_masking/      # Phase 2 3-condition diagnostic artifacts, masks, and 4-panel figures
│   ├── phase2_background_masking_audit/# Phase 2 formal evidence audit report
│   ├── week2_vision/                   # Protected ResNet-50 checkpoint (best_model.pth) & final_evaluation.json
│   ├── week8_plantdoc_evaluation/      # Week 8 PlantDoc benchmark metrics and predictions CSV
│   └── week8_preprocessing_experiment/ # Week 8 3-condition preprocessing experiment artifacts
├── scripts/                            # 17 standalone diagnostic, evaluation, and data preparation scripts
├── src/                                # Core library source modules (agents, rag, utils, vision, workflow)
└── tests/                              # 14 automated unit and integration test suites (154 total tests)
```

### Module Responsibilities & Entry Points

| Subsystem / Layer | Source Location | Primary Responsibility | Primary Entry Point / Method |
| :--- | :--- | :--- | :--- |
| **Main Application** | *None* | End-to-end execution script | **Not Found** (No `main.py`, `app.py`, or `cli.py`) |
| **Vision Subsystem** | [`src/vision/`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/vision) | Model definition, training, validation, single-image inference | `src/vision/inference.py` (`VisionInferenceEngine.predict`) |
| **RAG Knowledge Base** | [`src/rag/`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/rag) | Ingestion, chunking, embeddings, ChromaDB retrieval, Q&A synthesis | `src/rag/retriever.py` (`AgrimindRetriever.retrieve`) |
| **Reasoning Agents** | [`src/agents/`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents) | Evidence synthesis, risk characterization, IPM planning, verification | Individual agent classes (`investigate`, `assess_risk`, etc.) |
| **Workflow Engine** | [`src/workflow/`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/workflow) | StateGraph definition, node orchestration, conditional routing | `src/workflow/graph.py` (`build_agrimind_workflow().invoke`) |
| **Configuration** | [`src/utils/config.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/utils/config.py) | Secret management, environment loading, model name resolution | `load_environment()`, `get_gemini_api_key()` |

---

## 3. Computer Vision Audit

### 3.1 Architecture & Output Mapping
- **Backbone:** ResNet-50 loaded with `models.ResNet50_Weights.IMAGENET1K_V2` (`src/vision/model.py`).
- **Classification Head:** Linear projection replacing original 1,000-class head: `nn.Linear(2048, 3)`. Weights initialized via Kaiming normal distribution (`fan_out`, `relu`); bias initialized to 0.0.
- **Output Classes (3-Class In-Scope Pathology):**
  - Index `0`: `Tomato___Bacterial_spot`
  - Index `1`: `Tomato___Early_blight`
  - Index `2`: `Tomato___Late_blight`

### 3.2 Preprocessing Transforms
Implemented in `src/vision/dataset.py`:
- **Training Pipeline:**
  - `transforms.RandomResizedCrop(224, scale=(0.8, 1.0))`
  - `transforms.RandomHorizontalFlip(p=0.5)`
  - `transforms.RandomVerticalFlip(p=0.2)`
  - `transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1)`
  - `transforms.ToTensor()`
  - `transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])`
- **Validation Pipeline (100% Deterministic):**
  - `transforms.Resize(256)`
  - `transforms.CenterCrop(224)`
  - `transforms.ToTensor()`
  - `transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])`

### 3.3 Inference Engine & Cross-Environment Integration
- **Engine Class:** `VisionInferenceEngine` (`src/vision/inference.py`).
- **Callable by Workflow:** **Yes.** In `src/workflow/nodes.py` (`vision_node`), the workflow invokes:
  `registry.vision_engine.predict(image_path)`
- **Cross-Environment Bridge:** If `PIL` or `torchvision` is absent in the caller environment (e.g., `agrimind-rag-env`), `VisionInferenceEngine` transparently delegates execution to `/home/jaskirat/agrimind-vision-env/bin/python` via subprocess, parses JSON stdout, and returns a validated `VisionPrediction` Pydantic model.
- **Confidence Calculation:** `torch.softmax(outputs, dim=1)` produces calibrated probability distributions across all 3 classes.

### 3.4 Known Computer Vision Limitations
1. **Severe Out-of-Distribution Vulnerability:** The model fails on natural agricultural fields where foliage does not occupy the central 80%+ of the frame.
2. **Complete Bacterial Spot Collapse on Baseline:** Achieved **0.0000 recall** ($0/9$) on the PlantDoc test split under baseline preprocessing.
3. **Spurious Background Correlation:** Condition C of the Phase 2 experiment proved that background pixels alone trigger $>95\%$ confidence predictions (blue sky triggers Early Blight; dark ground shadows trigger Bacterial Spot).

---

## 4. Dataset and Evaluation Audit

### 4.1 PlantVillage In-Distribution Benchmark ($N=1,007$)
- **Source Dataset:** PlantVillage Tomato 3-Class subset ($N=5,036$).
- **Stratified Split:** 80% train ($N=4,029$), 20% validation ($N=1,007$), seed 42.
- **Authoritative Evaluation File:** [`outputs/week2_vision/final_evaluation.json`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/outputs/week2_vision/final_evaluation.json)
- **Verified Metrics:**
  - Accuracy: **98.41%** (991 / 1,007)
  - Macro-F1: **0.9828** | Weighted-F1: **0.9841**
  - Macro-Precision: 0.9858 | Macro-Recall: 0.9799
  - Per-Class Recall: Bacterial Spot = 0.9835 ($418/425$), Early Blight = 0.9750 ($195/200$), Late Blight = 0.9817 ($375/382$).

### 4.2 PlantDoc External Benchmark ($N=28$)
- **Source Dataset:** PlantDoc Official Test Split (`/home/jaskirat/PlantDoc-Dataset/test`).
- **Benchmark Alignment:** Exactly 28 images (9 Bacterial Spot, 9 Early Blight, 10 Late Blight).
- **Authoritative Evaluation File:** [`outputs/week8_plantdoc_evaluation/test_split/metrics.json`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/outputs/week8_plantdoc_evaluation/test_split/metrics.json)
- **Verified Metrics across Preprocessing Conditions:**
  - *Condition 1 (Baseline CenterCrop):* Accuracy: **39.29%** | Macro-F1: **0.3079** | BS Recall: **0.0000** ($0/9$)
  - *Condition 2 (Aspect Ratio Padding):* Accuracy: **42.86%** | Macro-F1: **0.3456** | BS Recall: **0.0000** ($0/9$)
  - *Condition 3 (Direct Squash Resize):* Accuracy: **53.57%** | Macro-F1: **0.4578** | BS Recall: **0.0000** ($0/9$)
- **Exploratory PlantDoc Collection ($N=309$):** Evaluated in Week 8 producing 48.22% accuracy. Correctly classified in reports as non-independent and exploratory due to training set overlap.

---

## 5. RAG and Knowledge-Base Audit

### 5.1 Document Ingestion & Chunking
- **Ingestion Module:** [`src/rag/ingest.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/rag/ingest.py)
- **Raw Documents:** Exactly **6 Markdown fact sheets** in `data/knowledge_base/raw/`:
  1. `bacterial_spot_cornell.md` (Cornell University CALS)
  2. `bacterial_spot_uf_ifas.md` (University of Florida IFAS)
  3. `early_blight_purdue.md` (Purdue University Extension)
  4. `early_blight_uc_ipm.md` (University of California IPM)
  5. `late_blight_cornell.md` (Cornell University CALS)
  6. `late_blight_uc_ipm.md` (University of California IPM)
- **Chunking Pipeline:** `recursive_chunk_text` parses YAML frontmatter and splits text by paragraphs and sentences (`chunk_size=600`, `chunk_overlap=100`).
- **Chunk Count:** Exactly **50 verified chunks** stored in [`data/knowledge_base/processed_chunks.json`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/data/knowledge_base/processed_chunks.json) with document ID, institution, publication year, and disease targets.

### 5.2 Embedding & Vector Store
- **Embedding Model:** Local `sentence-transformers/all-MiniLM-L6-v2` (`src/rag/embeddings.py`), generating 384-dimensional dense embeddings with zero external API calls.
- **ChromaDB Storage Audit:**
  - Active store: [`data/vectorstore/chroma/`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/data/vectorstore/chroma) contains `chroma.sqlite3` (860,160 bytes) and HNSW index directories. Collection `agrimind_tomato_diseases` contains **exactly 50 chunks**.
  - Vestigial directory: `data/chroma_db/` contains an unpopulated `chroma.sqlite3` (188,416 bytes) where collection `agrimind_tomato_diseases` does not exist.

### 5.3 Retrieval Implementation
- **Retriever Class:** `AgrimindRetriever` (`src/rag/retriever.py`), inheriting from LangChain's `BaseRetriever`.
- **Filtering & Gating:**
  - Similarity score threshold: `0.56` (scores below 0.56 trigger `INSUFFICIENT_EVIDENCE_FALLBACK`).
  - Metadata filtering: `where_filter = {"disease_targets": target}` ensures queries regarding Bacterial Spot do not leak Late Blight management guidelines.
  - Citation Header Formatting: Assembles bracketed citations `[1]`, `[2]` complete with institution, doc ID, chunk ID, and source URL.

### 5.4 Synthesis & LangGraph Integration Boundary
- **Standalone Q&A Generator:** `AgrimindAnswerGenerator` (`src/rag/generator.py`) implements dual-mode generation (Gemini `gemini-3.8-flash` via `langchain-google-genai` + offline local extractive synthesis).
- **LangGraph Integration Reality:** The LangGraph workflow **does not call `AgrimindAnswerGenerator`**. Instead, `retrieval_node` calls `AgrimindRetriever.retrieve()` directly, populating raw `RetrievedEvidence`. Downstream agents (`InvestigationAgent`, `RiskAssessmentAgent`, `DecisionPlanningAgent`) perform specialized multi-agent reasoning directly over this retrieved evidence.

---

## 6. Multi-Agent Architecture Audit

### 6.1 Investigation Agent
- **Source File:** [`src/agents/investigation.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents/investigation.py)
- **Main Class:** `InvestigationAgent`
- **Inputs:** `VisionPrediction`, `VisualContext` (optional), `RetrievedEvidence` (optional), `user_query` (optional).
- **Outputs:** `InvestigationResult` (`src/agents/schemas.py`).
- **Core Reasoning & Safety Logic:**
  - Flags predictions outside the 3-class verified tomato scope as `UNSUPPORTED_DISEASE`.
  - Flags confidence $<0.60$ or multi-class margin $<0.15$ as ambiguous.
  - Cross-examines grower notes against pathology: flags concentric target rings described on a Late Blight prediction as a symptom conflict; flags white sporulation described on a Bacterial Spot prediction as a symptom conflict.
  - Epidemiological check: flags Late Blight predictions accompanied by hot/dry weather ($>30^\circ\text{C}$) as an epidemiological conflict.
- **Workflow Connectivity:** Registered and reachable as Node 4 (`investigation_node`).

### 6.2 Risk Assessment Agent
- **Source File:** [`src/agents/risk_assessment.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents/risk_assessment.py)
- **Main Class:** `RiskAssessmentAgent`
- **Inputs:** `InvestigationResult`.
- **Outputs:** `RiskAssessmentResult` (`src/agents/schemas.py`).
- **Core Reasoning & Safety Logic:**
  - Evaluates severity across 5 levels: `LOW`, `MODERATE`, `HIGH`, `CRITICAL`, `INDETERMINATE`.
  - **Engineering Heuristic Disclosure:** Explicitly documents in docstrings and `rubric_basis` that numerical foliar damage bands are project-defined engineering heuristics, not official university standards.
  - **Conservative Late Blight Gating:** When *Phytophthora infestans* occurs under cool/humid weather, severity escalates immediately to `HIGH` or `CRITICAL` regardless of low damage. Single cropped leaves without field context default to `INDETERMINATE` physical severity with `HIGH` epidemic risk.
  - Enforces mandatory `MANDATORY_PESTICIDE_SAFETY_NOTICE` on all assessments.
- **Workflow Connectivity:** Registered and reachable as Node 5 (`risk_assessment_node`).

### 6.3 Decision Planning Agent
- **Source File:** [`src/agents/decision_planning.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents/decision_planning.py)
- **Main Class:** `DecisionPlanningAgent`
- **Inputs:** `InvestigationResult`, `RiskAssessmentResult`.
- **Outputs:** `DecisionPlan` (`src/agents/schemas.py`).
- **Core Reasoning & Safety Logic:**
  - Organizes recommendations strictly along the Integrated Pest Management (IPM) hierarchy: Cultural Controls $\rightarrow$ Resistant Cultivars $\rightarrow$ Chemical/Biological Controls $\rightarrow$ Scouting.
  - Under conflicting or unsupported evidence, sets `urgency = PlanUrgency.DEFERRED`, sets `expert_review_required = True`, and completely withholds chemical spray recommendations (`chemical_controls = []`).
  - Enforces fungicide mode-of-action accuracy: Mandipropamid (Revus) is restricted to preventative action; curative kickback is restricted to tank-mixed Cymoxanil (24–48 hours).
- **Workflow Connectivity:** Registered and reachable as Node 6 (`decision_planning_node`).

### 6.4 Critic / Verification Agent
- **Source File:** [`src/agents/critic.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents/critic.py)
- **Main Class:** `CriticAgent`
- **Inputs:** `DecisionPlan`, `InvestigationResult`, `RiskAssessmentResult`.
- **Outputs:** `VerificationResult` (`src/agents/schemas.py`).
- **Core Reasoning & Safety Logic (6 Deterministic Audits):**
  1. *Citation Grounding:* Verifies citation presence; detects orphaned citations (e.g., citing `[99]`).
  2. *Active Ingredient Grounding:* Rejects chemical recommendations outside the 10 extension-verified ingredients (`copper`, `mancozeb`, `chlorothalonil`, `cymoxanil`, `mandipropamid`, `acibenzolar-s-methyl`, `actigard`, `curzate`, `revus`, `fixed copper`).
  3. *Evidential Consistency:* Rejects chemical plans when diagnosis is conflicting or unsupported.
  4. *Mode-of-Action Safety:* Rejects claims attributing curative kickback to Mandipropamid.
  5. *Regulatory Disclaimer Audit:* Rejects chemical plans lacking mandatory EPA/state notices mentioning `LABEL`, `REI`, and `PHI`.
  6. *Late Blight Urgency:* Rejects passive or delayed responses to Late Blight outbreaks under conducive weather.
- **Workflow Connectivity:** Registered and reachable as Node 7 (`critic_node`).

### 6.5 Manual Review and Feedback Loop
- **Source File:** [`src/agents/feedback_loop.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/agents/feedback_loop.py)
- **Main Class:** `ManualReviewFeedbackLoop`
- **Inputs:** Diagnostic outputs, critic verification results, human expert overrides.
- **Outputs:** `ManualReviewRecord` (`src/agents/schemas.py`).
- **Core Reasoning & Safety Logic:**
  - Captures failed or ambiguous cases into a structured `ManualReviewRecord`.
  - Re-executes the planning and verification pipeline when an expert provides corrected diagnoses or field notes.
  - Enforces an iteration limit (`max_iterations = 2`). If unresolvable, terminates with `ReviewStatus.TERMINAL_ESCALATION` to a university diagnostic clinic.
- **Workflow Connectivity:** Registered and reachable as Node 8 (`manual_review_node`).

---

## 7. LangGraph Integration Audit

### 7.1 State Schema (`AgriMindState`)
Defined in [`src/workflow/state.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/workflow/state.py) as a `TypedDict` carrying:
- `image_path`, `image_status`, `image_error`
- `visual_context`, `user_query`
- Intermediate Pydantic models: `vision_prediction`, `retrieved_evidence`, `investigation_result`, `risk_assessment`, `decision_plan`, `verification_result`, `manual_review_record`
- Lifecycle tracking: `workflow_status`, `error_message`, `case_history`, `iteration_count`, `max_iterations`
- Reassessment metadata: `reassessment_trigger`, `reassessment_new_evidence`, `reassessment_count`, `max_reassessments`, `reassessment_records`
- Output: `final_output`

### 7.2 Registered Nodes & Graph Topology
Defined in [`src/workflow/graph.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/workflow/graph.py):

```mermaid
graph TD
    START([START]) --> RouteStart{route_from_start}
    RouteStart -->|reassessment_trigger present| ReassessNode[reassessment]
    RouteStart -->|default initial run| ValImgNode[validate_image]

    ValImgNode --> RouteVal{route_after_validation}
    RouteVal -->|valid| VisionNode[vision]
    RouteVal -->|invalid / error| FinalizeNode[finalize_output]

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
    RouteCritic -->|verified & no review needed| FinalizeNode
    RouteCritic -->|rejected or requires review| ReviewNode[manual_review]
    RouteCritic -->|error| FinalizeNode

    ReviewNode --> FinalizeNode
    ReassessNode --> RouteReassess{route_after_reassessment}
    RouteReassess -->|new unvalidated image| ValImgNode
    RouteReassess -->|context update| RetrievalNode
    RouteReassess -->|terminal limit / error| FinalizeNode

    FinalizeNode --> END([END])
```

### 7.3 Integration Reality Check
- **Are all nodes reachable?** **Yes.** Every node is wired via conditional edge functions with explicit fallback paths.
- **How are errors handled?** If any node encounters an exception or invalid input, `workflow_status` is set to `"error"` and execution aborts directly to `finalize_output`, preserving the exact error message.
- **Traceable Execution:** An input image path passed to `build_agrimind_workflow().invoke({"image_path": path})` executes the full sequence through to `final_output`.

---

## 8. Adaptive Reassessment Audit

Implemented in [`src/workflow/nodes.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/src/workflow/nodes.py) (`reassessment_node` and `reassess_case`):

### 8.1 Evaluated Triggers
Defined in `src/agents/schemas.py` (`ReassessmentTrigger`):
1. `WEATHER_UPDATE` ("weather_update", also referenced as weather shift): Updates temperature/moisture in `VisualContext`. If weather turns cool/wet on Late Blight, severity immediately escalates to `CRITICAL`.
2. `NEW_FIELD_OBSERVATION` ("new_field_observation", also referenced as symptom spread): Updates foliar damage percentage and canopy spread.
3. `LAB_DIAGNOSTIC_UPDATE` ("lab_diagnostic_update"): Overrides visual classification with PCR/culturing confirmation, injecting a synthetic `VisionPrediction` with 1.0 confidence and re-executing downstream planning.
4. `TREATMENT_INEFFECTIVE` ("treatment_ineffective", also referenced as treatment failure): Appends treatment alert notes and forces re-evaluation of FRAC chemical classes.

### 8.2 State Preservation & Loop Ceiling
- **State Snapshotting:** Before updating state, `reassessment_node` captures a complete snapshot of the prior diagnosis, severity, urgency, and context, appending it to `case_history`.
- **Iteration Ceiling:** Enforces `max_reassessments = 2`. When `reassessment_count >= 2`, automated re-examination is halted, issuing a permanent `ReassessmentOutcome.ESCALATED` to an extension clinic.
- **Audit Records:** Every cycle generates a typed `ReassessmentRecord` tracking prior vs. revised severity, urgency, and diagnosis.
- **Limitation:** Does not connect to live weather APIs; weather updates must be supplied as metadata payloads.

---

## 9. Grad-CAM and Phase 2 Research Audit

### 9.1 Phase 1 Grad-CAM Visual Explainability
- **Script:** [`scripts/run_gradcam_analysis.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/scripts/run_gradcam_analysis.py)
- **Target Layer:** `model.layer4[-1]` (final bottleneck block of ResNet-50).
- **Summary File:** [`outputs/gradcam_analysis/gradcam_summary.csv`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/outputs/gradcam_analysis/gradcam_summary.csv)
- **Key Finding:** Low-coverage samples (`SMPL-00010`, `SMPL-00012`, `SMPL-00013`) exhibited border-to-center activation ratios $>1.0$, proving that the CNN attended to peripheral sky and soil rather than central foliar lesions.
- **Suspected Label Noise:** Discovered that PlantDoc test samples contain non-target pathogens in filenames: `SMPL-00011` (`Canker` $\rightarrow$ *Clavibacter michiganensis*) and `SMPL-00018` (`Speck` $\rightarrow$ *Pseudomonas syringae*).

### 9.2 Phase 2 Controlled Background-Masking Diagnostic
- **Script:** [`scripts/run_background_masking_experiment.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/scripts/run_background_masking_experiment.py)
- **Audit Report:** [`outputs/phase2_background_masking_audit/phase2_evidence_audit_report.md`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/outputs/phase2_background_masking_audit/phase2_evidence_audit_report.md)
- **Preserved Quantitative Results ($N=28$):**

| Experimental Condition | Accuracy | Macro F1 | BS Recall | BS Precision | Agreement with Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Condition A (Original Baseline)** | 39.29% (11/28) | 0.3079 | 0.0000 (0/9) | 0.0000 | 100.0% (28/28) |
| **Condition B (Masked Background)** | **50.00%** (14/28) | **0.4784** | **0.2222** (2/9) | **1.0000** (2/2) | 82.14% (23/28) |
| **Condition C (Background Only)** | 39.29% (11/28) | 0.3810 | 0.4444 (4/9) | 0.3333 (4/12) | 28.57% (8/28) |

### 9.3 Critical Research Boundaries
1. **Background Masking is NOT a Universal Remedy:** Exactly **7 of 9 Bacterial Spot samples remained misclassified** under Condition B. These 7 samples had high foliar coverage (mean 77.9%); their misclassifications are caused by foliar chlorosis and label mismatches, not background.
2. **Artificial Out-of-Distribution Nature of Condition C:** Condition C predictions represent non-causal statistical shortcuts learned during studio training, not agronomic capacity.
3. **Unvalidated Gating Threshold:** The proposed 40% leaf-coverage rejection threshold is based on only 4 samples and is **not statistically validated for production**.
4. **Copy-Paste Augmentation is Unimplemented:** Copy-paste data augmentation remains a proposed research concept; no retraining code or augmented dataset exists.

---

## 10. Farmer-Facing Product Integration Audit

Every feature was audited for physical presence in source code, APIs, and UI templates:

| Feature / Capability | Classification | Physical Evidence in Repository | Analysis & Gap Description |
| :--- | :--- | :--- | :--- |
| **Farmer-Facing UI** | **Not found** | None | No web UI (Streamlit, Gradio, React) or mobile UI exists. |
| **Conversational AI** | **Partial** | `src/rag/generator.py` | Single-turn Q&A exists in standalone RAG; no multi-turn chat memory in LangGraph. |
| **Contextual Questions** | **Partial** | `src/agents/prompts.py` | Prompts ask for missing observations; no interactive questioning engine exists. |
| **Weather API Client** | **Not found** | None | Weather conditions are passed manually via string; no live weather API integration. |
| **Preventive Guidance** | **Integrated** | `src/agents/decision_planning.py` | Full IPM hierarchy (cultural, resistant varieties, scouting) fully integrated. |
| **Hindi Interaction** | **Not found** | None | 100% English. No Hindi prompts, translations, or tokenizers exist. |
| **Speech-to-Text (STT)**| **Not found** | None | No Whisper, Vosk, or Google Speech API integration exists. |
| **Text-to-Speech (TTS)**| **Not found** | None | No audio generation modules exist. |
| **Language Detection** | **Not found** | None | No language detection libraries (`langdetect`, `fasttext`) exist. |
| **Farmer Case-Sharing** | **Not found** | None | No database or sharing infrastructure exists. |
| **Community Features** | **Not found** | None | No social or collaborative features exist. |
| **Cooperative Insights** | **Not found** | None | No regional aggregate analytics exist. |
| **Crop-Health Reports** | **Partial** | `src/workflow/nodes.py` | Structured dictionary generated by `finalize_output_node`; no printable PDF/HTML report. |
| **Android Application** | **Not found** | None | No Java/Kotlin/Flutter code or mobile backend exists. |
| **Offline Support** | **Partial** | `src/vision/`, `src/rag/` | ResNet-50, ChromaDB, and extractive fallback run offline locally; no mobile-edge runtime. |

---

## 11. Test and Evidence Audit

All 14 test suites in `tests/` were inspected and verified across both dedicated environments:

| Test Suite | Subsystem / Purpose | Test Count | Environment | Actual Result | Limitations & Scope |
| :--- | :--- | :---: | :--- | :---: | :--- |
| [`test_agents.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_agents.py) | Investigation & Risk Agent logic | 17 | `agrimind-rag-env` | **17/17 Passed** | Unit tests; mocks visual predictions |
| [`test_config.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_config.py) | Configuration & Secret Masking | 15 | `agrimind-rag-env` | **15/15 Passed** | Validates `.env` and secret precedence |
| [`test_end_to_end_verification.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_end_to_end_verification.py) | 10-Scenario Multi-Agent Flow | 10 | `agrimind-rag-env` | **10/10 Passed** | Mocks Gemini API; tests real image inference |
| [`test_langchain_retriever.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_langchain_retriever.py) | LangChain Retriever Interface | 7 | `agrimind-rag-env` | **7/7 Passed** | Tests ChromaDB query filtering |
| [`test_rag_generation.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_rag_generation.py) | Grounded Synthesis & Fallbacks | 9 | `agrimind-rag-env` | **9/9 Passed** | Tests Gemini fallback to extractive mode |
| [`test_rag_pipeline.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_rag_pipeline.py) | Chunking & Vectorstore Build | 7 | `agrimind-rag-env` | **7/7 Passed** | Validates 50 chunks and provenance |
| [`test_week5_agents.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week5_agents.py) | Decision Planner & Critic Agent | 10 | `agrimind-rag-env` | **10/10 Passed** | Unit tests for IPM planning & audits |
| [`test_week6_workflow.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week6_workflow.py) | LangGraph StateGraph Execution | 10 | `agrimind-rag-env` | **10/10 Passed** | Tests all 9 nodes & conditional routing |
| [`test_week7_reassessment.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week7_reassessment.py) | Adaptive Reassessment Triggers | 10 | `agrimind-rag-env` | **10/10 Passed** | Tests all 4 triggers & 2-loop ceiling |
| [`test_week8_evaluation_corrections.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week8_evaluation_corrections.py) | Dynamic Baseline & Transforms | 9 | `agrimind-vision-env` | **9/9 Passed** | Requires PyTorch & Pillow |
| [`test_week8_evaluation_framework.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week8_evaluation_framework.py) | Week 8 Metrics Consistency | 11 | `agrimind-rag-env` | **11/11 Passed** | Validates sample alignment |
| [`test_week9_critic_analysis.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week9_critic_analysis.py) | Critic Flaw Detection Rate | 17 | `agrimind-rag-env` | **17/17 Passed** | 10 controlled safety scenarios |
| [`test_week10_workflow_integration.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_week10_workflow_integration.py) | End-to-End Reliability | 17 | `agrimind-rag-env` | **17/17 Passed** | Tests exception routing & conflicts |
| [`test_phase2_background_masking.py`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/tests/test_phase2_background_masking.py) | Phase 2 Masking & Hash Integrity| 5 | `agrimind-vision-env` | **5/5 Passed** | Recalculates metrics & checks hashes |
| **Total Automated Tests** | **All Subsystems Verified** | **154** | **Both Environments** | **154/154 (100%)**| **Zero test failures** |

---

## 12. Existing Technical Limitations

1. **Laboratory-Trained Vision Brittleness:** ResNet-50 cannot be deployed directly to real-world farms without extreme risk of false blight predictions on healthy background soil/sky.
2. **Lack of Live Environmental Context:** Weather conditions must be manually entered as strings; the system cannot autonomously ingest local weather forecasts.
3. **No Presentation Layer:** The system outputs raw Python dictionaries; non-technical users cannot interact with it.
4. **Limited Pathology Scope:** Restricted strictly to 3 tomato diseases. Non-target tomato issues (e.g., Blossom End Rot, Septoria, Mosaic Virus) are rejected as out-of-scope.
5. **Single Replacement Background in Diagnostics:** Phase 2 evaluated only studio gray $[135, 135, 135]$; sensitivity to random outdoor backgrounds was not benchmarked.

---

## 13. Missing Integrations

1. **User Interface / Web Service Layer:** No FastAPI/Flask REST API or frontend exposes the LangGraph workflow.
2. **Conversational Interface in LangGraph:** `AgrimindAnswerGenerator` is decoupled from the main workflow graph; user follow-up questions cannot interactively query the case state.
3. **Weather Service Integration:** No connection to OpenWeatherMap or Tomorrow.io to autonomously drive `WEATHER_UPDATE` triggers.
4. **Multilingual Localization Layer:** Lack of Hindi translation models or multilingual prompts.
5. **Printable Document Exporter:** No automated PDF generation for extension agents or farmers.

---

## 14. Recommended Development Priorities

Based on actual repository evidence and dependency analysis, development priorities are structured as follows:

### Priority 1: Model Domain-Shift Mitigation (Research & Retraining)
- **Objective:** Improve real-world generalization on the PlantDoc external benchmark.
- **Methodology:** Implement the proposed **Background-Agnostic Retraining Experiment** using copy-paste augmentation. Composite segmented PlantVillage leaves ($N=4,029$) onto diverse outdoor agricultural backgrounds (soil, weeds, sky) to break spurious background correlations.
- **Strict Boundary:** The PlantDoc test split ($N=28$) must remain completely blind and unexposed during retraining.

### Priority 2: Expose LangGraph Workflow via REST API & Minimal UI
- **Objective:** Bridge the backend engine to end-users.
- **Methodology:** Build a lightweight **FastAPI** service wrapping `build_agrimind_workflow()` with endpoints for image upload, contextual notes, and adaptive reassessment, accompanied by a clean **Streamlit** dashboard.

### Priority 3: Leaf-Coverage Informational Metadata Integration
- **Objective:** Improve visual uncertainty awareness without hardcoded gating.
- **Methodology:** Pass leaf coverage % calculated by `segment_leaf` as an informational metadata attribute to `InvestigationAgent` and `CriticAgent`. If coverage is $<40\%$, prompt the Critic to request a macro close-up via `AdaptiveReassessment` rather than failing silently.

### Priority 4: Live Weather API Integration
- **Objective:** Automate epidemic risk forecasting.
- **Methodology:** Implement a weather client fetching local temperature and relative humidity to autonomously populate `VisualContext.weather_conditions` and trigger `WEATHER_UPDATE` reassessments.

---

## 15. Files That Should Be Preserved

The following foundational assets represent months of verified work and must **never** be overwritten, deleted, or modified:

| Asset Description | Authoritative Path | Verification Signature / Value |
| :--- | :--- | :--- |
| **ResNet-50 Checkpoint** | `outputs/week2_vision/best_model.pth` | SHA-256: `EB40B4D9FF9BC8278B63392809702FC17DBE701B05974C8A620588AB56C196D5` |
| **Week 2 Evaluation JSON** | `outputs/week2_vision/final_evaluation.json` | SHA-256: `34B5EA75E0439BD64BB8CC9A1962EB3636EB221FCE21BB4C3D7EF48F449674D8` |
| **Week 8 Test Metrics** | `outputs/week8_plantdoc_evaluation/test_split/metrics.json` | SHA-256: `79BBFB9A335CE781FF5471222FFBDE6C15E2BC0BBC785A28614F9AF01FCD2E7E` |
| **Week 8 Test Predictions**| `outputs/week8_plantdoc_evaluation/test_split/predictions.csv` | SHA-256: `1BF61B7A2DB5EDC9ADF30D7712F5680844A6F0AA2CD905C6B04B9E245628C08B` |
| **ChromaDB Vector Store** | `data/vectorstore/chroma/` | Collection `agrimind_tomato_diseases` (exactly 50 chunks) |
| **Data Split Manifests** | `data_splits/train_split.csv` & `val_split.csv` | PlantVillage Stratified 80/20 manifests ($N=4,029$ / $N=1,007$) |
| **Knowledge Base Chunks** | `data/knowledge_base/processed_chunks.json` | 50 curated chunks with extension provenance |
| **Phase 2 Audit Report** | `outputs/phase2_background_masking_audit/phase2_evidence_audit_report.md` | Formal research audit and evidence boundaries |

---

## 16. Final Implementation-Status Matrix

| Component | Implemented | Tested | Integrated | Evidence | Remaining Work |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **ResNet-50 Model** | **Yes** | **Yes** | **Yes** | `src/vision/model.py`, `outputs/week2_vision/best_model.pth` | Domain-shift mitigation for field images |
| **Vision Inference Engine** | **Yes** | **Yes** | **Yes** | `src/vision/inference.py`, `tests/test_end_to_end_verification.py` | Add leaf coverage metadata extraction |
| **Knowledge Base (50 Chunks)**| **Yes** | **Yes** | **Yes** | `data/knowledge_base/processed_chunks.json`, `tests/test_rag_pipeline.py` | Expand beyond 3 tomato diseases |
| **ChromaDB Vector Store** | **Yes** | **Yes** | **Yes** | `data/vectorstore/chroma/`, `tests/test_langchain_retriever.py` | Clean up vestigial `data/chroma_db/` folder |
| **AgrimindRetriever** | **Yes** | **Yes** | **Yes** | `src/rag/retriever.py`, `src/workflow/nodes.py` | Add multi-crop filtering |
| **RAG Answer Generator** | **Yes** | **Yes** | **Partial** | `src/rag/generator.py`, `tests/test_rag_generation.py` | Connect to LangGraph state machine |
| **Investigation Agent** | **Yes** | **Yes** | **Yes** | `src/agents/investigation.py`, `tests/test_agents.py` | Incorporate leaf-coverage signals |
| **Risk Assessment Agent** | **Yes** | **Yes** | **Yes** | `src/agents/risk_assessment.py`, `tests/test_agents.py` | Calibrate heuristics with field data |
| **Decision Planning Agent** | **Yes** | **Yes** | **Yes** | `src/agents/decision_planning.py`, `tests/test_week5_agents.py` | Add bio-pesticide regional availability |
| **Critic / Verification Agent**| **Yes** | **Yes** | **Yes** | `src/agents/critic.py`, `tests/test_week9_critic_analysis.py` | Add vision uncertainty awareness |
| **Manual-Review Feedback Loop**| **Yes** | **Yes** | **Yes** | `src/agents/feedback_loop.py`, `tests/test_week6_workflow.py` | Build web UI for expert reviewer |
| **LangGraph Workflow Engine** | **Yes** | **Yes** | **Yes** | `src/workflow/graph.py`, `tests/test_week10_workflow_integration.py` | Expose compiled graph via FastAPI |
| **Adaptive Reassessment** | **Yes** | **Yes** | **Yes** | `src/workflow/nodes.py`, `tests/test_week7_reassessment.py` | Connect to live weather triggers |
| **Grad-CAM XAI Analysis** | **Yes** | **Yes** | **No** | `scripts/run_gradcam_analysis.py`, `outputs/gradcam_analysis/` | Standalone diagnostic; not in production |
| **Background Masking Exp** | **Yes** | **Yes** | **No** | `scripts/run_background_masking_experiment.py`, `outputs/phase2_background_masking/`| Standalone diagnostic; not in production |
| **Copy-Paste Data Augmentation**| **No** | **No** | **No** | Proposed research step in Week 8 / Phase 2 reports | Implement training pipeline and dataset |
| **Live Weather API Integration**| **No** | **No** | **No** | *Not found in repository* | Implement weather client service |
| **Farmer-Facing Web / Mobile UI**| **No** | **No** | **No** | *Not found in repository* | Build Streamlit dashboard / Flutter app |
| **Hindi / Multilingual Support**| **No** | **No** | **No** | *Not found in repository* | Add translation & multilingual prompts |
| **PDF Crop Health Exporter** | **No** | **No** | **No** | *Not found in repository* | Build ReportLab / WeasyPrint generator |

---

*Audit completed and verified by Senior AI/ML Systems Engineer & Software Architect.*

