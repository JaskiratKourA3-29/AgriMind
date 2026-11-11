# AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support

**Course Code:** COM71116-21 (7th-Semester B.Tech Computer Science & Engineering Minor Project)  
**Academic Session:** 2026–2027  
**Project Team:**  
- Jaskirat Kour (Team Leader, Roll No: COM71116)  
- Palakjot Kour (Roll No: COM71117)  
- Sayam Malhotra (Roll No: COM71118)  
- Ikjot Singh (Roll No: COM71119)  
**Project Repository:** `C:\Users\asus\Downloads\Agri_Mind_Minor_Project`  
**Document Version:** 1.0.0 (Final Comprehensive Project Dissertation & Defense Dossier)  

---

## Abstract

Crop diseases present severe risks to agricultural yields, rural food security, and smallholder farmer livelihoods. Conventional deep learning approaches to automated foliar diagnosis rely primarily on monolithic convolutional neural networks trained on controlled laboratory datasets. While achieving near-perfect laboratory accuracy, such models fail in field deployments due to background clutter, inability to reason about environmental contexts (such as weather), and lack of actionable, grounded treatment recommendations.

**AgriMind** addresses these critical limitations through a unified, full-stack, multi-agent artificial intelligence decision support system. The architecture integrates:
1. A calibrated **ResNet-50** deep convolutional neural network for 3-class in-scope tomato foliar pathology (`Tomato___Bacterial_spot`, `Tomato___Early_blight`, `Tomato___Late_blight`).
2. A **LangGraph-orchestrated Multi-Agent Reasoning Core** comprising an Investigation Agent, Risk Assessment Agent (with dynamic weather-driven epidemiological gating), Decision Planning Agent (enforcing a 4-tier Integrated Pest Management hierarchy), Critic/Verification Agent, and an Adaptive Reassessment mechanism with a strict 2-cycle quota.
3. A **Retrieval-Augmented Generation (RAG)** engine grounded in 63 curated vector chunks from accredited university extension publications (Cornell CALS, UC IPM, Purdue, and UF/IFAS).
4. A production-ready **Native Android Application** built entirely with Kotlin and Jetpack Compose (Material 3), featuring bilingual vernacular voice interaction (English and Hindi STT/TTS with automated Devanagari script detection), offline local SQLite data caching, native on-device A4 PDF crop-health report generation, and an expandable chronological reassessment history timeline.

Across 94 automated tests (29 backend integration tests, 21 mocked unit tests, and 44 Android ViewModel unit tests) and extensive live execution on physical and emulated devices, AgriMind achieved a **100% test pass rate**, demonstrating robust agronomic safety guardrails, offline resilience, and operational field readiness.

---

## 1. Problem Formulation & Motivation

### 1.1 Limitations of Existing Approaches
1. **Monolithic Decision Bottlenecks:** Existing applications provide a disease label and a raw probability without evaluating symptom distribution across the canopy or factoring in ambient weather conditions.
2. **Laboratory-to-Field Domain Shift:** Models trained on clean, single-leaf datasets (such as PlantVillage) suffer catastrophic performance degradation when evaluated against in-the-wild agricultural imagery (such as PlantDoc) due to complex outdoor backgrounds (sky, soil, shadows).
3. **Hallucination & Agronomic Danger:** Large Language Models (LLMs) used without strict retrieval gating often hallucinate chemical recommendations, suggest off-label pesticide tank mixes, or confuse preventative anti-sporulants (Mandipropamid) with curative post-infection kickback fungicides (Cymoxanil).
4. **Language & Usability Barriers in Rural India:** Most digital agricultural assistants operate solely in English and require high-speed internet, alienating smallholder farmers who communicate in regional vernaculars (Hindi) and operate under low-connectivity conditions.

