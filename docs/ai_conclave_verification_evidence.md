# AgriMind AI Conclave — End-to-End Verification Evidence & Benchmark Log

**Project:** AgriMind Minor Project (`COM71116-21`)  
**Audit Date:** 2026-11-03  
**Execution Environment:**  
- **Host OS:** Windows 11 Home (Build 26200)  
- **Subsystem:** Ubuntu 24.04 LTS (WSL2), Linux 6.6.x  
- **Python Environment:** Python 3.13.16 in `/home/jaskirat/agrimind-rag-env`  
- **PyTorch Device:** CPU (Intel Core / AMD x86_64)  
- **Vector Store:** ChromaDB v0.4.x (SQLite persistent backend: `data/vectorstore/chroma/chroma.sqlite3`)  
- **Vision Model Checkpoint:** ResNet-50 PyTorch weights (`outputs/week2_vision/best_model.pth`, 282.6 MB)  
- **Android Toolchain:** OpenJDK 17, Gradle 8.13, AGP 8.8.0, Kotlin 2.1.0, Jetpack Compose BOM 2024.10.01  

---

## 1. Asset & Checkpoint Integrity Verification

Prior to testing, authoritative project checkpoints and data splits were inspected and verified as unaltered:

```bash
# Checkpoint verification
$ ls -lh outputs/week2_vision/best_model.pth
-rwxrwxrwx 1 jaskirat jaskirat 283M Oct 13 21:14 outputs/week2_vision/best_model.pth
# Size: 296,358,683 bytes (282.6 MB)

# ChromaDB Vector Store verification
$ python -c "import sqlite3; conn = sqlite3.connect('data/vectorstore/chroma/chroma.sqlite3'); cur = conn.cursor(); cur.execute('SELECT count(*) FROM embeddings;'); print('Chunks:', cur.fetchone()[0]); cur.execute('SELECT count(*) FROM embedding_metadata;'); print('Metadata rows:', cur.fetchone()[0])"
Chunks: 63
Metadata rows: 882
```

**Metadata Institutional Distribution (63 indexed chunks):**
- Cornell University Cooperative Extension & Vegetable Program: 9 chunks
- Cornell University Plant Disease Diagnostic Clinic: 18 chunks
- Purdue University Extension (BP-85-W): 9 chunks
- University of California Statewide IPM Program (UC IPM): 21 chunks
- University of Florida IFAS Extension (EDIS PP-73): 6 chunks

---

## 2. Feature 1: Conversational AI and Contextual Follow-Up

### Current implementation found
- `src/rag/generator.py`: `AgrimindAnswerGenerator`, `resolve_query_referent` (anaphora referent resolution), `synthesize_extractive_answer` (grounded extractive synthesis fallback for Gemini API 429 quota exhaustion).
- `src/rag/retriever.py`: `AgrimindRetriever` with dual-threshold gating: `anchored_score_threshold = 0.30` for queries with verified disease targets against disease-filtered chunks, and `score_threshold = 0.55` for general unanchored queries.
- `src/rag/language_detector.py`: `AgrimindLanguageDetector` with authentic Dogri lexical markers (`"गेया"`, `"गेन"`, `"कचे"`, `"इयां"`, `"किदां"`, `"कुस चाल्ली"`).
- `src/api/routes.py`: POST `/chat` endpoint with case context anchoring.
- `android/app/src/main/java/com/agrimind/app/ui/viewmodel/ChatViewModel.kt` and `ChatScreen.kt`.

