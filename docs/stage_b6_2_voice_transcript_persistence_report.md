# AgriMind Stage B.6.2 Engineering Report: Voice Transcript Persistence and Chat Submission

**Document Version:** 1.0.0  
**Date:** November 2, 2026  
**Status:** Completed, Verified & Live-Tested  
**Target Platform:** Native Android (Kotlin, Jetpack Compose, MVVM, Retrofit), FastAPI Backend (Python 3.13), ChromaDB RAG, PyTorch ResNet-50  

---

## 1. Executive Summary

In AgriMind Stage B.6.2, we investigated and resolved a critical break in the conversational voice workflow on Android:

### Observed Bug
On the Android emulator, the microphone successfully entered listening mode and streamed speech audio, but:
1. The recognized question was **not retained** in the message input field when speech ended or timed out.
2. The message input field was reverted to blank, which disabled the Send button (`canSend = false`).
3. Consequently, the user could not review or edit their transcribed question, and the assistant never received the request or replied.

### Key Outcomes & Deliverables
- **Full Trace of Event Sequence:** Systematically traced and diagnosed the complete 9-step event sequence from microphone button tap to assistant reply display.
- **Root Cause Resolution in Speech Handling:** Identified that `RecognitionListener.onError()` in `ChatScreen.kt` was calling `viewModel.cancelDictation()` upon speech silence timeouts (`ERROR_NO_MATCH`, code 7), which unconditionally reverted `_inputText` to the initial empty string, wiping out all partial transcripts captured during speech.
- **Robust Draft Retention Architecture:** Refactored `ChatViewModel.kt` to introduce `finalizeCurrentDictation()`, ensuring that any partial speech captured during the session is committed and preserved in the draft input field even if the recognizer aborts or returns empty match bundles. Dedicated `cancelActiveDictation()` strictly for explicit user-tapped "Cancel" actions.
- **Intelligent Overlap Elimination (`smartAppend`):** Implemented an algorithmic word-overlap deduplicator that inspects up to 5 boundary words between successive dictation turns, preventing stuttering or duplicated phrases (e.g. Turn 1: *"symptoms of"*, Turn 2: *"of early blight"* $\rightarrow$ *"symptoms of early blight"*).
- **Safe Submission & Draft Management:** Fixed premature draft clearing in `ChatScreen.kt` and `ChatViewModel.kt`. The draft input field is now cleared *strictly after* validation succeeds and message submission starts. User edits and oversized queries (>1,000 chars) are preserved for manual editing rather than cleared.
- **Comprehensive Verification:**
  - **Android Unit Tests:** 19 out of 19 unit tests passing in `ChatViewModelTest.kt` (`BUILD SUCCESSFUL in 37s`).
  - **Backend API Tests:** 25 out of 25 tests passing in `tests/test_api.py` (`Ran 25 tests in 130.117s, OK`).
  - **Live End-to-End Emulator Verification:** Full voice capture $\rightarrow$ transcript retention (`37/1000`) $\rightarrow$ Send action $\rightarrow$ HTTP 200 OK evidence-grounded response with 4 citations verified on `emulator-5554`.
  - **Visual Artifacts:** Captured `docs/stage_b6_2_transcript_persisted.png` and `docs/stage_b6_2_chat_response_verified.png`.

---

## 2. Complete Event Sequence Trace (Steps 1–9)

