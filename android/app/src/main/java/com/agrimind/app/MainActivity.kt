package com.agrimind.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Eco
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.local.OfflineQueueManager
import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.repository.LocalCaseRepository
import com.agrimind.app.ui.screens.*
import com.agrimind.app.ui.theme.AgriMindTheme
import com.agrimind.app.ui.theme.ForestGreenDark
import com.agrimind.app.ui.theme.ForestGreenPrimary
import com.agrimind.app.ui.theme.LightGreenBackground
import com.agrimind.app.ui.viewmodel.*

/**
 * Main application entry activity for AgriMind Native Android.
 * Integrates:
 * - Secure Authentication Flow: LoginScreen, SignupScreen, and Guest Field Mode
 * - Two Distinct Role-Separated Dashboards:
 *   1. Administrator & Project Owner Console (Telemetry, User Governance, Audit Trail, Moderation)
 *   2. Farmer Decision-Support Dashboard (AI Diagnosis, Local History, Agronomic Assistant, Settings)
 * - Dedicated Full-Screen Case Details & Adaptive Reassessment
 * - Offline Action Queue Auto-Reconciliation
 */
class MainActivity : ComponentActivity() {

    private val healthViewModel: HealthViewModel by viewModels()
    private val diagnosisViewModel: DiagnosisViewModel by viewModels()
    private val historyViewModel: HistoryViewModel by viewModels()
    private val caseDetailViewModel: CaseDetailViewModel by viewModels()
    private val chatViewModel: ChatViewModel by viewModels()
    private val settingsViewModel: SettingsViewModel by viewModels()
    private val communityViewModel: CommunityViewModel by viewModels()

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val initialSession = UserSessionManager.getInstance(applicationContext)
        val savedGateway = initialSession.getGatewayUrl()
        if (!savedGateway.isNullOrBlank()) {
            RetrofitClient.setBaseUrl(savedGateway)
        }
        setContent {
            AgriMindTheme {
                val sessionManager = remember { UserSessionManager.getInstance(applicationContext) }
                val settingsState by settingsViewModel.uiState.collectAsState()

                var isLoggedIn by remember { mutableStateOf(sessionManager.isLoggedIn()) }
                var isGuestMode by remember { mutableStateOf(false) }
                var authScreen by remember { mutableStateOf("login") } // "login" or "signup"
                var adminPreviewFarmerMode by remember { mutableStateOf(false) }

                var selectedTab by remember { mutableIntStateOf(0) }
                var activeDetailCase by remember { mutableStateOf<LocalCaseRecord?>(null) }
                var isDetailChatOpen by remember { mutableStateOf(false) }
                var isSystemHealthOpen by remember { mutableStateOf(false) }

                // Sync retrofit auth token on resume and verify server-side role authoritative profile
                LaunchedEffect(isLoggedIn) {
                    if (isLoggedIn) {
                        val currentToken = sessionManager.getAuthToken()
                        RetrofitClient.setAuthToken(currentToken)
                        if (!currentToken.isNullOrBlank()) {
                            try {
                                val profileRes = RetrofitClient.apiService.getProfile()
                                if (profileRes.isSuccessful && profileRes.body() != null) {
                                    val verified = profileRes.body()!!
                                    // Authoritative server-side profile update: forces true role into session
                                    sessionManager.saveSession(
                                        token = currentToken,
                                        userId = verified.userId,
                                        username = verified.username ?: verified.email,
                                        role = verified.role,
                                        fullName = verified.fullName,
                                        email = verified.email,
                                        permissions = verified.permissions
                                    )
                                    settingsViewModel.refreshSession()
                                } else if (profileRes.code() == 401 || profileRes.code() == 403) {
                                    // Invalid, revoked or expired token: purge and force login
                                    sessionManager.clearSession()
                                    RetrofitClient.setAuthToken(null)
                                    settingsViewModel.refreshSession()
                                    isLoggedIn = false
                                }
                            } catch (_: Exception) {
                                // Offline field operation: retain cached local credentials
                            }
                        }
                    }
                }

                // 1. Auth Flow: If not logged in and not in guest mode, show Login/Signup
                if (!isLoggedIn && !isGuestMode) {
                    if (authScreen == "signup") {
                        SignupScreen(
                            onSignupSuccess = { auth ->
                                sessionManager.clearSession()
                                sessionManager.saveSession(
                                    token = auth.accessToken,
                                    userId = auth.effectiveUserId,
                                    username = auth.username ?: auth.effectiveEmail,
                                    role = auth.effectiveRole,
                                    fullName = auth.effectiveFullName,
                                    email = auth.effectiveEmail,
                                    permissions = auth.effectivePermissions
                                )
                                RetrofitClient.setAuthToken(auth.accessToken)
                                settingsViewModel.refreshSession()
                                isLoggedIn = true
                            },
                            onNavigateToLogin = { authScreen = "login" }
                        )
                    } else {
                        LoginScreen(
                            onLoginSuccess = { auth ->
                                sessionManager.clearSession()
                                sessionManager.saveSession(
                                    token = auth.accessToken,
                                    userId = auth.effectiveUserId,
                                    username = auth.username ?: auth.effectiveEmail,
                                    role = auth.effectiveRole,
                                    fullName = auth.effectiveFullName,
                                    email = auth.effectiveEmail,
                                    permissions = auth.effectivePermissions
                                )
                                RetrofitClient.setAuthToken(auth.accessToken)
                                settingsViewModel.refreshSession()
                                isLoggedIn = true
                            },
                            onNavigateToSignup = { authScreen = "signup" },
                            onContinueAsGuest = {
                                sessionManager.clearSession()
                                RetrofitClient.setAuthToken(null)
                                isGuestMode = true
                            }
                        )
                    }
                }
                // 2. Administrator Dashboard: If user is admin/owner and not explicitly testing farmer view
                else if (sessionManager.isAdmin() && !adminPreviewFarmerMode) {
                    AdminDashboardScreen(
                        sessionManager = sessionManager,
                        onLogout = {
                            sessionManager.clearSession()
                            RetrofitClient.setAuthToken(null)
                            settingsViewModel.refreshSession()
                            isLoggedIn = false
                            isGuestMode = false
                            adminPreviewFarmerMode = false
                            authScreen = "login"
                        },
                        onSwitchToFarmerMode = {
                            adminPreviewFarmerMode = true
                        }
                    )
                }
                // 3. Farmer Dashboard / Preview Mode
                else {
                    if (isSystemHealthOpen) {
                        BackHandler {
                            isSystemHealthOpen = false
                        }
                        Scaffold(
                            topBar = {
                                TopAppBar(
                                    title = {
                                        Text(
                                            text = if (settingsState.language == "hi") "सिस्टम स्वास्थ्य और टेलीमेट्री" else "Backend Telemetry & Status",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = Color.White
                                        )
                                    },
                                    navigationIcon = {
                                        IconButton(onClick = { isSystemHealthOpen = false }) {
                                            Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = Color.White)
                                        }
                                    },
                                    colors = TopAppBarDefaults.topAppBarColors(containerColor = ForestGreenPrimary)
                                )
                            }
                        ) { p ->
                            Box(modifier = Modifier.fillMaxSize().padding(p)) {
                                HealthScreen(viewModel = healthViewModel)
                            }
                        }
                    }
                    // If user is currently inspecting a specific case, show CaseDetailScreen or ChatScreen
                    else if (activeDetailCase != null) {
                        if (isDetailChatOpen) {
                            BackHandler {
                                isDetailChatOpen = false
                            }
                            ChatScreen(
                                viewModel = chatViewModel,
                                caseId = activeDetailCase!!.caseId,
                                onBackClicked = { isDetailChatOpen = false }
                            )
                        } else {
                            BackHandler {
                                activeDetailCase = null
                            }
                            CaseDetailScreen(
                                caseRecord = activeDetailCase!!,
                                viewModel = caseDetailViewModel,
                                onBackClicked = { activeDetailCase = null },
                                onAskAssistantClicked = { caseId ->
                                    chatViewModel.setCaseContext(caseId, activeDetailCase?.primaryDiagnosis)
                                    isDetailChatOpen = true
                                }
                            )
                        }
                    } else {
                        Scaffold(
                            topBar = {
                                TopAppBar(
                                    title = {
                                        androidx.compose.foundation.layout.Column {
                                            Text(
                                                text = "AgriMind",
                                                style = MaterialTheme.typography.titleLarge,
                                                fontWeight = FontWeight.Bold,
                                                color = Color.White
                                            )
                                            val subtitle = when (selectedTab) {
                                                0 -> if (settingsState.language == "hi") "टमाटर रोग एआई निदान" else "AI Tomato Disease Diagnosis"
                                                1 -> if (settingsState.language == "hi") "किसान समुदाय और सामाजिक चर्चा" else "Farmer Community & Discussions"
                                                2 -> if (settingsState.language == "hi") "कृषि विस्तार सहायक" else "Evidence-Grounded Assistant"
                                                3 -> if (settingsState.language == "hi") "स्थानीय निदान इतिहास" else "Local Investigation History"
                                                else -> if (settingsState.language == "hi") "सेटिंग्स और प्रोफ़ाइल" else "Settings & User Profile"
                                            }
                                            Text(
                                                text = subtitle,
                                                fontSize = 12.sp,
                                                color = Color.White.copy(alpha = 0.85f)
                                            )
                                        }
                                    },
                                    actions = {
                                        // If admin is in preview mode, give button to return to admin console
                                        if (sessionManager.isAdmin() && adminPreviewFarmerMode) {
                                            IconButton(onClick = { adminPreviewFarmerMode = false }) {
                                                Icon(
                                                    Icons.Default.AdminPanelSettings,
                                                    contentDescription = "Return to Admin Console",
                                                    tint = Color(0xFFFFD700)
                                                )
                                            }
                                        }

                                        Surface(
                                            shape = androidx.compose.foundation.shape.RoundedCornerShape(12.dp),
                                            color = Color.White.copy(alpha = 0.2f),
                                            modifier = Modifier.padding(end = 12.dp)
                                        ) {
                                            androidx.compose.foundation.layout.Row(
                                                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                            ) {
                                                Text(
                                                    text = if (settingsState.language == "hi") "HI" else "EN",
                                                    color = Color.White,
                                                    fontWeight = FontWeight.Bold,
                                                    fontSize = 11.sp
                                                )
                                                Spacer(modifier = Modifier.width(4.dp))
                                                Text(
                                                    text = "• ${if (isGuestMode) "GUEST" else settingsState.role.uppercase()}",
                                                    color = Color.White.copy(alpha = 0.85f),
                                                    fontSize = 11.sp
                                                )
                                            }
                                        }
                                    },
                                    colors = TopAppBarDefaults.topAppBarColors(
                                        containerColor = ForestGreenPrimary
                                    )
                                )
                            },
                            bottomBar = {
                                NavigationBar(
                                    containerColor = MaterialTheme.colorScheme.surface
                                ) {
                                    NavigationBarItem(
                                        selected = selectedTab == 0,
                                        onClick = { selectedTab = 0 },
                                        icon = { Icon(Icons.Default.Eco, contentDescription = "Diagnosis") },
                                        label = { Text("Diagnosis") },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = ForestGreenPrimary,
                                            selectedTextColor = ForestGreenDark,
                                            indicatorColor = Color(0xFFC8E6C9)
                                        )
                                    )
                                    NavigationBarItem(
                                        selected = selectedTab == 1,
                                        onClick = { selectedTab = 1 },
                                        icon = { Icon(Icons.Default.Groups, contentDescription = "Community") },
                                        label = { Text("Community") },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = ForestGreenPrimary,
                                            selectedTextColor = ForestGreenDark,
                                            indicatorColor = Color(0xFFC8E6C9)
                                        )
                                    )
                                    NavigationBarItem(
                                        selected = selectedTab == 2,
                                        onClick = { selectedTab = 2 },
                                        icon = { Icon(Icons.Default.Forum, contentDescription = "Assistant") },
                                        label = { Text("Assistant") },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = ForestGreenPrimary,
                                            selectedTextColor = ForestGreenDark,
                                            indicatorColor = Color(0xFFC8E6C9)
                                        )
                                    )
                                    NavigationBarItem(
                                        selected = selectedTab == 3,
                                        onClick = { selectedTab = 3 },
                                        icon = { Icon(Icons.Default.History, contentDescription = "History") },
                                        label = { Text("History") },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = ForestGreenPrimary,
                                            selectedTextColor = ForestGreenDark,
                                            indicatorColor = Color(0xFFC8E6C9)
                                        )
                                    )
                                    NavigationBarItem(
                                        selected = selectedTab == 4,
                                        onClick = { selectedTab = 4 },
                                        icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                                        label = { Text("Settings") },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = ForestGreenPrimary,
                                            selectedTextColor = ForestGreenDark,
                                            indicatorColor = Color(0xFFC8E6C9)
                                        )
                                    )
                                }
                            },
                            containerColor = LightGreenBackground
                        ) { innerPadding ->
                            Surface(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(innerPadding),
                                color = LightGreenBackground
                            ) {
                                when (selectedTab) {
                                    0 -> DiagnosisScreen(
                                        viewModel = diagnosisViewModel,
                                        onViewCaseDetails = { caseId ->
                                            val record = LocalCaseRepository.getInstance(applicationContext).getCaseById(caseId)
                                            if (record != null) {
                                                caseDetailViewModel.setCase(record)
                                                activeDetailCase = record
                                            }
                                        },
                                        onAskAssistant = { caseId, diagnosis ->
                                            chatViewModel.setCaseContext(caseId, diagnosis)
                                            selectedTab = 2
                                        }
                                    )
                                    1 -> CommunityScreen(
                                        viewModel = communityViewModel,
                                        sessionManager = sessionManager
                                    )
                                    2 -> ChatScreen(
                                        viewModel = chatViewModel,
                                        caseId = null,
                                        onBackClicked = null
                                    )
                                    3 -> HistoryScreen(
                                        viewModel = historyViewModel,
                                        onCaseSelected = { record ->
                                            caseDetailViewModel.setCase(record)
                                            activeDetailCase = record
                                        }
                                    )
                                    4 -> SettingsScreen(
                                        viewModel = settingsViewModel,
                                        onNavigateToSystemHealth = { isSystemHealthOpen = true },
                                        onNavigateToAuth = {
                                            sessionManager.clearSession()
                                            RetrofitClient.setAuthToken(null)
                                            settingsViewModel.refreshSession()
                                            isLoggedIn = false
                                            isGuestMode = false
                                            authScreen = "login"
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // Perform initial backend health check on application startup
        healthViewModel.checkBackendHealth()

        // Background auto-reconciliation of offline action queue
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                OfflineQueueManager.getInstance(applicationContext).syncPendingActions(
                    RetrofitClient.apiService,
                    LocalCaseRepository.getInstance(applicationContext)
                )
            } catch (e: Exception) {
                // Background sync failure is non-fatal
            }
        }
    }
}
