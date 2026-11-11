# AgriMind Stage B.7 — Hindi Response Consistency and Persistent Chat History Milestone Report

**Date:** November 2, 2026  
**Status:** Completed & Fully Verified  
**Target Architecture:** Native Android (Kotlin, Jetpack Compose, SQLite, Material 3) & FastAPI (Python 3.13, ChromaDB RAG, LangGraph)

---

## 1. Executive Summary

Stage B.7 addresses two critical user experience and architectural requirements for the AgriMind tomato disease diagnosis and decision support system:
1. **Hindi Response Consistency:** Diagnosing and resolving the issue where Hindi questions received English answers, ensuring that Hindi queries (typed or voiced) produce fluent, agricultural responses in Devanagari script grounded in university extension research, while English queries continue returning English responses. Automatic script detection ensures Devanagari input is recognized regardless of default selector states, and Android Text-to-Speech (TTS) switches dynamically to `Locale("hi", "IN")` while stripping bibliography URLs from spoken audio and providing actionable guidance if voice packs are missing.
2. **Persistent Chat History:** Implementing an on-device persistent conversation and message storage system using native Android SQLite (`android.database.sqlite.SQLiteOpenHelper`). The system persists conversations and messages with full relational integrity (`ON DELETE CASCADE`), derives conversation titles automatically from the first user query, and surfaces a Material 3 `ModalBottomSheet` allowing farmers to resume past threads, initiate fresh consultations, and delete conversations with permanent confirmation.

All 27 Android unit tests (`testDebugUnitTest`) and 25 backend regression tests (`test_api.py`) passed with zero regressions to the ResNet-50 classifier, 63 ChromaDB knowledge chunks, or Stages B.1–B.5 features.

---

## 2. Root Cause Analysis

### 2.1 Why Hindi Questions Received English Answers
Thorough code inspection of `src/rag/generator.py` and `ChatViewModel.kt` revealed three compounding root causes:

1. **Strict Gemini Key Format Check & Model Deprecation:**
   - In `src/rag/generator.py`, the LLM path contained `if not key or not key.startswith("AIzaSy"): return None`. Modern Google Gemini API keys frequently start with alternate prefixes (such as `AQ.Ab8RN6L...`). Furthermore, `gemini-1.5-flash` was deprecated by the upstream API. Because of this, the generator fell back to `synthesize_extractive_answer()`.
2. **Extractive Synthesis Translation Limitations & Markdown Heading Capture:**
   - In `synthesize_extractive_answer()`, `extract_key_agronomic_points()` was capturing raw Markdown headings (e.g., `# Tomato Cultural Management and General Plant Health Guidelines`).
   - The fallback translator `translate_agronomic_sentence_to_hindi()` contained only 15 basic regex patterns. Complex extension sentences regarding soil preparation, irrigation, spacing, trellising, fungicides (e.g., *Chlorothalonil*, *Mancozeb*, *Cymoxanil*), and bactericides were not matched and remained in English.
   - Document titles and extension institutions were rendered in verbatim English without Hindi localization.
3. **Android Client-Side Language Defaulting:**
   - In `ChatViewModel.kt`, `selectedLanguage` defaulted to `"en"`. When a user spoke or typed in Hindi without explicitly tapping the Hindi radio button, `ChatRequest.language = "en"` was dispatched to the backend. The backend strictly honored the requested language `"en"`, synthesizing an English answer.

### 2.2 Database & Storage Architecture
- Prior to Stage B.7, `LocalCaseRepository` stored `LocalCaseRecord` JSON in SharedPreferences via Gson; no SQLite or Room database existed on the Android client for chat.
- SQLite was previously used only on the backend in `src/api/case_store.py`.
- Using native Android `SQLiteOpenHelper` provided full relational ACID persistence without requiring external KSP plugins, Room compiler dependencies, or schema migration overhead.

---

## 3. Technical Implementation

