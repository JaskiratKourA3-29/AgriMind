package com.agrimind.app.ui.screens

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.HelpOutline
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.agrimind.app.data.model.ChatCitationItem
import com.agrimind.app.data.model.ConversationEntity
import com.agrimind.app.ui.theme.*
import com.agrimind.app.ui.viewmodel.ChatUiState
import com.agrimind.app.ui.viewmodel.ChatViewModel
import com.agrimind.app.ui.viewmodel.UiChatMessage
import com.agrimind.app.ui.viewmodel.VoiceInputState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.atomic.AtomicReference

/**
 * Sanitizes markdown, bracketed citations, and raw URLs so TextToSpeech reads cleanly.
 * Truncates bibliography reference sections to prevent speaking URLs and technical metadata.
 */
fun cleanTextForSpeech(raw: String): String {
    var text = raw
    // Truncate bibliography section before speaking so URLs and citation tables are never spoken
    val bibIndexHi = text.indexOf("### संदर्भित विस्तार स्रोत")
    val bibIndexEn = text.indexOf("### Cited Extension Sources")
    val cutIndex = when {
        bibIndexHi >= 0 && bibIndexEn >= 0 -> minOf(bibIndexHi, bibIndexEn)
        bibIndexHi >= 0 -> bibIndexHi
        bibIndexEn >= 0 -> bibIndexEn
        else -> -1
    }
    if (cutIndex >= 0) {
        text = text.substring(0, cutIndex)
    }

    text = text.replace(Regex("https?://\\S+"), "")
    text = text.replace(Regex("\\[\\d+\\]"), "")
    text = text.replace(Regex("\\[DOC-[^\\]]+\\]"), "")
    text = text.replace("**", "").replace("###", "").replace("#", "")
    text = text.replace("- ", ". ")
    return text.replace(Regex("\\s+"), " ").trim()
}