### 1.2 Approved Minor Project Scope (`COM71116-21`)
The approved minor project specification bounds the system to:
- A single-farm decision support tool (standalone edge/local client-server model).
- Strict focus on the 3 primary foliar tomato diseases affecting smallholder yield in North India:
  - **Bacterial Spot** (*Xanthomonas spp.*)
  - **Early Blight** (*Alternaria solani*)
  - **Late Blight** (*Phytophthora infestans*)
- Complete multi-agent reasoning, RAG grounding, native Android Compose interface, local PDF generation, and vernacular Hindi assistance.

---

## 2. System Architecture & Technical Specifications

```
                                  [AgriMind Architecture]

   ┌────────────────────────────────────────────────────────────────────────┐
   │                       Native Android Application                       │
   │                      (Kotlin, Jetpack Compose, M3)                     │
   │                                                                        │
   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  ┌───────────┐│
   │   │  Diagnosis   │   │   History    │   │  Assistant   │  │  Health   ││
   │   │  Screen (M3) │   │  Screen (DB) │   │  (STT / TTS) │  │ Telemetry ││
   │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘  └─────┬─────┘│
   │          │                  │                  │                │      │
   │          │           ┌──────┴──────────────────┴────────┐       │      │
   │          │           │ Local SQLite Store (agrimind.db) │       │      │
   │          │           │ Offline Cache & PDF Report Engine│       │      │
   │          │           └─────────────────┬────────────────┘       │      │
   └──────────┼─────────────────────────────┼────────────────────────┼──────┘
              │ Multipart/JSON              │ Retrofit 2             │ REST
              ▼                             ▼                        ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                          FastAPI REST Gateway                          │
   │            (Input Validation, 15MB Limit, Bitstream Sniffing)          │
   │                                                                        │
   │  Endpoints: POST /diagnose | POST /chat | POST /reassess | GET /cases  │
   └───────────────────────────────────┬────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  Computer Vision Subsystem   │              │   LangGraph Multi-Agent Core │
│  ResNet-50 3-Class Backbone  │              │  Investigation Agent         │
│  (PyTorch Linear Projection Head)            │  Risk Assessment (Weather)   │
│  Outputs Calibrated Softmax  │              │  Decision Planning (4-Tier)  │
└──────────────┬───────────────┘              │  Critic & Verification       │
               │                              │  Adaptive Reassessment Loop │
               │                              └──────────────┬───────────────┘
               │                                             │
               ▼                                             ▼
        ┌────────────────────────────────────────────────────────────┐
        │             Authoritative Grounding & Storage              │
        │  • ChromaDB Vector Store (63 Chunks, MiniLM-L6-v2 Embeddings)│
        │  • Server-Side SQLite Case Store (data/cases.db)            │
        │  • Extension Knowledge Base (Cornell, UC IPM, Purdue, UF)   │
        └────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Implementation Details

### 3.1 Computer Vision Classifier
- **Backbone Architecture:** Deep residual network (ResNet-50) initialized with `IMAGENET1K_V2` weights.
- **Classification Head:** Linear projection replacing the default 1000-class layer:
  $$\text{Head} = \text{nn.Linear}(\text{in\_features}=2048, \text{out\_features}=3)$$
- **Target Pathogen Indexing:**
  - Index `0`: `Tomato___Bacterial_spot`
  - Index `1`: `Tomato___Early_blight`
  - Index `2`: `Tomato___Late_blight`
- **Trained Model Checkpoint:** `outputs/week2_vision/best_model.pth` ($282,626,785\text{ bytes}$).
- **Empirical Accuracy:**
  - **PlantVillage Validation Split ($N=1,007$):** **98.41% Accuracy**, Macro F1: 0.9839.
  - **PlantDoc In-the-Wild Benchmark ($N=28$):** 39.29% baseline accuracy. Documented domain gap analysis proved that outdoor background clutter (soil, sky) causes misclassifications, and background masking elevates accuracy to 50.00%.

### 3.2 LangGraph Multi-Agent Decision Engine
The core reasoning backend is compiled as a cyclical `StateGraph` in `src/workflow/graph.py`:
1. **Investigation Agent (`src/agents/investigation.py`):**
   - Synthesizes model predictions with farmer visual context (damage percentage, canopy spread, affected organs).
   - Flags diagnostic conflicts (e.g., model predicts Early Blight on upper canopy when lesions are exclusively on fruit).
2. **Risk Assessment Agent (`src/agents/risk_assessment.py`):**
   - Enforces epidemiological safety gating.
   - **Weather Risk Escalation:** Monitors ambient temperature, humidity, and leaf wetness. If Late Blight is detected under cool/wet conditions ($<20^\circ\text{C}$ with free moisture), risk escalates from `MODERATE` to `HIGH` or `CRITICAL` regardless of low visual foliar damage.
3. **Decision Planning Agent (`src/agents/decision_planning.py`):**
   - Constructs a 4-tier Integrated Pest Management (IPM) plan:
     - *Tier 1: Cultural & Sanitation:* Removal of infected plant debris, spacing, drip irrigation.
     - *Tier 2: Resistant Cultivars:* Deployment of Ph-2 + Ph-3 dual-gene cultivars.
     - *Tier 3: Preventive Chemical:* Copper hydroxide, Mancozeb, Chlorothalonil protectant sprays.
     - *Tier 4: Curative Chemical:* Strict kickback gating (Cymoxanil within 24–48h of infection; Mandipropamid anti-sporulant only).
4. **Critic & Verification Agent (`src/agents/critic.py`):**
   - Audits proposed actions against retrieved literature. Validates pesticide safety notices, REI/PHI label requirements, and ensures chemical interventions are withheld under diagnostic conflict.
5. **Adaptive Reassessment Mechanism (`src/agents/reassessment.py`):**
   - Provides longitudinal tracking across up to 2 reassessment cycles per case. Integrates new field evidence and recomputes severity shifts (`revised`, `confirmed`, `escalated`).

### 3.3 Authoritative Agricultural Knowledge Base & RAG
- **Raw Fact Sheets:** 6 university extension documents from Cornell CALS, UC IPM, Purdue Extension, and UF/IFAS.
- **Processed Chunks:** Exactly 63 validated agronomic chunks stored in `data/knowledge_base/processed_chunks.json`.
- **Vector Store:** ChromaDB persistent collection indexed with `sentence-transformers/all-MiniLM-L6-v2` cosine similarity.
- **Response Synthesis:** Combines semantic retrieval with template/LLM generation, providing verbatim citation metadata and university URLs.

### 3.4 Native Android Compose Application
- **Language & Toolkit:** 100% Kotlin with Jetpack Compose, Material 3, and Kotlin Coroutines/Flow.
- **Navigation Flow:**
  - **Tab 0 (Diagnosis):** Camera capture, gallery picker, manual visual context inputs, progress indicators, preliminary assessment disclaimer, and "Ask Assistant About This Case" direct action.
  - **Tab 1 (History):** Local case browsing, search by Case ID, pathogen filtering, and date sorting.
  - **Tab 2 (Assistant):** Multi-turn chat, markdown rendering, university citation chips, audio wave visualizer, STT microphone sheet, TTS playback, and persistent conversation sheet.
  - **Tab 3 (System Health):** Real-time gateway status, ResNet-50 status, 63 RAG chunk telemetry, CPU device info, and active classes.
  - **Case Detail Screen:** Comprehensive diagnostic record, expandable/collapsible chronological reassessment timeline, reassessment request dialog, and native PDF report export.
- **Vernacular Assistance:**
  - *Hindi Text Generation:* Automatic routing via Devanagari Unicode detection (`\u0900..\u097F`).
  - *Speech-to-Text:* Google `SpeechRecognizer` configured for `en-IN` and `hi-IN`.
  - *Text-to-Speech:* Android `TextToSpeech` with regex-based markdown/URL sanitization.
- **Local PDF Report Engine:**
  - Uses native `android.graphics.pdf.PdfDocument` to generate publication-grade multi-page A4 crop-health reports on device without internet connectivity.
  - Integrates with Android `FileProvider` and `ACTION_SEND` share sheet for sharing via WhatsApp, Gmail, and Google Drive.

---

## 4. Empirical Evaluation & Test Results

### 4.1 Automated Test Suite Verification

| Test Suite | Test Scope | Number of Tests | Execution Time | Pass Rate |
|:---|:---|:---:|:---:|:---:|
| **Backend Integration Suite** (`tests/test_api.py`) | Real ResNet-50 inference, RAG retrieval, multi-turn chat, case persistence, remote retrieval, reassessments | 29 | 101.10s | **100% (29/29)** |
| **Backend Mocked Suite** (`TestApiUnitMocked`) | Corrupt payloads, 15MB rejection, magic bytes, vectorstore failure fallbacks | 21 | 3.14s | **100% (21/21)** |
| **Android Unit Suite** (`testDebugUnitTest`) | ViewModels, timeline state, empty history, trigger mapping, ISO date formatting | 44 | 29.00s | **100% (44/44)** |
| **Total Automated Suite** | Full-Stack End-to-End Regression | **94** | **133.24s** | **100% (94/94)** |

### 4.2 Weather Risk Escalation Empirical Benchmarks
Conducted on the live FastAPI backend using a calibrated Late Blight specimen:

$$\begin{aligned}
\text{Condition 1: } & \text{hot\_dry} + 3\% \text{ foliar damage} \longrightarrow \text{Severity: MODERATE}, \text{Risk: MODERATE} \\
\text{Condition 2: } & \text{cool\_wet} + 3\% \text{ foliar damage} \longrightarrow \text{Severity: HIGH}, \text{Risk: HIGH} \quad (\textbf{Weather Escalation Triggered}) \\
\text{Condition 3: } & \text{cool\_wet} + 10\% \text{ foliar damage} \longrightarrow \text{Severity: CRITICAL}, \text{Risk: CRITICAL} \quad (\textbf{Epidemic Threshold Exceeded})
\end{aligned}$$

### 4.3 Release Packaging Metrics
- **Release Compilation Task:** `cd android && gradlew.bat assembleRelease` completed in 10m 47s (`BUILD SUCCESSFUL`).
- **Release APK Output:** `android/app/build/outputs/apk/release/app-release-unsigned.apk` ($11,406,303\text{ bytes}$).
- **Debug APK Output:** `android/app/build/outputs/apk/debug/app-debug.apk` ($11,768,591\text{ bytes}$, signed with Android debug keystore).
- **Signature Verification:** Verified via `apksigner verify --verbose` (Debug: v2 scheme verified; Release: unsigned per security requirements).

---

## 5. Deployment Guide for Physical Android Devices

To demonstrate AgriMind on a physical smartphone during project viva evaluation:

### Procedure A: USB Tethering with Port Forwarding (Recommended)
1. Enable **Developer Options** and **USB Debugging** on the target Android phone.
2. Connect the phone to the laptop via USB cable.
3. Establish port forwarding from the host machine:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
4. Install the pre-signed debug APK:
   ```bash
   adb install -r android/app/build/outputs/apk/debug/app-debug.apk
   ```
5. Launch the Uvicorn backend in WSL2:
   ```bash
   python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
   ```
6. Open the app on the phone; the default gateway `http://10.0.2.2:8000/` or `http://localhost:8000/` routes directly through the USB tunnel, whitelisted under `network_security_config.xml`.

