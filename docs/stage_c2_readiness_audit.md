# AgriMind Stage C.2 — System Readiness & Unfinished Requirements Audit Report

**Date:** November 2, 2026  
**Auditor Role:** Senior Android, Kotlin, Jetpack Compose, FastAPI, Computer Vision & AI Systems Engineer  
**Audit Scope:** Full-stack operational verification, backend-to-emulator reachability, project configuration audit, database/model/RAG discrepancy investigation, and prioritized requirements roadmap.  
**Repository Root:** `C:\Users\asus\Downloads\Agri_Mind_Minor_Project`  
**Execution Environment:** Windows 11 host with Ubuntu 24.04 (WSL2) and Android Emulator (`emulator-5554`)  
**Status:** **AUDIT COMPLETE — ALL SUBSYSTEMS VERIFIED ONLINE & OPERATIONAL**  

---

## 1. Executive Summary

Following the completion of **AgriMind Stage C.1** (Conversational Workflow and Image Validation), this audit establishes the empirical readiness of the platform before implementing subsequent stages.

All checks were executed without modifying working application code, model weights, or datasets. No postponed features (such as multi-crop expansion or Dogri voice synthesis) were initiated.

### Key Audit Findings:
1. **Backend Reachability & Connectivity:** The FastAPI backend running on Uvicorn inside WSL2 (`0.0.0.0:8000`) is **100% reachable** from the Android emulator (`emulator-5554`) via `http://10.0.2.2:8000/` and via `adb reverse` on `127.0.0.1:8000`. Socket connectivity tests using Android toybox `nc` confirmed immediate HTTP 200 responses.
2. **Android Live Telemetry & API Verification:** The installed debug APK (`com.agrimind.app.debug`) connects directly to `http://10.0.2.2:8000/`. Live end-to-end tests confirmed that `POST /chat`, `POST /diagnose`, and `GET /health` return real, verified API responses on `emulator-5554`.
3. **Database Architecture:** Both server-side SQLite (`data/cases.db`, 59 cases) and client-side SQLite (`agrimind_chat.db`, multi-turn conversations with `ON DELETE CASCADE`) are active, valid, and structurally isolated.
4. **RAG Corpus Discrepancy Investigated:** The persistent ChromaDB vector store contains **63 chunks** in its `embeddings` table, perfectly matching `data/knowledge_base/processed_chunks.json`. However, `GET /health` in `src/api/routes.py` hardcodes `rag_chunks = 50 if has_chroma else 0` from an earlier Stage A baseline. This causes Android's System Health screen to display `50 chunks indexed` instead of the actual `63 chunks`.
5. **Model Checkpoint Integrity:** The protected ResNet-50 checkpoint (`outputs/week2_vision/best_model.pth`, 282,626,785 bytes) remains intact, unmodified since October 13, 2026, and actively powers vision inference.
6. **Prioritized Next Steps:** The platform is stable and ready for **Stage C.2**, focusing on dynamic telemetry synchronization and authoritative case retrieval (`GET /cases/{case_id}`).

---

## 2. Backend & Emulator Reachability Verification (Items 1 & 2)

### 2.1 Process & Host Status
- **Backend Process:** `python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000` running in WSL2 environment (`agrimind-rag-env`).
- **Host Endpoint:** `http://127.0.0.1:8000/health` verified via Windows curl:
  ```json
  {"status":"healthy","timestamp":"2026-11-02T15:15:26.066104+00:00","version":"1.0.0","models_available":{"resnet50":true,"rag_chromadb":true},"rag_chunks":50,"active_classes":["Tomato___Bacterial_spot","Tomato___Early_blight","Tomato___Late_blight"],"device":"cpu"}
  ```

### 2.2 Emulator In-Guest Socket Probe
To verify reachability directly from Android guest user space to the development host gateway, a socket probe was dispatched via ADB shell:
```bash
adb shell "(printf 'GET /health HTTP/1.1\r\nHost: 10.0.2.2:8000\r\nConnection: close\r\n\r\n'; sleep 1) | nc 10.0.2.2 8000"
```
**Empirical Output:**
```http
HTTP/1.1 200 OK
date: Mon, 02 Nov 2026 15:15:25 GMT
server: uvicorn
content-length: 265
content-type: application/json
connection: close

{"status":"healthy","timestamp":"2026-11-02T15:15:26.066104+00:00","version":"1.0.0",...}
```
**Result:** Verified. `10.0.2.2:8000` maps cleanly from Android emulator space to the Uvicorn server on the host.

