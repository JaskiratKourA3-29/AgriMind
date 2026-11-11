package com.agrimind.app.ui.viewmodel

import com.agrimind.app.data.model.*
import com.google.gson.Gson
import org.junit.Assert.*
import org.junit.Test

class CommunityFeatureModelTest {

    private val gson = Gson()

    @Test
    fun testCommunityPostSerializationAndCategoryMapping() {
        val post = CommunityPost(
            postId = "POST-TEST-1001",
            authorId = "USER-FARMER-SIMRAN",
            authorName = "Simran Kour",
            authorRole = "farmer",
            title = "Tomato Early Blight Symptoms on Lower Foliage",
            content = "Concentric brown rings appearing on lower leaves after rain. Looking for organic management advice.",
            category = "crop_disease",
            categoryLabel = "Crop Disease",
            imageUrl = "/community/images/leaf_sample.jpg",
            likesCount = 5,
            commentsCount = 2,
            hasLiked = true,
            isPinned = false,
            isResolved = true,
            createdAt = "2026-11-03T18:00:00Z",
            updatedAt = "2026-11-03T18:00:00Z"
        )

        assertEquals("Crop Disease", post.displayCategory)
        assertEquals("FARMER", post.displayAuthorBadge)
        assertFalse(post.isAuthorOfficerOrOwner)
        assertTrue(post.isResolved)

        // Serialize and Deserialize
        val json = gson.toJson(post)
        val deserialized = gson.fromJson(json, CommunityPost::class.java)

        assertEquals(post.postId, deserialized.postId)
        assertEquals(post.title, deserialized.title)
        assertEquals(post.likesCount, deserialized.likesCount)
        assertTrue(deserialized.hasLiked)
        assertTrue(deserialized.isResolved)
    }

    @Test
    fun testCommunityPostAuthorBadgesForGovernanceRoles() {
        val ownerPost = CommunityPost(
            postId = "POST-OWNER",
            authorId = "USER-3FC32032",
            authorName = "Jaskirat Kour",
            authorRole = "owner",
            title = "Seasonal IPM Guidelines for Tomato Growers",
            content = "Please refer to the updated ICAR schedule."
        )
        assertEquals("PROJECT OWNER", ownerPost.displayAuthorBadge)
        assertTrue(ownerPost.isAuthorOfficerOrOwner)

        val subOwnerPost = CommunityPost(
            postId = "POST-SUB",
            authorId = "USER-SUB",
            authorName = "Extension Specialist",
            authorRole = "sub_owner",
            title = "Soil pH testing in RS Pura",
            content = "Soil testing camps available."
        )
        assertEquals("SUB-OWNER", subOwnerPost.displayAuthorBadge)
        assertTrue(subOwnerPost.isAuthorOfficerOrOwner)

        val adminPost = CommunityPost(
            postId = "POST-ADMIN",
            authorId = "USER-ADMIN",
            authorName = "Officer",
            authorRole = "admin",
            title = "Weather advisory",
            content = "Heavy rain expected."
        )
        assertEquals("OFFICER / ADMIN", adminPost.displayAuthorBadge)
        assertTrue(adminPost.isAuthorOfficerOrOwner)
    }

    @Test
    fun testCommunityCommentWithThreadedReplies() {
        val reply = CommunityComment(
            commentId = "COMM-REPLY-02",
            postId = "POST-TEST-1001",
            parentCommentId = "COMM-TOP-01",
            authorId = "USER-3FC32032",
            authorName = "Jaskirat Kour",
            authorRole = "owner",
            commentText = "Copper oxychloride at 2.5 g/L is recommended if disease exceeds ETL.",
            likesCount = 3,
            hasLiked = false,
            isAccepted = true,
            createdAt = "2026-11-03T18:15:00Z"
        )

        val topComment = CommunityComment(
            commentId = "COMM-TOP-01",
            postId = "POST-TEST-1001",
            parentCommentId = null,
            authorId = "USER-FARMER-RAMESH",
            authorName = "Ramesh Kumar",
            authorRole = "farmer",
            commentText = "Have you checked the soil moisture levels?",
            likesCount = 1,
            hasLiked = true,
            isAccepted = false,
            createdAt = "2026-11-03T18:10:00Z",
            replies = listOf(reply)
        )

        assertEquals("FARMER", topComment.displayAuthorBadge)
        assertEquals("PROJECT OWNER", reply.displayAuthorBadge)
        assertTrue(reply.isAccepted)
        assertEquals(1, topComment.replies.size)
        assertEquals("COMM-TOP-01", topComment.replies[0].parentCommentId)

        // Verify JSON round-trip
        val json = gson.toJson(topComment)
        val deserialized = gson.fromJson(json, CommunityComment::class.java)
        assertEquals("COMM-TOP-01", deserialized.commentId)
        assertEquals(1, deserialized.replies.size)
        assertEquals("COMM-REPLY-02", deserialized.replies[0].commentId)
        assertTrue(deserialized.replies[0].isAccepted)
    }

    @Test
    fun testCommunityFeedResponseParsing() {
        val json = """
            {
                "posts": [
                    {
                        "post_id": "POST-01",
                        "author_id": "USER-01",
                        "author_name": "Farmer 1",
                        "author_role": "farmer",
                        "title": "Aphid Control Question",
                        "content": "Need biological control suggestions for aphids.",
                        "category": "pest_management",
                        "likes_count": 4,
                        "comments_count": 1,
                        "has_liked": false,
                        "is_pinned": false,
                        "is_resolved": false,
                        "created_at": "2026-11-03T18:20:00Z",
                        "updated_at": "2026-11-03T18:20:00Z"
                    }
                ],
                "total_count": 1,
                "limit": 20,
                "offset": 0,
                "has_more": false
            }
        """.trimIndent()

        val feed = gson.fromJson(json, CommunityFeedResponse::class.java)
        assertEquals(1, feed.totalCount)
        assertFalse(feed.hasMore)
        assertEquals(1, feed.posts.size)
        assertEquals("Pest Management", feed.posts[0].displayCategory)
    }

    @Test
    fun testCommunityReactionResponseParsing() {
        val json = """
            {
                "status": "success",
                "message": "Reaction toggled successfully",
                "target_type": "post",
                "target_id": "POST-01",
                "likes_count": 5,
                "has_liked": true
            }
        """.trimIndent()

        val resp = gson.fromJson(json, CommunityReactionResponse::class.java)
        assertEquals("success", resp.status)
        assertEquals(5, resp.likesCount)
        assertTrue(resp.hasLiked)
        assertEquals("post", resp.targetType)
    }

    @Test
    fun testPiiProtectionInCommunityModels() {
        // Assert that CommunityPost and CommunityComment data models have no email or phone property
        val postFields = CommunityPost::class.java.declaredFields.map { it.name.lowercase() }
        assertFalse("CommunityPost must NOT contain an email field", postFields.contains("email"))
        assertFalse("CommunityPost must NOT contain a phone field", postFields.contains("phone"))

        val commentFields = CommunityComment::class.java.declaredFields.map { it.name.lowercase() }
        assertFalse("CommunityComment must NOT contain an email field", commentFields.contains("email"))
        assertFalse("CommunityComment must NOT contain a phone field", commentFields.contains("phone"))
    }
}

