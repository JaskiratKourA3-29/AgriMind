package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Authentication, Role Separation & Security Governance Data Models for AgriMind.
 */
data class UserLoginRequest(
    @SerializedName("email") val email: String? = null,
    @SerializedName("username") val username: String? = null,
    @SerializedName("password") val password: String
)

data class UserSignupRequest(
    @SerializedName("email") val email: String,
    @SerializedName("password") val password: String,
    @SerializedName("full_name") val fullName: String,
    @SerializedName("role") val role: String = "farmer",
    @SerializedName("phone") val phone: String? = null,
    @SerializedName("username") val username: String? = null
)

data class UserProfileResponse(
    @SerializedName("user_id") val userId: String = "",
    @SerializedName("email") val email: String = "",
    @SerializedName("full_name") val fullName: String = "",
    @SerializedName("role") val role: String = "farmer",
    @SerializedName("phone") val phone: String? = "",
    @SerializedName("is_active") val isActive: Boolean = true,
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("username") val username: String? = null,
    @SerializedName("permissions") val permissions: List<String> = emptyList()
) {
    val displayRole: String
        get() = when (role.lowercase()) {
            "owner" -> "PROJECT OWNER"
            "sub_owner" -> "SUB-OWNER"
            "admin" -> "ADMINISTRATOR"
            else -> "REGISTERED FARMER"
        }
}

data class AuthTokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
    @SerializedName("expires_in") val expiresIn: Int = 86400,
    @SerializedName("user") val user: UserProfileResponse? = null,
    @SerializedName("user_id") val userId: String? = null,
    @SerializedName("username") val username: String? = null,
    @SerializedName("role") val role: String? = null,
    @SerializedName("full_name") val fullName: String? = null
) {
    val effectiveUserId: String
        get() = userId ?: user?.userId ?: ""

    val effectiveRole: String
        get() = role ?: user?.role ?: "farmer"

    val effectiveFullName: String
        get() = fullName ?: user?.fullName ?: username ?: user?.email ?: "AgriMind Farmer"

    val effectiveEmail: String
        get() = user?.email ?: username ?: ""

    val effectivePermissions: List<String>
        get() = user?.permissions ?: emptyList()
}

data class SubOwnerInfo(
    @SerializedName("user_id") val userId: String = "",
    @SerializedName("email") val email: String = "",
    @SerializedName("full_name") val fullName: String = "",
    @SerializedName("role") val role: String = "sub_owner",
    @SerializedName("is_active") val isActive: Boolean = true,
    @SerializedName("permissions") val permissions: List<String> = emptyList(),
    @SerializedName("granted_by") val grantedBy: String? = "Main Owner",
    @SerializedName("created_at") val createdAt: String? = null,
    @SerializedName("updated_at") val updatedAt: String? = null
)

data class GrantSubOwnerRequest(
    @SerializedName("user_id") val userId: String,
    @SerializedName("permissions") val permissions: List<String> = listOf("can_view_telemetry")
)

data class UpdateSubOwnerPermissionsRequest(
    @SerializedName("permissions") val permissions: List<String>
)

data class UserRoleUpdateRequest(
    @SerializedName("role") val role: String
)

data class UserStatusUpdateRequest(
    @SerializedName("is_active") val isActive: Boolean
)

data class AuditLogItem(
    @SerializedName("log_id") val logId: String = "",
    @SerializedName("actor_id") val actorId: String = "",
    @SerializedName("actor_email") val actorEmail: String = "",
    @SerializedName("actor_role") val actorRole: String = "",
    @SerializedName("target_user_id") val targetUserId: String? = null,
    @SerializedName("action") val action: String = "",
    @SerializedName("details") val details: String? = null,
    @SerializedName("timestamp") val timestamp: String = ""
)

data class AdminSystemStats(
    @SerializedName("total_users") val totalUsers: Int = 0,
    @SerializedName("total_farmers") val totalFarmers: Int = 0,
    @SerializedName("total_admins") val totalAdmins: Int = 0,
    @SerializedName("total_sub_owners") val totalSubOwners: Int = 0,
    @SerializedName("active_users") val activeUsers: Int = 0,
    @SerializedName("suspended_users") val suspendedUsers: Int = 0,
    @SerializedName("total_audit_events") val totalAuditEvents: Int = 0
)

data class AdminSystemStatusResponse(
    @SerializedName("server_time") val serverTime: String? = null,
    @SerializedName("total_cases") val totalCases: Int = 0,
    @SerializedName("total_users") val totalUsers: Int = 0,
    @SerializedName("total_shared_cases") val totalSharedCases: Int = 0,
    @SerializedName("total_comments") val totalComments: Int = 0,
    @SerializedName("vectorstore_chunks") val vectorstoreChunks: Int = 63,
    @SerializedName("vision_model_status") val visionModelStatus: String? = "active",
    @SerializedName("active_classes") val activeClasses: List<String> = emptyList(),
    @SerializedName("supported_crops") val supportedCrops: List<String> = emptyList(),
    @SerializedName("system_stats") val systemStats: AdminSystemStats? = null
)