### 3.1 Backend: High-Fidelity Agronomic Hindi Synthesis (`src/rag/generator.py`)
1. **Markdown Header Stripping:**
   - Updated `extract_key_agronomic_points()` to ignore lines starting with `#`, `##`, `###`, `---`, or short title strings, selecting only genuine recommendation sentences.
2. **Semantic Pattern Dictionary (`AGRONOMIC_SENTENCE_PATTERNS_HI`):**
   - Expanded `translate_agronomic_sentence_to_hindi()` with 20+ specialized agricultural patterns covering soil preparation, direct sunlight, drip irrigation, plant spacing, trellising, mulching, crop rotation, nitrogen balance, and disease management for Early Blight (*Alternaria linariae*), Late Blight (*Phytophthora infestans*), and Bacterial Spot (*Xanthomonas*).
   - Preserves Latin pathogen names, active ingredients, and measurements in parentheses.
3. **Institutional and Document Title Localization:**
   - Added `DOC_TITLE_HINDI_MAP` and `INSTITUTION_HINDI_MAP` to translate extension titles (e.g., Cornell University Cooperative Extension $\rightarrow$ कॉर्नेल यूनिवर्सिटी विस्तार सेवा, Purdue University Extension $\rightarrow$ पर्ड्यू यूनिवर्सिटी विस्तार सेवा).
4. **Devanagari Script Detection:**
   - Added automatic detection in `generate_answer()`: `re.search(r"[\u0900-\u097F]", clean_query)`. If Devanagari script is present, language is resolved to Hindi (`"hi"`), while preserving explicit Dogri (`"doi"`) development status notices.

### 3.2 Android SQLite Database Architecture (`com.agrimind.app.data.local`)
1. **Database Helper (`ChatDatabaseHelper.kt`):**
   - Implements `SQLiteOpenHelper` managing `agrimind_chat.db` (Schema version 1).
   - Tables:
     - `conversations`: `id TEXT PRIMARY KEY`, `title TEXT NOT NULL`, `created_at INTEGER NOT NULL`, `updated_at INTEGER NOT NULL`, `language TEXT NOT NULL`, `case_id TEXT`
     - `chat_messages`: `id TEXT PRIMARY KEY`, `conversation_id TEXT NOT NULL`, `role TEXT NOT NULL`, `content TEXT NOT NULL`, `citations_json TEXT`, `has_sufficient_evidence INTEGER NOT NULL`, `generation_mode TEXT NOT NULL`, `disease_target TEXT`, `language TEXT NOT NULL`, `is_error INTEGER NOT NULL`, `timestamp INTEGER NOT NULL`
   - Constraints & Indices:
     - Foreign key constraint: `FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE`
     - Indices: `idx_messages_convo_time (conversation_id, timestamp ASC)` and `idx_convo_updated (updated_at DESC)`
     - PRAGMA `foreign_keys = ON` enabled in `onConfigure()`.

2. **Repository Architecture (`IChatRepository.kt`, `ChatRepository.kt`, `InMemoryChatRepository.kt`):**
   - Interface `IChatRepository` exposes `conversationsFlow: StateFlow<List<ConversationEntity>>` and suspend methods: `getMessagesForConversation()`, `createConversation()`, `saveMessage()`, `deleteConversation()`.
   - `ChatRepository` executes SQLite operations asynchronously on `Dispatchers.IO`.
   - `InMemoryChatRepository` provides a lightweight, thread-safe in-memory implementation for headless JVM unit tests.

### 3.3 Android ViewModel Architecture (`ChatViewModel.kt`)
1. **Constructor Overloading (`@JvmOverloads`):**
   - Annotated primary constructor with `@JvmOverloads` to enable Android's `ViewModelProvider$AndroidViewModelFactory` to reflectively instantiate `ChatViewModel(application)` on the main thread.
