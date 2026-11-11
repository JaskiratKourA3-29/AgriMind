# AgriMind — Verified Project Baseline & Feature Matrix

**Project:** AgriMind Minor Project (`COM71116-21`)  
**Audit Timestamp:** 2026-11-03T12:57:00+05:30  
**Evaluator:** Senior Full-Stack, AI/ML, Security, QA & Agricultural AI Engineer  
**Baseline Principle:** Strict truth-in-advertising. Zero assumed success. Results derived strictly from running test runners, physical checkpoints, database schemas, and codebase inspection.

---

## 1. Automated Test Baseline Summary

| Component / Test Runner | Total Tests Discovered | Passed | Failed | Errors | Skipped | Measured Duration | Exit Code |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Suite (`unittest` via WSL Python 3.13)** | **218** | **182** | **33** | **3** | 0 | $564.76\text{ s}$ ($9.4\text{ min}$) | `1` |
| **Android Unit Suite (`testDebugUnitTest` via Gradle)** | **49** | **49** | **0** | **0** | 0 | $25.00\text{ s}$ | `0` |
| **Combined Project Total** | **267** | **231** | **33** | **3** | **0** | — | — |

> [!IMPORTANT]
> The historical claim that "95/95 tests pass" was an arbitrary sum of 46 cherry-picked backend tests and 49 Android unit tests. When executing the full repository test suite, **182 backend tests pass** and **36 tests fail or error** (primarily due to cross-test cache pollution, legacy week 5-9 milestone schema drifts, and function signature mismatches).

---

## 2. Nine Core Features Baseline Matrix

| # | Feature Area | Current Baseline Status | Primary Implementation Files | Verified Behavior & Evidence | Critical Gaps & Blockers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Conversational AI & Follow-up** | **Implemented but partially verified** | `src/rag/generator.py`, `src/rag/retriever.py`, `src/api/routes.py`, `ChatViewModel.kt` | Anaphora resolution and case anchoring verified. Extractive synthesis handles Gemini API 429 quota exhaustion. | Fabrication weakness: unanchored fake chemical queries (`crypto-solanidine-XYZ99`) score $0.5506$ against Actigard chunks and fail to trigger insufficient-evidence fallback. |
| **2** | **Vision Inference, Confidence & Scanner** | **Partially implemented** | `src/vision/inference.py`, `src/api/routes.py`, `DiagnosisViewModel.kt`, `DiagnosisScreen.kt` | ResNet-50 checkpoint verified ($282.6\text{ MB}$, 3 tomato classes). Low-confidence policy triggers below $0.65$. | 1. Duplicate cache key omits `field_notes`.<br>2. Cross-test cache pollution causes `test_03` failure.<br>3. Closed-set softmax lacks non-plant/OOD rejection.<br>4. Android app lacks direct camera shutter capture. |
| **3** | **Preventive & Context-Aware Guidance** | **Implemented and verified** | `src/workflow/nodes.py`, `src/agents/prompts.py`, `DiagnosisScreen.kt` | 4-tier IPM hierarchy (Cultural -> Resistant -> Chemical -> Monitoring). Wallin/Hyre weather model escalates Late Blight. | Must expand agricultural agronomy Q&A guidance beyond tomatoes while keeping vision strictly tomato-focused. |
| **4** | **Farmer Case Sharing & Community** | **Implemented but partially verified** | `src/services/case_sharing_service.py`, `src/api/routes.py`, `CaseDetailViewModel.kt` | PII sanitization ("Anonymous Farmer"), GPS 1-decimal truncation ($11.1\text{ km}$ grid), comment threads with `is_ai` flag. | Defect in `tests/test_case_sharing.py`: `record_outcome` called with invalid kwargs causing `TypeError`. Missing user account isolation. |
| **5** | **Cooperative-to-Cooperative Insights** | **Implemented and verified** | `src/services/cooperative_service.py`, `src/api/routes.py`, `HistoryViewModel.kt` | Regional disease aggregation and outbreak detection. External partner nodes (Punjab, Himachal) explicitly set `is_live_partnership: False`. | Inter-state data remains synthetic for demonstration. |
| **6** | **Weather Integration & Risk Escalation** | **Implemented and verified** | `src/services/weather_service.py`, `src/api/routes.py`, `DiagnosisScreen.kt` | Open-Meteo REST API integration with 30-min cache and offline seasonal fallback. | Need richer localized English and Hindi advice for heat stress, waterlogging, and prolonged leaf wetness. |
| **7** | **Jammu-Focused Demonstration** | **Implemented and verified** | `scripts/demo_jammu_rspura.py` | 7-step scenario for R.S. Pura border belt ($32.61^\circ\text{N}, 74.73^\circ\text{E}$) running end-to-end in ~42s. | CLI demonstration only; live emulator UI was not attached during run. |
| **8** | **Crop-Health PDF Reports** | **Implemented and verified** | `PdfReportGenerator.kt`, `CaseDetailViewModel.kt`, `outputs/AgriMind_Report_CASE-7DC903FC.pdf` | Native Android `PdfDocument` rendering 2 pages with QR code, weather, IPM, citations, and regulatory phytosanitary disclaimer box. | Live on-device generation verified through unit tests and physical PDF decompression. |
| **9** | **Low-Connectivity & Farmer Experience** | **Partially implemented** | `OfflineQueueManager.kt`, `LocalCaseRepository.kt`, `DiagnosisViewModel.kt` | Room SQLite database queues offline actions. Saved cases readable without network. | Lacks clear visual online/offline connectivity badge on dashboard, and lacks a practical QR-code installation workflow. |

