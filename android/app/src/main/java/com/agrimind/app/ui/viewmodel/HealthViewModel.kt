package com.agrimind.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException

/**
 * ViewModel managing the AgriMind backend health check state.
 * Performs HTTP requests asynchronously on the IO dispatcher without blocking the UI thread.
 */
class HealthViewModel : ViewModel() {

    private val _uiState = MutableStateFlow<HealthUiState>(HealthUiState.Idle)
    val uiState: StateFlow<HealthUiState> = _uiState.asStateFlow()

    fun checkBackendHealth() {
        val targetUrl = RetrofitClient.getBaseUrl() + "health"
        _uiState.value = HealthUiState.Loading

        viewModelScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    RetrofitClient.apiService.getHealth()
                }

                if (response.isSuccessful && response.body() != null) {
                    _uiState.value = HealthUiState.Success(response.body()!!)
                } else {
                    val code = response.code()
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    _uiState.value = HealthUiState.Error(
                        message = "Backend returned HTTP $code: $errorBody",
                        urlAttempted = targetUrl
                    )
                }
            } catch (e: SocketTimeoutException) {
                _uiState.value = HealthUiState.Error(
                    message = "Connection timed out (15s). Ensure the cloud backend is reachable.",
                    urlAttempted = targetUrl
                )
            } catch (e: ConnectException) {
                _uiState.value = HealthUiState.Error(
                    message = "Connection refused at $targetUrl. Verify cloud backend server is reachable.",
                    urlAttempted = targetUrl
                )
            } catch (e: IOException) {
                _uiState.value = HealthUiState.Error(
                    message = "Network I/O error: ${e.localizedMessage ?: "Unable to reach server"}",
                    urlAttempted = targetUrl
                )
            } catch (e: Exception) {
                _uiState.value = HealthUiState.Error(
                    message = "Unexpected error: ${e.localizedMessage ?: e.javaClass.simpleName}",
                    urlAttempted = targetUrl
                )
            }
        }
    }

    fun updateBaseUrl(newUrl: String) {
        RetrofitClient.setBaseUrl(newUrl)
    }
}