2. **Automatic Script Detection (`detectLanguage()`):**
   - Detects Devanagari Unicode range `\u0900..\u097F`. Automatically switches `selectedLanguage` to `"hi"` upon receiving Devanagari input.
3. **Conversation State Management:**
   - Exposes `conversations: StateFlow<List<ConversationEntity>>` and `currentConversationId: StateFlow<String?>`.
   - `loadConversation(convoId)`: Loads messages from SQLite and switches active conversation.
   - `startNewConversation()`: Clears active messages and draft without deleting past threads.
   - `deleteConversation(convoId)`: Permanently deletes thread with database cascade.
   - `sendMessage()`: Persists user message immediately, dispatches POST `/chat`, and persists assistant response upon 200 OK. Temporary errors and validation failures are not persisted as valid assistant responses.

### 3.4 Android UI & Text-to-Speech (`ChatScreen.kt`)
1. **Material 3 Chat History Sheet (`ChatHistorySheetContent`):**
   - Accessible via TopAppBar history button (`Icons.Default.History`).
   - Displays all saved conversations with titles, formatted timestamps (`MMM d, h:mm a`), language badges (`हिन्दी` / `EN`), and delete buttons.
   - "+ New Chat" button to quickly reset active conversation.
2. **Delete Confirmation Dialog:**
   - Material 3 `AlertDialog` confirming permanent deletion before invoking `deleteConversation()`.
3. **Text-to-Speech Localized Playback:**
   - `cleanTextForSpeech()`: Truncates `### संदर्भित विस्तार स्रोत` and `### Cited Extension Sources` URL blocks, markdown asterisks, brackets, and citation numbers so spoken audio flows naturally.
   - Dynamic Locale: Switches to `Locale("hi", "IN")` for Hindi and `Locale("en", "IN")` for English.
   - Voice Data Check: Detects `LANG_MISSING_DATA` or `LANG_NOT_SUPPORTED` and displays an actionable Toast directing the user to Android Settings $\rightarrow$ Language $\rightarrow$ Text-to-Speech to install the Hindi voice pack.

---

## 4. Verification & Testing

### 4.1 Android Unit Tests (`ChatViewModelTest.kt`)
Executed via `gradlew testDebugUnitTest`:
```
BUILD SUCCESSFUL in 1m 2s
27 tests, 0 failures, 0 ignored (100% success rate)
```
Key tests verified:
- `testDetectLanguageDevanagariReturnsHindi()`: Verifies Devanagari detection.
- `testDetectLanguageLatinReturnsEnglish()`: Verifies Latin text defaults to English.
- `testSendMessageWithDevanagariSwitchesSelectedLanguageToHindi()`: Verifies query auto-detection.
- `testSendMessageCreatesConversationAndPersistsMessages()`: Verifies SQLite persistence.
- `testStartNewConversationClearsCurrentStateButPreservesStoredConversations()`: Verifies new chat lifecycle.
- `testLoadConversationRestoresMessagesInChronologicalOrder()`: Verifies message sorting.
- `testDeleteConversationCascadesAndRemovesFromList()`: Verifies cascade deletion.

### 4.2 Backend Regression Tests (`tests/test_api.py`)
Executed via WSL Ubuntu Python 3.13:
```
Ran 25 tests in 84.773s
OK (failures=0, errors=0)
```
- Full diagnostic inference, reassessment, PDF report, and chat endpoints verified.
- Dogri (`doi`) development status notice verified with Devanagari script queries.

### 4.3 Live Android Emulator Verification (`emulator-5554`)
1. **Hindi Query Flow:**
   - Switched language to Hindi $\rightarrow$ UI updated to Devanagari headers, suggested prompts, and labels.
   - Submitted prompt: `"टमाटर को स्वस्थ कैसे उगाएं?"`.
   - Logcat: `Request submission started: queryLen=27, caseId=null, historyCount=0, lang=hi`.
   - Backend returned 200 OK in 754 ms with a 2,559-character grounded Devanagari response and 4 citations.
   - Verified Devanagari rendering on device with Cornell and Purdue extension recommendations and citation links.
