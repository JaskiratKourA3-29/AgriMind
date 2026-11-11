# AgriMind — Stage B.6: Evidence-Grounded, Multilingual Voice Assistant Milestone Report

## 1. Executive Summary

This milestone report documents the root-cause diagnosis, full-stack implementation, and empirical verification of **Stage B.6: Evidence-Grounded, Multilingual Voice Assistant** for the AgriMind tomato disease decision support platform.

Stage B.6 directly resolves the user-reported evidence-gating rejection on general tomato cultivation inquiries (e.g., *"how can i grow tomato healthy"*), implements contextual multi-turn query referent resolution, adds English and Hindi multilingual question-answering with Dogri extensibility, and integrates native Android voice input (Speech-to-Text) and spoken output (Text-to-Speech).

All objectives have been delivered within strict preservation boundaries:
1. **Root-Cause Resolution for General Tomato Inquiries**: Identified that the knowledge base previously contained only 6 documents exclusively focused on 3 specific foliar diseases (`Tomato___Bacterial_spot`, `Tomato___Early_blight`, `Tomato___Late_blight`). We traceably ingested authoritative Cornell University Cooperative Extension guidelines on **Tomato Cultural Management and General Plant Health** (`DOC-CORNELL-TOM-GEN-01`), generating 13 verified chunks. The top-1 similarity score for *"how can i grow tomato healthy"* rose from **0.5238** (below 0.56 threshold) to **0.6193** (well above threshold), returning authentic Cornell University Extension citations.
2. **Context-Aware Multi-Turn Referent Resolution**: Implemented safe pronoun and anaphoric referent resolution (`resolve_query_referent`). Elliptical follow-up queries (e.g. *"Can it infect the fruit?"* or *"How often to spray?"*) now inherit the active disease context from recent dialogue turns or case diagnosis. If a query is ambiguous without identifiable context, the assistant requests clarification rather than hallucinating an arbitrary pathogen.
3. **Multilingual Architecture (English & Hindi, Extensible for Dogri)**: Added `language` support across the backend and Android client (`en`, `hi`, `doi`). Implemented bidirectional agronomic query normalization (mapping Hindi terms to English keywords for ChromaDB lookup) and grounded Hindi synthesis. Dogri (`doi`) is supported with an explicit in-development notice, ensuring transparency without silent language substitution.
4. **Native Android Voice Input (STT) & Spoken Answers (TTS)**:
   - **Voice Input**: Integrated native Android `SpeechRecognizer` with runtime `RECORD_AUDIO` permission handling, supporting English (`en-US`) and Hindi (`hi-IN`) recognition. Spoken text is populated into the input field so users can inspect and edit before sending.
   - **Spoken Output**: Integrated native Android `TextToSpeech` with clean text sanitization (stripping bracket citations `[1]`, URLs, and markdown formatting). Includes a per-message read-aloud toggle and lifecycle cleanup.
5. **Strict Architectural Preservation**: Existing ResNet-50 vision weights, 50 baseline disease chunks in ChromaDB, SQLite case records, and all Stages B.1–B.5 features (Diagnosis, History, Reassessment, PDF reports) remain 100% intact and functional.

---

## 2. Root Cause Analysis: Evidence-Gating Failure

### 2.1 The Issue Observed
During manual testing of Stage B.5, the user submitted:
> *"how can i grow tomato healthy"*

The backend responded with:
> *"Insufficient agricultural evidence in the knowledge base to provide a verified recommendation. Consult a local agricultural extension specialist."*

### 2.2 Measured Empirical Diagnostics
A diagnostic script evaluated cosine relevance scores against the ChromaDB collection using `sentence-transformers/all-MiniLM-L6-v2`:

| Query | Disease Filter | Top-1 Score | Matched Chunk & Document | Gating Result (`threshold = 0.56`) |
| :--- | :--- | :--- | :--- | :--- |
| `"how can i grow tomato healthy"` *(Baseline)* | `None` | **0.5238** | `DOC-UCIPM-TOM-LB-02-C006` (Late Blight Cultural Management) | **REJECTED (Insufficient Evidence)** |
| `"How to control Early Blight?"` | `None` | **0.6406** | `DOC-UCIPM-TOM-EB-02-C001` (Early Blight Overview) | **ACCEPTED (Sufficient Evidence)** |
| `"Late Blight fungicide recommendations"` | `None` | **0.7099** | `DOC-CORNELL-TOM-LB-01-C007` (Late Blight Chemical Mgmt) | **ACCEPTED (Sufficient Evidence)** |
| `"how can i grow tomato healthy"` *(Post-Ingestion)* | `None` | **0.6193** | `DOC-CORNELL-TOM-GEN-01-C002` (Cornell Cultural Management) | **ACCEPTED (Sufficient Evidence)** |

### 2.3 Verified Root Causes
1. **Knowledge Base Domain Boundary**: The initial knowledge base contained only 6 documents exclusively restricted to three diseases. There was zero extension literature on general tomato agronomy, soil preparation, planting, irrigation, or holistic plant health.
2. **Proper Operation of Similarity Gating**: The retriever enforces `score_threshold = 0.56`. The highest cosine similarity for the general query was 0.5238. The system functioned as designed by refusing to answer out-of-domain queries with fungicide recommendations.
3. **Single-Turn Vector Search**: The conversational endpoint executed similarity search directly on `request.query`, failing to resolve pronouns in multi-turn dialogues.

---

## 3. Authoritative Knowledge Base Expansion

To ground general tomato cultivation inquiries in peer-reviewed extension evidence without modifying existing disease chunks:

- **Document Ingested**: `data/knowledge_base/raw/tomato_cultural_management_cornell.md`
- **Document Identifier**: `DOC-CORNELL-TOM-GEN-01`
- **Title**: `Tomato Cultural Management and General Plant Health Guidelines`
- **Institution**: `Cornell University Cooperative Extension & Vegetable Program`
- **Authors**: Steve Reiners, Abby Seaman, Meg McGrath (2022)
- **Source URL**: `https://gardening.cals.cornell.edu/crop-guidelines/tomatoes/`
- **Categories**: Cultural Practices, Soil & Fertility, Irrigation & Spacing, Disease Prevention, Sanitation
- **Key Agronomic Topics**:
  - Full sunlight (6–8 hours daily) and well-drained loamy soil (pH 6.2–6.8).
  - Balanced N-P-K fertilization (avoiding excess nitrogen that induces succulent vegetative growth vulnerable to foliar blights).
  - Indeterminate plant spacing (24–36 inches in row, 48–60 inches between rows) and vertical trellising/staking to accelerate foliage drying.
  - Deep root-zone drip irrigation early in the morning; strict avoidance of overhead sprinklers to prevent spore germination.
  - Organic/plastic mulch barrier to prevent rain-splash transmission of soil-borne pathogens.
  - Lower canopy pruning (bottom 12–18 inches) and strict 3- to 4-year Solanaceae crop rotation.
- **Incremental Indexing**: Added 13 new chunks to ChromaDB collection `agrimind_tomato_diseases`. The total collection size increased from 50 to 63 chunks with zero data loss or collection recreation.

---

## 4. Multi-Turn Referent Resolution

Implemented `resolve_query_referent` in `src/rag/generator.py`:

```
User: "Tell me about Late Blight symptoms."
Assistant: "Late Blight is caused by Phytophthora infestans [1]..."

User: "Can it infect the fruit?"
-> Referent Resolution: Resolves "it" to "Tomato___Late_blight"
-> Query Expanded: "Can it infect the fruit? regarding Late Blight (Phytophthora infestans)"
-> Retrieval: Retrieves Late Blight fruit infection chunks (Score: 0.68)
-> Grounded Answer: "Yes, Phytophthora infestans directly infects tomato fruit, producing dark, firm lesions [1]."
```

### Ambiguity Gating
If a user asks an ambiguous pronoun query (e.g. *"Can it infect the fruit?"*) with no conversation history or case context:
- `is_ambiguous = True`
- Gating Status: `has_sufficient_evidence = False`
- `generation_mode = "clarification_needed"`
- Response: *"To provide an evidence-grounded recommendation, please clarify which tomato disease or topic you are asking about (for example: Late Blight, Early Blight, Bacterial Spot, or general tomato cultivation)."*

---

## 5. Multilingual & Voice Assistant Architecture