### Procedure B: Wi-Fi Local Area Network (LAN)
1. Connect both laptop and phone to the same Wi-Fi hotspot.
2. Note the host laptop's LAN IP (e.g. `192.168.1.100`).
3. Set the gateway URL in **System Health** to `http://192.168.1.100:8000/`.
4. Ensure host firewall permits inbound traffic on port 8000.

---

## 6. Comprehensive Project Defense Q&A (Viva Voce Preparation)

### Q1: Why did you use a Multi-Agent architecture instead of a simple end-to-end LLM?
**Answer:**  
A monolithic LLM cannot reliably perform vision inference on raw pixels, is prone to hallucinating unregistered chemical dosages, and cannot maintain deterministic safety gates. In AgriMind, LangGraph orchestrates specialized agents: the Investigation Agent binds physical leaf evidence, the Risk Assessment Agent enforces quantitative agronomic rules (e.g. weather-based Late Blight escalation), the Decision Planning Agent organizes interventions into a strict 4-tier IPM hierarchy, and the Critic Agent audits all recommendations against accredited university literature before anything reaches the farmer.

### Q2: Why is the computer vision model limited to 3 tomato diseases?
**Answer:**  
In agricultural pathology, diagnostic precision is paramount. Generalist models claiming to identify dozens of diseases often exhibit high misclassification rates in the field. Bounding the problem space to the three most destructive tomato foliar diseases in North India (`Bacterial_spot`, `Early_blight`, and `Late_blight`) allowed rigorous training, high validation accuracy (98.41%), and exhaustive domain-shift evaluation against the PlantDoc in-the-wild benchmark.

