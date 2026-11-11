package com.agrimind.app.ui.viewmodel

import com.agrimind.app.data.model.HealthResponse

/**
 * UI State for the AgriMind Backend Connection Screen.
 */
sealed interface HealthUiState {
    object Idle : HealthUiState
    object Loading : HealthUiState
    data class Success(val data: HealthResponse) : HealthUiState
    data class Error(
        val message: String,
        val urlAttempted: String,
        val canRetry: Boolean = true
    ) : HealthUiState
}