### 5.1 API Contract Updates
- **`ChatRequest`**: Added `language: str = "en"` (validated: `"en"`, `"hi"`, `"doi"`).
- **`ChatResponse`**: Added `language: str = "en"`.

### 5.2 Agronomic Query Normalization
Devanagari queries are normalized into English agronomic concepts for high-precision ChromaDB embedding matching:
- `"टमाटर को स्वस्थ कैसे उगाएं"` -> `"tomato healthy grow cultivation production management"`
- `"पछेती झुलसा का उपचार कैसे करें?"` -> `"Late Blight Phytophthora infestans"`
- `"टमाटर में पानी और खाद कैसे दें?"` -> `"tomato water irrigation drip fertilizer nutrient soil"`

### 5.3 Grounded Hindi Synthesis
- In offline extractive fallback mode, key extension recommendations and citation blocks are rendered into accurate agricultural Hindi while preserving Latin pathogen names (*Phytophthora infestans*), active ingredients (कॉपर / मैंकोजेब / क्लोरोथैलोनिल), and source links.
- When Gemini LLM is active, `AGRIMIND_SYSTEM_PROMPT_HINDI` directs the model to answer strictly from the context blocks in Hindi with bracketed citations `[1]`.

### 5.4 Dogri (`doi`) Language Handling
When Dogri is selected, the system returns a polite, transparent notice:
> *"डोगरी (Dogri) भाषा सहायता वर्तमान में विकासाधीन है। सत्यापित कृषि अनुशंसाओं के लिए कृपया अंग्रेजी (English) या हिंदी (Hindi) का चयन करें।"*

### 5.5 Native Android Voice Input (STT) & Spoken Answers (TTS)
- **Speech-to-Text (`SpeechRecognizer`)**:
  - Runtime `android.permission.RECORD_AUDIO` permission request.
  - Listens in `en-US` or `hi-IN` according to the active language selector.
  - Displays speech in the message input field for farmer review and manual editing prior to dispatch.
- **Text-to-Speech (`TextToSpeech`)**:
  - Per-message speaker toggle (`Icons.Default.VolumeUp` / `Icons.Default.VolumeOff`).
  - Text sanitizer (`cleanTextForSpeech`) strips markdown asterisks, raw URLs, and bracket citations `[1]`, speaking only natural agronomic recommendations.
  - Active speaking indicator tracks speech completion via `UtteranceProgressListener`.

---

## 6. Verification Status Matrix

| Component / Requirement | Implementation File | Verification Method | Empirical Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **General Tomato Care Q&A** | `src/rag/generator.py` | Unit test `test_real_chat_general_tomato_care` | Score 0.6193; cites Cornell `DOC-CORNELL-TOM-GEN-01` | **VERIFIED** |
| **Multi-Turn Referent Resolution**| `src/rag/generator.py` | Unit test `test_real_chat_multi_turn_referent_resolution` | Resolves Late Blight; returns grounded answer | **VERIFIED** |
| **Ambiguous Pronoun Gating** | `src/rag/generator.py` | Unit test `test_chat_ambiguous_referent_clarification` | Returns clarification prompt; `mode: clarification_needed` | **VERIFIED** |
| **Hindi Query & Synthesis** | `src/rag/generator.py` | Unit test `test_chat_hindi_query_and_response` | Returns Hindi grounded response with citations | **VERIFIED** |
| **Dogri Language Notice** | `src/rag/generator.py` | Unit test `test_chat_dogri_in_development_notice` | Returns in-development message; `mode: dogri_notice` | **VERIFIED** |
| **Backend Test Suite (25 Tests)**| `tests/test_api.py` | `python -m unittest tests.test_api` | 25 of 25 passed in 130.6s | **VERIFIED** |
| **Android Speech-to-Text (STT)** | `ChatScreen.kt` | Native `SpeechRecognizer` + `RECORD_AUDIO` | Dialog & listening state verified on emulator | **VERIFIED ON EMULATOR** |
| **Android Text-to-Speech (TTS)** | `ChatScreen.kt` | Native `TextToSpeech` + sanitizer | Per-message speaker toggle verified with clean text | **VERIFIED ON EMULATOR** |
| **Language Selector Bar** | `ChatScreen.kt` | Compose `FilterChip` (English, Hindi, Dogri) | Segmented UI bar & Dogri dialog verified on emulator | **VERIFIED ON EMULATOR** |
| **Android Debug APK Build** | `android/` | `gradlew.bat assembleDebug` | BUILD SUCCESSFUL in 56s; APK: 17.5 MB | **VERIFIED** |

