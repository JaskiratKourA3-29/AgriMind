package com.agrimind.app.data.api

import com.agrimind.app.data.model.*
import com.agrimind.app.data.model.AdminSystemStatusResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit API interface for AgriMind backend communication.
 * Endpoints:
 * - GET  /health           -> Server health & model status
 * - POST /diagnose         -> Multi-agent tomato disease diagnostic workflow
 * - POST /reassess         -> Adaptive case reassessment with updated agronomic evidence
 * - GET  /cases/{case_id}  -> Retrieve authoritative case by case ID
 * - POST /chat             -> Grounded agronomic conversational assistant
 */
interface AgriMindApiService {

    @GET("health")
    suspend fun getHealth(): Response<HealthResponse>

    @GET("cases/{case_id}")
    suspend fun getCase(
        @Path("case_id") caseId: String
    ): Response<DiagnosisResponse>

    @Multipart
    @POST("diagnose")
    suspend fun diagnose(
        @Part file: MultipartBody.Part,
        @Part("leaf_damage_percentage") leafDamagePercentage: RequestBody? = null,
        @Part("canopy_spread") canopySpread: RequestBody? = null,
        @Part("affected_organs") affectedOrgans: RequestBody? = null,
        @Part("weather_conditions") weatherConditions: RequestBody? = null,
        @Part("field_notes") fieldNotes: RequestBody? = null,
        @Part("latitude") latitude: RequestBody? = null,
        @Part("longitude") longitude: RequestBody? = null,
        @Part("use_live_weather") useLiveWeather: RequestBody? = null
    ): Response<DiagnosisResponse>

    @GET("weather/live")
    suspend fun getLiveWeather(
        @Query("latitude") latitude: Double? = null,
        @Query("longitude") longitude: Double? = null
    ): Response<LiveWeatherData>

    @POST("cases/share")
    suspend fun shareCase(
        @Body request: CaseShareRequest
    ): Response<CaseShareResponse>

    @GET("cases/shared")
    suspend fun listSharedCases(
        @Query("target_entity") targetEntity: String = "cooperative_all",
        @Query("limit") limit: Int = 50
    ): Response<List<SharedCaseSummary>>

    @GET("cooperative/insights")
    suspend fun getCooperativeInsights(
        @Query("cooperative_id") cooperativeId: String = "cooperative_all",
        @Query("region") region: String = "Jammu & Kashmir Cooperative"
    ): Response<CooperativeInsightsData>

    @GET("cooperative/comparison")
    suspend fun getCooperativeComparison(): Response<CooperativeComparisonResponse>

    @POST("cases/{case_id}/comments")
    suspend fun addCaseComment(
        @Path("case_id") caseId: String,
        @Body request: CaseCommentCreate
    ): Response<CaseComment>

    @GET("cases/{case_id}/comments")
    suspend fun getCaseComments(
        @Path("case_id") caseId: String
    ): Response<List<CaseComment>>

    @POST("cases/{case_id}/outcome")
    suspend fun recordCaseOutcome(
        @Path("case_id") caseId: String,
        @Body request: CaseOutcomeCreate
    ): Response<CaseOutcome>

    @GET("cases/{case_id}/outcome")
    suspend fun getCaseOutcome(
        @Path("case_id") caseId: String
    ): Response<CaseOutcome>

    @POST("reassess")
    suspend fun reassess(
        @Body request: ReassessmentRequest
    ): Response<ReassessmentResponse>

    @POST("chat")
    suspend fun chat(
        @Body request: ChatRequest
    ): Response<ChatResponse>

    @POST("auth/signup")
    suspend fun signup(
        @Body request: UserSignupRequest
    ): Response<AuthTokenResponse>

    @POST("auth/login")
    suspend fun login(
        @Body request: UserLoginRequest
    ): Response<AuthTokenResponse>

    @POST("auth/logout")
    suspend fun logout(): Response<Map<String, String>>

    @GET("auth/me")
    suspend fun getProfile(): Response<UserProfileResponse>

    @GET("admin/system/status")
    suspend fun getAdminSystemStatus(): Response<AdminSystemStatusResponse>

