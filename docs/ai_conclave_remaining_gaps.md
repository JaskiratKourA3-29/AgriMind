# AgriMind AI Conclave — Remaining Gaps, Architectural Boundaries & Fallback Strategies

**Project:** AgriMind Minor Project (`COM71116-21`)  
**Document Purpose:** Unvarnished, transparent disclosure of system boundaries, edge constraints, hardware limitations, and future work.  
**Audit Date:** 2026-11-03  

---

## 1. Approved Scope Boundaries

### Sole Future-Scope Item: iOS Support
- **Status:** **Deferred to Future Scope** (approved by academic project guidelines).
- **Rationale:** AgriMind targets smallholder tomato farmers across the Jammu & Kashmir and Northern Indian agricultural belts, where Android commands over 97% of the mobile market share.
- **Architectural Readiness:** The FastAPI backend is 100% platform-agnostic with strict OpenAPI 3.0 schemas, RESTful JSON payloads, and standard multipart upload endpoints, allowing rapid future iOS client development via Swift / SwiftUI without backend modification.

---

## 2. Hardware, Compute & Latency Boundaries

### Edge-Server CPU vs Mobile On-Device Execution
- **Current Architecture:** Thin client (Android Kotlin / Jetpack Compose) + Edge Server (FastAPI on CPU).
- **Measured CPU Latencies (Intel/AMD x86_64 host):**
  - ResNet-50 vision forward pass: **$16.6\text{ s} - 18.1\text{ s}$**
  - LangGraph multi-agent reasoning: **$21.5\text{ s} - 25.0\text{ s}$**
  - Total diagnostic response time: **$38.2\text{ s} - 42.5\text{ s}$**
- **Disclosed Limitation:** The application does **not** execute real-time on-device neural network inference on the smartphone. The smartphone performs local image pre-validation (dimensions, format, size), offline request caching, and PDF generation, but delegates deep vision inference and RAG retrieval to the edge server.
- **Future Production Roadmap:** Quantization of ResNet-50 to INT8 via PyTorch Mobile / ONNX Runtime to enable lightweight on-device inference for devices with $\ge 4\text{ GB}$ RAM, alongside TensorRT/CUDA acceleration on GPU-equipped edge servers reducing round-trip latency to $<1.5\text{ s}$.

---

## 3. Multilingual Voice & Speech Boundaries

### Dogri Voice Input & Spoken Output Limitation
- **Status:** **Implemented with Strongest Feasible Vernacular Text Fallback; Hardware Engine Limitation Fully Disclosed.**
- **Underlying Limitation:** Neither Google Speech Services nor standard Android AOSP `android.speech.tts.TextToSpeech` provides a certified native Dogri (`doi` / `dgo`) acoustic model or TTS voice pack on standard Android distributions.
- **Feasible Implementation Deployed:**
  1. Lexical detection: `LanguageDetector.kt` and `src/rag/language_detector.py` accurately identify authentic Dogri lexical markers (`"गेया"`, `"गेन"`, `"कचे"`, `"इयां"`, `"किदां"`, `"कुस चाल्ली"`).
  2. RAG Synthesis: `AgrimindAnswerGenerator` synthesizes authentic Dogri phrasing in Devanagari script for extension guidance.
  3. Audio Output Fallback: When the user requests Dogri audio playback on devices lacking a native Dogri engine, the app displays the native Dogri Devanagari text on-screen while routing audio phonemes through the standard Hindi (`hi-IN`) TTS engine with an explicit on-screen advisory explaining engine fallback.
- **Truth-in-Advertising Commitment:** The project does **not** claim full native Dogri speech synthesis on stock mobile devices.

---

## 4. External Cloud Service & Quota Boundaries

### Google Gemini API Free-Tier Quota Exhaustion
- **Current Behavior:** Free-tier Gemini 2.5/3.0 API keys enforce strict rate limits (e.g., 20 requests per day on certain free tiers).
- **Engineered Fallback Strategy:** The AgriMind backend implements dual-tier generation in `src/rag/generator.py`:
  - When Gemini API is available and responsive: Generates natural conversational agronomic synthesis.
  - When Gemini API returns HTTP 429 (`RESOURCE_EXHAUSTED`) or 503: The backend instantly and deterministically falls back to **Grounded Extractive Synthesis**, compiling direct quotes and bulleted recommendations from the verified 63-chunk ChromaDB vector store with exact bracketed citations `[1]`, `[2]`.
- **Integrity Guarantee:** The system never fails completely due to cloud API quota limits and never hallucinates unverified chemical compounds during quota exhaustion.

---

## 5. Inter-Cooperative Governance & Regional Data Sharing

### Multi-Region Comparison Boundary
- **Current Behavior:** Displays regional disease distribution comparing local live pilot data from Jammu (R.S. Pura Hub) with simulated partner grids (Punjab Gurdaspur and Himachal Kangra).
- **Enforced Boundary:** All responses from `/cooperative/comparison` set `is_live_partnership: False` and prominently attach the following disclaimer:
  > *"Multi-cooperative comparison presents local live pilot cases alongside simulated regional partner nodes for demonstration of multi-cooperative interoperability. Formal inter-state data exchange requires approved data governance protocols."*
- **Truth-in-Advertising Commitment:** The project makes no unverified claims of active formal bilateral institutional partnerships with Punjab or Himachal agricultural departments.

---

## 6. Regulatory & Phytosanitary Certification Boundaries

### Statutory Limits of AI Decision Support
- **Current Behavior:** AgriMind provides decision support based on accredited university extension literature (Cornell, Purdue, UC IPM, UF/IFAS).
- **Enforced Boundary:** The application and exported PDF reports explicitly carry the statutory certification boundary notice:
  > *"NOTICE: AI image analysis alone does NOT issue an official disease-free certificate. Any formal phytosanitary certification requires an authorized inspection and approved certification process by competent state agricultural authorities."*
- **Legal Compliance:** In accordance with national agricultural regulations, all chemical bactericide and fungicide dosages are explicitly marked as preliminary and require local extension officer confirmation prior to field application.

---

## 7. Mobile Device & Live Emulator Testing Environment

### Active ADB Session State
- **Current Audit Finding:** Executing `adb devices` during this final audit session returns `List of devices attached` with 0 connected devices or emulators.
- **Automated Verification Deployed:** In the absence of a booted emulator or physical USB device during this session, the Android application layer is verified via:
  1. Automated execution of all 49 Gradle unit tests across `DiagnosisViewModelTest`, `CaseDetailViewModelTest`, `ChatViewModelTest`, and `LanguageDetectorTest` (`BUILD SUCCESSFUL in 27s`, Exit code 0).
  2. Inspection of the pre-built debug APK (`android/app/build/outputs/apk/debug/app-debug.apk`, 17.8 MB).
  3. Decompression and binary inspection of the generated sample PDF report artifact (`outputs/AgriMind_Report_CASE-7DC903FC.pdf`, 96,404 bytes, 2 pages, Skia/PDF m148).
- **Truth-in-Advertising Disclosure:** Real-time on-device touchscreen interactions, physical microphone speech recognition, and physical device airplane-mode toggles were not executed live in this audit turn. Prior live emulator runs and screenshots remain documented in the Stage C5 acceptance report (`docs/stage_c5_acceptance_and_release_report.md` and `outputs/stage_b4_pdf_viewer_screen.png`).