/**
 * Evidence-Grounded, Multilingual Conversational Screen with Voice Input (STT)
 * and Spoken Answers (TTS) for AgriMind.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    viewModel: ChatViewModel,
    caseId: String? = null,
    onBackClicked: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val messages by viewModel.messages.collectAsState()
    val uiState by viewModel.uiState.collectAsState()
    val activeCaseId by viewModel.caseId.collectAsState()
    val selectedLanguage by viewModel.selectedLanguage.collectAsState()
    val activeSpeakingId by viewModel.activeSpeakingMessageId.collectAsState()
    val inputText by viewModel.inputText.collectAsState()
    val voiceInputState by viewModel.voiceInputState.collectAsState()
    val conversations by viewModel.conversations.collectAsState()
    val currentConversationId by viewModel.currentConversationId.collectAsState()

    var showDogriDialog by remember { mutableStateOf(false) }
    var showHistorySheet by remember { mutableStateOf(false) }
    var conversationToDelete by remember { mutableStateOf<ConversationEntity?>(null) }
    val speechRecognizerRef = remember { AtomicReference<SpeechRecognizer?>(null) }
    var tts by remember { mutableStateOf<TextToSpeech?>(null) }
    var isTtsReady by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()
    val keyboardController = LocalSoftwareKeyboardController.current
    val context = LocalContext.current

    // Synchronize case context whenever caseId parameter changes
    LaunchedEffect(caseId) {
        if (caseId != null) {
            viewModel.setCaseContext(caseId)
        }
    }

    // Scroll to latest message on update
    LaunchedEffect(messages.size, uiState) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    // Initialize TextToSpeech engine and lifecycle cleanup
    DisposableEffect(context) {
        var ttsInstance: TextToSpeech? = null
        ttsInstance = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                isTtsReady = true
                ttsInstance?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) {
                        viewModel.setActiveSpeakingMessageId(null)
                    }
                    override fun onError(utteranceId: String?) {
                        viewModel.setActiveSpeakingMessageId(null)
                    }
                })
            }
        }
        tts = ttsInstance

        onDispose {
            try {
                val recognizer = speechRecognizerRef.get()
                recognizer?.stopListening()
                recognizer?.cancel()
                recognizer?.destroy()
                speechRecognizerRef.set(null)
                ttsInstance?.stop()
                ttsInstance?.shutdown()
            } catch (e: Exception) {}
        }
    }

    // Speech-to-Text helper functions
    fun stopListening(cancel: Boolean = false) {
        try {
            val recognizer = speechRecognizerRef.get()
            if (cancel) {
                recognizer?.cancel()
                recognizer?.destroy()
                speechRecognizerRef.set(null)
                viewModel.cancelActiveDictation()
                viewModel.setVoiceInputState(VoiceInputState.Idle)
            } else {
                viewModel.setVoiceInputState(VoiceInputState.Processing(selectedLanguage))
                recognizer?.stopListening()
            }
        } catch (e: Exception) {
            Log.w("AgriMindChat", "Error during stopListening", e)
            viewModel.setVoiceInputState(VoiceInputState.Idle)
        }
    }

    fun startListening() {
        // Stop any active TTS readout so mic doesn't capture speaker audio
        tts?.stop()
        viewModel.setActiveSpeakingMessageId(null)

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            val unavailMsg = if (selectedLanguage == "hi") {
                "इस डिवाइस पर स्पीच रिकग्निशन सेवा उपलब्ध नहीं है।"
            } else {
                "Speech recognition service is not available on this device."
            }
            viewModel.setVoiceInputState(VoiceInputState.Error(unavailMsg, canRetry = false))
            return
        }

        // Clean up any lingering instance before creating a new one
        try {
            val existing = speechRecognizerRef.get()
            existing?.cancel()
            existing?.destroy()
            speechRecognizerRef.set(null)
        } catch (e: Exception) {}

        // Anchor base text for incremental multi-part dictation
        viewModel.startDictationSession()

        val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
        speechRecognizerRef.set(recognizer)

        recognizer.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                Log.d("AgriMindChat", "Recognition callback: onReadyForSpeech")
                viewModel.setVoiceInputState(VoiceInputState.Listening(selectedLanguage, isSpeaking = false))
            }

            override fun onBeginningOfSpeech() {
                Log.d("AgriMindChat", "Recognition callback: onBeginningOfSpeech")
                viewModel.setVoiceInputState(VoiceInputState.Listening(selectedLanguage, isSpeaking = true))
            }

            override fun onRmsChanged(rmsdB: Float) {}

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                Log.d("AgriMindChat", "Recognition callback: onEndOfSpeech")
                // User paused longer than silence threshold; recognizer transcribes audio into final text
                viewModel.setVoiceInputState(VoiceInputState.Processing(selectedLanguage))
            }

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
                    SpeechRecognizer.ERROR_AUDIO ->
                        if (isHindi) "ऑडियो रिकॉर्डिंग त्रुटि। माइक्रोफ़ोन सेटिंग्स जाँचें।"
                        else "Audio recording error. Check your microphone settings."
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ->
                        if (isHindi) "माइक्रोफ़ोन अनुमति आवश्यक है।"
                        else "Microphone permission is required."
                    SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT ->
                        if (isHindi) "नेटवर्क समय समाप्त। कृपया इंटरनेट कनेक्शन की जाँच करें।"
                        else "Network timeout during speech recognition. Check your connection."
                    SpeechRecognizer.ERROR_RECOGNIZER_BUSY ->
                        if (isHindi) "स्पीच रिकग्नाइज़र व्यस्त है। कृपया पुनः प्रयास करें।"
                        else "Speech recognizer is busy. Please try again."
                    SpeechRecognizer.ERROR_SERVER, SpeechRecognizer.ERROR_SERVER_DISCONNECTED ->
                        if (isHindi) "सर्वर त्रुटि। कृपया थोड़ी देर बाद पुनः प्रयास करें।"
                        else "Recognition server error. Please try again."
                    SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED, SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE ->
                        if (isHindi) "इस डिवाइस पर हिंदी भाषा समर्थित नहीं है। कृपया अंग्रेज़ी का उपयोग करें।"
                        else "Language not supported by the device recognition service."
                    SpeechRecognizer.ERROR_CLIENT ->
                        if (isHindi) "अनुरोध रद्द या क्लाइंट त्रुटि।"
                        else "Recognition cancelled or client error."
                    else ->
                        if (isHindi) "स्पीच रिकग्निशन त्रुटि ($error)"
                        else "Speech recognition error ($error)"
                }
                viewModel.setVoiceInputState(VoiceInputState.Error(msg))
                try {
                    recognizer.destroy()
                    speechRecognizerRef.set(null)
                } catch (e: Exception) {}
            }

            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val recognized = matches?.firstOrNull()?.trim() ?: ""
                Log.d("AgriMindChat", "Recognition callback: onResults [matchCount=${matches?.size ?: 0}, len=${recognized.length}]")
                if (recognized.isNotBlank()) {
                    viewModel.finalizeDictation(recognized)
                } else {
                    viewModel.finalizeCurrentDictation()
                }
                viewModel.setVoiceInputState(VoiceInputState.Idle)
                try {
                    recognizer.destroy()
                    speechRecognizerRef.set(null)
                } catch (e: Exception) {}
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val partialMatches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val partialText = partialMatches?.firstOrNull()?.trim() ?: ""
                if (partialText.isNotBlank()) {
                    Log.d("AgriMindChat", "Recognition callback: onPartialResults (len=${partialText.length})")
                    viewModel.updatePartialDictation(partialText)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        val targetLangCode = when (selectedLanguage) {
            "doi" -> "doi-IN"
            "hi" -> "hi-IN"
            else -> "en-US"
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, targetLangCode)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, targetLangCode)
            putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, targetLangCode)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            // Natural speech pause configurations: tolerate 2.5 - 3.5s pauses
            // Note: Google RecognitionService calls getIntExtra(), expecting Integer rather than Long
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 3000)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3500)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 2500)
            putExtra("android.speech.extra.DICTATION_MODE", true)
            val promptText = when (selectedLanguage) {
                "doi" -> "डोगरी च बोलो (Listening in Dogri)..."
                "hi" -> "बोलिए (Listening in Hindi)..."
                else -> "Speak your question..."
            }
            putExtra(RecognizerIntent.EXTRA_PROMPT, promptText)
        }

        try {
            viewModel.setVoiceInputState(VoiceInputState.Listening(selectedLanguage, isSpeaking = false))
            recognizer.startListening(intent)
            Log.d("AgriMindChat", "startListening successfully dispatched for $targetLangCode")
        } catch (e: Exception) {
            Log.e("AgriMindChat", "Exception calling startListening", e)
            val isHindi = (selectedLanguage == "hi")
            val msg = if (isHindi) "स्पीच रिकग्निशन शुरू करने में विफल: ${e.message}" else "Failed to start speech recognition: ${e.message}"
            viewModel.finalizeCurrentDictation()
            viewModel.setVoiceInputState(VoiceInputState.Error(msg))
            try {
                recognizer.destroy()
                speechRecognizerRef.set(null)
            } catch (ex: Exception) {}
        }
    }

    // Audio permission launcher
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startListening()
        } else {
            Toast.makeText(context, "Microphone permission is required for voice input.", Toast.LENGTH_SHORT).show()
        }
    }

    // TTS playback toggle
    fun toggleTts(message: UiChatMessage) {
        if (activeSpeakingId == message.id) {
            tts?.stop()
            viewModel.setActiveSpeakingMessageId(null)
            return
        }

        tts?.stop()
        val hasDevanagari = message.content.any { it in '\u0900'..'\u097F' }
        val isDogri = message.language == "doi" || selectedLanguage == "doi"

        val targetLocale = if (isDogri) {
            val doiLocale = Locale("doi", "IN")
            val doiAvail = tts?.isLanguageAvailable(doiLocale)
            if (doiAvail != TextToSpeech.LANG_MISSING_DATA && doiAvail != TextToSpeech.LANG_NOT_SUPPORTED) {
                doiLocale
            } else {
                Toast.makeText(context, "डोगरी ध्वनि देवनागरी इंजन द्वारा बोली जा रही है (Devanagari fallback)", Toast.LENGTH_SHORT).show()
                Locale("hi", "IN")
            }
        } else if (hasDevanagari || message.language == "hi" || selectedLanguage == "hi") {
            Locale("hi", "IN")
        } else {
            Locale("en", "IN")
        }

        val availability = tts?.isLanguageAvailable(targetLocale)
        if (availability == TextToSpeech.LANG_MISSING_DATA || availability == TextToSpeech.LANG_NOT_SUPPORTED) {
            val errorMsg = if (targetLocale.language == "hi") {
                "हिंदी वॉयस डेटा इस डिवाइस पर उपलब्ध नहीं है। कृपया Android सेटिंग्स > भाषा > Text-to-Speech में जाकर हिंदी वॉयस पैक इंस्टॉल करें।"
            } else {
                "English voice data is not installed on this device. Please install it in Android Text-to-Speech settings."
            }
            Toast.makeText(context, errorMsg, Toast.LENGTH_LONG).show()
            return
        }

        tts?.language = targetLocale
        val speechText = cleanTextForSpeech(message.content)
        tts?.speak(speechText, TextToSpeech.QUEUE_FLUSH, null, message.id)
        viewModel.setActiveSpeakingMessageId(message.id)
    }

    val displayCaseId = caseId ?: activeCaseId

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = if (selectedLanguage == "hi") "एग्रीमाइंड सहायक (AgriMind)" else "AgriMind Assistant",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        val subtitle = if (displayCaseId != null) {
                            "Case: $displayCaseId • Grounded Literature"
                        } else {
                            if (selectedLanguage == "hi") "सत्यापित कृषि निर्णय समर्थन (Grounded QA)" else "Evidence-Grounded Agronomic QA"
                        }
                        Text(
                            text = subtitle,
                            fontSize = 12.sp,
                            color = Color.White.copy(alpha = 0.85f)
                        )
                    }
                },
                navigationIcon = {
                    if (onBackClicked != null) {
                        IconButton(onClick = onBackClicked) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = "Back",
                                tint = Color.White
                            )
                        }
                    }
                },
                actions = {
                    // Chat History drawer/sheet button
                    IconButton(onClick = { showHistorySheet = true }) {
                        Icon(
                            imageVector = Icons.Default.History,
                            contentDescription = if (selectedLanguage == "hi") "बातचीत इतिहास" else "Conversation History",
                            tint = Color.White
                        )
                    }
                    // Start new conversation button
                    IconButton(onClick = { viewModel.startNewConversation() }) {
                        Icon(
                            imageVector = Icons.Default.AddComment,
                            contentDescription = if (selectedLanguage == "hi") "नया संवाद" else "New Conversation",
                            tint = Color.White
                        )
                    }
                    // Clear / Delete current chat button
                    IconButton(
                        onClick = {
                            val activeId = currentConversationId
                            val activeConv = conversations.find { it.id == activeId }
                            if (activeConv != null) {
                                conversationToDelete = activeConv
                            } else {
                                viewModel.clearChat()
                            }
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Default.DeleteOutline,
                            contentDescription = "Clear Chat",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = ForestGreenPrimary
                )
            )
        },
        containerColor = LightGreenBackground
    ) { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Multilingual Language Selector Bar
            LanguageSelectorBar(
                currentLanguage = selectedLanguage,
                onLanguageSelected = { lang ->
                    viewModel.setLanguage(lang)
                    if (lang == "doi") {
                        Toast.makeText(context, "डोगरी मोड सक्रिय: प्रामाणिक कृषि शब्दावली (Dogri Vernacular Active)", Toast.LENGTH_SHORT).show()
                    }
                },
                onDogriSelected = {
                    viewModel.setLanguage("doi")
                    Toast.makeText(context, "डोगरी मोड सक्रिय: प्रामाणिक कृषि शब्दावली (Dogri Vernacular Active)", Toast.LENGTH_SHORT).show()
                }
            )

            // Main message stream
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                if (messages.isEmpty() && uiState !is ChatUiState.Loading) {
                    EmptyChatPromptView(
                        caseId = displayCaseId,
                        language = selectedLanguage,
                        onSuggestionSelected = { suggestion ->
                            viewModel.setInputText(suggestion)
                            viewModel.sendMessage(suggestion)
                        }
                    )
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(messages, key = { it.id }) { message ->
                            ChatMessageBubble(
                                message = message,
                                isSpeaking = (activeSpeakingId == message.id),
                                onToggleTts = { toggleTts(message) },
                                onOpenUrl = { url ->
                                    try {
                                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                                        }
                                        context.startActivity(intent)
                                    } catch (e: Exception) {
                                        Toast.makeText(context, "Could not open extension link: ${e.message}", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            )
                        }

                        if (uiState is ChatUiState.Loading) {
                            item {
                                AssistantLoadingBubble(language = selectedLanguage)
                            }
                        }
                    }
                }
            }

            // Error notification banner if state is Error
            if (uiState is ChatUiState.Error) {
                Surface(
                    color = ErrorRedLight,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.ErrorOutline,
                            contentDescription = null,
                            tint = ErrorRed,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = (uiState as ChatUiState.Error).message,
                            fontSize = 12.sp,
                            color = ErrorRed,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // Bottom Input Bar with Speech-to-Text Microphone
            Surface(
                color = Color.White,
                shadowElevation = 8.dp,
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                ) {
                    // Voice recognition status indicators (Listening, Processing, Error)
                    when (val vState = voiceInputState) {
                        is VoiceInputState.Listening -> {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(bottom = 6.dp)
                            ) {
                                Surface(
                                    shape = CircleShape,
                                    color = ErrorRed,
                                    modifier = Modifier.size(8.dp)
                                ) {}
                                Spacer(modifier = Modifier.width(6.dp))
                                val statusText = if (vState.language == "hi") {
                                    if (vState.isSpeaking) "आवाज़ दर्ज हो रही है... बोलिए (Recording)" else "सुन रहा हूँ... बोलिए (Listening in Hindi)"
                                } else {
                                    if (vState.isSpeaking) "Receiving speech... Keep speaking" else "Listening in English... Speak now"
                                }
                                Text(
                                    text = statusText,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = ErrorRed,
                                    modifier = Modifier.weight(1f)
                                )
                                TextButton(
                                    onClick = { stopListening(cancel = true) },
                                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = if (selectedLanguage == "hi") "रद्द करें" else "Cancel",
                                        fontSize = 11.sp,
                                        color = ErrorRed
                                    )
                                }
                            }
                        }
                        is VoiceInputState.Processing -> {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(bottom = 6.dp)
                            ) {
                                CircularProgressIndicator(
                                    color = ForestGreenPrimary,
                                    strokeWidth = 2.dp,
                                    modifier = Modifier.size(12.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = if (vState.language == "hi") "आवाज़ समझी जा रही है... (Processing)" else "Transcribing speech into text...",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = ForestGreenDark
                                )
                            }
                        }
                        is VoiceInputState.Error -> {
                            Surface(
                                color = ErrorRedLight,
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(bottom = 6.dp)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Info,
                                        contentDescription = null,
                                        tint = ErrorRed,
                                        modifier = Modifier.size(14.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = vState.message,
                                        fontSize = 11.sp,
                                        color = ErrorRed,
                                        modifier = Modifier.weight(1f)
                                    )
                                    if (vState.canRetry) {
                                        TextButton(
                                            onClick = {
                                                viewModel.dismissVoiceError()
                                                startListening()
                                            },
                                            contentPadding = PaddingValues(horizontal = 6.dp, vertical = 0.dp)
                                        ) {
                                            Text(
                                                text = if (selectedLanguage == "hi") "पुनः प्रयास" else "Retry",
                                                fontSize = 11.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = ForestGreenPrimary
                                            )
                                        }
                                    }
                                    IconButton(
                                        onClick = { viewModel.dismissVoiceError() },
                                        modifier = Modifier.size(20.dp)
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Close,
                                            contentDescription = "Dismiss",
                                            tint = TextMuted,
                                            modifier = Modifier.size(14.dp)
                                        )
                                    }
                                }
                            }
                        }
                        is VoiceInputState.Idle -> {
                            // No status banner in idle state
                        }
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = inputText,
                            onValueChange = { viewModel.setInputText(it) },
                            placeholder = {
                                val placeholderText = if (selectedLanguage == "hi") {
                                    if (displayCaseId != null) "इस केस के बारे में पूछें..." else "टमाटर की खेती या रोग के बारे में पूछें..."
                                } else {
                                    if (displayCaseId != null) "Ask about this case..." else "Ask an agronomic question..."
                                }
                                Text(
                                    text = placeholderText,
                                    fontSize = 14.sp
                                )
                            },
                            supportingText = {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    if (inputText.length > 800) {
                                        val remaining = 1000 - inputText.length
                                        val isOver = remaining < 0
                                        Text(
                                            text = if (isOver) {
                                                if (selectedLanguage == "hi") "सीमा समाप्त: ${-remaining} वर्ण अधिक" else "Limit exceeded by ${-remaining} chars"
                                            } else {
                                                if (selectedLanguage == "hi") "$remaining वर्ण शेष" else "$remaining characters left"
                                            },
                                            color = if (isOver) ErrorRed else TextMuted,
                                            fontSize = 11.sp
                                        )
                                    } else {
                                        Spacer(modifier = Modifier.weight(1f))
                                    }

                                    Text(
                                        text = "${inputText.length}/1000",
                                        color = if (inputText.length > 1000) ErrorRed else TextMuted,
                                        fontSize = 11.sp,
                                        fontWeight = if (inputText.length > 1000) FontWeight.Bold else FontWeight.Normal
                                    )
                                }
                            },
                            isError = inputText.length > 1000,
                            modifier = Modifier
                                .weight(1f)
                                .padding(end = 6.dp),
                            shape = RoundedCornerShape(24.dp),
                            maxLines = 4,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = ForestGreenPrimary,
                                unfocusedBorderColor = Color(0xFFCCCCCC),
                                errorBorderColor = ErrorRed
                            ),
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                            keyboardActions = KeyboardActions(
                                onSend = {
                                    if (inputText.isNotBlank() && inputText.length <= 1000 && uiState !is ChatUiState.Loading) {
                                        Log.d("AgriMindChat", "IME Send triggered: queryLen=${inputText.trim().length}")
                                        keyboardController?.hide()
                                        viewModel.sendMessage(inputText)
                                    }
                                }
                            )
                        )

                        // Microphone Voice Input Button
                        val isListeningOrProcessing = (voiceInputState is VoiceInputState.Listening || voiceInputState is VoiceInputState.Processing)
                        FilledIconButton(
                            onClick = {
                                if (isListeningOrProcessing) {
                                    stopListening(cancel = false)
                                } else {
                                    viewModel.dismissVoiceError()
                                    val hasPerm = ContextCompat.checkSelfPermission(
                                        context,
                                        Manifest.permission.RECORD_AUDIO
                                    ) == PackageManager.PERMISSION_GRANTED

                                    if (hasPerm) {
                                        startListening()
                                    } else {
                                        permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                                    }
                                }
                            },
                            colors = IconButtonDefaults.filledIconButtonColors(
                                containerColor = if (isListeningOrProcessing) ErrorRed else Color(0xFFE8F5E9)
                            ),
                            modifier = Modifier
                                .size(48.dp)
                                .padding(end = 4.dp)
                        ) {
                            Icon(
                                imageVector = if (isListeningOrProcessing) Icons.Default.MicOff else Icons.Default.Mic,
                                contentDescription = if (isListeningOrProcessing) "Stop listening" else "Voice input",
                                tint = if (isListeningOrProcessing) Color.White else ForestGreenPrimary
                            )
                        }

                        // Send Button
                        val canSend = inputText.isNotBlank() && inputText.length <= 1000 && uiState !is ChatUiState.Loading
                        FilledIconButton(
                            onClick = {
                                if (canSend) {
                                    Log.d("AgriMindChat", "Send button tapped: queryLen=${inputText.trim().length}")
                                    keyboardController?.hide()
                                    viewModel.sendMessage(inputText)
                                }
                            },
                            enabled = canSend,
                            colors = IconButtonDefaults.filledIconButtonColors(
                                containerColor = ForestGreenPrimary,
                                disabledContainerColor = Color(0xFFE0E0E0)
                            ),
                            modifier = Modifier.size(48.dp)
                        ) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.Send,
                                contentDescription = "Send",
                                tint = if (canSend) Color.White else Color.Gray
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = if (selectedLanguage == "hi") {
                            "साक्ष्य सूचना: मार्गदर्शन विश्वविद्यालय विस्तार साहित्य से संकलित है। बहु-संवाद संदर्भ सीमित है।"
                        } else {
                            "Grounding Notice: Guidance is synthesized strictly from university extension literature. Multi-turn dialogue context is bounded."
                        },
                        fontSize = 10.sp,
                        color = TextMuted,
                        lineHeight = 12.sp,
                        modifier = Modifier.padding(horizontal = 4.dp)
                    )
                }
            }
        }
    }

    // Dogri Informational Dialog
    if (showDogriDialog) {
        AlertDialog(
            onDismissRequest = { showDogriDialog = false },
            title = {
                Text(
                    text = "डोगरी भाषा सहायता (Dogri Language)",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    text = "डोगरी (Dogri) भाषा सहायता, अनुवाद और ध्वनि मॉडल वर्तमान में सक्रिय विकासाधीन हैं।\n\nसत्यापित कृषि निर्णय समर्थन के लिए कृपया अंग्रेजी (English) या हिंदी (Hindi) का उपयोग करें।\n\n(Dogri speech recognition and agricultural translation models are currently in active development. Please select English or Hindi for verified decision support.)"
                )
            },
            confirmButton = {
                TextButton(onClick = { showDogriDialog = false }) {
                    Text("ठीक है (OK)", color = ForestGreenPrimary, fontWeight = FontWeight.Bold)
                }
            }
        )
    }

    // Chat History Modal Bottom Sheet
    if (showHistorySheet) {
        ModalBottomSheet(
            onDismissRequest = { showHistorySheet = false },
            containerColor = Color.White
        ) {
            ChatHistorySheetContent(
                conversations = conversations,
                currentConversationId = currentConversationId,
                selectedLanguage = selectedLanguage,
                onSelectConversation = { convId ->
                    viewModel.loadConversation(convId)
                    showHistorySheet = false
                },
                onNewChat = {
                    viewModel.startNewConversation()
                    showHistorySheet = false
                },
                onDeleteConversation = { conv ->
                    conversationToDelete = conv
                }
            )
        }
    }

    // Delete Conversation Confirmation Dialog
    if (conversationToDelete != null) {
        val conv = conversationToDelete!!
        val isHindi = (selectedLanguage == "hi")
        AlertDialog(
            onDismissRequest = { conversationToDelete = null },
            icon = {
                Icon(
                    imageVector = Icons.Default.DeleteOutline,
                    contentDescription = null,
                    tint = ErrorRed
                )
            },
            title = {
                Text(
                    text = if (isHindi) "बातचीत हटाएं?" else "Delete Conversation?",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    text = if (isHindi)
                        "क्या आप वाकई '${conv.title}' बातचीत को स्थायी रूप से हटाना चाहते हैं? यह क्रिया पूर्ववत नहीं की जा सकती।"
                    else
                        "Are you sure you want to permanently delete '${conv.title}'? This action cannot be undone."
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        viewModel.deleteConversation(conv.id)
                        conversationToDelete = null
                    }
                ) {
                    Text(
                        text = if (isHindi) "हटाएं" else "Delete",
                        color = ErrorRed,
                        fontWeight = FontWeight.Bold
                    )
                }
            },
            dismissButton = {
                TextButton(onClick = { conversationToDelete = null }) {
                    Text(text = if (isHindi) "रद्द करें" else "Cancel")
                }
            }
        )
    }
}

/**
 * Top bar segment for language selection: English, Hindi, and Dogri (coming soon).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LanguageSelectorBar(
    currentLanguage: String,
    onLanguageSelected: (String) -> Unit,
    onDogriSelected: () -> Unit
) {
    Surface(
        color = Color.White,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Language,
                    contentDescription = null,
                    tint = ForestGreenPrimary,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "भाषा / Language:",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    color = TextPrimary
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                // English Chip
                FilterChip(
                    selected = (currentLanguage == "en"),
                    onClick = { onLanguageSelected("en") },
                    label = { Text("English", fontSize = 11.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = ForestGreenPrimary,
                        selectedLabelColor = Color.White
                    )
                )

                // Hindi Chip
                FilterChip(
                    selected = (currentLanguage == "hi"),
                    onClick = { onLanguageSelected("hi") },
                    label = { Text("हिंदी", fontSize = 11.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = ForestGreenPrimary,
                        selectedLabelColor = Color.White
                    )
                )

                // Dogri Chip
                FilterChip(
                    selected = (currentLanguage == "doi"),
                    onClick = { onLanguageSelected("doi") },
                    label = { Text("डोगरी", fontSize = 11.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = ForestGreenPrimary,
                        selectedLabelColor = Color.White
                    )
                )
            }
        }
    }
}

/**
 * Formats individual chat message bubbles for user vs assistant.
 */