### 2.3 Android Client Configuration & Screen Verification
- **Configured Base URL:** In [`RetrofitClient.kt`](file:///android/app/src/main/java/com/agrimind/app/data/api/RetrofitClient.kt), `DEFAULT_BASE_URL = "http://10.0.2.2:8000/"`.
- **System Health Screen (`selectedTab = 3`):**
  - Live inspection on `emulator-5554` confirmed active gateway: `http://10.0.2.2:8000/`.
  - Banner: `Backend Online & Healthy` (`Status: HEALTHY | v1.0.0`).
  - Vision Status: `ResNet-50 Vision Checkpoint: LOADED (Online)`.
  - Device: `CPU`.
  - Pathogens: `3 tomato classes`.
  - Telemetry Screenshot: Saved to [`docs/stage_c2_readiness_health_screen.png`](file:///docs/stage_c2_readiness_health_screen.png).

### 2.4 End-to-End API Response Verification
1. **Grounded Conversational Assistance (`POST /chat`):**
   - Question: *"How to control Early Blight?"*
   - Response received in Android `ChatScreen`: Synthesized guidance citing UC IPM and Purdue University Extension bulletins with preliminary AI assessment disclaimers.
   - Uvicorn Server Log: `INFO: 127.0.0.1:39578 - "POST /chat HTTP/1.1" 200 OK`.
2. **Diagnostic Workflow Execution (`POST /diagnose`):**
   - Submitted PlantDoc leaf image: Received `case_id: CASE-7FBD971E`, diagnosis `Tomato___Late_blight` (98.02% confidence), verified IPM plan, and 4 extension citations.
   - Uvicorn Server Log: `INFO: 127.0.0.1:52782 - "POST /diagnose HTTP/1.1" 200 OK`.
3. **Invalid/Corrupt Image Rejection:**
   - Corrupt bytes returned `HTTP 400 Bad Request` with detail `"Corrupted or unreadable image file. Unable to decode image content."`.

---

## 3. Configuration, Database, ML Model & RAG Corpus Audit (Item 4)

| Subsystem | Intended Component | Current State on Disk | Audit Assessment |
|:---|:---|:---|:---|
| **Vision Model** | ResNet-50 3-class classifier | `outputs/week2_vision/best_model.pth` (282,626,785 bytes) | **Intact & Authoritative**. Verified untouched since Oct 13, 2026. |
| **Model Classes** | 3 in-scope tomato diseases | `Tomato___Bacterial_spot`, `Tomato___Early_blight`, `Tomato___Late_blight` | **Compliant**. Strictly bounded to 3 classes across all schemas. |
| **RAG Raw Corpus** | 6 extension fact sheets | `data/knowledge_base/raw/*.md` (Cornell, UC IPM, Purdue, UF/IFAS) | **Intact**. All 6 fact sheets present with citation URLs. |
| **RAG Chunks** | Processed chunk metadata | `data/knowledge_base/processed_chunks.json` (63 chunks) | **Intact**. Contains 63 validated agronomic chunks. |
| **ChromaDB Vector Store** | Persistent Chroma collection | `data/vectorstore/chroma/chroma.sqlite3` (`agrimind_tomato_diseases`) | **63 records in `embeddings` table**. Cosine distance indexed. |
| **Backend Storage** | Server-side case storage | `data/cases.db` (SQLite, table `cases`) | **59 cases stored**. Enforces ACID persistence and state isolation. |
| **Android Chat Store** | Local conversation database | `agrimind_chat.db` (native Android SQLite) | **Operational**. Tables `conversations` & `chat_messages` with FK cascade. |
| **Android Case Store** | Device case repository | `LocalCaseRepository` (`agrimind_cases_prefs` SharedPreferences) | **Operational**. JSON-serialized case records for offline viewing. |
| **Android PDF Engine** | Native PDF generator | `PdfReportGenerator.kt` (`android.graphics.pdf.PdfDocument`) | **Operational**. Generates multi-page A4 crop-health reports locally. |

### 3.1 Investigation of the 50 vs. 63 Chunk Discrepancy
- **Query on ChromaDB SQLite table directly:**
  ```python
  import sqlite3
  conn = sqlite3.connect('data/vectorstore/chroma/chroma.sqlite3')
  print(conn.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0])
  # Result: 63
  ```
- **Code Inspection of `src/api/routes.py:213`:**
  ```python
  has_model = os.path.exists(CHECKPOINT_PATH)
  has_chroma = os.path.exists(CHROMA_DIR)

  # Count Chroma chunks if vectorstore is populated
  rag_chunks = 50 if has_chroma else 0
  ```
- **Conclusion:** The vector store contains all 63 chunks. The `/health` route simply hardcoded `50` as a placeholder during the Phase 0 baseline. This is a cosmetic telemetry discrepancy, not a vector store corruption or missing chunk error.

---

## 4. Prioritized List of Unfinished Requirements (Item 6)

### Category A: Confirmed Gaps (Genuinely Unfinished Implementation Requirements)

1. **Dynamic ChromaDB Telemetry in `/health` (Priority: High):**
   - *Current State:* Hardcoded `rag_chunks = 50 if has_chroma else 0`.
   - *Gap:* Does not reflect the true 63 chunks in ChromaDB, confusing users and testers inspecting the Android System Health screen.
   - *Required Action:* Query the collection count dynamically or cache the actual indexed chunk count upon vector store startup.

2. **Server-Side Case Retrieval Endpoint `GET /cases/{case_id}` (Priority: High):**
   - *Current State:* `src/api/case_store.py` implements `get_case(case_id)`, and `POST /reassess` uses it internally. However, there is no public REST endpoint `GET /cases/{case_id}`.
   - *Gap:* If an Android user enters a case ID from another session, or if local app storage is cleared, the app cannot fetch the authoritative case state from the backend.
   - *Required Action:* Expose `GET /cases/{case_id}` returning a validated `DiagnosisResponse`.

3. **Android Client Fallback to Server for Case Details (Priority: Medium):**
   - *Current State:* `CaseDetailScreen` only loads from `LocalCaseRepository`. If a case is not in the local SharedPreferences, it cannot be viewed.
   - *Gap:* Prevents cross-device case continuity or restoring case details by Case ID.
   - *Required Action:* In `CaseDetailViewModel`, if a case record is absent locally, query `GET /cases/{case_id}` via Retrofit.

4. **Case Reassessment History Display in Android (Priority: Medium):**
   - *Current State:* `LocalCaseRecord` preserves `reassessmentRecords`, and `CaseDetailScreen` shows the count ("Reassessed 2 of 2"). However, the individual historical snapshots (previous severity, timestamps, triggers) are not surfaced in an expandable timeline.
   - *Gap:* Agronomists cannot review the progressive changes in severity from Cycle 1 to Cycle 2.

---

### Category B: Optional / Postponed Enhancements (Explicitly Out of Current Scope)

1. **Dogri Language Conversational Model & Speech (Postponed):**
   - *Status:* Dialog currently displays "Soon". Language models for Dogri require specialized corpora and tokenizers.
   - *Constraint:* Postponed per project guidance; do not begin in Stage C.
2. **Hindi Voice Speech Recognition Fine-Tuning (Postponed):**
   - *Status:* Speech recognition is functional via Google SpeechRecognizer; deep acoustic model fine-tuning is out of scope.
3. **Multi-Crop Expansion (Postponed):**
   - *Status:* Classifier and RAG are strictly bounded to 3 tomato diseases. Expanding to potato, bell pepper, or corn requires new datasets and models.
4. **ResNet-50 Domain-Shift Retraining (Research Track):**
   - *Status:* PlantDoc background masking/copy-paste augmentation is documented in `full_existing_system_architecture_audit.md` as an academic proposal. Retraining or altering model weights is strictly forbidden.
5. **Live Weather API Integration (Optional Third-Party Cloud Feature):**
   - *Status:* Weather conditions are supplied via manual form entry in `VisualContextInput`. Integrating external APIs (OpenWeatherMap, NOAA) introduces network dependencies and API key requirements outside the standalone minor project scope.

---

## 5. Recommended Next Milestone (Item 7)

### **Recommendation: Stage C.2 — Case State Synchronization & Telemetry Alignment**

Based on empirical evidence from this audit, the next logical, genuinely unfinished requirement is **Stage C.2**.

#### Stage C.2 Implementation Scope:
1. **Dynamic Telemetry Fix (`src/api/routes.py`):**
   - Replace hardcoded `rag_chunks = 50` with dynamic collection count query (`coll.count()` = 63) in `GET /health`.
2. **Authoritative Case Retrieval Endpoint (`GET /cases/{case_id}`):**
   - Add `GET /cases/{case_id}` to `src/api/routes.py` with validation and 404 handling.
   - Add corresponding integration test in `tests/test_api.py`.
3. **Android Client Remote Case Fetching:**
   - Add `@GET("cases/{case_id}")` to `AgriMindApiService.kt`.
   - Update `CaseDetailViewModel.kt` to fetch from API when given a case ID not found in local cache.
4. **Comprehensive Automated Testing & APK Verification:**
   - Execute backend test suite (`python -m unittest tests/test_api.py`).
   - Run Android unit tests (`.\gradlew.bat testDebugUnitTest`).
   - Verify live on `emulator-5554`.

