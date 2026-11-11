package com.agrimind.app.ui.viewmodel

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.model.ChatCitationItem
import com.agrimind.app.data.model.ChatMessageItem
import com.agrimind.app.data.model.ChatRequest
import com.agrimind.app.data.model.ConversationEntity
import com.agrimind.app.data.repository.ChatRepository
import com.agrimind.app.data.repository.IChatRepository
import com.agrimind.app.data.repository.InMemoryChatRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.util.UUID

/**
 * UI representation of a chat message in the conversation stream.
 */
data class UiChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val role: String, // "user" or "assistant"
    val content: String,
    val citations: List<ChatCitationItem> = emptyList(),
    val hasSufficientEvidence: Boolean = true,
    val generationMode: String = "unknown",
    val diseaseTarget: String? = null,
    val language: String = "en",
    val isError: Boolean = false,
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * UI State for conversational Q&A operations.
 */
sealed interface ChatUiState {
    object Idle : ChatUiState
    object Loading : ChatUiState
    data class Error(val message: String) : ChatUiState
}

/**
 * UI State for Voice Input (Speech-to-Text).
 */
sealed interface VoiceInputState {
    object Idle : VoiceInputState
    data class Listening(val language: String, val isSpeaking: Boolean = false) : VoiceInputState
    data class Processing(val language: String) : VoiceInputState
    data class Error(val message: String, val canRetry: Boolean = true) : VoiceInputState
}

/**
 * Helper function that appends recognized speech text to an existing base text
 * with clean whitespace boundaries while preventing duplicated words from multi-part dictation overlaps.
 */
fun smartAppend(base: String, addition: String): String {
    val b = base.trim()
    val a = addition.trim()
    if (b.isEmpty()) return a
    if (a.isEmpty()) return b
    if (b.equals(a, ignoreCase = true)) return b
    if (b.endsWith(a, ignoreCase = true)) return b
    if (a.startsWith(b, ignoreCase = true)) return a

    val bWords = b.split(Regex("\\s+"))
    val aWords = a.split(Regex("\\s+"))
    val maxOverlap = minOf(bWords.size, aWords.size, 5)

    for (k in maxOverlap downTo 1) {
        val bSuffix = bWords.takeLast(k).joinToString(" ")
        val aPrefix = aWords.take(k).joinToString(" ")
        if (bSuffix.equals(aPrefix, ignoreCase = true)) {
            val remainingA = aWords.drop(k).joinToString(" ")
            return if (remainingA.isEmpty()) b else "$b $remainingA"
        }
    }

    return "$b $a"
}

/**
 * ViewModel managing evidence-grounded conversational decision support.
 * Coordinates POST /chat requests, binds saved case diagnoses, maintains local message stream,
 * provides multi-part speech-to-text dictation buffering, performs strict client-side validation,
 * provides automatic Hindi/English language detection, and persists conversation history in SQLite.
 */
