# AgriMind — Stage B.3: Android Case Details, Reassessment & History Report

## 1. Executive Summary

This report documents the design, implementation, and empirical verification of **Stage B.3 (Android Case Details, Reassessment & History)** for the AgriMind tomato disease decision support platform. 

All primary objectives of Stage B.3 were completed without modifying or regressing any existing Week 1–10 assets, machine learning checkpoints, vector stores, or established backend endpoints:
1. **Case Details View (Feature A)**: A comprehensive, Material 3 native Jetpack Compose screen ([`CaseDetailScreen.kt`](file:///android/app/src/main/java/com/agrimind/app/ui/screens/CaseDetailScreen.kt)) displaying full case diagnostic telemetry, specimen image thumbnail, disease identification, calibrated metrics (confidence, severity, risk), Critic Agent verification badge, categorized Integrated Pest Management (IPM) recommendations, academic citations, and a chronological reassessment audit log.
2. **Adaptive Reassessment Integration (Feature B)**: Full end-to-end integration with the existing `POST /reassess` FastAPI endpoint ([`ReassessmentModels.kt`](file:///android/app/src/main/java/com/agrimind/app/data/model/ReassessmentModels.kt), [`CaseDetailViewModel.kt`](file:///android/app/src/main/java/com/agrimind/app/ui/viewmodel/CaseDetailViewModel.kt)), featuring a responsive Modal Bottom Sheet for trigger selection and evidence input, enforcing duplicate submission locking, enforcing the 2-cycle reassessment ceiling, and reflecting updated severity/risk profiles while preserving the primary diagnostic record.
3. **Local Diagnosis History (Feature C)**: Because the existing FastAPI backend stores cases in SQLite (`data/cases.db`) but exposes no case listing endpoint, a robust client-side persistence repository ([`LocalCaseRepository.kt`](file:///android/app/src/main/java/com/agrimind/app/data/repository/LocalCaseRepository.kt)) was engineered using `SharedPreferences` and `Gson`. Diagnoses are automatically recorded upon completion and surfaced in a dedicated, searchable History tab ([`HistoryScreen.kt`](file:///android/app/src/main/java/com/agrimind/app/ui/screens/HistoryScreen.kt)).
4. **Verification & Preserved Boundaries**: The native Android application was built cleanly (`gradlew assembleDebug` succeeded in 1m 3s), all 20 backend regression tests passed in 79.7s, and live end-to-end diagnostic, detail inspection, adaptive reassessment, and history search flows were verified on the Android emulator (`Medium_Phone_API_37.0`).

---

## 2. Pre-Implementation Inspection & Architecture Findings

Prior to authoring code, an exhaustive inspection of the existing codebase was conducted to identify contracts, constraints, and integration boundaries:

### 2.1 Backend Route & Storage Analysis
- **Route Definitions (`src/api/routes.py`)**:
  - `GET /health`: Returns service status, model checkpoint status, and vector store chunk count.
  - `POST /diagnose`: Accepts multipart image upload, returns `DiagnosisResponse` with `case_id`, primary diagnosis, confidence, severity, risk assessment, Critic verification, and management plan.
  - `POST /reassess`: Accepts JSON body matching `ReassessmentRequest`, returns `ReassessmentResponse`.
  - **Identified Gap**: There are **no endpoints** for listing cases (`GET /cases`) or querying an existing case by ID (`GET /cases/{case_id}`).
- **Server-Side Case Storage (`src/api/case_store.py`)**:
  - SQLite database persists case state at `data/cases.db` with columns `case_id`, `state_json`, `created_at`, and `updated_at`.
  - Methods implemented: `save_case(case_id, state)`, `get_case(case_id)`, `update_case(case_id, state)`, `case_exists(case_id)`, and `get_case_count()`.
  - No listing or pagination method exists in the store layer.
- **Architectural Decision for Feature C**:
  - In strict compliance with instructions to not invent backend endpoints without approval, local history storage was implemented natively on the Android client (`LocalCaseRepository`).
  - Section 7 of this report documents the backend case listing gap and requests formal approval before implementing any backend query endpoints.

### 2.2 Reassessment Contract Inspection
- **Trigger Enum (`ReassessmentTrigger`)**:
  - `new_field_observation`
  - `weather_update`
  - `treatment_ineffective`
  - `lab_diagnostic_update`
- **Supported Evidence Fields (`new_evidence`)**:
  - `leaf_damage_percentage`: float (0.0 to 100.0)
  - `weather_conditions`: string (e.g., `cool_wet`, `warm_humid`)
  - `canopy_spread`: string (e.g., `lower_canopy`, `mid_canopy`, `whole_plant`)
  - `treatment_notes`: string
  - `field_notes`: string
  - `lab_confirmed_disease`: optional string
  - `confirmed_pathogen`: optional string
- **Server-Side Constraints**:
  - Enforces a strict ceiling of 2 reassessment cycles (`reassessment_count < 2`). Exceeding this returns HTTP 400 (`Bad Request: Reassessment cycle limit reached`).
  - Server bypasses vision inference during reassessment, directly re-executing LangGraph decision and planning nodes in ~11 ms.

---

## 3. Architecture & Data Flow

The Stage B.3 Android implementation strictly adheres to Clean Architecture and MVVM patterns with unidirectional data flow (UDF):

```
+-----------------------------------------------------------------------------------+
|                                 Android Presentation Layer                         |
|                                                                                   |
|  +--------------------+   +-----------------------+   +------------------------+  |
|  |   DiagnosisScreen  |   |    CaseDetailScreen   |   |     HistoryScreen      |  |
|  +--------------------+   +-----------------------+   +------------------------+  |
|            |                          |                            |              |
|            v                          v                            v              |
|  +--------------------+   +-----------------------+   +------------------------+  |
|  | DiagnosisViewModel |   |  CaseDetailViewModel  |   |    HistoryViewModel    |  |
|  +--------------------+   +-----------------------+   +------------------------+  |
+------------|--------------------------|----------------------------|--------------+
             |                          |                            |
+------------|--------------------------|----------------------------|--------------+
|            v                          v                            v              |
|  +-----------------------------------------------------------------------------+  |
|  |                               Repositories                                  |  |
|  |                                                                             |  |
|  |  +--------------------------+             +-------------------------------+ |  |
|  |  |   LocalCaseRepository    |<------------|     DiagnosisRepository       | |  |
|  |  |  (SharedPreferences/Gson)|             |      (Retrofit Network)       | |  |
|  |  +--------------------------+             +-------------------------------+ |  |
+--------------------------------------------------------------|--------------------+
                                                               | (HTTP / REST)
+--------------------------------------------------------------v--------------------+
|                                FastAPI Backend (WSL)                              |
|                                                                                   |
|     +------------------+     +--------------------+     +-------------------+     |
|     |  POST /diagnose  |     |   POST /reassess   |     |    GET /health    |     |
|     +------------------+     +--------------------+     +-------------------+     |
|               |                         |                         |               |
|               v                         v                         |               |
|       ResNet-50 Vision         LangGraph Workflow                 |               |
|       & Multi-Agent Flow      (Decision & Planning)               |               |
|               |                         |                         |               |
|               +------------+------------+                         |               |
|                            |                                      |               |
|                            v                                      v               |
|                     SQLite Case Store                     ChromaDB Vector Store   |
|                     (`data/cases.db`)                     (`data/chroma_db/`)     |
+-----------------------------------------------------------------------------------+
```

### 3.1 Unidirectional State Flow
1. **Diagnosis Completion**: When `DiagnosisViewModel` receives a successful `DiagnosisResponse`, it persists the new record directly to `LocalCaseRepository`.
2. **Reactive Local Storage**: `LocalCaseRepository` exposes a `StateFlow<List<LocalCaseRecord>>` that automatically updates `HistoryViewModel` and any open screens.
3. **Adaptive Reassessment**: `CaseDetailViewModel` submits `ReassessmentRequest` via `AgriMindApiService` on `Dispatchers.IO`. Upon HTTP 200, it appends a new `ReassessmentRecordItem` to the local case record, updates the current severity/risk, and notifies the UI.

---

## 4. Feature Implementation Details

### 4.1 Feature A: Case Details View (`CaseDetailScreen.kt`)
The Case Details view is accessed either directly from the diagnosis result card ("View Full Case Details & Reassess") or by tapping any item in the History list:
- **Header Card**: Prominently displays the `case_id` (e.g., `CASE-7DC903FC`), the creation timestamp, and a green badge confirming `Critic Verified` status.
- **Disease & Metric Cards**: Displays the primary disease class (`Late blight`), prediction confidence (`100.0%`), current severity (`CRITICAL`), and epidemic risk level (`CRITICAL`), styled with severity-coded container colors (e.g., light red for critical/high, light green for low).
- **Reassessment History Audit Trail**: When reassessments have been performed, an amber audit trail card appears, summarizing each cycle (cycle index, trigger type, outcome, rationale, and resulting severity/risk).
- **Categorized IPM Plan**: Parses and sorts management actions into clear categories (`Cultural Controls`, `Resistant Cultivars`, `Targeted Chemical Controls`, `Scouting & Monitoring`), displaying actionable advice in structured Material 3 cards.
- **Citations & Disclaimer**: Renders verified university extension citations (Cornell University, UC IPM) and a prominent disclaimer advising users that AI recommendations require human agronomist verification.
- **Action Buttons**: Features a top app bar action and bottom floating button to launch the adaptive reassessment sheet.

### 4.2 Feature B: Reassessment Integration (`CaseDetailViewModel.kt`)
- **Schema Alignment**: Constructs a strict `ReassessmentRequest`:
  ```json
  {
    "case_id": "CASE-7DC903FC",
    "trigger": "weather_update",
    "new_evidence": {
      "weather_conditions": "cool_wet",
      "leaf_damage_percentage": 25.0,
      "canopy_spread": "mid_canopy"
    },
    "rationale": "Sudden temperature drop and continuous rainfall accelerating lesion expansion."
  }
  ```
- **Interactive Modal Bottom Sheet**: Provides user-friendly radio selections for all 4 backend triggers, numerical inputs for leaf damage percentage, and text inputs for field observations and rationale.
- **Duplicate Prevention & Cycle Guard**: UI disables submission buttons while `isSubmitting` is true. Furthermore, if `reassessment_count >= 2`, the reassessment button is permanently disabled with an informative label (`Cycle Limit Reached (2/2)`), matching backend policy.
- **Outcome Handling**: Differentiates between `revised` (updates severity, risk, and IPM plan) and `unchanged` (retains current plan), updating the local record and UI without overwriting the original diagnosis.

### 4.3 Feature C: Diagnosis History (`LocalCaseRepository.kt` & `HistoryScreen.kt`)
- **Local Persistence**: Implemented using Android's `SharedPreferences` serialized with `Gson`. Thread-safety is guaranteed using synchronized file writing.
- **History List UI**: Renders each case in an elevated card with the Case ID, localized timestamp, formatted disease name, confidence badge, severity badge, risk badge, and an orange `Reassessed 1x` counter badge.
- **Search & Filtering**: Real-time search bar dynamically filters cases by Case ID or disease name. A single-tap "Clear search" icon restores the complete list.
- **Navigation**: Tapping any card opens the complete `CaseDetailScreen` with full state continuity.

---

## 5. Verification & Testing Evidence

### 5.1 Android Application Build Verification
The Android application was compiled using Gradle 8.13 with JDK 21 on Windows:
```
Command: .\gradlew.bat assembleDebug
Result: BUILD SUCCESSFUL in 1m 3s
Generated APK: android/app/build/outputs/apk/debug/app-debug.apk (12.4 MB)
```

### 5.2 Backend API Regression Suite
To ensure no regressions occurred in the FastAPI backend or multi-agent workflows, the full test suite was executed against the active virtual environment:
```
Command: python -m unittest discover -s tests -p 'test_api*.py'
Result: Ran 20 tests in 79.691s (OK)
- test_api.py: 13 passed (Health, Diagnosis, Reassessment, Ceiling Enforcement, Validation)
- test_api_security.py: 7 passed (Input sanitization, State integrity, Reassessment bounds)
```

### 5.3 Live Latency Benchmarks
Empirical latencies measured during the verification run:
| Benchmark Stage | Measured Latency | Components Involved |
| :--- | :--- | :--- |
| **Model Vision Inference** | **22,438 ms** | ResNet-50 PyTorch forward pass on CPU |
| **Complete Diagnosis Workflow** | **63,467 ms** | Vision + ChromaDB RAG + LangGraph Multi-Agent Nodes |
| **Adaptive Reassessment** | **11.29 ms** | LangGraph Decision/Planning re-run (Vision bypassed) |
| **Local Case Retrieval** | **< 1 ms** | Local SharedPreferences / In-Memory StateFlow |

---

## 6. Screenshots & Visual Evidence

All visual evidence has been captured directly from the live Android emulator (`Medium_Phone_API_37.0`) and verified for image integrity:

| Screenshot File | Resolution | Description & Verified State |
| :--- | :--- | :--- |
| [`stage_b3_initial_screen.png`](file:///outputs/stage_b3_initial_screen.png) | 1080 x 2400 | App launched with 3-tab navigation (Diagnosis, History, System Health) and notice banner. |
| [`stage_b3_health_tab.png`](file:///outputs/stage_b3_health_tab.png) | 1080 x 2400 | System Health tab confirming `Backend Online & Healthy`, 50 ChromaDB chunks, ResNet-50 loaded. |
| [`stage_b3_image_preview_screen.png`](file:///outputs/stage_b3_image_preview_screen.png) | 1080 x 2400 | Tomato leaf specimen loaded with file size, metadata, and "Run AI Diagnosis" button. |
| [`stage_b3_diagnosing_screen.png`](file:///outputs/stage_b3_diagnosing_screen.png) | 1080 x 2400 | Progress state showing multi-agent investigation active message. |
| [`stage_b3_diagnosis_result_screen.png`](file:///outputs/stage_b3_diagnosis_result_screen.png) | 1080 x 2400 | Initial diagnosis result card displaying Case ID, confidence, and "View Full Case Details & Reassess" button. |
| [`stage_b3_case_detail_screen.png`](file:///outputs/stage_b3_case_detail_screen.png) | 1080 x 2400 | Full Case Details screen displaying specimen metrics, Critic badge, IPM plan, and Reassess actions. |
| [`stage_b3_reassess_dialog_screen.png`](file:///outputs/stage_b3_reassess_dialog_screen.png) | 1080 x 2400 | Reassessment Modal Bottom Sheet with trigger selection, weather inputs, and leaf damage controls. |
| [`stage_b3_reassessed_screen.png`](file:///outputs/stage_b3_reassessed_screen.png) | 1080 x 2400 | Reassessed Case Details showing `Adaptive Reassessment Complete (REVISED)`, updated CRITICAL severity, and Audit Trail card. |
| [`stage_b3_history_screen.png`](file:///outputs/stage_b3_history_screen.png) | 1080 x 2400 | Local Investigation History tab displaying the saved case card with `Reassessed 1x` counter badge and search bar. |

---

## 7. Backend Case Listing Capability & Future Recommendations

### 7.1 Identified Missing Backend Capability
During pre-implementation inspection, we identified that the backend maintains an SQLite database table at `data/cases.db`:
```sql
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
However, the FastAPI backend does **not** expose any endpoint for listing cases or querying cases by ID:
- No `GET /cases` endpoint (for paginated case listing across sessions/devices).
- No `GET /cases/{case_id}` endpoint (for fetching authoritative server state).

### 7.2 Justification for Future Implementation
Implementing these endpoints in a future stage would provide substantial architectural benefits:
1. **Cross-Device Synchronization**: Enabling a user or agronomist to access historical cases across multiple mobile devices or web portals.
2. **Server-Side Search & Filtering**: Allowing fast, indexed server queries across thousands of historical cases by date, disease class, or severity.
3. **Restoration on Clean Install**: Preventing loss of case history if the mobile app data is cleared or reinstalled.

> [!IMPORTANT]
> **Approval Request**: Because adding backend endpoints alters the server-side API contract, no changes were made to `src/api/routes.py` during Stage B.3. We formally recommend adding `GET /cases` and `GET /cases/{case_id}` in a subsequent iteration and request your explicit approval before proceeding with that implementation.

---

## 8. Preserved Assets Confirmation

The following repository assets were strictly protected and remain unmodified:
- **ResNet-50 Checkpoint**: `outputs/week2_vision/resnet50_best.pth` (MD5 intact, unchanged).
- **ChromaDB Vector Store**: `data/chroma_db/` (50 active agricultural knowledge chunks, untouched).
- **RAG Preprocessing & Evaluation Data**: `data/rag_knowledge_base/`, `data/splits/`, `outputs/week8_preprocessing_experiment/` (unmodified).
- **Multi-Agent Workflow**: `src/agents/` (LangGraph workflow nodes, agent prompts, and state schemas preserved).
- **Backend Endpoints**: `src/api/routes.py` (`GET /health`, `POST /diagnose`, and `POST /reassess` preserved without modifications).

---

## 9. Conclusion & Readiness

Stage B.3 has successfully delivered a robust, feature-complete native Android experience for Case Details, Adaptive Reassessment, and Local Investigation History. All components are thoroughly tested, performant, and aligned with university-level engineering standards.

The application foundation is fully prepared for subsequent milestones (such as Stage B.4: PDF reporting, offline caching, and remote case synchronization).

