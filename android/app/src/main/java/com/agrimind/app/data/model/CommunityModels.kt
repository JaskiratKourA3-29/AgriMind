package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Data models for AgriMind Farmer-to-Farmer Community & Social Connection.
 *
 * Implements:
 * - Peer discussion posts with agricultural categorization & image attachments
 * - Author display name and role badge (PII protected: zero email/phone exposure)
 * - Threaded comments with parent_comment_id hierarchy
 * - Helpful / Like vote counters and toggle state
 * - Solution acceptance flag (is_accepted) for question resolution
 * - Peer advice regulatory disclaimer metadata
 * - Content moderation reports
 */

data class CommunityPost(
    @SerializedName("post_id")
    val postId: String = "",

    @SerializedName("author_id")
    val authorId: String = "",

    @SerializedName("author_name")
    val authorName: String = "Farmer",

    @SerializedName("author_role")
    val authorRole: String = "farmer",

    @SerializedName("title")
    val title: String = "",

    @SerializedName("content")
    val content: String = "",

    @SerializedName("category")
    val category: String = "general_farming",

    @SerializedName("category_label")
    val categoryLabel: String? = null,

    @SerializedName("image_url")
    val imageUrl: String? = null,

    @SerializedName("likes_count")
    val likesCount: Int = 0,

    @SerializedName("comments_count")
    val commentsCount: Int = 0,

    @SerializedName("has_liked")
    val hasLiked: Boolean = false,

    @SerializedName("is_pinned")
    val isPinned: Boolean = false,

    @SerializedName("is_resolved")
    val isResolved: Boolean = false,

    @SerializedName("created_at")
    val createdAt: String = "",

    @SerializedName("updated_at")
    val updatedAt: String = ""
) {
    val displayCategory: String
        get() = categoryLabel ?: when (category.lowercase()) {
            "crop_disease" -> "Crop Disease"
            "pest_management" -> "Pest Management"
            "irrigation" -> "Irrigation & Water"
            "soil_health" -> "Soil Health"
            "fertilizers" -> "Fertilizers & Nutrients"
            "weather_impacts" -> "Weather Impacts"
            else -> "General Farming"
        }

    val displayAuthorBadge: String
        get() = when (authorRole.lowercase()) {
            "owner" -> "PROJECT OWNER"
            "sub_owner" -> "SUB-OWNER"
            "admin" -> "OFFICER / ADMIN"
            else -> "FARMER"
        }

    val isAuthorOfficerOrOwner: Boolean
        get() = authorRole.lowercase() in listOf("owner", "sub_owner", "admin")
}

data class CommunityComment(
    @SerializedName("comment_id")
    val commentId: String = "",

    @SerializedName("post_id")
    val postId: String = "",

    @SerializedName("parent_comment_id")
    val parentCommentId: String? = null,

    @SerializedName("author_id")
    val authorId: String = "",

    @SerializedName("author_name")
    val authorName: String = "Farmer",

    @SerializedName("author_role")
    val authorRole: String = "farmer",

    @SerializedName("comment_text")
    val commentText: String = "",

    @SerializedName("likes_count")
    val likesCount: Int = 0,

    @SerializedName("has_liked")
    val hasLiked: Boolean = false,

    @SerializedName("is_accepted")
    val isAccepted: Boolean = false,

    @SerializedName("created_at")
    val createdAt: String = "",

    @SerializedName("updated_at")
    val updatedAt: String = "",

    @SerializedName("replies")
    val replies: List<CommunityComment> = emptyList()
) {
    val displayAuthorBadge: String
        get() = when (authorRole.lowercase()) {
            "owner" -> "PROJECT OWNER"
            "sub_owner" -> "SUB-OWNER"
            "admin" -> "OFFICER / ADMIN"
            else -> "FARMER"
        }
}

data class CommunityFeedResponse(
    @SerializedName("posts")
    val posts: List<CommunityPost> = emptyList(),

    @SerializedName("total_count")
    val totalCount: Int = 0,

    @SerializedName("limit")
    val limit: Int = 20,

    @SerializedName("offset")
    val offset: Int = 0,

    @SerializedName("has_more")
    val hasMore: Boolean = false
)

data class CommunityReactionResponse(
    @SerializedName("status")
    val status: String = "",

    @SerializedName("message")
    val message: String = "",

    @SerializedName("target_type")
    val targetType: String = "",

    @SerializedName("target_id")
    val targetId: String = "",

    @SerializedName("likes_count")
    val likesCount: Int = 0,

    @SerializedName("has_liked")
    val hasLiked: Boolean = false
)

data class CommunityReportResponse(
    @SerializedName("report_id")
    val reportId: String = "",

    @SerializedName("reporter_id")
    val reporterId: String = "",

    @SerializedName("target_type")
    val targetType: String = "",

    @SerializedName("target_id")
    val targetId: String = "",

    @SerializedName("reason")
    val reason: String = "",

    @SerializedName("details")
    val details: String? = null,

    @SerializedName("status")
    val status: String = "pending",

    @SerializedName("created_at")
    val createdAt: String = ""
)

data class CommunityPostCreateRequest(
    @SerializedName("title")
    val title: String,

    @SerializedName("content")
    val content: String,

    @SerializedName("category")
    val category: String = "general_farming",

    @SerializedName("image_url")
    val imageUrl: String? = null
)

data class CommunityPostUpdateRequest(
    @SerializedName("title")
    val title: String? = null,

    @SerializedName("content")
    val content: String? = null,

    @SerializedName("category")
    val category: String? = null,

    @SerializedName("image_url")
    val imageUrl: String? = null
)

data class CommunityCommentCreateRequest(
    @SerializedName("comment_text")
    val commentText: String,

    @SerializedName("parent_comment_id")
    val parentCommentId: String? = null
)

data class CommunityReactionRequest(
    @SerializedName("reaction_type")
    val reactionType: String = "like"
)

data class CommunityReportRequest(
    @SerializedName("target_type")
    val targetType: String,

    @SerializedName("target_id")
    val targetId: String,

    @SerializedName("reason")
    val reason: String,

    @SerializedName("details")
    val details: String? = null
)

object CommunityCategories {
    val ALL = listOf(
        "all" to "All Categories",
        "crop_disease" to "Crop Disease",
        "pest_management" to "Pest Management",
        "irrigation" to "Irrigation",
        "soil_health" to "Soil Health",
        "fertilizers" to "Fertilizers",
        "weather_impacts" to "Weather",
        "general_farming" to "General Farming"
    )

    val CREATION_LIST = listOf(
        "general_farming" to "General Farming",
        "crop_disease" to "Crop Disease",
        "pest_management" to "Pest Management",
        "irrigation" to "Irrigation & Water",
        "soil_health" to "Soil Health",
        "fertilizers" to "Fertilizers & Nutrients",
        "weather_impacts" to "Weather Impacts"
    )
}