---

## 3. Scope & Boundary Baseline

1. **Authentication & Role Separation:**
   - **Current State:** **Not implemented**. The backend currently has zero user registration, login, session token validation, or role separation. All diagnostic cases and shared items are unauthenticated or rely on arbitrary client-supplied IDs.
   - **Action Required:** Implement user authentication with secure password hashing (`PBKDF2`/`bcrypt`), JWT session tokens, role-based access control (`farmer` vs `admin`), and cross-farmer record isolation.
2. **Crop Support Scope:**
   - Image diagnosis is strictly validated for **three tomato disease classes**:
     - `Tomato___Bacterial_spot`
     - `Tomato___Early_blight`
     - `Tomato___Late_blight`
   - Conversational AI will support multi-crop agronomy (Wheat, Rice, Potato, Chili, Mustard, Maize, Tomato) with clear disclosure that image diagnosis is tomato-only.
3. **Language Scope:**
   - **English:** Fully supported.
   - **Hindi:** Fully supported (UI strings, guidance, error prompts, TTS).
   - **Dogri:** Reclassified to **Future Scope Only**. Misleading approximations (routing Dogri through Hindi TTS) must not be presented as native Dogri support.
4. **Platform Scope:**
   - **Android:** First-tier target platform.
   - **iOS:** Sole future scope item.

---

## 4. Confirmed Critical Defects for Stage B Resolution

1. **Defect 1: Diagnosis Cache Key Omission (`src/api/routes.py` line 382)**
   - *Impact:* Duplicate cache key `f"{image_sha256}_{leaf_damage_percentage}_{weather_conditions}_{latitude}_{longitude}"` omits `field_notes`, `affected_organs`, `canopy_spread`, and `user_query`. Changing farmer observations returns stale cached responses.
2. **Defect 2: Cross-Test Cache Pollution (`tests/test_feature2_vision_inference.py`)**
   - *Impact:* `_IMAGE_SUBMISSION_CACHE` is not cleared in test `setUp()`/`tearDown()`, causing `test_03` to fail with `AssertionError: True is not false`.
3. **Defect 3: Function Signature Mismatch (`tests/test_case_sharing.py` line 143)**
   - *Impact:* `test_treatment_outcome_recording` calls `record_outcome` with kwargs (`treatment_applied`, `outcome_status`, `recovery_percentage`, `notes`), causing `TypeError`.
4. **Defect 4: Dense Bi-Encoder Hallucination Bypass (`src/rag/retriever.py`, `src/rag/generator.py`)**
   - *Impact:* Queries containing domain stopwords and fabricated chemicals match Actigard chunks with similarity $0.5506 > 0.55$, bypassing fallback gating.