### Q3: How does AgriMind handle the computer vision "domain gap"?
**Answer:**  
Our Phase 1 (Grad-CAM) and Phase 2 (Background Masking) research revealed that standard CNN backbones trained on laboratory leaves activate strongly on outdoor soil and sky clutter. While masking background pixels improved out-of-domain PlantDoc accuracy from 39.29% to 50.00%, our audit proved that 7 of 9 Bacterial Spot samples remained difficult due to fine lesion morphology and suspected label noise. We transparently documented these findings, integrated farmer visual context forms, and added preliminary AI disclaimers to prevent false confidence in field conditions.

### Q4: How is chemical safety enforced in the recommendations?
**Answer:**  
1. All chemical recommendations are preceded by a mandatory pesticide safety disclaimer emphasizing EPA/state label adherence, Personal Protective Equipment (PPE), Restricted-Entry Intervals (REI), and Pre-Harvest Intervals (PHI).
2. Curative kickback fungicides (such as Cymoxanil) are strictly restricted to 24–48 hours post-infection and must be tank-mixed with protectants to manage FRAC resistance.
3. Preventative anti-sporulants (Mandipropamid) are explicitly barred from curative kickback claims.
4. If the Critic Agent detects diagnostic conflict or low identification confidence, automated chemical recommendations are withheld entirely.