    @GET("admin/users")
    suspend fun listUsers(
        @Query("limit") limit: Int = 50
    ): Response<List<UserProfileResponse>>

    @GET("admin/users/search")
    suspend fun searchUsers(
        @Query("query") query: String? = null,
        @Query("role") role: String? = null,
        @Query("limit") limit: Int = 50
    ): Response<List<UserProfileResponse>>

    @POST("admin/users/{user_id}/role")
    suspend fun updateUserRole(
        @Path("user_id") userId: String,
        @Body request: UserRoleUpdateRequest
    ): Response<Map<String, String>>

    @POST("admin/users/{user_id}/status")
    suspend fun updateUserStatus(
        @Path("user_id") userId: String,
        @Body request: UserStatusUpdateRequest
    ): Response<Map<String, String>>

    @GET("admin/audit-logs")
    suspend fun getAuditLogs(
        @Query("limit") limit: Int = 50
    ): Response<List<AuditLogItem>>

    @GET("admin/sub-owners")
    suspend fun listSubOwners(): Response<List<SubOwnerInfo>>

    @POST("admin/sub-owners/grant")
    suspend fun grantSubOwner(
        @Body request: GrantSubOwnerRequest
    ): Response<Map<String, Any>>

    @POST("admin/sub-owners/{user_id}/revoke")
    suspend fun revokeSubOwner(
        @Path("user_id") userId: String
    ): Response<Map<String, String>>

    @POST("admin/sub-owners/{user_id}/permissions")
    suspend fun updateSubOwnerPermissions(
        @Path("user_id") userId: String,
        @Body request: UpdateSubOwnerPermissionsRequest
    ): Response<Map<String, Any>>

    // =========================================================================
    // Farmer Community & Social Connection Endpoints
    // =========================================================================

    @GET("community/posts")
    suspend fun getCommunityPosts(
        @Query("query") query: String? = null,
        @Query("category") category: String? = null,
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0
    ): Response<CommunityFeedResponse>

    @GET("community/posts/{post_id}")
    suspend fun getCommunityPost(
        @Path("post_id") postId: String
    ): Response<CommunityPost>

    @POST("community/posts")
    suspend fun createCommunityPost(
        @Body request: CommunityPostCreateRequest
    ): Response<CommunityPost>

    @PUT("community/posts/{post_id}")
    suspend fun updateCommunityPost(
        @Path("post_id") postId: String,
        @Body request: CommunityPostUpdateRequest
    ): Response<CommunityPost>

    @DELETE("community/posts/{post_id}")
    suspend fun deleteCommunityPost(
        @Path("post_id") postId: String
    ): Response<Map<String, String>>

    @GET("community/posts/{post_id}/comments")
    suspend fun getCommunityComments(
        @Path("post_id") postId: String
    ): Response<List<CommunityComment>>

    @POST("community/posts/{post_id}/comments")
    suspend fun addCommunityComment(
        @Path("post_id") postId: String,
        @Body request: CommunityCommentCreateRequest
    ): Response<CommunityComment>

    @DELETE("community/comments/{comment_id}")
    suspend fun deleteCommunityComment(
        @Path("comment_id") commentId: String
    ): Response<Map<String, String>>

    @POST("community/posts/{post_id}/comments/{comment_id}/accept")
    suspend fun acceptCommunityAnswer(
        @Path("post_id") postId: String,
        @Path("comment_id") commentId: String
    ): Response<Map<String, String>>

    @POST("community/reactions/{target_type}/{target_id}")
    suspend fun toggleCommunityReaction(
        @Path("target_type") targetType: String,
        @Path("target_id") targetId: String,
        @Body request: CommunityReactionRequest? = null
    ): Response<CommunityReactionResponse>

    @POST("community/reports")
    suspend fun reportCommunityContent(
        @Body request: CommunityReportRequest
    ): Response<Map<String, String>>

    @GET("community/reports")
    suspend fun listCommunityReports(
        @Query("limit") limit: Int = 50
    ): Response<List<CommunityReportResponse>>

    @Multipart
    @POST("community/upload-image")
    suspend fun uploadCommunityImage(
        @Part file: MultipartBody.Part
    ): Response<Map<String, String>>
}