@Composable
fun ChatMessageBubble(
    message: UiChatMessage,
    isSpeaking: Boolean = false,
    onToggleTts: (() -> Unit)? = null,
    onOpenUrl: (String) -> Unit
) {
    val isUser = message.role == "user"

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 320.dp)
                .clip(
                    if (isUser) {
                        RoundedCornerShape(16.dp, 16.dp, 2.dp, 16.dp)
                    } else {
                        RoundedCornerShape(16.dp, 16.dp, 16.dp, 2.dp)
                    }
                )
                .background(
                    when {
                        isUser -> ForestGreenPrimary
                        message.isError -> ErrorRedLight
                        else -> SurfaceCard
                    }
                )
                .border(
                    width = 1.dp,
                    color = when {
                        isUser -> Color.Transparent
                        message.isError -> ErrorRed
                        else -> Color(0xFFE0E0E0)
                    },
                    shape = if (isUser) {
                        RoundedCornerShape(16.dp, 16.dp, 2.dp, 16.dp)
                    } else {
                        RoundedCornerShape(16.dp, 16.dp, 16.dp, 2.dp)
                    }
                )
                .padding(12.dp)
        ) {
            Column {
                // Header badge for assistant messages
                if (!isUser) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 6.dp)
                    ) {
                        Icon(
                            imageVector = if (message.isError) Icons.Default.Warning else Icons.Default.Eco,
                            contentDescription = null,
                            tint = if (message.isError) ErrorRed else ForestGreenPrimary,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = if (message.isError) "System Error" else "AgriMind Expert",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (message.isError) ErrorRed else ForestGreenDark
                        )

                        if (!message.isError && message.diseaseTarget != null) {
                            Spacer(modifier = Modifier.width(6.dp))
                            Surface(
                                color = Color(0xFFE8F5E9),
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = message.diseaseTarget.replace("Tomato___", "").replace("_", " "),
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = ForestGreenPrimary,
                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                                )
                            }
                        }

                        // Spoken Answer (TTS) Toggle Button
                        if (!message.isError && onToggleTts != null) {
                            Spacer(modifier = Modifier.weight(1f))
                            IconButton(
                                onClick = onToggleTts,
                                modifier = Modifier.size(24.dp)
                            ) {
                                Icon(
                                    imageVector = if (isSpeaking) Icons.Default.VolumeOff else Icons.Default.VolumeUp,
                                    contentDescription = if (isSpeaking) "Stop reading aloud" else "Read answer aloud",
                                    tint = if (isSpeaking) ForestGreenPrimary else Color.Gray,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        }
                    }
                }

                // Message Text Content
                Text(
                    text = message.content,
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                    color = when {
                        isUser -> Color.White
                        message.isError -> ErrorRed
                        else -> TextPrimary
                    }
                )

                // Insufficient Evidence Gating Notice
                if (!isUser && !message.hasSufficientEvidence && !message.isError) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Surface(
                        color = Color(0xFFFFF3E0),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Info,
                                contentDescription = null,
                                tint = Color(0xFFE65100),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Evidence-Gated: Outside verified tomato disease literature.",
                                fontSize = 11.sp,
                                color = Color(0xFFE65100),
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                // Supporting Institutional Citations
                if (!isUser && message.citations.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(10.dp))
                    HorizontalDivider(color = Color(0xFFEEEEEE), thickness = 1.dp)
                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "Supporting Extension Literature:",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark,
                        modifier = Modifier.padding(bottom = 4.dp)
                    )

                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        message.citations.forEach { cit ->
                            CitationCard(citation = cit, onOpenUrl = onOpenUrl)
                        }
                    }
                }
            }
        }
    }
}

