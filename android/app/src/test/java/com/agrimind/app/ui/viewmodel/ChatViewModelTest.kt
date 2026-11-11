package com.agrimind.app.ui.viewmodel

import android.app.Application
import com.agrimind.app.data.repository.InMemoryChatRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for ChatViewModel dictation buffering, smart overlap removal,
 * transcript persistence, client-side message validation, Hindi language detection,
 * and persistent conversation lifecycle.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class ChatViewModelTest {

    private lateinit var viewModel: ChatViewModel
    private lateinit var testRepository: InMemoryChatRepository

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        val app = Application()
        testRepository = InMemoryChatRepository()
        viewModel = ChatViewModel(app, testRepository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // =========================================================================
    // smartAppend Unit Tests
    // =========================================================================

    @Test
    fun testSmartAppend_emptyBase_returnsAddition() {
        val result = smartAppend("", "How can I grow healthy tomato plants?")
        assertEquals("How can I grow healthy tomato plants?", result)
    }

    @Test
    fun testSmartAppend_emptyAddition_preservesBase() {
        val result = smartAppend("How can I grow", "")
        assertEquals("How can I grow", result)
    }

    @Test
    fun testSmartAppend_whitespaceAddition_preservesBase() {
        val result = smartAppend("How can I grow", "    \n  ")
        assertEquals("How can I grow", result)
    }

    @Test
    fun testSmartAppend_cleanSeparation_appendsWithSpace() {
        val result = smartAppend("What is", "early blight?")
        assertEquals("What is early blight?", result)
    }

    @Test
    fun testSmartAppend_singleWordOverlap_eliminatesDuplicate() {
        val result = smartAppend("symptoms of", "of early blight")
        assertEquals("symptoms of early blight", result)
    }

    @Test
    fun testSmartAppend_multiWordOverlap_eliminatesDuplicateWords() {
        val result = smartAppend("How to control", "to control early blight")
        assertEquals("How to control early blight", result)
    }

    @Test
    fun testSmartAppend_exactDuplicate_returnsExistingText() {
        val result = smartAppend("healthy tomato plants", "healthy tomato plants")
        assertEquals("healthy tomato plants", result)
    }

    @Test
    fun testSmartAppend_additionIsSuffix_returnsBase() {
        val result = smartAppend("grow healthy tomato plants", "tomato plants")
        assertEquals("grow healthy tomato plants", result)
    }

    @Test
    fun testSmartAppend_baseIsPrefix_returnsExpandedAddition() {
        val result = smartAppend("grow", "grow healthy tomato plants")
        assertEquals("grow healthy tomato plants", result)
    }

    // =========================================================================
    // Dictation Buffering & Transcript Persistence Tests
    // =========================================================================

    @Test
    fun testDictation_finalRecognitionUpdatesDraft() {
        viewModel.startDictationSession()
        viewModel.finalizeDictation("How to treat tomato early blight?")
        assertEquals("How to treat tomato early blight?", viewModel.inputText.value)
    }

    @Test
    fun testDictation_partialResultsStreamIntoDraft() {
        viewModel.startDictationSession()
        viewModel.updatePartialDictation("How")
        assertEquals("How", viewModel.inputText.value)

        viewModel.updatePartialDictation("How to treat")
        assertEquals("How to treat", viewModel.inputText.value)

        viewModel.finalizeDictation("How to treat tomato early blight?")
        assertEquals("How to treat tomato early blight?", viewModel.inputText.value)
    }

    @Test
    fun testDictation_emptyCallbackDoesNotErasePartialTranscript() {
        // User spoke something captured via partial results
        viewModel.startDictationSession()
        viewModel.updatePartialDictation("How can I grow")

        // Final callback is empty or blank (e.g. low-confidence silence timeout)
        viewModel.finalizeCurrentDictation()

        // Draft must retain the partial transcript!
        assertEquals("How can I grow", viewModel.inputText.value)
    }

    @Test
    fun testDictation_multiPartDictationPreservesEarlierText() {
        // Session 1
        viewModel.startDictationSession()
        viewModel.finalizeDictation("What is early blight")
        assertEquals("What is early blight", viewModel.inputText.value)

        // Session 2 continues
        viewModel.startDictationSession()
        viewModel.updatePartialDictation("and how to control it?")
        viewModel.finalizeDictation("and how to control it?")

        assertEquals("What is early blight and how to control it?", viewModel.inputText.value)
    }

    @Test
    fun testDictation_multiPartWithWordOverlap_avoidsDuplication() {
        // Session 1 ended with "symptoms of"
        viewModel.startDictationSession()
        viewModel.finalizeDictation("What are the symptoms of")

        // Session 2 began repeating "of early blight"
        viewModel.startDictationSession()
        viewModel.finalizeDictation("of early blight?")

        assertEquals("What are the symptoms of early blight?", viewModel.inputText.value)
    }

    @Test
    fun testDictation_manualKeyboardEditPreservedAcrossSession() {
        // User dictated
        viewModel.startDictationSession()
        viewModel.finalizeDictation("Tomato blight")

        // User edited with keyboard
        viewModel.setInputText("Tomato late blight in greenhouse")

        // User starts next dictation session
        viewModel.startDictationSession()
        viewModel.finalizeDictation("spray schedule")

        assertEquals("Tomato late blight in greenhouse spray schedule", viewModel.inputText.value)
    }

    @Test
    fun testDictation_cancelActiveDictationRevertsOnlyActiveSession() {
        viewModel.setInputText("Existing notes")
        viewModel.startDictationSession()
        viewModel.updatePartialDictation("accidental speech")

        // Explicit user cancel
        viewModel.cancelActiveDictation()

        // Prior base text is restored
        assertEquals("Existing notes", viewModel.inputText.value)
    }

    // =========================================================================
    // Client-side Send & Validation Tests
    // =========================================================================

    @Test
    fun testSendMessage_rejectsEmptyQuery() {
        viewModel.sendMessage("   ")
        assertTrue(viewModel.uiState.value is ChatUiState.Error)
        val error = (viewModel.uiState.value as ChatUiState.Error).message
        assertTrue(error.contains("Please enter or speak a question"))
        assertTrue(viewModel.messages.value.isEmpty())
    }

    @Test
    fun testSendMessage_rejectsOversizedQueryWithoutClearingDraft() {
        val longText = "a".repeat(1005)
        viewModel.setInputText(longText)

        viewModel.sendMessage(longText)

        // Must transition to Error with specific excess character count
        assertTrue(viewModel.uiState.value is ChatUiState.Error)
        val error = (viewModel.uiState.value as ChatUiState.Error).message
        assertTrue(error.contains("1005/1000"))
        assertTrue(error.contains("5 characters"))

        // Draft text must NOT be cleared, so user can edit and shorten!
        assertEquals(longText, viewModel.inputText.value)
        assertTrue(viewModel.messages.value.isEmpty())
    }

    @Test
    fun testSendMessage_acceptsValidQueryAndClearsDraft() {
        viewModel.setInputText("How to manage bacterial spot?")
        viewModel.sendMessage("How to manage bacterial spot?")

        // Draft is cleared upon acceptance
        assertEquals("", viewModel.inputText.value)

        // User message is placed into dialogue stream
        assertEquals(1, viewModel.messages.value.size)
        assertEquals("user", viewModel.messages.value[0].role)
        assertEquals("How to manage bacterial spot?", viewModel.messages.value[0].content)

        // State moves to Loading while network request executes
        assertTrue(viewModel.uiState.value is ChatUiState.Loading || viewModel.uiState.value is ChatUiState.Error)
    }

    // =========================================================================
    // Language Detection & Response Consistency Tests (Stage B.7)
    // =========================================================================

    @Test
    fun testDetectLanguage_hindiQueryDetected() {
        val hindiQuery = "टमाटर के पौधों को स्वस्थ कैसे रखें?"
        assertEquals("hi", viewModel.detectLanguage(hindiQuery))
    }

    @Test
    fun testDetectLanguage_englishQueryDetected() {
        val englishQuery = "How can I keep my tomato plants healthy?"
        assertEquals("en", viewModel.detectLanguage(englishQuery))
    }

    @Test
    fun testDetectLanguage_mixedQueryWithHindiCharactersDetectedAsHindi() {
        val mixedQuery = "Tomato plant टमाटर रोग"
        assertEquals("hi", viewModel.detectLanguage(mixedQuery))
    }

    @Test
    fun testSendMessage_automaticallySwitchesLanguageToHindiForDevanagariQuery() {
        viewModel.setLanguage("en")
        val hindiQuery = "टमाटर के पौधों को स्वस्थ कैसे रखें?"
        viewModel.sendMessage(hindiQuery)

        // Selected language in ViewModel should automatically synchronize to Hindi
        assertEquals("hi", viewModel.selectedLanguage.value)
    }

    // =========================================================================
    // Persistent Conversation Storage & Lifecycle Tests (Stage B.7)
    // =========================================================================

    @Test
    fun testConversation_createdWhenSendingMessage() = runBlocking {
        viewModel.sendMessage("What are the symptoms of early blight?")

        val convId = viewModel.currentConversationId.value
        assertTrue(!convId.isNullOrBlank())

        val convs = testRepository.getAllConversations()
        assertEquals(1, convs.size)
        assertEquals(convId, convs[0].id)
        assertTrue(convs[0].title.startsWith("What are the symptoms"))

        val messages = testRepository.getMessagesForConversation(convId!!)
        assertEquals(1, messages.size)
        assertEquals("What are the symptoms of early blight?", messages[0].content)
        assertEquals("user", messages[0].role)
    }

    @Test
    fun testConversation_loadRestoresMessagesInCorrectOrder() = runBlocking {
        val conv = testRepository.createConversation("Test Bacterial Spot", language = "en")
        testRepository.saveMessage(
            conv.id,
            UiChatMessage(role = "user", content = "First question", timestamp = 1000L)
        )
        testRepository.saveMessage(
            conv.id,
            UiChatMessage(role = "assistant", content = "First answer", timestamp = 2000L)
        )

        viewModel.loadConversation(conv.id)

        assertEquals(conv.id, viewModel.currentConversationId.value)
        assertEquals(2, viewModel.messages.value.size)
        assertEquals("First question", viewModel.messages.value[0].content)
        assertEquals("user", viewModel.messages.value[0].role)
        assertEquals("First answer", viewModel.messages.value[1].content)
        assertEquals("assistant", viewModel.messages.value[1].role)
    }

    @Test
    fun testConversation_startNewResetsActiveThreadWithoutDeletingOld() = runBlocking {
        viewModel.sendMessage("Question 1")
        val firstId = viewModel.currentConversationId.value
        assertTrue(firstId != null)

        viewModel.startNewConversation()
        assertNull(viewModel.currentConversationId.value)
        assertTrue(viewModel.messages.value.isEmpty())

        // The previous conversation must remain safe in storage
        val all = testRepository.getAllConversations()
        assertEquals(1, all.size)
        assertEquals(firstId, all[0].id)
    }

    @Test
    fun testConversation_deleteRemovesActiveThreadAndMessages() = runBlocking {
        val conv1 = testRepository.createConversation("Conv 1")
        val conv2 = testRepository.createConversation("Conv 2")
        testRepository.saveMessage(conv1.id, UiChatMessage(role = "user", content = "Message 1"))
        testRepository.saveMessage(conv2.id, UiChatMessage(role = "user", content = "Message 2"))

        viewModel.loadConversation(conv1.id)
        assertEquals(conv1.id, viewModel.currentConversationId.value)

        viewModel.deleteConversation(conv1.id)

        // Active thread should be reset
        assertNull(viewModel.currentConversationId.value)
        assertTrue(viewModel.messages.value.isEmpty())

        // Only conv2 remains in storage; conv1 and its messages are removed
        val remaining = testRepository.getAllConversations()
        assertEquals(1, remaining.size)
        assertEquals(conv2.id, remaining[0].id)
        assertTrue(testRepository.getMessagesForConversation(conv1.id).isEmpty())
        assertEquals(1, testRepository.getMessagesForConversation(conv2.id).size)
    }

    @Test
    fun testConversation_startNewResetsCaseContextAndActiveDiagnosis() {
        viewModel.setCaseContext("CASE-9999", "Tomato___Early_blight")
        assertEquals("CASE-9999", viewModel.caseId.value)

        viewModel.startNewConversation()
        assertNull(viewModel.caseId.value)
        assertTrue(viewModel.messages.value.isEmpty())
    }

    @Test
    fun testConversation_loadNonCaseThreadResetsCaseContext() = runBlocking {
        viewModel.setCaseContext("CASE-1234", "Tomato___Late_blight")
        assertEquals("CASE-1234", viewModel.caseId.value)

        val nonCaseConv = testRepository.createConversation("General Tomato Question", language = "en", caseId = null)
        viewModel.loadConversation(nonCaseConv.id)

        assertNull(viewModel.caseId.value)
    }

    @Test
    fun testSetCaseContext_formatsPreliminaryAssessmentDisclaimer() {
        viewModel.setCaseContext("CASE-ABC", "Tomato___Bacterial_spot")
        val greeting = viewModel.messages.value.firstOrNull()?.content ?: ""

        assertTrue(greeting.contains("Preliminary AI Assessment"))
        assertTrue(greeting.contains("Bacterial spot"))
        assertTrue(greeting.contains("does not replace expert field confirmation"))
    }
}
