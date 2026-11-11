# AgriMind — Stage B.5: Android Conversational AI Integration Milestone Report

## 1. Executive Summary

This milestone report documents the complete design, implementation, and empirical verification of **Stage B.5: Android Conversational AI Integration** for the AgriMind tomato disease decision support platform.

Building upon the completed foundation (Stage B.1: Native Architecture), image diagnosis (Stage B.2), case details, reassessment & history (Stage B.3), and PDF reporting (Stage B.4), Stage B.5 introduces interactive, evidence-grounded agronomic decision support within the native Android client.

All objectives have been delivered within strict preservation boundaries:
1. **Full-Stack Conversational Flow**: Connected the native Android client to the FastAPI `POST /chat` endpoint. Supported both general agronomic inquiries and case-anchored Q&A focusing specifically on the pathogen diagnosed in saved cases.
2. **Wire Contract Fidelity & Strict Isolation**: Built dedicated Kotlin data models (`ChatRequest`, `ChatMessageItem`, `ChatResponse`, `ChatCitationItem`) perfectly mirroring the backend Pydantic models. Client-only UI states (`UiChatMessage`, `ChatUiState`, formatted timestamps) are strictly isolated from the wire payload to comply with backend `extra="forbid"` schema validation.
3. **Evidence-Grounded UI & Clickable Citations**: Implemented a modern Material 3 conversational interface (`ChatScreen.kt`) featuring user/assistant chat bubbles, suggested prompt chips, evidence-gating warning banners, and expandable university extension citations (Cornell, UF/IFAS, Purdue, UC IPM) with direct browser viewing via `Intent.ACTION_VIEW`.
4. **Seamless Case Anchoring & Navigation**: Added dedicated entry points to conversational support:
   - A global **Assistant** tab in the main bottom navigation bar for general agronomic questions.
   - An **"Ask AgriMind Assistant About This Case"** action and app bar button in `CaseDetailScreen.kt`, automatically pre-populating the active case ID and scoping RAG retrieval to the diagnosed pathogen.
5. **Preserved Boundaries & Verified Stability**: No changes were made to the ResNet-50 vision model, ChromaDB vector collection, or SQLite database. All Stage B.1 through B.4 capabilities (Diagnosis, Reassessment, History, PDF generation and sharing) remain 100% operational. The Android debug APK compiled with zero errors (`BUILD SUCCESSFUL in 1m 12s`, 17.5 MB).

---

## 2. API Contract & Communication Layer

### 2.1 Backend Contract (`POST /chat`)
The FastAPI conversational endpoint is hosted at `http://10.0.2.2:8000/chat` (Android emulator loopback) / `http://127.0.0.1:8000/chat` (local backend).

**Request Schema (`ChatRequest`):**
```json
{
  "query": "What fungicide should I use for late blight?",
  "case_id": "CASE-7DC903FC",
  "disease_target": "Tomato___Late_blight",
  "conversation_history": [
    {
      "role": "user",
      "content": "Can late blight infect green tomato fruit?"
    },
    {
      "role": "assistant",
      "content": "Yes, Phytophthora infestans directly infects tomato fruit causing dark, greasy lesions."
    }
  ]
}
```

**Response Schema (`ChatResponse`):**
```json
{
  "reply": "For late blight (Phytophthora infestans), fixed copper or chlorothalonil should be applied as protectants prior to disease establishment...",
  "case_id": "CASE-7DC903FC",
  "disease_target": "Tomato___Late_blight",
  "citations": [
    {
      "chunk_id": "chunk_lb_04",
      "title": "Tomato Late Blight Management",
      "source_url": "https://extension.psu.edu/tomato-late-blight-management",
      "disease_target": "Tomato___Late_blight",
      "section_type": "chemical_management"
    }
  ],
  "has_sufficient_evidence": true,
  "used_fallback": false,
  "generation_method": "extractive_grounded"
}
```

### 2.2 Wire Schema Enforcement
- In `src/api/schemas.py`, the backend configures `model_config = ConfigDict(extra="forbid")` on `ChatMessage`.
- Sending client metadata (such as `timestamp`, `id`, or `citations`) inside `conversation_history` results in HTTP 422 Unprocessable Entity.
- In `ChatModels.kt`, the wire transfer model `ChatMessageItem` contains strictly `role: String` and `content: String`. Client metadata is encapsulated exclusively in `UiChatMessage`.

---

## 3. Architecture & Implementation

### 3.1 Android Conversational Layer Components

| Component | File Path | Architectural Responsibility |
| :--- | :--- | :--- |
| **Data Models** | `android/app/.../data/model/ChatModels.kt` | Kotlin data classes mapping wire JSON schemas and UI states. |
| **API Service** | `android/app/.../data/api/AgriMindApiService.kt` | Retrofit interface declaration for `POST /chat`. |
| **ViewModel** | `android/app/.../ui/viewmodel/ChatViewModel.kt` | MVVM state management, coroutine dispatching, error mapping, bounded history (last 10 items). |
| **UI Screen** | `android/app/.../ui/screens/ChatScreen.kt` | Jetpack Compose Material 3 UI with chat bubbles, quick chips, citations, and disclaimer banners. |
| **Case Detail Hook**| `android/app/.../ui/screens/CaseDetailScreen.kt` | "AgriMind Decision Assistant" card and top app bar action linking case ID to chat. |
| **Main Navigation** | `android/app/.../MainActivity.kt` | Added Assistant tab to bottom navigation (index 2) and modal overlay navigation from case details. |

### 3.2 State Management & Error Handling
`ChatViewModel` exposes two reactive `StateFlow`s:
- `messages: StateFlow<List<UiChatMessage>>`: Sequential chat thread containing user prompts and assistant replies with citations.
- `uiState: StateFlow<ChatUiState>`:
  - `ChatUiState.Idle`: Ready for user input.
  - `ChatUiState.Loading`: Displaying typing indicator / progress spinner.
  - `ChatUiState.Error(message)`: Surfacing actionable error messages with a "Retry" button.