/**
 * Clickable institutional citation card linking to published university research.
 */
@Composable
fun CitationCard(
    citation: ChatCitationItem,
    onOpenUrl: (String) -> Unit
) {
    Surface(
        color = Color(0xFFF1F8E9),
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(0.5.dp, Color(0xFFC8E6C9)),
        modifier = Modifier
            .fillMaxWidth()
            .clickable {
                if (citation.sourceUrl.isNotBlank()) {
                    onOpenUrl(citation.sourceUrl)
                }
            }
    ) {
        Row(
            modifier = Modifier.padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                shape = CircleShape,
                color = ForestGreenPrimary,
                modifier = Modifier.size(18.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        text = citation.citationNumber.toString(),
                        color = Color.White,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Spacer(modifier = Modifier.width(8.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = citation.title,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = TextPrimary,
                    maxLines = 1
                )
                Text(
                    text = citation.institution,
                    fontSize = 10.sp,
                    color = TextMuted
                )
            }

            if (citation.sourceUrl.isNotBlank()) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.OpenInNew,
                    contentDescription = "Open source",
                    tint = ForestGreenPrimary,
                    modifier = Modifier.size(14.dp)
                )
            }
        }
    }
}

/**
 * Typing / RAG retrieval loading animation bubble.
 */
@Composable
fun AssistantLoadingBubble(language: String = "en") {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.Start
    ) {
        Surface(
            color = SurfaceCard,
            shape = RoundedCornerShape(16.dp, 16.dp, 16.dp, 2.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE0E0E0)),
            modifier = Modifier.padding(4.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                CircularProgressIndicator(
                    color = ForestGreenPrimary,
                    strokeWidth = 2.dp,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (language == "hi") "विस्तार साहित्य की खोज जारी है..." else "Retrieving extension literature...",
                    fontSize = 12.sp,
                    fontStyle = FontStyle.Italic,
                    color = TextMuted
                )
            }
        }
    }
}

