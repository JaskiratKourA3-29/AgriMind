package com.agrimind.app.ui.viewmodel

import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.*
import com.google.gson.Gson
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class AuthAndAdminModelTest {

    private lateinit var sessionManager: UserSessionManager
    private val gson = Gson()

    @Before
    fun setUp() {
        UserSessionManager.resetInstanceForTesting()
        sessionManager = UserSessionManager(null)
    }

    @After
    fun tearDown() {
        UserSessionManager.resetInstanceForTesting()
    }

    @Test
    fun testFarmerSessionRoleSeparation() {
        sessionManager.saveSession(
            token = "jwt-farmer-token",
            userId = "USER-FARMER-01",
            username = "ramesh_singh",
            role = "farmer",
            fullName = "Ramesh Singh",
            email = "ramesh@example.com"
        )

        assertTrue(sessionManager.isLoggedIn())
        assertEquals("USER-FARMER-01", sessionManager.getUserId())
        assertEquals("ramesh_singh", sessionManager.getUsername())
        assertEquals("ramesh@example.com", sessionManager.getEmail())
        assertEquals("farmer", sessionManager.getRole())
        assertFalse("Farmer must NOT possess administrator privileges", sessionManager.isAdmin())
        assertFalse("Farmer must NOT possess owner privileges", sessionManager.isOwner())
        assertEquals("Bearer jwt-farmer-token", sessionManager.getAuthHeader())
    }

    @Test
    fun testAdminSessionRolePrivileges() {
        sessionManager.saveSession(
            token = "jwt-admin-token",
            userId = "USER-ADMIN-01",
            username = "extension_officer",
            role = "admin",
            fullName = "State Extension Officer",
            email = "admin@agrimind.jammu.gov.in"
        )

        assertTrue(sessionManager.isLoggedIn())
        assertEquals("admin", sessionManager.getRole())
        assertTrue("Admin must possess administrator privileges", sessionManager.isAdmin())
        assertFalse("Admin must NOT be classified as owner", sessionManager.isOwner())
    }

    @Test
    fun testOwnerSessionRolePrivileges() {
        sessionManager.saveSession(
            token = "jwt-owner-token",
            userId = "USER-OWNER-01",
            username = "lead_pi",
            role = "owner",
            fullName = "AgriMind Project Director",
            email = "owner@agrimind.jammu.gov.in"
        )

        assertTrue(sessionManager.isLoggedIn())
        assertEquals("owner", sessionManager.getRole())
        assertTrue("Project Owner must have administrator console access", sessionManager.isAdmin())
        assertTrue("Project Owner must be recognized as owner", sessionManager.isOwner())
    }

    @Test
    fun testClearSessionRevokesState() {
        sessionManager.saveSession(
            token = "jwt-test-token",
            userId = "USER-TEMP",
            username = "temp_user",
            role = "farmer"
        )
        assertTrue(sessionManager.isLoggedIn())

        sessionManager.clearSession()
        assertFalse(sessionManager.isLoggedIn())
        assertNull(sessionManager.getAuthToken())
        assertNull(sessionManager.getAuthHeader())
        assertEquals("farmer", sessionManager.getRole())
    }

    @Test
    fun testAuthTokenResponseNestedJsonParsing() {
        val json = """
            {
                "access_token": "jwt-nested-token-xyz",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "user_id": "USER-NESTED-99",
                    "email": "farmer_nested@example.com",
                    "full_name": "Nested Farmer",
                    "role": "farmer",
                    "is_active": true
                }
            }
        """.trimIndent()

        val parsed = gson.fromJson(json, AuthTokenResponse::class.java)
        assertEquals("jwt-nested-token-xyz", parsed.accessToken)
        assertEquals("USER-NESTED-99", parsed.effectiveUserId)
        assertEquals("farmer", parsed.effectiveRole)
        assertEquals("Nested Farmer", parsed.effectiveFullName)
        assertEquals("farmer_nested@example.com", parsed.effectiveEmail)
    }

    @Test
    fun testAuthTokenResponseFlatJsonParsing() {
        val json = """
            {
                "access_token": "jwt-flat-token-abc",
                "token_type": "bearer",
                "expires_in": 86400,
                "user_id": "USER-FLAT-01",
                "username": "flat_user",
                "role": "admin",
                "full_name": "Flat Admin"
            }
        """.trimIndent()

        val parsed = gson.fromJson(json, AuthTokenResponse::class.java)
        assertEquals("jwt-flat-token-abc", parsed.accessToken)
        assertEquals("USER-FLAT-01", parsed.effectiveUserId)
        assertEquals("admin", parsed.effectiveRole)
        assertEquals("Flat Admin", parsed.effectiveFullName)
    }

    @Test
    fun testUserProfileDisplayRoleFormatting() {
        val farmer = UserProfileResponse(userId = "1", email = "f@a.com", fullName = "F", role = "farmer")
        val admin = UserProfileResponse(userId = "2", email = "a@a.com", fullName = "A", role = "admin")
        val owner = UserProfileResponse(userId = "3", email = "o@a.com", fullName = "O", role = "owner")

        assertEquals("REGISTERED FARMER", farmer.displayRole)
        assertEquals("ADMINISTRATOR", admin.displayRole)
        assertEquals("PROJECT OWNER", owner.displayRole)
    }

    @Test
    fun testAuditLogItemSerialization() {
        val log = AuditLogItem(
            logId = "AUDIT-123456",
            actorId = "USER-OWNER",
            actorEmail = "owner@agrimind.in",
            actorRole = "owner",
            targetUserId = "USER-FARMER-01",
            action = "ROLE_CHANGE",
            details = "Promoted user to administrator",
            timestamp = "2026-11-03T12:00:00Z"
        )
        val json = gson.toJson(log)
        val deserialized = gson.fromJson(json, AuditLogItem::class.java)

        assertEquals(log.logId, deserialized.logId)
        assertEquals(log.action, deserialized.action)
        assertEquals(log.actorRole, deserialized.actorRole)
        assertEquals(log.details, deserialized.details)
    }
}