**Handled Failure Scenarios:**
- **HTTP 404 (Case Not Found)**: Notifies the user that the referenced case ID does not exist in backend case storage.
- **HTTP 422 (Validation Error)**: Handles empty queries or malformed payloads gracefully without crashing.
- **HTTP 500 / Network Timeout**: Catches `SocketTimeoutException` and `IOException` (e.g. backend offline), displaying clear recovery instructions.
- **Insufficient Evidence / Evidence Gating**: When `has_sufficient_evidence == false`, the assistant displays a warning badge indicating that recommendations are based on conservative extension baselines due to limited literature matches.

---

## 4. Verification & Build Results

### 4.1 Android Compilation & Packaging
- **Gradle Command**: `gradlew.bat assembleDebug`
- **Kotlin Compiler**: Version 1.9.22
- **Compilation Output**:
  ```
  BUILD SUCCESSFUL in 1m 12s
  35 actionable tasks: 6 executed, 29 up-to-date
  ```
- **Generated Artifact**: `android/app/build/outputs/apk/debug/app-debug.apk`
- **Artifact Size**: 17,484,420 bytes (~17.5 MB)
- **Compilation Errors**: 0

### 4.2 Backend Unit & Integration Tests
Executed the API test suite in the WSL Ubuntu environment:
```bash
wsl -d Ubuntu bash -c "source /home/jaskirat/agrimind-rag-env/bin/activate && cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && python -m unittest tests.test_api"
```
- **Test Count**: 18 tests
  - 8 existing diagnosis & reassessment tests
  - 9 mocked `/chat` tests (valid query, case rehydration, disease scoping, history bounding, error validation)
  - 1 live ChromaDB retrieval test (`test_real_chat_extractive_generation`)
- **Result**: `Ran 18 tests in 23.4s — OK`

---

## 5. Important Backend Contract Limitations

1. **Single-Turn Vector Retrieval**:
   - The backend validates `conversation_history` (bounded to max 10 messages) to maintain API contract compliance.
   - However, the RAG retriever executes similarity search directly on `request.query`.
   - The backend does **not** currently implement LLM-based query contextualization, coreference resolution (e.g. resolving "Can it infect green fruit?" into "Can Late Blight infect green tomato fruit?"), or multi-turn query rewriting.
   - The Android client preserves complete visual history for the user, but queries should be reasonably self-contained for optimal retrieval precision.
2. **Offline Extractive Fallback**:
   - When no external Gemini API key is configured, the backend automatically uses `extractive_grounded` generation. It synthesizes answers directly from retrieved ChromaDB chunks without calling external cloud LLMs.
3. **Case Rehydration**:
   - When a `case_id` is supplied, the backend fetches the stored case from SQLite, looks up its `primary_diagnosis`, and filters ChromaDB search to that pathogen, preventing cross-disease contamination of recommendations.

---

## 6. Manual Emulator Acceptance Testing Guide

### Prerequisites
1. Start the FastAPI backend in WSL (if not already running):
   ```bash
   wsl -d Ubuntu bash -c "source /home/jaskirat/agrimind-rag-env/bin/activate && cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project && python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000"
   ```
2. Verify backend health:
   ```bash
   curl http://127.0.0.1:8000/health
   # Expected response: {"status":"healthy","model_loaded":true,"vectorstore_loaded":true,...}
   ```
3. Start the Android emulator:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_37.0
   ```
4. Install the freshly built APK:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r android\app\build\outputs\apk\debug\app-debug.apk
   ```
5. Launch the application:
   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" shell am start -n com.agrimind.app/.MainActivity
   ```

### Test Case 1: General Agronomic Inquiry via Assistant Tab
1. Tap the **Assistant** tab in the bottom navigation bar.
2. Confirm the empty state appears with suggested prompt chips:
   - *"How to control Early Blight?"*
   - *"Late Blight fungicide recommendations"*
   - *"Bacterial Spot copper spray guidelines"*
3. Tap one of the suggested chips or type:
   `"What cultural practices help prevent Late Blight?"`
4. Tap **Send** (or press keyboard Send action).
5. Verify:
   - User message bubble appears on the right.
   - Loading indicator appears.
   - Assistant reply appears on the left with grounded recommendations.
   - Citations section expands showing university extension references (e.g. Penn State / Cornell).
   - Tapping **"View Extension Publication"** opens the URL in the Android browser.

### Test Case 2: Case-Anchored Decision Support
1. Go to the **History** tab and open any saved case (e.g. `CASE-7DC903FC` - Late Blight).
2. Scroll to the **"AgriMind Decision Assistant"** card at the bottom (or tap the Forum/Chat icon in the top app bar).
3. Tap **"Ask AgriMind Assistant About This Case"**.
4. Verify:
   - The chat screen opens with a banner showing: `Case: CASE-7DC903FC • Tomato___Late_blight`.
   - A contextual prompt is suggested: *"What emergency actions should I take for this case?"*
5. Send a question:
   `"Can this spread to my potato crop?"`
6. Verify:
   - The assistant answers with Late Blight specific cross-infection guidance grounded in agricultural extension literature.
7. Tap the back arrow:
   - Returns seamlessly to the Case Details screen with all case data intact.

### Test Case 3: Offline / Recovery Resilience
1. In the emulator settings or notification shade, enable Airplane Mode (or stop the backend).
2. Send any inquiry.
3. Verify:
   - An error card appears: `"Unable to connect to AgriMind server"`.
   - A **Retry** button is displayed.
   - Existing messages in the conversation thread remain visible and are not lost.

