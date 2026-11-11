package com.agrimind.app.ui.viewmodel

import android.graphics.Bitmap
import android.net.Uri
import com.agrimind.app.data.model.DiagnosisResponse

/**
 * UI State for the AgriMind Image Selection & Disease Diagnosis Flow.
 */
sealed interface DiagnosisUiState {

    /** Initial state: no image selected. */
    object Idle : DiagnosisUiState

    /** Image chosen and verified; ready for diagnosis submission. */
    data class ImageSelected(
        val uri: Uri,
        val bitmap: Bitmap,
        val fileName: String,
        val fileSizeBytes: Long
    ) : DiagnosisUiState

    /** Upload and multi-agent workflow inference in progress. */
    data class Diagnosing(
        val uri: Uri,
        val bitmap: Bitmap
    ) : DiagnosisUiState

    /** Diagnosis successfully received and verified. */
    data class Success(
        val response: DiagnosisResponse,
        val bitmap: Bitmap?
    ) : DiagnosisUiState

    /** Failure encountered during file validation, network upload, or inference. */
    data class Error(
        val errorMessage: String,
        val bitmap: Bitmap?,
        val canRetry: Boolean = true
    ) : DiagnosisUiState

    /** Saved offline due to lack of network connectivity. */
    data class QueuedOffline(
        val uri: Uri,
        val bitmap: Bitmap,
        val message: String
    ) : DiagnosisUiState
}

