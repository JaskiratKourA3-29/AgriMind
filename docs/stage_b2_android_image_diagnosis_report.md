# AgriMind — Stage B.2 Implementation Report: Image Capture & Disease Diagnosis UI

**Project:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Stage:** Stage B.2: Image Capture & Disease Diagnosis UI  
**Platform:** Native Android (Kotlin, Jetpack Compose Material 3, Retrofit, OkHttp, Coroutines, StateFlow, MVVM)  
**Backend:** FastAPI Application (`http://10.0.2.2:8000/`)  
**Date:** November 1, 2026  
**Status:** Completed & Empirically Verified  

---

## 1. Executive Summary & Completion Status

Stage B.2 expands the native Android foundation established in Stage B.1 into a functional AI-powered diagnostic interface. The application now enables an operator to select tomato leaf photographs from the Android device photo gallery, review a downsampled local preview, remove or replace the selection, submit the image via multipart HTTP upload to the FastAPI `/diagnose` backend, and observe complete multi-agent diagnostic findings rendered cleanly in Material 3.

All requirements for Stage B.2 have been fulfilled:
- **Zero-permission photo selection:** Integrated `ActivityResultContracts.PickVisualMedia` using Android's system photo picker.
- **Image preview & management:** In-memory decoded bitmap preview with file metadata, "Change", and "Remove" actions.
- **Backend diagnosis integration:** Multipart upload directly to `POST /diagnose` over Retrofit/OkHttp with a 120-second read timeout accommodating multi-agent CPU inference.
- **Rich diagnostic display:** Primary disease classification, model confidence, assigned disease severity, epidemic risk rating, critic agent verification, categorized IPM management actions (Cultural, Chemical, Resistant Variety), literature citations, and mandatory pesticide legal disclaimer.
- **Preserved health check:** Maintained the Stage B.1 backend telemetry and health check screen accessible via a unified Material 3 `NavigationBar`.
- **Resilient error handling & state recovery:** Validated both client-side magic-byte checking and non-fatal error recovery allowing retries without restarting the app.

---

## 2. Architecture & Code Changes

The Android codebase was extended following strict MVVM and Clean Architecture patterns under `android/app/src/main/java/com/agrimind/app/`:

```
android/app/src/main/java/com/agrimind/app/
├── MainActivity.kt                            [MODIFIED] Added Material 3 NavigationBar (Diagnosis + Health tabs)
├── data/
│   ├── api/
│   │   ├── AgriMindApiService.kt             [MODIFIED] Added @Multipart @POST("diagnose") interface
│   │   └── RetrofitClient.kt                 [MODIFIED] Configured 120s timeout and HttpLoggingInterceptor.Level.HEADERS
│   └── model/
│       ├── HealthResponse.kt                  [PRESERVED] Stage B.1 health telemetry schema
│       └── DiagnosisResponse.kt              [CREATED] Full Pydantic-equivalent Gson models for /diagnose
└── ui/
    ├── screens/
    │   ├── HealthScreen.kt                   [PRESERVED] Stage B.1 health check screen
    │   └── DiagnosisScreen.kt                [CREATED] Material 3 image picker, preview, loading & result cards
    ├── theme/
    │   ├── Color.kt                          [PRESERVED] Material 3 agricultural color palette
    │   ├── Theme.kt                          [PRESERVED] Dynamic and dark/light color themes
    │   └── Type.kt                           [PRESERVED] Typography definition
    └── viewmodel/
        ├── HealthUiState.kt                  [PRESERVED] Health check state machine
        ├── HealthViewModel.kt                [PRESERVED] Health check ViewModel
        ├── DiagnosisUiState.kt               [CREATED] Diagnosis UI sealed interface (Idle, ImageSelected, Diagnosing, Success, Error)
        └── DiagnosisViewModel.kt             [CREATED] StateFlow ViewModel with client validation, downsampling & multipart dispatch
```

### 2.1 File Responsibilities & Implementation Details

1. **[`android/app/src/main/java/com/agrimind/app/data/model/DiagnosisResponse.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/model/DiagnosisResponse.kt):**
   - Matches the FastAPI Pydantic schema for `POST /diagnose` and `POST /reassess`.
   - Maps fields: `case_id`, `crop`, `disease_prediction`, `confidence`, `severity`, `epidemic_risk`, `recommended_actions`, `critic_verdict`, `reassessment_count`, `management_plan` (summary, immediate_actions, chemical_control, biological_control, cultural_practices, resistant_varieties, monitoring_advice, regulatory_notes, citations, disclaimer), and `latency` breakdown (`model_inference_ms`, `total_workflow_ms`).

2. **[`android/app/src/main/java/com/agrimind/app/data/api/AgriMindApiService.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/api/AgriMindApiService.kt):**
   - Added `@Multipart @POST("diagnose") suspend fun diagnose(@Part file: MultipartBody.Part): Response<DiagnosisResponse>`.