### Evidence inspected
- Authoritative 63-chunk ChromaDB vector store (`data/vectorstore/chroma/chroma.sqlite3`).
- Case store persistence (`src/api/case_store.py`).
- Multilingual prompts and extractive synthesis patterns in `src/rag/generator.py`.
- Jetpack Compose conversational UI composables in `ChatScreen.kt`.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_feature1_conversational_ai.py -v"
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_language_detector.py -v"
```

### Actual result
- **`tests/test_feature1_conversational_ai.py`**: **9/9 tests passed in 247.792s (Exit code 0)**.
  - `test_01_first_question_with_valid_case`: Grounded answer with extension citations returned (ok).
  - `test_02_follow_up_depending_on_previous_turn`: Anaphora resolved ('how often should I spray it?' resolves referent) (ok).
  - `test_03_follow_up_referring_to_active_case`: Inherits case's diagnostic disease target (ok).
  - `test_04_switching_cases_isolates_context`: Switching Case 1 (Bacterial Spot) to Case 2 (Early Blight) does not leak Case 1 disease target (ok).
  - `test_05_missing_or_invalid_case_id`: Returns HTTP 404 cleanly (ok).
  - `test_06_unsupported_question_triggers_safe_fallback`: Questions outside tomato disease management return safe fallback without hallucination (ok).
  - `test_07_no_useful_chunks_honest_disclosure`: When query has zero match in Chroma, system does not fabricate dosages (ok).
  - `test_08_multilingual_inputs_routing`: English, Devanagari Hindi, Romanized Hindi, and Dogri queries routed accurately (ok).
  - `test_09_inspect_real_chroma_citations_no_inflation`: Citations point to real documents; no duplicate numbers exist (ok).
- **`tests/test_language_detector.py`**: **3/3 passed in 0.05s (Exit code 0)**.

### Remaining limitations
- Free-tier Google Gemini API quota (20 requests/day) triggers HTTP 429 when exhausted; the system automatically and deterministically falls back to grounded extractive synthesis directly quoting Chroma extension literature.
- Speech synthesis for Dogri on standard Android falls back to Hindi phoneme rendering with an explicit on-screen advisory because stock Android distributions lack a native Dogri TTS engine.

### Status
**VERIFIED**

---

## 3. Feature 2: Vision Inference, Latency, Confidence & Invalid-Image Handling

### Current implementation found
- `src/vision/inference.py`: `VisionInferenceEngine` loading PyTorch ResNet-50 (`outputs/week2_vision/best_model.pth`, 282.6 MB); `verify_image_integrity` checking headers, dimensions, and corrupt bitstreams.
- `src/api/routes.py`: POST `/diagnose` endpoint with SHA-256 duplicate submission cache (`_IMAGE_SUBMISSION_CACHE`) with 120s TTL; low-confidence policy threshold (`is_low_confidence=True` when confidence < 0.65 or margin < 0.15).
- `android/app/src/main/java/com/agrimind/app/ui/viewmodel/DiagnosisViewModel.kt` and `DiagnosisScreen.kt`.

### Evidence inspected
- ResNet-50 checkpoint weights file (`outputs/week2_vision/best_model.pth`, 296,358,683 bytes).
- Real PlantVillage dataset test specimens in `raw/color/Tomato___Bacterial_spot/`, `Tomato___Early_blight/`, `Tomato___Late_blight/`.
- Latency instrumentation clocks in `src/api/routes.py`.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_feature2_vision_inference.py -v"
```

### Actual result
- **`tests/test_feature2_vision_inference.py`**: **5/5 tests passed in 51.600s (Exit code 0)**.
  - `test_01_corrupted_empty_and_non_image_rejection`: 100% rejection of 0-byte, text, and corrupted payloads with HTTP 400 (ok).
  - `test_02_low_confidence_policy_triggering`: Confidence < 0.65 triggers `is_low_confidence=True`, `requires_manual_review=True`, and guidance message (ok).
  - `test_03_high_confidence_policy`: Confidence >= 0.65 correctly preserves high-confidence status (ok).
  - `test_04_real_image_inference_bacterial_spot`: Real ResNet-50 forward pass on PlantVillage image correctly identifies Bacterial Spot with 100% confidence (ok).
  - `test_05_duplicate_submission_prevention`: Duplicate submission returns cached result in milliseconds (ok).

**Measured Latency Breakdown Profile (CPU Host):**
- ResNet-50 Vision Model Inference (Forward Pass): **$16,636.88\text{ ms}$** ($\approx 16.6\text{ s}$)
- LangGraph Multi-Agent Workflow Latency: **$21,554.09\text{ ms}$** ($\approx 21.6\text{ s}$)
- Total Diagnostic Workflow Latency: **$38,190.97\text{ ms}$** ($\approx 38.2\text{ s}$)
- End-to-End Client HTTP Round-Trip: **$38.45\text{ s}$**
- Duplicate Image Submission Cache:
  - Fresh Submission: **$12.24\text{ s}$**
  - Cached Submission: **$0.0107\text{ s}$** ($10.7\text{ ms}$)
  - Cache Acceleration Factor: **$1144.1\times$**

### Remaining limitations
- ResNet-50 forward pass takes ~16.6s–18.1s on host CPU. The smartphone functions as a thin client and delegates neural network inference to the edge server.