### Q5: How does the application function in low-connectivity rural environments?
**Answer:**  
1. All previously recorded cases and multi-turn chat conversations are persisted locally in SQLite databases (`data/cases.db` on server and `agrimind_chat.db` on device) with cascading deletes.
2. Full multi-page A4 crop-health PDF advisory reports are generated locally using Android’s native `PdfDocument` engine without requiring internet access.
3. The server backend is designed to run on a local edge server, farm laptop, or micro-PC accessible over local Wi-Fi without active internet.

---

## 7. Conclusion & Project Sign-Off

The **AgriMind** minor project (`COM71116-21`) has achieved complete full-stack implementation, meeting all approved functional and academic requirements:
- **Vision Inference:** Verified 3-class ResNet-50 classifier.
- **Reasoning Core:** Multi-agent LangGraph workflow with dynamic weather escalation and 4-tier IPM planning.
- **RAG Subsystem:** 63-chunk ChromaDB knowledge base grounded in university extension publications.
- **Android Client:** Native Kotlin/Compose app with bilingual voice assistant, offline SQLite caching, and native PDF generation.
- **Empirical Rigor:** 94 of 94 automated tests passed (100% pass rate) with zero release-blocking defects.

The system is fully documented, packaged, verified on real hardware and emulators, and ready for academic viva voce evaluation.