/**
 * Empty conversation placeholder displaying suggested question chips.
 */
@Composable
fun EmptyChatPromptView(
    caseId: String?,
    language: String = "en",
    onSuggestionSelected: (String) -> Unit
) {
    val suggestions = if (language == "hi") {
        if (caseId != null) {
            listOf(
                "इस रोग के नियंत्रण के लिए आपातकालीन कदम क्या हैं?",
                "क्या यह फल को संक्रमित कर सकता है?",
                "पड़ोसी टमाटर के पौधों की रक्षा कैसे करें?",
                "कौन से कवकनाशी उपचार प्रभावी हैं?"
            )
        } else {
            listOf(
                "टमाटर को स्वस्थ कैसे उगाएं?",
                "टमाटर में पानी और खाद देने का सही तरीका क्या है?",
                "पछेती झुलसा (Late Blight) का नियंत्रण कैसे करें?",
                "अगेती झुलसा (Early Blight) के लक्षण क्या हैं?"
            )
        }
    } else {
        if (caseId != null) {
            listOf(
                "What emergency actions should I take for this case?",
                "Can this pathogen infect green fruit?",
                "How do I prevent transmission to adjacent plants?",
                "What protectant fungicides are recommended?"
            )
        } else {
            listOf(
                "how can i grow tomato healthy",
                "How to control Early Blight?",
                "Late Blight fungicide recommendations",
                "tomato watering and soil care"
            )
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Surface(
            shape = CircleShape,
            color = Color(0xFFE8F5E9),
            modifier = Modifier.size(64.dp)
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Default.Forum,
                    contentDescription = null,
                    tint = ForestGreenPrimary,
                    modifier = Modifier.size(32.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = if (language == "hi") "एग्रीमाइंड कृषि निर्णय सहायक" else "AgriMind Decision Assistant",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = ForestGreenDark
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = if (language == "hi") {
                "सत्यापित विश्वविद्यालय विस्तार प्रकाशनों पर आधारित साक्ष्य-समर्थित उत्तर प्राप्त करें।"
            } else {
                "Ask questions grounded strictly in university agricultural extension research."
            },
            fontSize = 12.sp,
            color = TextMuted,
            lineHeight = 16.sp,
            modifier = Modifier.padding(horizontal = 16.dp)
        )

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = if (language == "hi") "सुझाए गए प्रश्न (Suggested Prompts):" else "Suggested Inquiries:",
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color = TextPrimary,
            modifier = Modifier.align(Alignment.Start)
        )

        Spacer(modifier = Modifier.height(8.dp))

        suggestions.forEach { prompt ->
            Surface(
                color = Color.White,
                shape = RoundedCornerShape(20.dp),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFDCE7D6)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp)
                    .clickable { onSuggestionSelected(prompt) }
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.HelpOutline,
                        contentDescription = null,
                        tint = ForestGreenPrimary,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = prompt,
                        fontSize = 12.sp,
                        color = TextPrimary
                    )
                }
            }
        }
    }
}