2. **Text-to-Speech Playback:**
   - Tapped speaker icon on Hindi response bubble.
   - Logcat verified URL bibliography was truncated. Missing voice pack was identified and the localized guide Toast was displayed: `"हिंदी वॉयस डेटा इस डिवाइस पर उपलब्ध नहीं है। कृपया Android सेटिंग्स > भाषा > Text-to-Speech में जाकर हिंदी वॉयस पैक इंस्टॉल करें।"`.
3. **English Query Flow:**
   - Switched language to English and submitted: `"how can i grow tomato healthy"`.
   - Backend returned 200 OK in 561 ms with 2,315-character grounded English response with 4 citations.
4. **Chat History Persistence & Relaunch:**
   - Relaunched the application and navigated to Assistant. The active chat session was restored from `agrimind_chat.db`.
   - Opened Conversation History sheet. Both conversations (`how can i grow tomato healthy` and `टमाटर को स्वस्थ कैसे उगाएं?`) were displayed with correct timestamps and language tags.
5. **Cascade Deletion:**
   - Tapped delete on `how can i grow tomato healthy` $\rightarrow$ Confirmation dialog appeared.
   - Confirmed deletion $\rightarrow$ SQLite permanently removed conversation and cascaded to all child messages.
   - Selected `टमाटर को स्वस्थ कैसे उगाएं?` $\rightarrow$ Hindi conversation thread was immediately loaded into view.

---

## 5. Artifacts and Deliverables

| Deliverable | Path | Description |
|---|---|---|
| Backend Generator | `src/rag/generator.py` | Devanagari script detection, extension header stripping, agronomic Hindi pattern dictionary, and institution localization |
| Conversation Entity | `android/app/src/main/java/.../model/ConversationEntity.kt` | Data model for SQLite conversation records |
| SQLite Helper | `android/app/src/main/java/.../local/ChatDatabaseHelper.kt` | Native SQLite OpenHelper managing `conversations` and `chat_messages` with cascade deletion |
| Chat Repository | `android/app/src/main/java/.../repository/ChatRepository.kt` | Repository interface and implementations (`ChatRepository`, `InMemoryChatRepository`) |
| Chat ViewModel | `android/app/src/main/java/.../viewmodel/ChatViewModel.kt` | `@JvmOverloads` constructor, language detection, and conversation persistence lifecycle |
| Chat Screen Composable | `android/app/src/main/java/.../screens/ChatScreen.kt` | History BottomSheet, deletion dialog, localized UI strings, and TTS URL truncation |
| Unit Test Suite | `android/app/src/test/java/.../ChatViewModelTest.kt` | 27 unit tests validating chat state, language switching, and persistence |
| Hindi UI Screenshot | `docs/stage_b7_hindi_verified.png` | Device screencap showing grounded Devanagari response with citations |
| History Sheet Screenshot | `docs/stage_b7_chat_history_sheet.png` | Device screencap showing ModalBottomSheet with saved conversation threads |
| Debug APK | `android/app/build/outputs/apk/debug/app-debug.apk` | Signed debug APK installed and verified on `emulator-5554` |

---

## 6. Architectural Preservation & Non-Regression Summary

- **ML Classifier:** No weights, architecture, or labels for ResNet-50 (`Tomato___Bacterial_spot`, `Tomato___Early_blight`, `Tomato___Late_blight`) were altered.
- **RAG Knowledge Base:** 63 agricultural knowledge chunks in ChromaDB remained intact; cosine similarity threshold remains fixed at 0.56.
- **Stages B.1–B.5 Features:** Leaf Photo Diagnosis, Reassessment, History, Case Details, and PDF Crop-Health Reports operate without regression.
- **Query Length Constraints:** The 1,000-character query limit and client-side sanitization remain strictly enforced.

