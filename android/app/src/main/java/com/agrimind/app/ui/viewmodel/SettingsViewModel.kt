package com.agrimind.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.AdminSystemStatusResponse
import com.agrimind.app.data.model.UserLoginRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val isLoggedIn: Boolean = false,
    val username: String = "Guest Farmer",
    val fullName: String = "AgriMind User",
    val role: String = "farmer",
    val language: String = "en",
    val isLoading: Boolean = false,
    val statusMessage: String? = null,
    val adminStatus: AdminSystemStatusResponse? = null,
    val gatewayUrl: String = RetrofitClient.DEFAULT_BASE_URL,
    val gatewayInput: String = RetrofitClient.DEFAULT_BASE_URL,
    val gatewayError: String? = null,
    val isTestingGateway: Boolean = false,
    val gatewayTestResult: String? = null,
    val gatewayTestSuccess: Boolean? = null
)

class SettingsViewModel(application: Application) : AndroidViewModel(application) {

    private val sessionManager = UserSessionManager.getInstance(application)
    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        val savedGateway = sessionManager.getGatewayUrl()
        if (!savedGateway.isNullOrBlank()) {
            RetrofitClient.setBaseUrl(savedGateway)
        }
        val currentGateway = RetrofitClient.getBaseUrl()
        _uiState.update {
            it.copy(
                gatewayUrl = currentGateway,
                gatewayInput = currentGateway
            )
        }
        refreshSession()
    }

    fun refreshSession() {
        val loggedIn = sessionManager.isLoggedIn()
        val token = sessionManager.getAuthToken()
        RetrofitClient.setAuthToken(token)

        _uiState.update {
            it.copy(
                isLoggedIn = loggedIn,
                username = sessionManager.getUsername(),
                fullName = sessionManager.getFullName(),
                role = sessionManager.getRole(),
                language = sessionManager.getLanguage()
            )
        }

        if (sessionManager.isAdmin()) {
            fetchAdminStatus()
        }
    }

    fun setLanguage(langCode: String) {
        sessionManager.setLanguage(langCode)
        _uiState.update { it.copy(language = langCode) }
    }

    fun login(username: String, pass: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, statusMessage = null) }
            try {
                val req = UserLoginRequest(
                    email = if (username.contains("@")) username else null,
                    username = if (!username.contains("@")) username else null,
                    password = pass
                )
                val resp = RetrofitClient.apiService.login(req)
                if (resp.isSuccessful && resp.body() != null) {
                    val auth = resp.body()!!
                    sessionManager.saveSession(
                        token = auth.accessToken,
                        userId = auth.effectiveUserId,
                        username = auth.username ?: auth.effectiveEmail,
                        role = auth.effectiveRole,
                        fullName = auth.effectiveFullName,
                        email = auth.effectiveEmail
                    )
                    RetrofitClient.setAuthToken(auth.accessToken)
                    _uiState.update {
                        it.copy(
                            isLoggedIn = true,
                            username = auth.username ?: auth.effectiveEmail,
                            fullName = auth.effectiveFullName,
                            role = auth.effectiveRole,
                            isLoading = false,
                            statusMessage = "Logged in successfully as ${auth.effectiveRole.uppercase()}"
                        )
                    }
                    if (sessionManager.isAdmin()) {
                        fetchAdminStatus()
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            statusMessage = "Authentication failed: ${resp.message()} (${resp.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        statusMessage = "Network error: ${e.localizedMessage ?: "Unable to connect to backend"}"
                    )
                }
            }
        }
    }

    fun loginAsDemoFarmer() {
        sessionManager.saveSession(
            token = "demo-farmer-session-token",
            userId = "usr-demo-farmer-01",
            username = "jammu_farmer",
            role = "farmer",
            fullName = "Raghubir Singh (R.S. Pura)"
        )
        refreshSession()
    }

    fun loginAsDemoAdmin() {
        sessionManager.saveSession(
            token = "demo-admin-session-token",
            userId = "usr-demo-admin-01",
            username = "agri_admin",
            role = "admin",
            fullName = "State Extension Officer (Jammu & Kashmir)"
        )
        refreshSession()
    }

    fun logout() {
        sessionManager.clearSession()
        RetrofitClient.setAuthToken(null)
        _uiState.update {
            it.copy(
                isLoggedIn = false,
                username = "Guest Farmer",
                fullName = "AgriMind User",
                role = "farmer",
                adminStatus = null,
                statusMessage = "Logged out successfully"
            )
        }
    }

    fun fetchAdminStatus() {
        viewModelScope.launch {
            try {
                val resp = RetrofitClient.apiService.getAdminSystemStatus()
                if (resp.isSuccessful && resp.body() != null) {
                    _uiState.update { it.copy(adminStatus = resp.body()) }
                }
            } catch (e: Exception) {
                // Admin status fetch is optional telemetry
            }
        }
    }

    fun setGatewayInput(input: String) {
        _uiState.update { it.copy(gatewayInput = input, gatewayError = null) }
    }

    private fun validateAndNormalizeUrl(raw: String): Pair<String?, String?> {
        val trimmed = raw.trim()
        if (trimmed.isBlank()) {
            return Pair(null, "Gateway URL cannot be empty.")
        }
        if (!trimmed.startsWith("http://", ignoreCase = true) && !trimmed.startsWith("https://", ignoreCase = true)) {
            return Pair(null, "URL must begin with http:// or https://")
        }
        val uri = try {
            java.net.URI(trimmed)
        } catch (e: Exception) {
            return Pair(null, "Invalid URL syntax: ${e.message}")
        }
        val host = uri.host
        if (host.isNullOrBlank()) {
            return Pair(null, "URL must contain a valid host name or IP address.")
        }

        // Production TLS enforcement: All remote gateway URLs must use secure HTTPS
        if (trimmed.startsWith("http://", ignoreCase = true)) {
            return Pair(null, "Production gateways must use secure HTTPS (https://). Cleartext HTTP is strictly prohibited.")
        }

        val normalized = if (trimmed.endsWith("/")) trimmed else "$trimmed/"
        return Pair(normalized, null)
    }

    fun saveGatewayUrl(urlToSave: String = _uiState.value.gatewayInput) {
        val (normalized, error) = validateAndNormalizeUrl(urlToSave)
        if (error != null) {
            _uiState.update { it.copy(gatewayError = error, gatewayTestResult = null, gatewayTestSuccess = null) }
            return
        }
        val target = normalized!!
        sessionManager.setGatewayUrl(target)
        RetrofitClient.setBaseUrl(target)
        _uiState.update {
            it.copy(
                gatewayUrl = target,
                gatewayInput = target,
                gatewayError = null,
                statusMessage = "Gateway URL updated to $target",
                gatewayTestResult = null,
                gatewayTestSuccess = null
            )
        }
    }

    fun resetToEmulatorGateway() {
        val defaultUrl = RetrofitClient.DEFAULT_BASE_URL
        sessionManager.setGatewayUrl(null)
        RetrofitClient.setBaseUrl(defaultUrl)
        _uiState.update {
            it.copy(
                gatewayUrl = defaultUrl,
                gatewayInput = defaultUrl,
                gatewayError = null,
                statusMessage = "Gateway reset to Emulator default ($defaultUrl)",
                gatewayTestResult = null,
                gatewayTestSuccess = null
            )
        }
    }

    fun testGatewayConnection() {
        viewModelScope.launch {
            _uiState.update { it.copy(isTestingGateway = true, gatewayTestResult = null, gatewayTestSuccess = null) }
            try {
                val start = System.currentTimeMillis()
                val resp = RetrofitClient.apiService.getHealth()
                val latency = System.currentTimeMillis() - start
                if (resp.isSuccessful && resp.body() != null) {
                    val body = resp.body()!!
                    val modelOk = body.modelsAvailable.resnet50
                    val ragOk = body.modelsAvailable.ragChromaDb
                    val chunks = body.ragChunks
                    _uiState.update {
                        it.copy(
                            isTestingGateway = false,
                            gatewayTestSuccess = true,
                            gatewayTestResult = "Connected (${latency}ms) — ResNet-50 (${if (modelOk) "Ready" else "N/A"}), ChromaDB (${chunks} chunks)"
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isTestingGateway = false,
                            gatewayTestSuccess = false,
                            gatewayTestResult = "Gateway returned HTTP ${resp.code()}: ${resp.message()}"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isTestingGateway = false,
                        gatewayTestSuccess = false,
                        gatewayTestResult = "Connection failed: ${e.localizedMessage ?: e.javaClass.simpleName}"
                    )
                }
            }
        }
    }
}