3. **[`android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt):**
   - Extended OkHttp `connectTimeout`, `readTimeout`, and `writeTimeout` to `120.seconds`. This prevents socket read timeouts during CPU-bound ResNet-50 vision inference and LangGraph multi-agent RAG synthesis (~40–55s on host).
   - Set `HttpLoggingInterceptor.Level.HEADERS` to prevent logging entire binary image payloads in Android Logcat.

4. **[`android/app/src/main/java/com/agrimind/app/ui/viewmodel/DiagnosisUiState.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/viewmodel/DiagnosisUiState.kt):**
   - Implemented sealed interface:
     - `Idle`: No photo selected.
     - `ImageSelected(uri, filename, fileSizeBytes, previewBitmap)`: Photo selected and validated; preview available.
     - `Diagnosing(previewBitmap)`: Request in flight; shows progress indicator.
     - `Success(previewBitmap, result)`: 200 OK returned; displays comprehensive diagnostic report.
     - `Error(message, canRetry, previewBitmap)`: Non-fatal failure; provides retry or re-selection options.

5. **[`android/app/src/main/java/com/agrimind/app/ui/viewmodel/DiagnosisViewModel.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/viewmodel/DiagnosisViewModel.kt):**
   - Exposes `uiState: StateFlow<DiagnosisUiState>`.
   - Validates file constraints before transmission:
     - Enforces maximum file size of 15 MB.
     - Checks magic bytes (JPEG: `FF D8 FF`, PNG: `89 50 4E 47`, GIF: `47 49 46 38`, BMP: `42 4D`).
   - Safely creates downsampled preview bitmaps (`inSampleSize` power of 2) to protect Android heap memory.
   - Executes multipart payload upload on `Dispatchers.IO`.
   - Maps HTTP errors (400 Bad Request, 500 Internal Error, `SocketTimeoutException`, `ConnectException`) into readable user messages.

6. **[`android/app/src/main/java/com/agrimind/app/ui/screens/DiagnosisScreen.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/ui/screens/DiagnosisScreen.kt):**
   - Employs Material 3 components: `Card`, `ElevatedCard`, `OutlinedCard`, `FilterChip`, `LinearProgressIndicator`, `CircularProgressIndicator`, `HorizontalDivider`.
   - Implements `rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia())`.
   - Displays dynamic UI depending on `uiState`.