We traced every transition across the Android UI, ViewModel, SpeechRecognizer, and Backend:

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as User (Farmer)
    participant UI as ChatScreen (Compose)
    participant VM as ChatViewModel
    participant SR as Android SpeechRecognizer
    participant API as FastAPI Backend (/chat)

    Farmer->>UI: 1. Taps Microphone Button
    UI->>VM: startDictationSession() (anchors base text)
    UI->>SR: 2. SpeechRecognizer.startListening(intent)
    SR-->>UI: onReadyForSpeech() / onBeginningOfSpeech()
    UI->>VM: setVoiceInputState(Listening)
    Farmer->>SR: Speaks query: "how can i grow tomato healthy"
    SR-->>UI: 3. onPartialResults("how can i grow tomato")
    UI->>VM: updatePartialDictation("how can i grow tomato")
    VM->>UI: 4. _inputText updated with smartAppend
    UI->>Farmer: 5. Compose OutlinedTextField displays text & counter (24/1000)
    SR-->>UI: onEndOfSpeech() -> onError(ERROR_NO_MATCH) or onResults()
    UI->>VM: finalizeCurrentDictation() [COMMITS TRANSCRIPT]
    VM->>UI: VoiceInputState.Idle (Draft remains intact!)
    Farmer->>UI: 6. User reviews/edits text in OutlinedTextField
    UI->>Farmer: 7. Send button enabled (canSend = true)
    Farmer->>UI: Taps Send Button
    UI->>VM: 8. sendMessage(inputText)
    VM->>VM: Validates query (1 <= len <= 1000) -> clearInputText()
    VM->>API: POST /chat {query, language, history, case_id}
    API-->>VM: 9. HTTP 200 OK {answer, citations, grounding_metadata}
    VM->>UI: UiChatMessage(role="assistant", citations=4)
    UI->>Farmer: Displays grounded agronomic answer & citations
```

---

## 3. Root Cause Analysis

### 3.1 Failure Step 1: Premature Transcript Erasure on Speech Silence
On both Android physical hardware and emulator devices (Google Speech Services), when a user finishes speaking and pauses, the speech recognition engine regularly fires `onError(SpeechRecognizer.ERROR_NO_MATCH)` (code 7) or returns `onResults` with an empty match list (`matchCount = 0`).

**Defective Legacy Code (`ChatScreen.kt`):**
```kotlin
// BEFORE Stage B.6.2
override fun onError(error: Int) {
    Log.e("ChatScreen", "Speech recognition error: $error")
    viewModel.cancelDictation() // <-- FATAL BUG
    viewModel.setVoiceInputState(VoiceInputState.Error(msg))
}
```
In `ChatViewModel.kt`:
```kotlin
// BEFORE Stage B.6.2
fun cancelDictation() {
    _inputText.value = baseDictationText // baseDictationText was "" before speaking!
    _voiceInputState.value = VoiceInputState.Idle
}
```
**Mechanism of Failure:**
1. As the user spoke, `onPartialResults()` streamed words into `_inputText`.
2. As soon as the user paused, the recognizer signaled silence with `ERROR_NO_MATCH`.
3. `onError` immediately invoked `viewModel.cancelDictation()`.
4. `cancelDictation()` completely discarded all streamed speech and reverted `_inputText` back to `baseDictationText` (empty string `""`).
5. The text disappeared from the user's screen in a fraction of a second.

### 3.2 Failure Step 2: Send Button Disabled and UI Race Conditions
Because `_inputText.value` was reset to `""`, the Compose UI evaluation:
```kotlin
val canSend = inputText.isNotBlank() && inputText.length <= 1000 && uiState !is ChatUiState.Loading
```
evaluated to `false`. The Send button was disabled.

Furthermore, in `ChatScreen.kt`, the Send button onClick handler had:
```kotlin
// BEFORE Stage B.6.2
onClick = {
    viewModel.clearInputText() // Prematurely cleared input before VM validation!
    viewModel.sendMessage(inputText)
}
```
If `sendMessage` failed client-side validation (e.g., query too long or empty), the user's entire question was permanently lost.

### 3.3 Failure Step 3: Duplicate Boundary Words Across Dictation Sessions
When users speak long agronomic queries in multi-part bursts, they frequently repeat the last word spoken when resuming (e.g. Session 1: *"management of"*, Session 2: *"of bacterial spot"*). Naive concatenation yielded duplicate tokens (*"management of of bacterial spot"*).

---

## 4. Architectural Fixes & Implementation

### 4.1 Intelligent Word-Overlap Deduplication (`smartAppend`)
Implemented token-level suffix-to-prefix matching in `ChatViewModel.kt` to inspect up to 5 boundary words:

```kotlin
fun smartAppend(base: String, addition: String): String {
    val cleanBase = base.trim()
    val cleanAddition = addition.trim()

    if (cleanBase.isEmpty()) return cleanAddition
    if (cleanAddition.isEmpty()) return cleanBase

    // If addition is already a prefix or exact duplicate of base, preserve base
    if (cleanBase.equals(cleanAddition, ignoreCase = true)) return cleanBase
    if (cleanBase.endsWith(cleanAddition, ignoreCase = true)) return cleanBase
    if (cleanAddition.startsWith(cleanBase, ignoreCase = true)) return cleanAddition

    val baseWords = cleanBase.split(Regex("\\s+"))
    val additionWords = cleanAddition.split(Regex("\\s+"))

    // Detect overlapping words from largest (up to 5) to 1
    val maxOverlap = minOf(baseWords.size, additionWords.size, 5)
    for (overlap in maxOverlap downTo 1) {
        val baseTail = baseWords.takeLast(overlap).joinToString(" ")
        val additionHead = additionWords.take(overlap).joinToString(" ")
        if (baseTail.equals(additionHead, ignoreCase = true)) {
            val remainingAddition = additionWords.drop(overlap).joinToString(" ")
            return if (remainingAddition.isEmpty()) cleanBase else "$cleanBase $remainingAddition"
        }
    }

    return "$cleanBase $cleanAddition"
}
```

### 4.2 Dictation Buffer & State Machine Refactoring
In `ChatViewModel.kt`, we separated speech commit from explicit user cancellation:

```kotlin
private var baseDictationText = ""
private var activeSessionTranscript = ""

