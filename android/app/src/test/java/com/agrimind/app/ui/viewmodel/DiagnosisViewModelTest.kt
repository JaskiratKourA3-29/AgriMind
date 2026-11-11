package com.agrimind.app.ui.viewmodel

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for DiagnosisViewModel image validation, duplicate submission protection,
 * error parsing, and state lifecycle transitions.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class DiagnosisViewModelTest {

    private lateinit var viewModel: DiagnosisViewModel
    private lateinit var app: Application

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        app = Application()
        viewModel = DiagnosisViewModel(app)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialState_isIdle() {
        assertTrue(viewModel.uiState.value is DiagnosisUiState.Idle)
    }

    @Test
    fun testRunDiagnosis_withoutImage_returnsErrorWithoutRetry() {
        viewModel.runDiagnosis()

        val state = viewModel.uiState.value
        assertTrue(state is DiagnosisUiState.Error)
        val errorState = state as DiagnosisUiState.Error
        assertEquals("No valid image selected. Please choose a tomato leaf photo first.", errorState.errorMessage)
        assertFalse(errorState.canRetry)
        assertNull(errorState.bitmap)
    }

    @Test
    fun testOnRemoveImage_resetsStateToIdle() {
        // Trigger an error state first
        viewModel.runDiagnosis()
        assertTrue(viewModel.uiState.value is DiagnosisUiState.Error)

        // Removing image should return to Idle
        viewModel.onRemoveImage()
        assertTrue(viewModel.uiState.value is DiagnosisUiState.Idle)
    }

    @Test
    fun testDetectMimeType_recognizesSupportedImageFormats() {
        // JPEG magic bytes: FF D8 FF
        val jpegBytes = byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE0.toByte())
        assertEquals("image/jpeg", viewModel.detectMimeType(jpegBytes))

        // PNG magic bytes: 89 50 4E 47
        val pngBytes = byteArrayOf(0x89.toByte(), 0x50.toByte(), 0x4E.toByte(), 0x47.toByte())
        assertEquals("image/png", viewModel.detectMimeType(pngBytes))

        // GIF magic bytes: 47 49 46
        val gifBytes = byteArrayOf(0x47.toByte(), 0x49.toByte(), 0x46.toByte(), 0x38.toByte())
        assertEquals("image/gif", viewModel.detectMimeType(gifBytes))

        // BMP magic bytes: 42 4D
        val bmpBytes = byteArrayOf(0x42.toByte(), 0x4D.toByte(), 0x00.toByte(), 0x00.toByte())
        assertEquals("image/bmp", viewModel.detectMimeType(bmpBytes))
    }

    @Test
    fun testDetectMimeType_rejectsUnsupportedAndCorruptedHeaders() {
        // Plain text "Hello"
        val textBytes = "Hello world".toByteArray()
        assertNull(viewModel.detectMimeType(textBytes))

        // PDF "%PDF"
        val pdfBytes = "%PDF-1.4".toByteArray()
        assertNull(viewModel.detectMimeType(pdfBytes))

        // Less than 4 bytes
        val shortBytes = byteArrayOf(0xFF.toByte(), 0xD8.toByte())
        assertNull(viewModel.detectMimeType(shortBytes))

        // Random garbage
        val garbageBytes = byteArrayOf(0x00, 0x01, 0x02, 0x03)
        assertNull(viewModel.detectMimeType(garbageBytes))
    }

    @Test
    fun testParseErrorMessage_extractsFastApiDetail() {
        val json = """{"detail": "Uploaded file exceeds maximum limit of 15MB."}"""
        val parsed = viewModel.parseErrorMessage(json)
        assertEquals("Uploaded file exceeds maximum limit of 15MB.", parsed)

        val jsonEmpty = """{"detail": "Uploaded file is empty (0 bytes)."}"""
        val parsedEmpty = viewModel.parseErrorMessage(jsonEmpty)
        assertEquals("Uploaded file is empty (0 bytes).", parsedEmpty)
    }

    @Test
    fun testParseErrorMessage_fallsBackOnPlainString() {
        val plainText = "Service Unavailable"
        val parsed = viewModel.parseErrorMessage(plainText)
        assertEquals("Service Unavailable", parsed)

        val emptyText = ""
        val parsedBlank = viewModel.parseErrorMessage(emptyText)
        assertEquals("", parsedBlank)
    }
}