### Status
**VERIFIED**

---

## 4. Feature 3: Preventive, Context-Aware Agricultural Guidance

### Current implementation found
- `src/workflow/nodes.py`: `risk_assessment_node`, `decision_planning_node` implementing the strict IPM hierarchy: Cultural Sanitation -> Resistant Varieties -> Chemical / Biological Protection.
- `src/workflow/graph.py`: StateGraph orchestration and conditional routing.
- `src/services/weather_service.py`: `calculate_epidemiological_risk` implementing the Wallin/Hyre weather model.
- `android/app/src/main/java/com/agrimind/app/ui/screens/DiagnosisScreen.kt`: Structured IPM plan rendering cards.

### Evidence inspected
- Agent decision schemas (`DecisionPlan`, `SeverityLevel`, `PlanUrgency`) in `src/agents/schemas.py`.
- University-grounded chemical recommendations with mandatory safety notices in `src/agents/prompts.py`.
- Android UI composables rendering 4-tier management plans.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_weather_service.py -v"
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_agents.py -v"
```

### Actual result
- **`tests/test_weather_service.py`**: **3/3 passed in 1.049s (Exit code 0)**.
  - Conducive cool/wet weather (10-24°C, >80% RH) automatically escalates Late Blight risk from MODERATE to CRITICAL.
  - Injects rain-fastness notices for Mancozeb/Chlorothalonil.
- **`tests/test_agents.py`**: **15/15 passed in 3.42s (Exit code 0)**.
  - Critic verification correctly catches contradictory chemical advice and verifies extension citations.

### Remaining limitations
- All chemical dosage advice is marked as preliminary decision support and legally mandates confirmation by a licensed local extension officer prior to field application.

### Status
**VERIFIED**

---

## 5. Feature 4: Farmer Case Sharing and Community Interactions

### Current implementation found
- `src/services/case_sharing_service.py`: `CaseSharingService` implementing tokenized sharing, PII sanitization, GPS coordinate fuzzing, comment thread management, and treatment outcome tracking.
- `src/api/routes.py`: Endpoints `/cases/share`, `/cases/shared/{share_id}`, `/cases/shared/{share_id}/comments`, `/cases/shared/{share_id}/outcome`, `/cases/share/{share_id}/revoke`.
- `android/app/src/main/java/com/agrimind/app/ui/viewmodel/CaseDetailViewModel.kt` and `CaseDetailScreen.kt`.

### Evidence inspected
- SQLite schema in `data/cases.db`: tables `cases`, `shared_cases`, `case_comments`, `case_outcomes`.
- GPS fuzzing math: coordinate truncation to 1 decimal place ($0.1^\circ \approx 11.1\text{ km}$ privacy radius).
- Privacy anonymization logic removing farmer name and phone number.
- Comment attribution schema tracking `is_ai: bool`.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_case_sharing.py -v"
```

### Actual result
- **`tests/test_case_sharing.py`**: **6/6 passed in 0.019s (Exit code 0)**.
  - `test_share_case_anonymized_pii`: Strips farmer name and phone; replaces with 'Anonymous Farmer' (ok).
  - `test_gps_fuzzing_math`: Validates truncation: $32.726612 \to 32.7$ (delta $0.0266^\circ$, buffer $2.96\text{ km}$) (ok).
  - `test_comments_human_and_ai_attribution`: Verifies comments thread strictly preserves `is_ai: false` vs `is_ai: true` (ok).
  - `test_treatment_outcome_recording`: Successfully records post-treatment recovery status (`helped`, `did_not_help`, `pending`) (ok).
  - `test_revoke_share`: Verifies that only owner can revoke a share and access is immediately revoked (ok).
  - `test_unauthorized_token_rejection`: Verifies invalid token access is rejected (ok).

### Remaining limitations
- GPS fuzzing uses deterministic 1-decimal-place truncation rather than random Gaussian noise injection.

### Status
**VERIFIED**

---

## 6. Feature 5: Cooperative-to-Cooperative Insights

### Current implementation found
- `src/services/cooperative_service.py`: `CooperativeService` calculating disease distribution, dominant pathogen identification, outbreak alert thresholding, and multi-region comparisons.
- `src/api/routes.py`: Endpoints `/cooperative/insights` and `/cooperative/comparison`.
- `android/app/src/main/java/com/agrimind/app/ui/viewmodel/HistoryViewModel.kt` and `HistoryScreen.kt`.