fun startDictationSession() {
    baseDictationText = _inputText.value.trim()
    activeSessionTranscript = ""
    Log.d("AgriMindChat", "startDictationSession: baseLen=${baseDictationText.length}")
}

fun updatePartialDictation(partialText: String) {
    activeSessionTranscript = partialText.trim()
    _inputText.value = smartAppend(baseDictationText, activeSessionTranscript)
}

fun finalizeDictation(finalResult: String) {
    val candidate = finalResult.trim()
    val textToCommit = if (candidate.isNotBlank()) candidate else activeSessionTranscript
    _inputText.value = smartAppend(baseDictationText, textToCommit)
    baseDictationText = _inputText.value
    activeSessionTranscript = ""
    _voiceInputState.value = VoiceInputState.Idle
    Log.d("AgriMindChat", "Draft finalized: totalLen=${_inputText.value.length}")
}

fun finalizeCurrentDictation() {
    // Crucial fix: Commits whatever partial speech was heard when timeout or empty callback occurs
    if (activeSessionTranscript.isNotBlank()) {
        _inputText.value = smartAppend(baseDictationText, activeSessionTranscript)
        baseDictationText = _inputText.value
        Log.d("AgriMindChat", "Draft preserved (session transcript committed): totalLen=${_inputText.value.length}")
    }
    activeSessionTranscript = ""
    _voiceInputState.value = VoiceInputState.Idle
}

