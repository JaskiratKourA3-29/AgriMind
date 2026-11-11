package com.agrimind.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.*
import com.agrimind.app.ui.theme.ForestGreenDark
import com.agrimind.app.ui.theme.ForestGreenPrimary
import com.agrimind.app.ui.theme.LightGreenBackground

/**
 * Administrator & Owner Console for AgriMind Mobile App.
 * Provides:
 * - Real-time system health and neural telemetry
 * - User management: search, role modifications, status toggles (Active/Suspended)
 * - Owner-governed privilege controls and last-owner protection
 * - Immutable security audit logs viewer
 * - Cooperative community case moderation
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminDashboardScreen(
    sessionManager: UserSessionManager,
    onLogout: () -> Unit,
    onSwitchToFarmerMode: () -> Unit
) {
    val coroutineScope = rememberCoroutineScope()
    var selectedTab by remember { mutableIntStateOf(0) }

    // State
    var systemStatus by remember { mutableStateOf<AdminSystemStatusResponse?>(null) }
    var usersList by remember { mutableStateOf<List<UserProfileResponse>>(emptyList()) }
    var auditLogs by remember { mutableStateOf<List<AuditLogItem>>(emptyList()) }
    var sharedCases by remember { mutableStateOf<List<SharedCaseSummary>>(emptyList()) }
    var subOwnersList by remember { mutableStateOf<List<SubOwnerInfo>>(emptyList()) }
    var communityReports by remember { mutableStateOf<List<CommunityReportResponse>>(emptyList()) }

    var searchQuery by remember { mutableStateOf("") }
    var roleFilter by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Dialog state for role change
    var userToChangeRole by remember { mutableStateOf<UserProfileResponse?>(null) }
    var selectedNewRole by remember { mutableStateOf("farmer") }

    // Dialog state for status toggle
    var userToToggleStatus by remember { mutableStateOf<UserProfileResponse?>(null) }

    // Dialog state for Sub-Owner governance
    var showGrantSubOwnerDialog by remember { mutableStateOf(false) }
    var subOwnerToEditPerms by remember { mutableStateOf<SubOwnerInfo?>(null) }
    var subOwnerToRevoke by remember { mutableStateOf<SubOwnerInfo?>(null) }

    fun refreshAllData() {
        isLoading = true
        errorMessage = null
        statusMessage = null
        coroutineScope.launch {
            try {
                // 1. Fetch system status (if authorized)
                if (sessionManager.hasPermission("can_view_telemetry")) {
                    val statusRes = RetrofitClient.apiService.getAdminSystemStatus()
                    if (statusRes.isSuccessful) {
                        systemStatus = statusRes.body()
                    }
                }

                // 2. Fetch users (if authorized)
                if (sessionManager.hasPermission("can_manage_users")) {
                    val usersRes = RetrofitClient.apiService.searchUsers(
                        query = if (searchQuery.isNotBlank()) searchQuery else null,
                        role = roleFilter,
                        limit = 100
                    )
                    if (usersRes.isSuccessful) {
                        usersList = usersRes.body() ?: emptyList()
                    }
                }

                // 3. Fetch audit logs (if authorized)
                if (sessionManager.hasPermission("can_view_audit_logs")) {
                    val logsRes = RetrofitClient.apiService.getAuditLogs(limit = 100)
                    if (logsRes.isSuccessful) {
                        auditLogs = logsRes.body() ?: emptyList()
                    }
                }

                // 4. Fetch shared cases
                val casesRes = RetrofitClient.apiService.listSharedCases(limit = 50)
                if (casesRes.isSuccessful) {
                    sharedCases = casesRes.body() ?: emptyList()
                }

                // 5. Fetch sub-owners (Owner only)
                if (sessionManager.isOwner()) {
                    val subRes = RetrofitClient.apiService.listSubOwners()
                    if (subRes.isSuccessful) {
                        subOwnersList = subRes.body() ?: emptyList()
                    }
                }

                // 6. Fetch community reports (if authorized)
                if (sessionManager.hasPermission("can_moderate_cases")) {
                    val repRes = RetrofitClient.apiService.listCommunityReports(limit = 50)
                    if (repRes.isSuccessful) {
                        communityReports = repRes.body() ?: emptyList()
                    }
                }
            } catch (e: Exception) {
                errorMessage = "Failed to load admin data: ${e.localizedMessage}"
            } finally {
                isLoading = false
            }
        }
    }

    fun deleteReportedPost(postId: String) {
        isLoading = true
        coroutineScope.launch {
            try {
                val res = RetrofitClient.apiService.deleteCommunityPost(postId)
                if (res.isSuccessful) {
                    statusMessage = "Reported post deleted successfully"
                    refreshAllData()
                } else {
                    errorMessage = "Failed to delete post: HTTP ${res.code()}"
                }
            } catch (e: Exception) {
                errorMessage = "Error deleting post: ${e.localizedMessage}"
            } finally {
                isLoading = false
            }
        }
    }

    fun deleteReportedComment(commentId: String) {
        isLoading = true
        coroutineScope.launch {
            try {
                val res = RetrofitClient.apiService.deleteCommunityComment(commentId)
                if (res.isSuccessful) {
                    statusMessage = "Reported comment deleted successfully"
                    refreshAllData()
                } else {
                    errorMessage = "Failed to delete comment: HTTP ${res.code()}"
                }
            } catch (e: Exception) {
                errorMessage = "Error deleting comment: ${e.localizedMessage}"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshAllData()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "AgriMind Admin Console",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            val (badgeText, badgeBg) = when {
                                sessionManager.isOwner() -> "OWNER" to Color(0xFFFFD700)
                                sessionManager.isSubOwner() -> "SUB-OWNER" to Color(0xFFBA68C8)
                                else -> "ADMIN" to Color(0xFFFFB74D)
                            }
                            Surface(
                                shape = RoundedCornerShape(4.dp),
                                color = badgeBg
                            ) {
                                Text(
                                    text = badgeText,
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                    color = if (sessionManager.isSubOwner()) Color.White else Color.Black,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                        Text(
                            text = sessionManager.getEmail().ifEmpty { sessionManager.getUsername() },
                            style = MaterialTheme.typography.bodySmall,
                            color = Color.White.copy(alpha = 0.85f),
                            fontSize = 11.sp
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { refreshAllData() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = Color.White)
                    }
                    IconButton(onClick = onSwitchToFarmerMode) {
                        Icon(Icons.Default.Eco, contentDescription = "Farmer View", tint = Color.White)
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.Logout, contentDescription = "Sign Out", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1B5E20)
                )
            )
        },
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                val isOwner = sessionManager.isOwner()
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.Dns, contentDescription = "Telemetry") },
                    label = { Text("Telemetry", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.People, contentDescription = "Users") },
                    label = { Text("Users", fontSize = 10.sp) }
                )
                if (isOwner) {
                    NavigationBarItem(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        icon = { Icon(Icons.Default.Security, contentDescription = "Sub-Owners") },
                        label = { Text("Sub-Owners", fontSize = 10.sp) }
                    )
                }
                val auditTabIndex = if (isOwner) 3 else 2
                NavigationBarItem(
                    selected = selectedTab == auditTabIndex,
                    onClick = { selectedTab = auditTabIndex },
                    icon = { Icon(Icons.Default.Security, contentDescription = "Audit") },
                    label = { Text("Audit", fontSize = 10.sp) }
                )
                val modTabIndex = if (isOwner) 4 else 3
                NavigationBarItem(
                    selected = selectedTab == modTabIndex,
                    onClick = { selectedTab = modTabIndex },
                    icon = { Icon(Icons.Default.Forum, contentDescription = "Community") },
                    label = { Text("Moderation", fontSize = 10.sp) }
                )
            }
        },
        containerColor = LightGreenBackground
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Status / Error Banners
                statusMessage?.let { msg ->
                    Surface(
                        color = Color(0xFFE8F5E9),
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Row(modifier = Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenDark, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = msg, style = MaterialTheme.typography.bodySmall, color = ForestGreenDark)
                        }
                    }
                }
                errorMessage?.let { err ->
                    Surface(
                        color = Color(0xFFFFEBEE),
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Row(modifier = Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = Color(0xFFC62828), modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = err, style = MaterialTheme.typography.bodySmall, color = Color(0xFFC62828))
                        }
                    }
                }

                val isOwner = sessionManager.isOwner()
                if (isOwner) {
                    when (selectedTab) {
                        0 -> AdminTelemetryTab(systemStatus = systemStatus, onRefresh = { refreshAllData() })
                        1 -> AdminUsersTab(
                            users = usersList,
                            searchQuery = searchQuery,
                            onSearchChange = {
                                searchQuery = it
                                refreshAllData()
                            },
                            roleFilter = roleFilter,
                            onRoleFilterChange = {
                                roleFilter = it
                                refreshAllData()
                            },
                            onInitiateRoleChange = { u ->
                                userToChangeRole = u
                                selectedNewRole = u.role
                            },
                            onInitiateStatusToggle = { u ->
                                userToToggleStatus = u
                            }
                        )
                        2 -> AdminSubOwnersTab(
                            subOwners = subOwnersList,
                            onOpenGrantDialog = { showGrantSubOwnerDialog = true },
                            onEditPermissions = { subOwnerToEditPerms = it },
                            onRevoke = { subOwnerToRevoke = it },
                            onRefresh = { refreshAllData() }
                        )
                        3 -> AdminAuditLogsTab(auditLogs = auditLogs, onRefresh = { refreshAllData() })
                        4 -> AdminModerationTab(
                            sharedCases = sharedCases,
                            communityReports = communityReports,
                            onDeleteReportedPost = { deleteReportedPost(it) },
                            onDeleteReportedComment = { deleteReportedComment(it) },
                            onRefresh = { refreshAllData() }
                        )
                    }
                } else {
                    when (selectedTab) {
                        0 -> {
                            if (sessionManager.hasPermission("can_view_telemetry")) {
                                AdminTelemetryTab(systemStatus = systemStatus, onRefresh = { refreshAllData() })
                            } else {
                                RestrictedAccessCard("System Telemetry & Health", "can_view_telemetry")
                            }
                        }
                        1 -> {
                            if (sessionManager.hasPermission("can_manage_users")) {
                                AdminUsersTab(
                                    users = usersList,
                                    searchQuery = searchQuery,
                                    onSearchChange = {
                                        searchQuery = it
                                        refreshAllData()
                                    },
                                    roleFilter = roleFilter,
                                    onRoleFilterChange = {
                                        roleFilter = it
                                        refreshAllData()
                                    },
                                    onInitiateRoleChange = { u ->
                                        userToChangeRole = u
                                        selectedNewRole = u.role
                                    },
                                    onInitiateStatusToggle = { u ->
                                        userToToggleStatus = u
                                    }
                                )
                            } else {
                                RestrictedAccessCard("User Account Management", "can_manage_users")
                            }
                        }
                        2 -> {
                            if (sessionManager.hasPermission("can_view_audit_logs")) {
                                AdminAuditLogsTab(auditLogs = auditLogs, onRefresh = { refreshAllData() })
                            } else {
                                RestrictedAccessCard("Security Audit Trail", "can_view_audit_logs")
                            }
                        }
                        3 -> {
                            if (sessionManager.hasPermission("can_moderate_cases")) {
                                AdminModerationTab(
                                    sharedCases = sharedCases,
                                    communityReports = communityReports,
                                    onDeleteReportedPost = { deleteReportedPost(it) },
                                    onDeleteReportedComment = { deleteReportedComment(it) },
                                    onRefresh = { refreshAllData() }
                                )
                            } else {
                                RestrictedAccessCard("Case Moderation", "can_moderate_cases")
                            }
                        }
                    }
                }
            }

            if (isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = ForestGreenPrimary)
                }
            }
        }
    }

    // Role Modification Dialog
    userToChangeRole?.let { user ->
        AlertDialog(
            onDismissRequest = { userToChangeRole = null },
            title = { Text("Update Role for ${user.fullName.ifEmpty { user.email }}") },
            text = {
                Column {
                    Text(
                        text = "Current Role: ${user.displayRole}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text("Select New Role:", style = MaterialTheme.typography.bodySmall)
                    Spacer(modifier = Modifier.height(8.dp))

                    val roles = if (sessionManager.isOwner()) listOf("farmer", "admin", "owner") else listOf("farmer", "admin")
                    roles.forEach { r ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                        ) {
                            RadioButton(
                                selected = selectedNewRole == r,
                                onClick = { selectedNewRole = r }
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = when (r) {
                                    "owner" -> "Project Owner (Chief Governance)"
                                    "admin" -> "Administrator (Full Console Access)"
                                    else -> "Registered Farmer"
                                },
                                fontWeight = if (selectedNewRole == r) FontWeight.Bold else FontWeight.Normal
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "Note: Changes are permanently recorded in the immutable audit trail. Demoting the last active Project Owner is strictly prevented.",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val targetId = user.userId
                        val newR = selectedNewRole
                        userToChangeRole = null
                        coroutineScope.launch {
                            isLoading = true
                            try {
                                val res = RetrofitClient.apiService.updateUserRole(
                                    userId = targetId,
                                    request = UserRoleUpdateRequest(role = newR)
                                )
                                if (res.isSuccessful) {
                                    statusMessage = "Role updated successfully to '$newR'."
                                    refreshAllData()
                                } else {
                                    errorMessage = "Role update failed: ${res.errorBody()?.string() ?: res.message()}"
                                }
                            } catch (e: Exception) {
                                errorMessage = "Error updating role: ${e.localizedMessage}"
                            } finally {
                                isLoading = false
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                ) {
                    Text("Save Role")
                }
            },
            dismissButton = {
                TextButton(onClick = { userToChangeRole = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Status Toggle Dialog
    userToToggleStatus?.let { user ->
        val willActivate = !user.isActive
        val actionVerb = if (willActivate) "Activate" else "Suspend"
        AlertDialog(
            onDismissRequest = { userToToggleStatus = null },
            title = { Text("$actionVerb Account") },
            text = {
                Text(
                    text = if (willActivate)
                        "Are you sure you want to reactivate the account for ${user.email}? They will regain full access to AgriMind."
                    else
                        "Are you sure you want to suspend the account for ${user.email}? They will be immediately blocked from signing in or performing diagnoses."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        val targetId = user.userId
                        userToToggleStatus = null
                        coroutineScope.launch {
                            isLoading = true
                            try {
                                val res = RetrofitClient.apiService.updateUserStatus(
                                    userId = targetId,
                                    request = UserStatusUpdateRequest(isActive = willActivate)
                                )
                                if (res.isSuccessful) {
                                    statusMessage = "Account status updated successfully."
                                    refreshAllData()
                                } else {
                                    errorMessage = "Status update failed: ${res.errorBody()?.string() ?: res.message()}"
                                }
                            } catch (e: Exception) {
                                errorMessage = "Error toggling status: ${e.localizedMessage}"
                            } finally {
                                isLoading = false
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (willActivate) ForestGreenPrimary else Color(0xFFC62828)
                    )
                ) {
                    Text(actionVerb)
                }
            },
            dismissButton = {
                TextButton(onClick = { userToToggleStatus = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // 1. Grant Sub-Owner Dialog
    if (showGrantSubOwnerDialog) {
        var selectedUserId by remember { mutableStateOf("") }
        var permUsers by remember { mutableStateOf(false) }
        var permModerate by remember { mutableStateOf(false) }
        var permTelemetry by remember { mutableStateOf(true) }
        var permAudit by remember { mutableStateOf(false) }

        val eligibleUsers = usersList.filter { it.role.lowercase() != "owner" && it.role.lowercase() != "sub_owner" }

        AlertDialog(
            onDismissRequest = { showGrantSubOwnerDialog = false },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Security, contentDescription = null, tint = Color(0xFF6A1B9A))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Grant Sub-Owner Access")
                }
            },
            text = {
                Column(modifier = Modifier.verticalScroll(rememberScrollState())) {
                    Text(
                        "Select User:",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(6.dp))

                    if (eligibleUsers.isEmpty()) {
                        Text(
                            "No eligible registered users found to appoint as Sub-Owner.",
                            fontSize = 12.sp,
                            color = Color.Gray
                        )
                    } else {
                        eligibleUsers.forEach { u ->
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 3.dp)
                            ) {
                                RadioButton(
                                    selected = selectedUserId == u.userId,
                                    onClick = { selectedUserId = u.userId }
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Column {
                                    Text(
                                        text = u.fullName.ifEmpty { u.email },
                                        fontWeight = if (selectedUserId == u.userId) FontWeight.Bold else FontWeight.Normal,
                                        fontSize = 12.sp
                                    )
                                    Text(text = u.email, fontSize = 10.sp, color = Color.Gray)
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(14.dp))
                    Text(
                        "Delegate Specific Permissions:",
                        style = MaterialTheme.typography.bodySmall,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(6.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permTelemetry, onCheckedChange = { permTelemetry = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("System Telemetry & Health", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permUsers, onCheckedChange = { permUsers = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("User Management (View / Search)", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permModerate, onCheckedChange = { permModerate = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Case Moderation", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permAudit, onCheckedChange = { permAudit = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Security Audit Logs Viewer", fontSize = 12.sp)
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Note: Sub-Owners cannot alter Main Project Owner privileges or appoint other sub-owners. You can revoke access at any time.",
                        fontSize = 10.sp,
                        color = Color.Gray
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (selectedUserId.isNotBlank()) {
                            val perms = mutableListOf<String>()
                            if (permTelemetry) perms.add("can_view_telemetry")
                            if (permUsers) perms.add("can_manage_users")
                            if (permModerate) perms.add("can_moderate_cases")
                            if (permAudit) perms.add("can_view_audit_logs")
                            if (perms.isEmpty()) perms.add("can_view_telemetry")

                            showGrantSubOwnerDialog = false
                            coroutineScope.launch {
                                isLoading = true
                                try {
                                    val res = RetrofitClient.apiService.grantSubOwner(
                                        GrantSubOwnerRequest(userId = selectedUserId, permissions = perms)
                                    )
                                    if (res.isSuccessful) {
                                        statusMessage = "Sub-Owner role granted successfully."
                                        refreshAllData()
                                    } else {
                                        errorMessage = "Failed to grant Sub-Owner: ${res.errorBody()?.string() ?: res.message()}"
                                    }
                                } catch (e: Exception) {
                                    errorMessage = "Error granting Sub-Owner: ${e.localizedMessage}"
                                } finally {
                                    isLoading = false
                                }
                            }
                        }
                    },
                    enabled = selectedUserId.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A1B9A))
                ) {
                    Text("Grant Access")
                }
            },
            dismissButton = {
                TextButton(onClick = { showGrantSubOwnerDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // 2. Edit Permissions Dialog
    subOwnerToEditPerms?.let { sub ->
        var permUsers by remember(sub) { mutableStateOf(sub.permissions.contains("can_manage_users")) }
        var permModerate by remember(sub) { mutableStateOf(sub.permissions.contains("can_moderate_cases")) }
        var permTelemetry by remember(sub) { mutableStateOf(sub.permissions.contains("can_view_telemetry")) }
        var permAudit by remember(sub) { mutableStateOf(sub.permissions.contains("can_view_audit_logs")) }

        AlertDialog(
            onDismissRequest = { subOwnerToEditPerms = null },
            title = { Text("Update Permissions: ${sub.fullName.ifEmpty { sub.email }}") },
            text = {
                Column {
                    Text("Configure delegated permissions for this Sub-Owner:", fontSize = 12.sp, color = Color.DarkGray)
                    Spacer(modifier = Modifier.height(10.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permTelemetry, onCheckedChange = { permTelemetry = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("System Telemetry & Health", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permUsers, onCheckedChange = { permUsers = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("User Management (View / Search)", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permModerate, onCheckedChange = { permModerate = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Case Moderation", fontSize = 12.sp)
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = permAudit, onCheckedChange = { permAudit = it })
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Security Audit Logs Viewer", fontSize = 12.sp)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val perms = mutableListOf<String>()
                        if (permTelemetry) perms.add("can_view_telemetry")
                        if (permUsers) perms.add("can_manage_users")
                        if (permModerate) perms.add("can_moderate_cases")
                        if (permAudit) perms.add("can_view_audit_logs")
                        val targetId = sub.userId
                        subOwnerToEditPerms = null
                        coroutineScope.launch {
                            isLoading = true
                            try {
                                val res = RetrofitClient.apiService.updateSubOwnerPermissions(
                                    userId = targetId,
                                    request = UpdateSubOwnerPermissionsRequest(permissions = perms)
                                )
                                if (res.isSuccessful) {
                                    statusMessage = "Sub-Owner permissions updated successfully."
                                    refreshAllData()
                                } else {
                                    errorMessage = "Update failed: ${res.errorBody()?.string() ?: res.message()}"
                                }
                            } catch (e: Exception) {
                                errorMessage = "Error updating permissions: ${e.localizedMessage}"
                            } finally {
                                isLoading = false
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A1B9A))
                ) {
                    Text("Save Permissions")
                }
            },
            dismissButton = {
                TextButton(onClick = { subOwnerToEditPerms = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // 3. Revoke Sub-Owner Dialog
    subOwnerToRevoke?.let { sub ->
        AlertDialog(
            onDismissRequest = { subOwnerToRevoke = null },
            icon = {
                Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFC62828), modifier = Modifier.size(36.dp))
            },
            title = { Text("Revoke Sub-Owner Privileges?") },
            text = {
                Column {
                    Text(
                        text = "Are you sure you want to revoke Sub-Owner privileges from ${sub.fullName.ifEmpty { sub.email }}?",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "• Elevated administrative privileges will terminate immediately.\n• Account role will revert to Farmer.\n• Personal records and case history remain intact.",
                        fontSize = 12.sp,
                        color = Color.DarkGray
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val targetId = sub.userId
                        subOwnerToRevoke = null
                        coroutineScope.launch {
                            isLoading = true
                            try {
                                val res = RetrofitClient.apiService.revokeSubOwner(userId = targetId)
                                if (res.isSuccessful) {
                                    statusMessage = "Sub-Owner privileges revoked. User restored to Farmer role."
                                    refreshAllData()
                                } else {
                                    errorMessage = "Revocation failed: ${res.errorBody()?.string() ?: res.message()}"
                                }
                            } catch (e: Exception) {
                                errorMessage = "Error revoking Sub-Owner: ${e.localizedMessage}"
                            } finally {
                                isLoading = false
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828))
                ) {
                    Text("Revoke Access")
                }
            },
            dismissButton = {
                TextButton(onClick = { subOwnerToRevoke = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun AdminSubOwnersTab(
    subOwners: List<SubOwnerInfo>,
    onOpenGrantDialog: () -> Unit,
    onEditPermissions: (SubOwnerInfo) -> Unit,
    onRevoke: (SubOwnerInfo) -> Unit,
    onRefresh: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Governance Header Card
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Default.Security,
                            contentDescription = null,
                            tint = Color(0xFF6A1B9A),
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Main Owner Governance",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF6A1B9A)
                        )
                    }
                    IconButton(onClick = onRefresh) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = Color(0xFF6A1B9A))
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Controlled exclusively by Project Owner Jaskirat Kour. Sub-owners receive only specifically delegated permissions and can be revoked immediately anytime.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.DarkGray
                )

                Spacer(modifier = Modifier.height(14.dp))
                Button(
                    onClick = onOpenGrantDialog,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6A1B9A)),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Add, contentDescription = null, tint = Color.White)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Grant Sub-Owner Access", fontWeight = FontWeight.Bold)
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Active Sub-Owners (${subOwners.size})",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        if (subOwners.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(top = 40.dp),
                contentAlignment = Alignment.TopCenter
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        Icons.Default.People,
                        contentDescription = null,
                        tint = Color.LightGray,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("No Sub-Owners currently appointed.", color = Color.Gray, fontWeight = FontWeight.Medium)
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "Tap 'Grant Sub-Owner Access' above to delegate specific permissions to an existing user.",
                        color = Color.Gray,
                        fontSize = 12.sp,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        modifier = Modifier.padding(horizontal = 24.dp)
                    )
                }
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(subOwners) { sub ->
                    SubOwnerCardItem(
                        subOwner = sub,
                        onEditPermissions = { onEditPermissions(sub) },
                        onRevoke = { onRevoke(sub) }
                    )
                }
            }
        }
    }
}

@Composable
fun SubOwnerCardItem(
    subOwner: SubOwnerInfo,
    onEditPermissions: () -> Unit,
    onRevoke: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = subOwner.fullName.ifEmpty { "Sub-Owner" },
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(text = subOwner.email, fontSize = 12.sp, color = Color.Gray)
                }

                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = Color(0xFFE1BEE7)
                ) {
                    Text(
                        text = "SUB-OWNER",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF6A1B9A),
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Granted by: ${subOwner.grantedBy ?: "Main Owner"}",
                fontSize = 11.sp,
                color = Color.DarkGray
            )

            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Delegated Permissions:",
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.Black
            )
            Spacer(modifier = Modifier.height(6.dp))

            val allPerms = listOf(
                "can_manage_users" to "User Management",
                "can_moderate_cases" to "Case Moderation",
                "can_view_telemetry" to "Telemetry",
                "can_view_audit_logs" to "Audit Trail"
            )

            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                allPerms.forEach { (permKey, permLabel) ->
                    val isGranted = subOwner.permissions.contains(permKey)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            if (isGranted) Icons.Default.CheckCircle else Icons.Default.Lock,
                            contentDescription = null,
                            tint = if (isGranted) ForestGreenDark else Color.LightGray,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = permLabel,
                            fontSize = 11.sp,
                            fontWeight = if (isGranted) FontWeight.Bold else FontWeight.Normal,
                            color = if (isGranted) ForestGreenDark else Color.Gray
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            Divider(color = Color(0xFFEEEEEE))
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(
                    onClick = onEditPermissions,
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Permissions", fontSize = 11.sp)
                }

                Spacer(modifier = Modifier.width(8.dp))

                OutlinedButton(
                    onClick = onRevoke,
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFFC62828)),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(14.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Revoke", fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
fun RestrictedAccessCard(sectionName: String, requiredPermission: String) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.Lock,
                    contentDescription = null,
                    tint = Color(0xFFE65100),
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Permission Required",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Your Sub-Owner account does not have access to $sectionName.",
                    fontSize = 13.sp,
                    color = Color.DarkGray,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = Color(0xFFF5F5F5)
                ) {
                    Text(
                        text = "Required: $requiredPermission",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.Gray,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Access is controlled exclusively by Main Project Owner Jaskirat Kour.",
                    fontSize = 11.sp,
                    color = Color.Gray,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        }
    }
}

@Composable
fun AdminTelemetryTab(
    systemStatus: AdminSystemStatusResponse?,
    onRefresh: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "System Telemetry & Health",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                    IconButton(onClick = onRefresh) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ForestGreenDark)
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    TelemetryStatCard(
                        title = "Diagnoses",
                        value = "${systemStatus?.totalCases ?: 0}",
                        icon = Icons.Default.Eco,
                        color = Color(0xFF2E7D32),
                        modifier = Modifier.weight(1f)
                    )
                    TelemetryStatCard(
                        title = "Registered Users",
                        value = "${systemStatus?.totalUsers ?: 0}",
                        icon = Icons.Default.People,
                        color = Color(0xFF1565C0),
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    TelemetryStatCard(
                        title = "Vector Chunks",
                        value = "${systemStatus?.vectorstoreChunks ?: 63}",
                        icon = Icons.Default.Dataset,
                        color = Color(0xFF6A1B9A),
                        modifier = Modifier.weight(1f)
                    )
                    TelemetryStatCard(
                        title = "Shared Cases",
                        value = "${systemStatus?.totalSharedCases ?: 0}",
                        icon = Icons.Default.Share,
                        color = Color(0xFFE65100),
                        modifier = Modifier.weight(1f)
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))
                Divider()
                Spacer(modifier = Modifier.height(12.dp))

                Text("Core Model & Knowledge Infrastructure:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(6.dp))
                Text("• Vision Classifier: ResNet-50 PyTorch (3 classes: Early Blight, Late Blight, Bacterial Spot)", fontSize = 12.sp, color = Color.DarkGray)
                Text("• RAG Retrieval: ChromaDB (63 chunks, SKUAST-J & ICAR Grounded)", fontSize = 12.sp, color = Color.DarkGray)
                Text("• Critic Agent: 3-rule deterministic verification & safety gate", fontSize = 12.sp, color = Color.DarkGray)
                Text("• Server Time: ${systemStatus?.serverTime ?: "Connected"}", fontSize = 12.sp, color = Color.Gray)
            }
        }
    }
}

@Composable
fun TelemetryStatCard(
    title: String,
    value: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = color.copy(alpha = 0.08f),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.2f)),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text(text = title, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = color)
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(text = value, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, color = color)
        }
    }
}

@Composable
fun AdminUsersTab(
    users: List<UserProfileResponse>,
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    roleFilter: String?,
    onRoleFilterChange: (String?) -> Unit,
    onInitiateRoleChange: (UserProfileResponse) -> Unit,
    onInitiateStatusToggle: (UserProfileResponse) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Search & Filter
        OutlinedTextField(
            value = searchQuery,
            onValueChange = onSearchChange,
            label = { Text("Search by name or email") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Role Filter Chips
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            FilterChip(
                selected = roleFilter == null,
                onClick = { onRoleFilterChange(null) },
                label = { Text("All", fontSize = 11.sp) }
            )
            FilterChip(
                selected = roleFilter == "farmer",
                onClick = { onRoleFilterChange("farmer") },
                label = { Text("Farmers", fontSize = 11.sp) }
            )
            FilterChip(
                selected = roleFilter == "sub_owner",
                onClick = { onRoleFilterChange("sub_owner") },
                label = { Text("Sub-Owners", fontSize = 11.sp) }
            )
            FilterChip(
                selected = roleFilter == "admin",
                onClick = { onRoleFilterChange("admin") },
                label = { Text("Admins", fontSize = 11.sp) }
            )
            FilterChip(
                selected = roleFilter == "owner",
                onClick = { onRoleFilterChange("owner") },
                label = { Text("Owner", fontSize = 11.sp) }
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (users.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No user accounts found matching query.", color = Color.Gray)
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(users) { user ->
                    UserCardItem(
                        user = user,
                        onRoleChange = { onInitiateRoleChange(user) },
                        onStatusToggle = { onInitiateStatusToggle(user) }
                    )
                }
            }
        }
    }
}

@Composable
fun UserCardItem(
    user: UserProfileResponse,
    onRoleChange: () -> Unit,
    onStatusToggle: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.5.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = user.fullName.ifEmpty { user.username ?: "User" },
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(text = user.email, fontSize = 12.sp, color = Color.Gray)
                }

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    // Role Badge
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = when (user.role.lowercase()) {
                            "owner" -> Color(0xFFFFD700)
                            "sub_owner" -> Color(0xFFE1BEE7)
                            "admin" -> Color(0xFFFFE0B2)
                            else -> Color(0xFFE8F5E9)
                        }
                    ) {
                        Text(
                            text = if (user.role.lowercase() == "sub_owner") "SUB-OWNER" else user.role.uppercase(),
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = when (user.role.lowercase()) {
                                "owner" -> Color.Black
                                "sub_owner" -> Color(0xFF6A1B9A)
                                "admin" -> Color(0xFFE65100)
                                else -> ForestGreenDark
                            },
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }

                    // Status Badge
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = if (user.isActive) Color(0xFFE8F5E9) else Color(0xFFFFEBEE)
                    ) {
                        Text(
                            text = if (user.isActive) "ACTIVE" else "SUSPENDED",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (user.isActive) ForestGreenDark else Color(0xFFC62828),
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
            }

            if (user.role.lowercase() == "sub_owner" && user.permissions.isNotEmpty()) {
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    user.permissions.forEach { perm ->
                        val shortName = when (perm) {
                            "can_manage_users" -> "Users"
                            "can_moderate_cases" -> "Moderation"
                            "can_view_telemetry" -> "Telemetry"
                            "can_view_audit_logs" -> "Audit"
                            else -> perm
                        }
                        Surface(
                            shape = RoundedCornerShape(3.dp),
                            color = Color(0xFFF3E5F5)
                        ) {
                            Text(
                                text = shortName,
                                fontSize = 9.sp,
                                color = Color(0xFF6A1B9A),
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(horizontal = 5.dp, vertical = 2.dp)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))
            Divider(color = Color(0xFFEEEEEE))
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                OutlinedButton(
                    onClick = onRoleChange,
                    shape = RoundedCornerShape(6.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Text("Change Role", fontSize = 11.sp)
                }

                Spacer(modifier = Modifier.width(8.dp))

                OutlinedButton(
                    onClick = onStatusToggle,
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = if (user.isActive) Color(0xFFC62828) else ForestGreenPrimary
                    ),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Text(if (user.isActive) "Suspend" else "Activate", fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
fun AdminAuditLogsTab(
    auditLogs: List<AuditLogItem>,
    onRefresh: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Immutable Security Audit Trail",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark
            )
            IconButton(onClick = onRefresh) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ForestGreenDark)
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        if (auditLogs.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No audit log events recorded.", color = Color.Gray)
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(auditLogs) { log ->
                    Card(
                        shape = RoundedCornerShape(8.dp),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(4.dp),
                                    color = when (log.action) {
                                        "OWNER_BOOTSTRAP" -> Color(0xFFFFF9C4)
                                        "ROLE_CHANGE" -> Color(0xFFE3F2FD)
                                        "STATUS_CHANGE" -> Color(0xFFFFEBEE)
                                        "SUB_OWNER_GRANTED", "SUB_OWNER_REVOKED", "SUB_OWNER_PERMISSIONS_UPDATED" -> Color(0xFFF3E5F5)
                                        else -> Color(0xFFF5F5F5)
                                    }
                                ) {
                                    Text(
                                        text = log.action,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = when (log.action) {
                                            "SUB_OWNER_GRANTED", "SUB_OWNER_REVOKED", "SUB_OWNER_PERMISSIONS_UPDATED" -> Color(0xFF6A1B9A)
                                            else -> Color.Black
                                        },
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                                Text(
                                    text = log.timestamp.take(19).replace("T", " "),
                                    fontSize = 11.sp,
                                    color = Color.Gray
                                )
                            }
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(text = log.details ?: "No details provided.", fontSize = 12.sp, color = Color.DarkGray)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Actor: ${log.actorEmail} (${log.actorRole.uppercase()})",
                                fontSize = 10.sp,
                                color = Color.Gray
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AdminModerationTab(
    sharedCases: List<SharedCaseSummary>,
    communityReports: List<CommunityReportResponse> = emptyList(),
    onDeleteReportedPost: (String) -> Unit = {},
    onDeleteReportedComment: (String) -> Unit = {},
    onRefresh: () -> Unit
) {
    var moderationSection by remember { mutableIntStateOf(0) } // 0 = Community Reports, 1 = Shared Cases
    var itemToDelete by remember { mutableStateOf<Pair<String, String>?>(null) } // Pair(targetType, targetId)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Community & Case Moderation",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark
            )
            IconButton(onClick = onRefresh) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ForestGreenDark)
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Section Selector Tabs
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = moderationSection == 0,
                onClick = { moderationSection = 0 },
                label = { Text("Community Reports (${communityReports.size})", fontSize = 12.sp) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = ForestGreenPrimary,
                    selectedLabelColor = Color.White
                )
            )
            FilterChip(
                selected = moderationSection == 1,
                onClick = { moderationSection = 1 },
                label = { Text("Shared Cases (${sharedCases.size})", fontSize = 12.sp) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = ForestGreenPrimary,
                    selectedLabelColor = Color.White
                )
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (moderationSection == 0) {
            // Community Moderation Reports
            if (communityReports.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenPrimary, modifier = Modifier.size(42.dp))
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("No community content reports pending review.", color = Color.Gray, fontSize = 13.sp)
                    }
                }
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(communityReports) { report ->
                        Card(
                            shape = RoundedCornerShape(10.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Surface(
                                        shape = RoundedCornerShape(4.dp),
                                        color = Color(0xFFFFEBEE)
                                    ) {
                                        Text(
                                            text = "REPORT ON ${report.targetType.uppercase()}",
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = Color(0xFFC62828),
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }

                                    Text(
                                        text = report.createdAt.take(10),
                                        fontSize = 11.sp,
                                        color = Color.Gray
                                    )
                                }

                                Spacer(modifier = Modifier.height(6.dp))

                                Text(
                                    text = "Reason: ${report.reason.uppercase()}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 13.sp,
                                    color = ForestGreenDark
                                )

                                report.details?.let { det ->
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = "Details: \"$det\"",
                                        fontSize = 12.sp,
                                        color = Color.DarkGray
                                    )
                                }

                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "Target ID: ${report.targetId} • Reporter: ${report.reporterId}",
                                    fontSize = 10.sp,
                                    color = Color.Gray
                                )

                                Spacer(modifier = Modifier.height(10.dp))

                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.End
                                ) {
                                    Button(
                                        onClick = { itemToDelete = Pair(report.targetType, report.targetId) },
                                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F)),
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(14.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("Delete Reported ${report.targetType.replaceFirstChar { it.uppercase() }}", fontSize = 11.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            // Shared Cases
            if (sharedCases.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No shared cases currently pending moderation.", color = Color.Gray)
                }
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(sharedCases) { caseItem ->
                        Card(
                            shape = RoundedCornerShape(8.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(text = caseItem.caseId, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                    Surface(
                                        shape = RoundedCornerShape(4.dp),
                                        color = Color(0xFFE8F5E9)
                                    ) {
                                        Text(
                                            text = caseItem.createdAt.take(10),
                                            fontSize = 10.sp,
                                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                                        )
                                    }
                                }
                                Spacer(modifier = Modifier.height(4.dp))
                                val pathogen = caseItem.caseSummary["primary_diagnosis"]?.toString() ?: "Diagnosed Case"
                                Text(text = "Pathogen: $pathogen", fontSize = 12.sp)
                                Text(text = "Target: ${caseItem.targetEntity}", fontSize = 11.sp, color = Color.Gray)
                                Text(text = "Notes: ${caseItem.notes ?: "Community shared case"}", fontSize = 11.sp, color = Color.Gray)
                            }
                        }
                    }
                }
            }
        }
    }

    // Deletion confirmation
    itemToDelete?.let { (targetType, targetId) ->
        AlertDialog(
            onDismissRequest = { itemToDelete = null },
            icon = { Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFD32F2F)) },
            title = { Text("Confirm Content Deletion") },
            text = { Text("As administrator/moderator, are you sure you want to permanently delete this reported $targetType ($targetId)?") },
            confirmButton = {
                Button(
                    onClick = {
                        if (targetType == "post") {
                            onDeleteReportedPost(targetId)
                        } else {
                            onDeleteReportedComment(targetId)
                        }
                        itemToDelete = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F))
                ) {
                    Text("Delete Permanently", color = Color.White)
                }
            },
            dismissButton = {
                TextButton(onClick = { itemToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}