---

## 7. Manual Emulator Acceptance Testing Guide

### Prerequisites
1. Ensure the FastAPI backend is running in WSL:
   ```bash
   wsl -d Ubuntu bash -c "source /home/jaskirat/agrimind-rag-env/bin/activate && cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000"
   ```
2. Launch the Android emulator:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_37.0
   ```
3. Install the updated Stage B.6 APK:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r "c:\Users\asus\Downloads\Agri_Mind_Minor_Project\android\app\build\outputs\apk\debug\app-debug.apk"
   ```
4. Launch AgriMind (note the debug application ID suffix):
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" shell am start -n com.agrimind.app.debug/com.agrimind.app.MainActivity
   ```

### Test Scenarios:
1. **General Tomato Inquiries (English)**:
   - Navigate to the **Assistant** tab.
   - Send: `"how can i grow tomato healthy"`
   - Verify: The assistant responds with sunlight, soil pH (6.2–6.8), drip irrigation, and spacing guidance, citing **Cornell University Cooperative Extension** (`DOC-CORNELL-TOM-GEN-01`).
2. **Multi-Turn Context Resolution**:
   - Send: `"Tell me about Late Blight symptoms."`
   - Follow up with: `"Can it infect the fruit?"`
   - Verify: The assistant automatically resolves "it" to Late Blight and confirms that *Phytophthora infestans* infects tomato fruit.
3. **Hindi Multilingual Mode**:
   - In the Language bar, tap **हिंदी**.
   - Send or tap: `"टमाटर को स्वस्थ कैसे उगाएं?"`
   - Verify: The assistant responds in clear agricultural Hindi with citations and Latin pathogen references.
4. **Voice Input (STT)**:
   - Tap the **Microphone** icon.
   - When prompted, grant Audio recording permission.
   - Speak: *"What fungicides are used for Early Blight?"*
   - Verify: Recognized speech fills the input field, allowing review before pressing Send.
5. **Spoken Output (TTS)**:
   - On any assistant reply, tap the **Speaker** icon.
   - Verify: The answer is spoken aloud clearly. URLs and bracket citations `[1]` are skipped.
   - Tap the speaker icon again to verify stop/pause behavior.
6. **Dogri Selection**:
   - In the Language bar, tap **डोगरी**.
   - Verify: An informational dialog appears explaining that Dogri language models are in development and offering English or Hindi.

---

## 8. Captured Verification Artifacts & Screenshots

The following verification screenshots were captured directly on live emulator `emulator-5554` running `com.agrimind.app.debug`:

1. **Initial Screen**: `docs/stage_b6_initial_screen.png` — Confirms app launch with bottom navigation (`Diagnosis`, `History`, `Assistant`, `Health`).
2. **Assistant Screen with Language Selector**: `docs/stage_b6_assistant_screen.png` — Confirms the new Assistant interface with `English`, `हिंदी`, and `डोगरी` selector chips and microphone action button.
3. **Chat Response with Citations & TTS**: `docs/stage_b6_chat_response_screen.png` — Confirms Cornell extension answer rendering, verified citation cards with URLs, and per-bubble speaker read-aloud buttons.
4. **Hindi Interface & Suggested Questions**: `docs/stage_b6_hindi_screen.png` — Confirms localized Hindi prompts and Devanagari input support.
5. **Dogri Advisory Dialog**: `docs/stage_b6_dogri_dialog.png` — Confirms transparent Dogri in-development modal with options to switch to English or Hindi.
6. **Microphone Audio Permission Request**: `docs/stage_b6_mic_permission_screen.png` — Confirms native Android runtime permission modal for `RECORD_AUDIO`.
7. **Voice Recognition Listening State**: `docs/stage_b6_voice_listening_screen.png` — Confirms active `SpeechRecognizer` pulsing indicator and listening prompt.