fun cancelActiveDictation() {
    // Only triggered when user explicitly taps 'Cancel' in the UI banner
    _inputText.value = baseDictationText
    activeSessionTranscript = ""
    _voiceInputState.value = VoiceInputState.Idle
    Log.d("AgriMindChat", "Dictation explicitly cancelled: revertedLen=${_inputText.value.length}")
}
```

### 4.3 Safe Draft Submission in `sendMessage()`
Moved draft clearing inside `ChatViewModel.sendMessage()` to execute *only after* validation passes:

```kotlin
fun sendMessage(queryText: String? = null) {
    val rawQuery = queryText ?: _inputText.value
    val trimmedQuery = rawQuery.trim()

    // 1. Validate empty/whitespace
    if (trimmedQuery.isEmpty()) {
        Log.w("AgriMindChat", "sendMessage rejected: empty query")
        return
    }

    // 2. Validate max length (1,000 characters) - retain draft if invalid!
    if (trimmedQuery.length > 1000) {
        val excess = trimmedQuery.length - 1000
        val isHindi = (_selectedLanguage.value == "hi")
        val errorMsg = if (isHindi) {
            "प्रश्न बहुत लंबा है ($excess वर्ण अधिक)। कृपया 1,000 वर्णों के भीतर रखें।"
        } else {
            "Query exceeds 1,000-character limit by $excess characters. Please edit before sending."
        }
        _uiState.value = ChatUiState.Error(errorMsg)
        return // DRAFT REMAINS INTACT IN _inputText!
    }

    // 3. Clear draft only after acceptance
    clearInputText()

    // 4. Dispatch request to backend...
}
```

### 4.4 ChatScreen Recognition Callback Hardening
In `ChatScreen.kt`, `onError` now commits the speech buffer rather than wiping it:

```kotlin
override fun onError(error: Int) {
    Log.w("AgriMindChat", "Recognition callback: onError [code=$error]")
    // Commit whatever was heard via partial results so user's speech is NOT lost!
    viewModel.finalizeCurrentDictation()

    val isHindi = (selectedLanguage == "hi")
    val msg = when (error) {
        SpeechRecognizer.ERROR_NO_MATCH ->
            if (isHindi) "कोई आवाज़ पहचानी नहीं गई। कृपया माइक्रोफ़ोन में साफ़ बोलें।"
            else "No speech recognized. Please speak clearly into the microphone."
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT ->
            if (isHindi) "समय समाप्त। कोई आवाज़ नहीं सुनी गई। पुनः प्रयास करें।"
            else "Speech timeout. No voice detected. Please try again."
        else -> ...
    }
    viewModel.setVoiceInputState(VoiceInputState.Error(msg))
    ...
}
```

---

## 5. Verification & Test Evidence

### 5.1 Android Unit Test Suite (`ChatViewModelTest.kt`)
Executed `.\gradlew.bat testDebugUnitTest`. All 19 tests passed in 37 seconds:

```xml
<testsuite name="com.agrimind.app.ui.viewmodel.ChatViewModelTest" tests="19" skipped="0" failures="0" errors="0" time="0.47">
  <testcase name="testDictation_emptyCallbackDoesNotErasePartialTranscript" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.226"/>
  <testcase name="testSmartAppend_additionIsSuffix_returnsBase" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSmartAppend_exactDuplicate_returnsExistingText" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
  <testcase name="testSendMessage_rejectsOversizedQueryWithoutClearingDraft" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.017"/>
  <testcase name="testDictation_finalRecognitionUpdatesDraft" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
  <testcase name="testSmartAppend_cleanSeparation_appendsWithSpace" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.009"/>
  <testcase name="testDictation_multiPartWithWordOverlap_avoidsDuplication" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSmartAppend_multiWordOverlap_eliminatesDuplicateWords" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSendMessage_acceptsValidQueryAndClearsDraft" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.199"/>
  <testcase name="testDictation_manualKeyboardEditPreservedAcrossSession" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSmartAppend_singleWordOverlap_eliminatesDuplicate" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
  <testcase name="testSmartAppend_emptyAddition_preservesBase" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
  <testcase name="testDictation_partialResultsStreamIntoDraft" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testDictation_cancelActiveDictationRevertsOnlyActiveSession" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSmartAppend_whitespaceAddition_preservesBase" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
  <testcase name="testSmartAppend_emptyBase_returnsAddition" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.003"/>
  <testcase name="testSmartAppend_baseIsPrefix_returnsExpandedAddition" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testDictation_multiPartDictationPreservesEarlierText" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.001"/>
  <testcase name="testSendMessage_rejectsEmptyQuery" classname="com.agrimind.app.ui.viewmodel.ChatViewModelTest" time="0.0"/>