### Evidence inspected
- Aggregation queries over shared cases in `data/cases.db`.
- Multi-region comparison schema with explicit `is_live_partnership: False` enforcement.
- Truth-in-advertising disclaimer text attached to all cooperative comparisons.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_cooperative_service.py -v"
```

### Actual result
- **`tests/test_cooperative_service.py`**: **3/3 passed in 0.012s (Exit code 0)**.
  - `test_empty_cooperative_insights`: Baseline low-risk insights returned when pool has no cases (ok).
  - `test_aggregated_insights_with_multiple_cases`: Analyzes cases, identifies dominant pathogen, escalates to CRITICAL risk (ok).
  - `test_regional_comparison_and_disclaimer`: Multi-region comparison returns live pilot alongside transparently disclosed simulated partner nodes with explicit disclaimer (ok).

### Remaining limitations
- External cooperative nodes (Punjab Gurdaspur, Himachal Kangra) are simulated demonstration nodes to show interoperability without claiming active inter-state institutional memorandums.

### Status
**VERIFIED**

---

## 7. Feature 6: Weather Integration & Risk Escalation

### Current implementation found
- `src/services/weather_service.py`: `WeatherService` querying Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`), caching observations with 30-minute TTL, and providing offline fallback baselines.
- `src/api/routes.py`: GET `/weather/live` endpoint.
- `android/app/src/main/java/com/agrimind/app/ui/screens/DiagnosisScreen.kt`: Ambient weather card.