class ChatViewModel @JvmOverloads constructor(
    application: Application,
    private val chatRepository: IChatRepository = try {
        if (application.applicationContext != null) {
            ChatRepository.getInstance(application)
        } else {
            InMemoryChatRepository()
        }
    } catch (e: Exception) {
        InMemoryChatRepository()
    }
) : AndroidViewModel(application) {

    // Persistent conversation threads from SQLite
    val conversations: StateFlow<List<ConversationEntity>> = chatRepository.conversationsFlow

    private val _currentConversationId = MutableStateFlow<String?>(null)
    val currentConversationId: StateFlow<String?> = _currentConversationId.asStateFlow()

    private val _messages = MutableStateFlow<List<UiChatMessage>>(emptyList())
    val messages: StateFlow<List<UiChatMessage>> = _messages.asStateFlow()

    private val _uiState = MutableStateFlow<ChatUiState>(ChatUiState.Idle)
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val _caseId = MutableStateFlow<String?>(null)
    val caseId: StateFlow<String?> = _caseId.asStateFlow()

    private val _activeDiagnosis = MutableStateFlow<String?>(null)
    val activeDiagnosis: StateFlow<String?> = _activeDiagnosis.asStateFlow()

    private val _selectedLanguage = MutableStateFlow("en")
    val selectedLanguage: StateFlow<String> = _selectedLanguage.asStateFlow()

    private val _activeSpeakingMessageId = MutableStateFlow<String?>(null)
    val activeSpeakingMessageId: StateFlow<String?> = _activeSpeakingMessageId.asStateFlow()

    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    private val _voiceInputState = MutableStateFlow<VoiceInputState>(VoiceInputState.Idle)
    val voiceInputState: StateFlow<VoiceInputState> = _voiceInputState.asStateFlow()

    // Base text anchor: text that existed before the current listening session started
    private var baseDictationText: String = ""
    // Active session transcript: most recent text captured during the current listening session
    private var activeSessionTranscript: String = ""

    init {
        // Automatically restore the most recent conversation on startup
        viewModelScope.launch {
            val list = chatRepository.getAllConversations()
            if (list.isNotEmpty()) {
                val latest = list.first()
                loadConversation(latest.id)
            }
        }
    }

    /**
     * Inspects text using hybrid script and vocabulary heuristic for Hindi, Dogri, and English.
     */
    fun detectLanguage(text: String): String {
        return com.agrimind.app.util.LanguageDetector.detectLanguage(text)
    }

    fun setLanguage(lang: String) {
        _selectedLanguage.value = lang
    }

    fun setActiveSpeakingMessageId(id: String?) {
        _activeSpeakingMessageId.value = id
    }

    fun setInputText(text: String) {
        _inputText.value = text
        baseDictationText = text.trim()
        activeSessionTranscript = ""
    }

    fun clearInputText() {
        _inputText.value = ""
        baseDictationText = ""
        activeSessionTranscript = ""
    }

    fun dismissError() {
        if (_uiState.value is ChatUiState.Error) {
            _uiState.value = ChatUiState.Idle
        }
    }

    /**
     * Dictation management: captures the text currently present in the input box
     * before listening starts, so subsequent utterances or partial previews append cleanly.
     */
    fun startDictationSession() {
        baseDictationText = _inputText.value.trim()
        activeSessionTranscript = ""
        Log.d("AgriMindChat", "startDictationSession: baseLen=${baseDictationText.length}")
    }

    /**
     * Updates the input field with partial speech recognition results while the user is speaking.
     * Prevents duplicate concatenation by anchoring against the starting base text.
     */
    fun updatePartialDictation(partialText: String) {
        val trimmed = partialText.trim()
        if (trimmed.isEmpty()) return
        activeSessionTranscript = trimmed
        _inputText.value = smartAppend(baseDictationText, activeSessionTranscript)
        Log.d("AgriMindChat", "Draft updated (partial): totalLen=${_inputText.value.length}")
    }

    /**
     * Finalizes recognized speech upon completion.
     * Appends with clean spacing and updates the base dictation anchor for subsequent voice inputs.
     */
    fun finalizeDictation(finalText: String) {
        val trimmed = finalText.trim()
        if (trimmed.isNotEmpty()) {
            activeSessionTranscript = trimmed
        }
        _inputText.value = smartAppend(baseDictationText, activeSessionTranscript)
        baseDictationText = _inputText.value.trim()
        activeSessionTranscript = ""
        Log.d("AgriMindChat", "Draft updated (final): totalLen=${_inputText.value.length}")
    }

    /**
     * Finalizes whatever was accumulated during this session (e.g. from partial results).
     * Ensures recognized text is retained even if Google Speech returns an empty final callback or timeout error.
     */
    fun finalizeCurrentDictation() {
        if (activeSessionTranscript.isNotEmpty()) {
            _inputText.value = smartAppend(baseDictationText, activeSessionTranscript)
            baseDictationText = _inputText.value.trim()
            activeSessionTranscript = ""
            Log.d("AgriMindChat", "Draft preserved (session transcript committed): totalLen=${_inputText.value.length}")
        } else {
            _inputText.value = baseDictationText
            Log.d("AgriMindChat", "Draft preserved (base text retained): totalLen=${_inputText.value.length}")
        }
    }

    /**
     * Explicit cancellation requested by the user tapping Cancel on the listening banner.
     * Reverts input text back to the base text captured prior to this dictation session.
     */
    fun cancelActiveDictation() {
        _inputText.value = baseDictationText
        activeSessionTranscript = ""
        Log.d("AgriMindChat", "Draft reverted on explicit cancel: totalLen=${_inputText.value.length}")
    }

    /**
     * General utility for appending text with clean spacing and duplicate prevention.
     */
    fun appendInputText(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty()) return
        _inputText.value = smartAppend(_inputText.value, trimmed)
        baseDictationText = _inputText.value.trim()
        activeSessionTranscript = ""
    }

    fun setVoiceInputState(state: VoiceInputState) {
        _voiceInputState.value = state
    }

    fun dismissVoiceError() {
        if (_voiceInputState.value is VoiceInputState.Error) {
            _voiceInputState.value = VoiceInputState.Idle
        }
    }

    /**
     * Binds the chat session to a specific diagnosis case.
     * When linked, the backend filters literature to the case's primary pathogen.
     */
    fun setCaseContext(newCaseId: String?, diagnosis: String? = null) {
        if (_caseId.value != newCaseId) {
            _caseId.value = newCaseId

            val resolvedDiagnosis = diagnosis ?: if (newCaseId != null) {
                try {
                    com.agrimind.app.data.repository.LocalCaseRepository.getInstance(getApplication()).getCaseById(newCaseId)?.primaryDiagnosis
                } catch (e: Exception) {
                    null
                }
            } else null

            _activeDiagnosis.value = resolvedDiagnosis

            if (_messages.value.isEmpty() && newCaseId != null) {
                val cleanDiagnosis = resolvedDiagnosis?.replace("Tomato___", "")?.replace("_", " ") ?: "tomato leaf specimen"
                val greeting = if (_selectedLanguage.value == "hi") {
                    "एग्रीमाइंड सहायक केस $newCaseId (प्रारंभिक एआई मूल्यांकन: $cleanDiagnosis) के लिए सक्रिय है। एकीकृत कीट प्रबंधन (IPM), अनुशंसित रासायनिक नियंत्रण या स्वच्छता उपायों के बारे में पूछें। मार्गदर्शन विश्वविद्यालय अनुसंधान पर आधारित है, रासायनिक उपचार से पूर्व विशेषज्ञ से पुष्टि करें।"
                } else {
                    "AgriMind Assistant active for case $newCaseId (Preliminary AI Assessment: $cleanDiagnosis). Ask me about IPM recommendations, registered chemical controls, or sanitation practices. Guidance is grounded in university research but does not replace expert field confirmation."
                }
                _messages.value = listOf(
                    UiChatMessage(
                        role = "assistant",
                        content = greeting,
                        diseaseTarget = resolvedDiagnosis
                    )
                )
            }
        }
    }

    /**
     * Loads a saved conversation from SQLite into the active chat stream.
     */
    fun loadConversation(conversationId: String) {
        viewModelScope.launch {
            val msgs = chatRepository.getMessagesForConversation(conversationId)
            _currentConversationId.value = conversationId
            _messages.value = msgs
            _uiState.value = ChatUiState.Idle
            clearInputText()

            val allConvs = chatRepository.getAllConversations()
            val conv = allConvs.find { it.id == conversationId }
            if (conv != null) {
                if (conv.language in listOf("en", "hi", "doi")) {
                    _selectedLanguage.value = conv.language
                }
                _caseId.value = conv.caseId
                _activeDiagnosis.value = null
            } else {
                _caseId.value = null
                _activeDiagnosis.value = null
            }
            Log.d("AgriMindChat", "Loaded conversation $conversationId with ${msgs.size} messages")
        }
    }

    /**
     * Resets the active conversation to prepare for a fresh chat session.
     * Does not delete past conversations from SQLite.
     * Guaranteed to reset any previous case linkage so new conversations are not contaminated.
     */
    fun startNewConversation() {
        _currentConversationId.value = null
        _caseId.value = null
        _activeDiagnosis.value = null
        _messages.value = emptyList()
        _uiState.value = ChatUiState.Idle
        _voiceInputState.value = VoiceInputState.Idle
        clearInputText()
        Log.d("AgriMindChat", "Started new conversation")
    }

    /**
     * Permanently deletes a single conversation from SQLite.
     */
    fun deleteConversation(conversationId: String) {
        viewModelScope.launch {
            chatRepository.deleteConversation(conversationId)
            if (_currentConversationId.value == conversationId) {
                startNewConversation()
            }
        }
    }

    /**
     * Clears all messages in the active view. If backed by a conversation, deletes it.
     */
    fun clearChat() {
        val activeId = _currentConversationId.value
        if (activeId != null) {
            deleteConversation(activeId)
        } else {
            _messages.value = emptyList()
            _uiState.value = ChatUiState.Idle
            _voiceInputState.value = VoiceInputState.Idle
            clearInputText()
        }
    }

    /**
     * Extracts a human-readable, specific validation error from FastAPI/Pydantic JSON responses.
     */
    private fun parseFastApiError(errorBodyString: String?): String? {
        if (errorBodyString.isNullOrBlank()) return null
        return try {
            val json = JSONObject(errorBodyString)
            if (json.has("detail")) {
                val detailObj = json.get("detail")
                when (detailObj) {
                    is JSONArray -> {
                        val messages = mutableListOf<String>()
                        for (i in 0 until detailObj.length()) {
                            val item = detailObj.getJSONObject(i)
                            val msg = item.optString("msg", "")
                            val locArray = item.optJSONArray("loc")
                            val field = if (locArray != null && locArray.length() > 0) {
                                (0 until locArray.length())
                                    .map { locArray.getString(it) }
                                    .filter { it != "body" }
                                    .joinToString(".")
                            } else null

                            if (!field.isNullOrBlank() && msg.isNotBlank()) {
                                messages.add("'$field': $msg")
                            } else if (msg.isNotBlank()) {
                                messages.add(msg)
                            }
                        }
                        if (messages.isNotEmpty()) {
                            messages.joinToString("; ")
                        } else null
                    }
                    is String -> detailObj
                    else -> detailObj.toString()
                }
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Dispatches an agronomic query to the AgriMind backend (POST /chat).
     * Validates input length and constraints client-side, sanitizes conversation history,
     * clears the draft input upon acceptance, detects query language automatically,
     * persists conversation and message state in SQLite, and maps backend error details accurately.
     */
    fun sendMessage(query: String) {
        val trimmedQuery = query.trim()

        // 1. Client-side input validation
        if (trimmedQuery.isEmpty()) {
            _uiState.value = ChatUiState.Error("Please enter or speak a question before sending.")
            return
        }

        if (trimmedQuery.length > 1000) {
            val excess = trimmedQuery.length - 1000
            val msg = "Question is too long (${trimmedQuery.length}/1000 characters). Please shorten by $excess character${if (excess > 1) "s" else ""}."
            _uiState.value = ChatUiState.Error(msg)
            return
        }

        if (_uiState.value is ChatUiState.Loading) return

        // 2. Query accepted for submission: clear the input box draft immediately
        clearInputText()

        // 3. Language detection & synchronization:
        val detected = detectLanguage(trimmedQuery)
        val cleanLanguage = if (detected == "doi" || _selectedLanguage.value == "doi") {
            _selectedLanguage.value = "doi"
            "doi"
        } else if (detected == "hi" || _selectedLanguage.value == "hi") {
            _selectedLanguage.value = "hi"
            "hi"
        } else if (_selectedLanguage.value in listOf("en", "hi", "doi")) {
            _selectedLanguage.value
        } else {
            "en"
        }

        // 4. Prepare wire-format conversation history (bounded to last 10 messages)
        val historyPayload = _messages.value
            .filter { !it.isError && it.content.isNotBlank() }
            .takeLast(10)
            .map { ChatMessageItem(role = it.role, content = it.content.take(2000).trim()) }
            .filter { it.content.isNotBlank() }

        // 5. Append user message to UI stream
        val userMsg = UiChatMessage(
            role = "user",
            content = trimmedQuery,
            language = cleanLanguage
        )
        _messages.value = _messages.value + userMsg

        val cleanCaseId = _caseId.value?.trim()?.takeIf { it.isNotBlank() }
        _uiState.value = ChatUiState.Loading
        Log.d("AgriMindChat", "Request submission started: queryLen=${trimmedQuery.length}, caseId=$cleanCaseId, historyCount=${historyPayload.size}, lang=$cleanLanguage")

        viewModelScope.launch {
            // Ensure persistent conversation exists in SQLite
            var convId = _currentConversationId.value
            if (convId == null) {
                val title = if (trimmedQuery.length <= 40) trimmedQuery else trimmedQuery.take(40) + "..."
                val newConv = chatRepository.createConversation(
                    title = title,
                    language = cleanLanguage,
                    caseId = cleanCaseId
                )
                convId = newConv.id
                _currentConversationId.value = convId
            }

            // Immediately persist user message to SQLite
            chatRepository.saveMessage(convId, userMsg)

            try {
                val request = ChatRequest(
                    query = trimmedQuery,
                    caseId = cleanCaseId,
                    conversationHistory = historyPayload,
                    language = cleanLanguage
                )

                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.chat(request)
                }

                Log.d("AgriMindChat", "HTTP status received: code=${response.code()}, isSuccess=${response.isSuccessful}")

                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    Log.d("AgriMindChat", "Assistant response received: answerLen=${body.answer.length}, citations=${body.citations.size}")
                    val assistantMsg = UiChatMessage(
                        role = "assistant",
                        content = body.answer,
                        citations = body.citations,
                        hasSufficientEvidence = body.hasSufficientEvidence,
                        generationMode = body.generationMode,
                        diseaseTarget = body.diseaseTarget,
                        language = body.language
                    )
                    _messages.value = _messages.value + assistantMsg
                    _uiState.value = ChatUiState.Idle

                    // Persist assistant message to SQLite
                    chatRepository.saveMessage(convId, assistantMsg)
                } else {
                    val rawError = response.errorBody()?.string()
                    val parsedDetail = parseFastApiError(rawError)
                    Log.w("AgriMindChat", "HTTP error response body: $rawError")

                    val errorDetail = when (response.code()) {
                        404 -> parsedDetail ?: "Case '${_caseId.value}' was not found on the server."
                        422 -> if (parsedDetail != null) {
                            "Validation error - $parsedDetail"
                        } else {
                            "Invalid request format or query exceeded maximum length (1,000 characters)."
                        }
                        else -> parsedDetail ?: "Server error (${response.code()}): ${response.message().ifBlank { "Unable to generate response" }}"
                    }

                    val errorMsg = UiChatMessage(
                        role = "assistant",
                        content = "⚠️ $errorDetail",
                        isError = true
                    )
                    _messages.value = _messages.value + errorMsg
                    _uiState.value = ChatUiState.Error(errorDetail)
                }
            } catch (e: ConnectException) {
                Log.e("AgriMindChat", "Network ConnectException: ${e.message}")
                val msg = "Cannot connect to AgriMind backend (10.0.2.2:8000). Please ensure FastAPI is running."
                _messages.value = _messages.value + UiChatMessage(role = "assistant", content = "⚠️ $msg", isError = true)
                _uiState.value = ChatUiState.Error(msg)
            } catch (e: SocketTimeoutException) {
                Log.e("AgriMindChat", "Network SocketTimeoutException: ${e.message}")
                val msg = "Connection timed out waiting for RAG answer generation."
                _messages.value = _messages.value + UiChatMessage(role = "assistant", content = "⚠️ $msg", isError = true)
                _uiState.value = ChatUiState.Error(msg)
            } catch (e: IOException) {
                Log.e("AgriMindChat", "Network IOException: ${e.message}")
                val msg = "Network error: ${e.localizedMessage ?: "I/O failure"}"
                _messages.value = _messages.value + UiChatMessage(role = "assistant", content = "⚠️ $msg", isError = true)
                _uiState.value = ChatUiState.Error(msg)
            } catch (e: Exception) {
                Log.e("AgriMindChat", "Unexpected Exception: ${e.javaClass.simpleName} - ${e.message}")
                val msg = "Unexpected error: ${e.localizedMessage ?: "Unknown failure"}"
                _messages.value = _messages.value + UiChatMessage(role = "assistant", content = "⚠️ $msg", isError = true)
                _uiState.value = ChatUiState.Error(msg)
            }
        }
    }
}