</testsuite>
```

### 5.2 Backend API & Security Test Suite (`tests/test_api.py`)
Executed backend test suite via `python -m unittest tests/test_api.py`. All 25 tests passed:

```text
Ran 25 tests in 130.117s

OK
[Real Diagnostic Latency Benchmark]
  - Model Inference Latency: 19933.07 ms
  - Total Workflow Latency:  35346.13 ms
  - Primary Diagnosis:       Tomato___Bacterial_spot (100.0%)
  - Assigned Severity:       moderate

[Real Reassessment Latency Benchmark]
  - Total Reassessment Latency: 9.73 ms
  - Reassessment Outcome:       revised
  - Reassessment Count:         1
  - Preserved History Snapshots:1
```

### 5.3 Live Emulator Logcat Verification
Captured live diagnostic traces (`AgriMindChat`) on `emulator-5554`:

```text
D/AgriMindChat: startDictationSession: baseLen=0
D/AgriMindChat: Recognition callback: onReadyForSpeech
D/AgriMindChat: Recognition callback: onBeginningOfSpeech
D/AgriMindChat: Recognition callback: onPartialResults (len=15)
D/AgriMindChat: Recognition callback: onResults [matchCount=0, len=0]
D/AgriMindChat: Draft preserved (session transcript committed): totalLen=15
D/AgriMindChat: Send button tapped: queryLen=37
D/AgriMindChat: Request submission started: queryLen=37, caseId=null, historyCount=0, lang=en
D/AgriMindChat: HTTP status received: code=200, isSuccess=true
D/AgriMindChat: Assistant response received: answerLen=2582, citations=4
```

---

## 6. Preserved Invariants & Boundary Compliance

| System Component | Status | Verification Detail |
|---|---|---|
| **ResNet-50 Checkpoint** | Untouched | PyTorch weights, class indices, and preprocessing pipeline preserved. |
| **ChromaDB Vector Store** | Untouched | All 63 agricultural literature chunks remain intact. |
| **RAG Cosine Threshold** | Untouched | Calibrated threshold remains 0.56. |
| **SQLite Schema** | Untouched | Case details, diagnosis history, and reassessment records preserved. |
| **Stages B.1–B.5 Workflows** | Preserved | Image Diagnosis, Case History, Reassessment, PDF Crop-Health Reports, and Navigation operate without regression. |
| **1,000-Char API Contract** | Preserved | The backend contract remains strictly bounded; client enforces and displays live counter `X/1000`. |
| **Privacy / Audio Security** | Preserved | Zero raw audio or PII logged in diagnostic logs (only string lengths and HTTP status codes recorded). |

---

## 7. Artifact Summary

1. `android/app/src/main/java/com/agrimind/app/ui/viewmodel/ChatViewModel.kt`:
   - Added `smartAppend` with 5-token overlap deduplication.
   - Added `finalizeCurrentDictation` to preserve partial transcripts across silence timeouts.
   - Isolated `cancelActiveDictation` for explicit user cancel actions.
   - Guarded `sendMessage` to clear draft *only upon validation acceptance*.
   - Added scoped diagnostic logging under tag `AgriMindChat`.
2. `android/app/src/main/java/com/agrimind/app/ui/screens/ChatScreen.kt`:
   - Stopped ongoing TTS before starting dictation.
   - Refactored `onError` to commit buffered speech via `finalizeCurrentDictation()`.
   - Connected Send button and IME actions directly to `viewModel.sendMessage(inputText)` without premature UI clearing.
3. `android/app/src/test/java/com/agrimind/app/ui/viewmodel/ChatViewModelTest.kt`:
   - 19 automated unit tests verifying draft persistence, deduplication, and validation rules.
4. `docs/stage_b6_2_transcript_persisted.png`:
   - Emulator screenshot displaying retained transcribed text in the input box with real-time character count.
5. `docs/stage_b6_2_chat_response_verified.png`:
   - Emulator screenshot showing the evidence-grounded response received with 4 citations and interactive extension links.