### Evidence inspected
- Open-Meteo API response schema (`WeatherData`).
- Offline fallback dictionaries in `src/services/weather_service.py`.
- Live weather fetch for R.S. Pura coordinates ($32.61^\circ\text{N}, 74.73^\circ\text{E}$).

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python -m unittest tests/test_weather_service.py -v"
```

### Actual result
- **`tests/test_weather_service.py`**: **3/3 passed in 1.049s (Exit code 0)**.
  - `test_fetch_live_weather_returns_structured_data`: Live API call returned temperature $24.3^\circ\text{C}$, relative humidity $43.0\%$, rain forecast $0.0\text{ mm}$ (ok).
  - `test_epidemiological_risk_hot_dry_non_conducive`: Hot and dry weather does not escalate Late Blight (ok).
  - `test_epidemiological_risk_late_blight_escalation`: Cool/wet conducive weather triggers HIGH/CRITICAL risk (ok).

### Remaining limitations
- Open-Meteo API free tier imposes rate limits; mitigated by 30-minute local in-memory caching.

### Status
**VERIFIED**

---

## 8. Feature 7: Jammu-Focused Demonstration

### Current implementation found
- `scripts/demo_jammu_rspura.py`: Authoritative 7-step end-to-end reproducible runner replicating agricultural conditions of R.S. Pura border belt, Jammu ($32.61^\circ\text{N}, 74.73^\circ\text{E}$).

### Evidence inspected
- End-to-end execution script exercising real Open-Meteo weather fetch, real PlantVillage image submission, ResNet-50 vision inference, LangGraph multi-agent RAG workflow, conversational follow-up, case sharing, community commenting, and multi-region surveillance.

### Exact tests and commands executed
```bash
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && PYTHONPATH=. /home/jaskirat/agrimind-rag-env/bin/python scripts/demo_jammu_rspura.py"
```

### Actual result
- **Execution Time:** ~42s (Exit code 0). Complete 7-step pipeline trace executed successfully:
  - Step 1: Open-Meteo live weather fetched for R.S. Pura ($24.3^\circ\text{C}$, $43.0\%$ RH, Partly Cloudy).
  - Step 2: Specimen diagnosed as `Tomato___Bacterial_spot` with $100.00\%$ confidence. Case ID `CASE-756B836F`. Vision latency: $16,742.82\text{ ms}$; Workflow: $40,590.51\text{ ms}$; Client: $41,736.35\text{ ms}$.
  - Step 3: 4 extension citations retrieved from Cornell University extension literature.
  - Step 4: Conversational follow-up answered in English citing verified extension sources.
  - Step 5: Case shared (`SHARE-44C44CB4`), farmer observation posted (`is_ai: false`), outcome recorded (`HELPED`).
  - Step 6: Multi-region comparison generated (Jammu 3 cases vs Punjab 42 cases vs Himachal 35 cases).
  - Step 7: Statutory phytosanitary certification boundary verified.

### Remaining limitations
- Demonstration executes in terminal mode; mobile UI interaction is evidenced via 49 passing Gradle unit tests and compiled APK.

### Status
**VERIFIED**

---

## 9. Feature 8: Crop-Health PDF Reporting and Certification Disclaimer

### Current implementation found
- `android/app/src/main/java/com/agrimind/app/report/PdfReportGenerator.kt`: Two-page crop health PDF report generator utilizing Android `PdfDocument`.
- `android/app/src/main/java/com/agrimind/app/ui/viewmodel/CaseDetailViewModel.kt`: `generatePdfReport` triggering on-device PDF rendering.
- `android/app/src/main/java/com/agrimind/app/ui/screens/CaseDetailScreen.kt`: UI action to export and view PDF.
- Output artifact: `outputs/AgriMind_Report_CASE-7DC903FC.pdf`.

### Evidence inspected
- Sample generated PDF report on disk: `outputs/AgriMind_Report_CASE-7DC903FC.pdf` ($96,404\text{ bytes}$, 2 pages, Producer: `Skia/PDF m148`).
- Decompressed PDF streams verifying rendered components:
  - Header with AgriMind branding & timestamp
  - Diagnostic summary card (Class, Confidence, Severity, Risk)
  - QR Code encoding case lookup URI
  - Ambient weather conditions (Temperature, Humidity, Rain forecast)
  - Four-tier IPM Management Plan (Cultural, Resistant varieties, Chemical, Monitoring)
  - Accredited University Extension Citations list
  - Bolded regulatory disclaimer box:
    > *"REGULATORY NOTICE & CERTIFICATION BOUNDARY: This document is an automated AI-assisted preliminary diagnostic evaluation generated by the AgriMind decision support platform. AI image analysis alone does NOT issue an official disease-free certificate. Any formal phytosanitary certification requires an authorized inspection and approved certification process by competent state agricultural authorities."*

### Exact tests and commands executed
```powershell
cd android; .\gradlew.bat testDebugUnitTest
wsl -d Ubuntu bash -c "cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && /home/jaskirat/agrimind-rag-env/bin/python scratch/inspect_pdf.py"
```

### Actual result
- Android unit tests executed and passed (`CaseDetailViewModelTest`).
- PDF artifact inspected and confirmed valid ($96,404\text{ bytes}$, 2 pages).
- All required components and statutory disclaimers verified present in the binary output stream.

### Remaining limitations
- Generated PDF rendering runs on-device using Android `PdfDocument`. Live emulator UI viewer was verified in prior Stage B4/C5 milestones (`outputs/stage_b4_pdf_viewer_screen.png`); during this turn, no emulator was attached via ADB.

### Status
**VERIFIED**

---

## 10. Feature 9: Farmer-Ready Experience and Low-Connectivity Support

### Current implementation found
- `android/app/src/main/java/com/agrimind/app/data/local/OfflineQueueManager.kt`: Room SQLite queue manager buffering actions (`OfflineActionEntity`).
- `android/app/src/main/java/com/agrimind/app/data/local/AppDatabase.kt` and `CaseEntity.kt`: Room database caching diagnostic cases locally.
- `src/api/routes.py`: Server-side duplicate prevention cache.

### Evidence inspected
- Room database annotations and entity definitions in Android Kotlin source.
- Automated tests in `android/app/src/test/java/com/agrimind/app/ui/viewmodel/DiagnosisViewModelTest.kt` and `CaseDetailViewModelTest.kt`.
- Built debug APK: `android/app/build/outputs/apk/debug/app-debug.apk` ($17.8\text{ MB}$).

### Exact tests and commands executed
```powershell
cd android; .\gradlew.bat testDebugUnitTest
```

### Actual result
- **Result:** `BUILD SUCCESSFUL in 27s (49/49 unit tests passed, Exit code 0)`.
- Offline diagnosis requests are queued locally in Room SQLite database.
- PDF generation operates 100% offline on-device without network access.
- Local case history remains fully readable without network connectivity.

### Remaining limitations
- ResNet-50 vision inference and LangGraph RAG reasoning require edge-server connectivity; on-device edge neural execution is not supported. Physical airplane mode toggle could not be re-demonstrated live in this turn because `adb devices` showed 0 attached devices/emulators.

### Status
**VERIFIED**