/**
 * Material 3 Bottom Sheet Content presenting saved conversation history,
 * allowing users to view timestamps, open past threads, start new chats, or delete conversations.
 */
@Composable
fun ChatHistorySheetContent(
    conversations: List<ConversationEntity>,
    currentConversationId: String?,
    selectedLanguage: String,
    onSelectConversation: (String) -> Unit,
    onNewChat: () -> Unit,
    onDeleteConversation: (ConversationEntity) -> Unit
) {
    val isHindi = (selectedLanguage == "hi")
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .padding(bottom = 28.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = if (isHindi) "सहेजी गई बातचीत (History)" else "Saved Conversations",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenPrimary
            )

            Button(
                onClick = onNewChat,
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = if (isHindi) "+ नया संवाद" else "+ New Chat",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

        if (conversations.isEmpty()) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 36.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    imageVector = Icons.Default.ChatBubbleOutline,
                    contentDescription = null,
                    tint = TextMuted,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = if (isHindi) "कोई सहेजी गई बातचीत नहीं है" else "No saved conversations yet",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = TextMuted
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = if (isHindi) "आपकी बातचीत स्वतः यहाँ सहेजी जाएगी।" else "Your conversations with AgriMind will be saved here.",
                    fontSize = 12.sp,
                    color = TextMuted.copy(alpha = 0.8f)
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 420.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(conversations, key = { it.id }) { conv ->
                    val isSelected = (conv.id == currentConversationId)
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = if (isSelected) Color(0xFFE8F5E9) else Color(0xFFF7F7F7),
                        border = if (isSelected) BorderStroke(1.dp, ForestGreenPrimary) else null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelectConversation(conv.id) }
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = conv.title,
                                    fontSize = 14.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (isSelected) ForestGreenPrimary else Color(0xFF1B1B1B),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    val dateStr = SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()).format(Date(conv.updatedAt))
                                    Text(
                                        text = dateStr,
                                        fontSize = 11.sp,
                                        color = TextMuted
                                    )
                                    Surface(
                                        shape = RoundedCornerShape(4.dp),
                                        color = if (conv.language == "hi") SuccessGreenLight else Color(0xFFE0E0E0)
                                    ) {
                                        Text(
                                            text = if (conv.language == "hi") "हिन्दी" else "EN",
                                            fontSize = 9.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = if (conv.language == "hi") ForestGreenPrimary else Color(0xFF555555),
                                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                        )
                                    }
                                    if (!conv.caseId.isNullOrBlank()) {
                                        Text(
                                            text = "Case: ${conv.caseId.take(8)}",
                                            fontSize = 11.sp,
                                            color = ForestGreenDark
                                        )
                                    }
                                }
                            }

                            IconButton(
                                onClick = { onDeleteConversation(conv) },
                                modifier = Modifier.size(32.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.DeleteOutline,
                                    contentDescription = "Delete",
                                    tint = ErrorRed.copy(alpha = 0.8f),
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
