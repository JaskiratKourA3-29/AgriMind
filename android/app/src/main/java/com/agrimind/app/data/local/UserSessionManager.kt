package com.agrimind.app.data.local

import android.content.Context
import android.content.SharedPreferences

/**
 * Local persistent session manager for user authentication, roles, and preferences.
 * Includes in-memory fallback for robust execution in testing and restricted sandboxes.
 */
class UserSessionManager(context: Context?) {

    private val inMemoryMap = mutableMapOf<String, String>()
    private val prefs: SharedPreferences? = try {
        context?.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    } catch (_: Throwable) {
        null
    }

    companion object {
        private const val PREFS_NAME = "agrimind_user_session"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USERNAME = "username"
        private const val KEY_FULL_NAME = "full_name"
        private const val KEY_EMAIL = "email"
        private const val KEY_ROLE = "role"
        private const val KEY_PERMISSIONS = "permissions"
        private const val KEY_LANGUAGE = "selected_language"
        private const val KEY_GATEWAY_URL = "custom_gateway_url"

        @Volatile
        private var instance: UserSessionManager? = null

        fun getInstance(context: Context?): UserSessionManager {
            return instance ?: synchronized(this) {
                instance ?: UserSessionManager(context?.applicationContext ?: context).also { instance = it }
            }
        }

        fun resetInstanceForTesting() {
            instance = null
        }
    }

    fun saveSession(
        token: String,
        userId: String,
        username: String,
        role: String = "farmer",
        fullName: String? = null,
        email: String? = null,
        permissions: List<String> = emptyList()
    ) {
        val name = fullName ?: username
        val mail = email ?: (if (username.contains("@")) username else "")
        val permsStr = permissions.joinToString(",")
        if (prefs != null) {
            prefs.edit()
                .putString(KEY_AUTH_TOKEN, token)
                .putString(KEY_USER_ID, userId)
                .putString(KEY_USERNAME, username)
                .putString(KEY_EMAIL, mail)
                .putString(KEY_ROLE, role)
                .putString(KEY_FULL_NAME, name)
                .putString(KEY_PERMISSIONS, permsStr)
                .apply()
        } else {
            inMemoryMap[KEY_AUTH_TOKEN] = token
            inMemoryMap[KEY_USER_ID] = userId
            inMemoryMap[KEY_USERNAME] = username
            inMemoryMap[KEY_EMAIL] = mail
            inMemoryMap[KEY_ROLE] = role
            inMemoryMap[KEY_FULL_NAME] = name
            inMemoryMap[KEY_PERMISSIONS] = permsStr
        }
    }

    fun clearSession() {
        val currentLang = getLanguage()
        if (prefs != null) {
            prefs.edit()
                .remove(KEY_AUTH_TOKEN)
                .remove(KEY_USER_ID)
                .remove(KEY_USERNAME)
                .remove(KEY_EMAIL)
                .remove(KEY_ROLE)
                .remove(KEY_FULL_NAME)
                .remove(KEY_PERMISSIONS)
                .apply()
        } else {
            inMemoryMap.remove(KEY_AUTH_TOKEN)
            inMemoryMap.remove(KEY_USER_ID)
            inMemoryMap.remove(KEY_USERNAME)
            inMemoryMap.remove(KEY_EMAIL)
            inMemoryMap.remove(KEY_ROLE)
            inMemoryMap.remove(KEY_FULL_NAME)
            inMemoryMap.remove(KEY_PERMISSIONS)
        }
        setLanguage(currentLang)
    }

    fun isLoggedIn(): Boolean {
        val token = if (prefs != null) prefs.getString(KEY_AUTH_TOKEN, null) else inMemoryMap[KEY_AUTH_TOKEN]
        return !token.isNullOrBlank()
    }

    fun getAuthToken(): String? {
        return if (prefs != null) prefs.getString(KEY_AUTH_TOKEN, null) else inMemoryMap[KEY_AUTH_TOKEN]
    }

    fun getAuthHeader(): String? {
        val token = getAuthToken()
        return if (!token.isNullOrBlank()) "Bearer $token" else null
    }

    fun getUserId(): String? {
        return if (prefs != null) prefs.getString(KEY_USER_ID, null) else inMemoryMap[KEY_USER_ID]
    }

    fun getUsername(): String {
        return (if (prefs != null) prefs.getString(KEY_USERNAME, "Guest Farmer") else inMemoryMap[KEY_USERNAME]) ?: "Guest Farmer"
    }

    fun getEmail(): String {
        return (if (prefs != null) prefs.getString(KEY_EMAIL, "") else inMemoryMap[KEY_EMAIL]) ?: ""
    }

    fun getFullName(): String {
        return (if (prefs != null) prefs.getString(KEY_FULL_NAME, "AgriMind User") else inMemoryMap[KEY_FULL_NAME]) ?: "AgriMind User"
    }

    fun getRole(): String {
        return (if (prefs != null) prefs.getString(KEY_ROLE, "farmer") else inMemoryMap[KEY_ROLE]) ?: "farmer"
    }

    fun isAdmin(): Boolean {
        val r = getRole().lowercase()
        return r == "admin" || r == "owner" || r == "sub_owner"
    }

    fun isOwner(): Boolean {
        return getRole().equals("owner", ignoreCase = true)
    }

    fun isSubOwner(): Boolean {
        return getRole().equals("sub_owner", ignoreCase = true)
    }

    fun getPermissions(): List<String> {
        val raw = if (prefs != null) prefs.getString(KEY_PERMISSIONS, "") else inMemoryMap[KEY_PERMISSIONS]
        return if (raw.isNullOrBlank()) emptyList() else raw.split(",").map { it.trim() }.filter { it.isNotEmpty() }
    }

    fun hasPermission(permission: String): Boolean {
        if (isOwner() || getRole().equals("admin", ignoreCase = true)) return true
        return getPermissions().contains(permission)
    }

    fun getLanguage(): String {
        return (if (prefs != null) prefs.getString(KEY_LANGUAGE, "en") else inMemoryMap[KEY_LANGUAGE]) ?: "en"
    }

    fun setLanguage(languageCode: String) {
        if (prefs != null) {
            prefs.edit().putString(KEY_LANGUAGE, languageCode).apply()
        } else {
            inMemoryMap[KEY_LANGUAGE] = languageCode
        }
    }

    fun getGatewayUrl(): String? {
        return if (prefs != null) prefs.getString(KEY_GATEWAY_URL, null) else inMemoryMap[KEY_GATEWAY_URL]
    }

    fun setGatewayUrl(url: String?) {
        val trimmed = url?.trim()
        if (prefs != null) {
            if (trimmed.isNullOrBlank()) {
                prefs.edit().remove(KEY_GATEWAY_URL).apply()
            } else {
                prefs.edit().putString(KEY_GATEWAY_URL, trimmed).apply()
            }
        } else {
            if (trimmed.isNullOrBlank()) {
                inMemoryMap.remove(KEY_GATEWAY_URL)
            } else {
                inMemoryMap[KEY_GATEWAY_URL] = trimmed
            }
        }
    }
}