7. **[`android/app/src/main/java/com/agrimind/app/MainActivity.kt`](file:///c:/Users/asus/Downloads/Agri_Mind_Minor_Project/android/app/src/main/java/com/agrimind/app/MainActivity.kt):**
   - Replaced single-screen container with a 2-tab Material 3 `NavigationBar`:
     - **Tab 0 ("Diagnosis"):** Hosted `DiagnosisScreen`.
     - **Tab 1 ("System Health"):** Hosted `HealthScreen`.

---

## 3. API Integration Details

| Metric / Attribute | Specification |
| :--- | :--- |
| **API Endpoint** | `POST http://10.0.2.2:8000/diagnose` |
| **Transport** | HTTP/1.1 via Retrofit 2.11.0 + OkHttp 4.12.0 |
| **Content-Type** | `multipart/form-data; boundary=...` |
| **Form Field** | `file` (binary payload, `image/jpeg` or `image/png`) |
| **Timeout Configuration** | 120s Connect, 120s Read, 120s Write |
| **Observed Latency** | Model Inference: 20,100 ms (20.1s); Total Workflow: 44,300 ms (44.3s) |
| **Response Format** | JSON (Pydantic `DiagnosisResponse`) |
| **Status Code** | `200 OK` |

---

## 4. UI/UX Design & State Machine

```
              ┌─────────────────────────┐
              │          IDLE           │
              │  - Notice Disclaimer    │
              │  - "Choose from Gallery"│
              │  - Button Disabled      │
              └────────────┬────────────┘
                           │ User selects photo (PickVisualMedia)
                           ▼
              ┌─────────────────────────┐
              │     IMAGE SELECTED      │
              │  - Specimen Thumbnail   │
              │  - Name & File Size     │
              │  - "Change" / "Remove"  │
              │  - "Run AI Diagnosis"   │
              └────────────┬────────────┘
                           │ User taps "Run AI Diagnosis"
                           ▼
              ┌─────────────────────────┐
              │       DIAGNOSING        │
              │  - Circular Progress    │
              │  - Progress Text        │
              │  - Multi-agent Status   │
              └────────────┬────────────┘
            Success        │        Network / Validation Failure
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│          SUCCESS          │   │           ERROR           │
│  - Specimen Thumbnail     │   │  - Error Banner & Details │
│  - Case ID & Critic Badge │   │  - Non-fatal Error Card   │
│  - Primary Disease Title  │   │  - "Choose Another"       │
│  - Confidence / Severity  │   │  - App Remains Alive      │
│  - Epidemic Risk Rating   │   └─────────────┬─────────────┘
│  - Categorized IPM Cards  │                 │
│  - Literature Citations   │                 │ User taps "Choose Another"
│  - Latency Breakdown      │                 ▼
│  - "Diagnose Another Leaf"│        (Returns to IDLE State)
└──────────────┬────────────┘
               │ User taps "Diagnose Another Leaf"
               ▼
      (Returns to IDLE State)
```

---

## 5. Live Verification Evidence

### 5.1 Real Image Diagnostic Execution

A genuine tomato late blight specimen from the PlantVillage dataset was pushed to `/sdcard/Pictures/tomato_late_blight.jpg` on the emulator and selected via the photo picker:

1. **Android Photo Selection:**
   - File: `45.jpg` (`tomato_late_blight.jpg`, 11.7 KB)
   - Status: Accepted by magic-byte validator; downsampled preview displayed.

2. **In-Flight Uvicorn Execution Log (`task-5448`):**
   ```
   INFO:     127.0.0.1:39640 - "POST /diagnose HTTP/1.1" 200 OK
   ```

3. **Backend Response Data Captured on Device:**
   - **Case ID:** `CASE-9A225844`
   - **Crop:** `Tomato`
   - **Disease Prediction:** `Late blight` (`Tomato___Late_blight`)
   - **Model Confidence:** `100.0%`
   - **Assigned Severity:** `INDETERMINATE`
   - **Epidemic Risk:** `HIGH`
   - **Critic Verdict:** `Verified` ("Analysis verified by AgriMind Critic Agent")
   - **Recommended Actions:**
     - `[Cultural] Immediate rogueing of initial hot-spot plants (Cornell Extension)`: Bag plants in plastic during dry midday, cut at soil line, seal, destroy to eliminate airborne sporangia.
     - `[Cultural] Eliminate volunteer solanaceous hosts and avoid overhead irrigation (UC IPM)`: Destroy volunteer potato/tomato plants within 1 mile. Irrigate via drip lines beneath plastic mulch.
     - `[Resistant Variety] Deploy dual-gene resistant cultivars (Ph-2 + Ph-3) (Cornell Extension)`: Iron Lady, Mountain Magic, Defiant PHR, Plum Regal.
     - `[Chemical Control] Targeted systemic oomycides with verified modes of action (Cornell Extension)`: Cymoxanil (Curzate) for kickback; Mandipropamid (Revus) for preventative anti-sporulant.
   - **Citations Displayed:**
     - `[1] Late Blight Management in Tomato` (Cornell University Cooperative Extension & USABlight)
     - `[2] Late Blight Management in Tomato` (Cornell University Cooperative Extension & USABlight)
     - `[3] Tomato: Late Blight (Phytophthora infestans)` (University of California Statewide IPM Program)
   - **Pesticide Notice:** Displayed in full EPA warning box.
   - **Latency Telemetry:** Inference: 20.1s | Total Workflow: 44.3s.

### 5.2 Screenshots Captured

All verification screenshots were extracted directly from the running emulator:

| Screenshot Artifact | Description |
| :--- | :--- |
| `outputs/stage_b2_initial_screen.png` | Initial empty state with disclaimer, picker button, and disabled diagnose CTA. |
| `outputs/stage_b2_image_preview_screen.png` | Preview card displaying specimen thumbnail, file size (11 KB), change/remove actions, and active diagnose button. |
| `outputs/stage_b2_diagnosing_screen.png` | Progress spinner and status text during multi-agent inference. |
| `outputs/stage_b2_diagnosis_result_screen.png` | Top half of diagnosis results: thumbnail, Case ID `CASE-9A225844`, disease name, confidence, severity, risk, and IPM actions. |
| `outputs/stage_b2_diagnosis_result_bottom.png` | Bottom half of diagnosis results: chemical control, university citations, pesticide disclaimer, latency, and "Diagnose Another Leaf" button. |
| `outputs/stage_b2_health_tab.png` | System Health tab showing active backend connection, 50 ChromaDB chunks, ResNet-50 status, and CPU inference device. |
| `outputs/stage_b2_error_screen.png` | Error state after attempting to select an invalid text file disguised as a JPEG. |

---

## 6. Error Handling & Edge Case Verification

The error recovery mechanisms were tested systematically:

1. **Client-Side Magic-Byte Validation (Invalid File Type):**
   - **Test File:** `outputs/fake_image.jpg` containing ASCII text `This is a fake text file pretending to be a JPG`.
   - **Behavior:** Selected through the picker. The `DiagnosisViewModel` inspected the header bytes, detected non-matching magic bytes, and immediately transitioned to `DiagnosisUiState.Error("Unsupported file format. The AgriMind backend only accepts JPEG, PNG, GIF, or BMP images.")`.
   - **Result:** No invalid network request was dispatched. The error card was presented on screen alongside a "Choose Another" button.
   - **Recovery:** Clicking "Choose Another" cleared the error and reset the UI to `DiagnosisUiState.Idle` without restarting the activity.

2. **Image Replacement & Removal:**
   - Clicking "Remove" on an active preview returned the application to the empty state without restarting.
   - Clicking "Change" reopened the photo picker directly.

3. **Backend Network Timeout Resiliency:**
   - Verified that OkHttp's 120-second timeout successfully accommodates long LangGraph execution windows (~44s) without triggering client-side socket cancellation.

---

## 7. Health Check Preservation

The Stage B.1 health check functionality was verified to be fully operational:
- Switching between the "Diagnosis" tab and "System Health" tab via the bottom navigation bar is immediate and preserves background state.
- The `HealthViewModel` polling and manual "Refresh Connection Status" continue to query `GET /health` on `http://10.0.2.2:8000/`.
- Verified live telemetry output:
  - Backend Status: `HEALTHY | v1.0.0`
  - ResNet-50 Vision Checkpoint: `LOADED (Online)`
  - ChromaDB RAG Chunks: `50 chunks indexed`
  - Inference Device: `CPU`
  - Active Classes: `3 tomato classes`

---

## 8. Backend Regression & Unit Test Verification

To ensure zero regression of existing backend models, RAG vector store, and LangGraph workflow, the complete test suite was run inside the WSL virtual environment:

```bash
source /home/jaskirat/agrimind-rag-env/bin/activate
python -m unittest discover -s tests -p 'test_api*.py'
```

**Results:**
```
Ran 20 tests in 55.446s

OK

[Real Diagnostic Latency Benchmark]
  - Model Inference Latency: 18282.76 ms
  - Total Workflow Latency:  40054.83 ms
  - Primary Diagnosis:       Tomato___Bacterial_spot (100.0%)
  - Assigned Severity:       moderate

[Real Reassessment Latency Benchmark]
  - Total Reassessment Latency: 9.23 ms
  - Reassessment Outcome:       revised
  - Reassessment Count:         1
  - Preserved History Snapshots:1
```

All 20 test cases in `tests/test_api.py` and `tests/test_api_security.py` passed with 100% success.

---

## 9. Constraints Compliance Audit

| Constraint | Status | Notes |
| :--- | :--- | :--- |
| **No Camera Capture** | Compliant | No CameraX, camera intents, or runtime camera permissions were added. |
| **No `/reassess` UI** | Compliant | Reassessment flow remains backend-only, reserved for Stage B.3. |
| **No Case History UI** | Compliant | Local database and case listing deferred to Stage B.3. |
| **No User Auth / Login** | Compliant | API security limitations documented; no client auth added. |
| **No Backend AI/RAG Changes** | Compliant | ResNet-50, ChromaDB, vectorstore, agents, and LangGraph remain untouched. |
| **Native Android Only** | Compliant | Built strictly in Kotlin and Jetpack Compose; no WebViews or wrappers. |

---

## 10. Known Limitations

1. **Development Host CPU Latency:** On the local CPU environment, inference latency ranges from 40 to 55 seconds (ResNet-50: ~18–20s; LangGraph RAG synthesis: ~22–25s). A 120s timeout is required.
2. **Single Image Analysis:** Only one leaf photograph can be submitted per diagnostic run.
3. **Session-Ephemeral Case ID:** The returned `case_id` (e.g. `CASE-9A225844`) is stored in server-side SQLite (`data/cases.db`), but the Android frontend does not yet persist historical cases locally across app launches.
4. **No Reassessment Submission from UI:** Reassessment inputs (e.g. spray date, observed spread, user symptom notes) are not yet exposed on this screen.

---

## 11. Recommendations for Stage B.3 (Pending Approval)

Once approved, **Stage B.3** should implement:
1. **Case Details & Reassessment UI:**
   - Dedicated Case Detail screen taking an active `case_id`.
   - Input controls for reassessment data: treatment applied, timeline, symptom evolution notes.
   - Dispatch to `POST /reassess` and presentation of revised risk and management adjustments.
2. **Local History (Room Database or Local Cache):**
   - Save completed diagnoses locally so the operator can review past investigations offline.
3. **Report Generation / Export Integration:**
   - Preparing data models for PDF export (Stage C).

*End of Report.*

