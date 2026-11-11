package com.agrimind.app.ui.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.agrimind.app.data.api.RetrofitClient
import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CommunityUiState(
    val feedPosts: List<CommunityPost> = emptyList(),
    val isLoadingFeed: Boolean = false,
    val feedError: String? = null,
    val searchQuery: String = "",
    val selectedCategory: String = "all",
    val totalCount: Int = 0,
    val hasMore: Boolean = false,
    val offset: Int = 0,

    val activePost: CommunityPost? = null,
    val comments: List<CommunityComment> = emptyList(),
    val isLoadingComments: Boolean = false,
    val commentError: String? = null,
    val replyingToComment: CommunityComment? = null,

    val isSubmitting: Boolean = false,
    val actionMessage: String? = null,
    val actionError: String? = null
)

class CommunityViewModel(application: Application) : AndroidViewModel(application) {

    private val sessionManager = UserSessionManager.getInstance(application)
    private val _uiState = MutableStateFlow(CommunityUiState())
    val uiState: StateFlow<CommunityUiState> = _uiState.asStateFlow()

    init {
        loadFeed(reset = true)
    }

    fun loadFeed(reset: Boolean = false) {
        viewModelScope.launch {
            val currentOffset = if (reset) 0 else _uiState.value.offset
            _uiState.update {
                it.copy(
                    isLoadingFeed = true,
                    feedError = null,
                    offset = currentOffset,
                    feedPosts = if (reset) emptyList() else it.feedPosts
                )
            }

            try {
                val catParam = if (_uiState.value.selectedCategory == "all") null else _uiState.value.selectedCategory
                val queryParam = if (_uiState.value.searchQuery.isBlank()) null else _uiState.value.searchQuery.trim()

                val res = RetrofitClient.apiService.getCommunityPosts(
                    query = queryParam,
                    category = catParam,
                    limit = 20,
                    offset = currentOffset
                )

                if (res.isSuccessful && res.body() != null) {
                    val feedResp = res.body()!!
                    _uiState.update {
                        val merged = if (reset) feedResp.posts else it.feedPosts + feedResp.posts
                        it.copy(
                            feedPosts = merged,
                            isLoadingFeed = false,
                            totalCount = feedResp.totalCount,
                            hasMore = feedResp.hasMore,
                            offset = currentOffset + feedResp.posts.size
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isLoadingFeed = false,
                            feedError = "Failed to load community feed: HTTP ${res.code()}"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoadingFeed = false,
                        feedError = "Connection error: ${e.localizedMessage ?: "Unable to connect"}"
                    )
                }
            }
        }
    }

    fun onSearchQueryChange(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
        loadFeed(reset = true)
    }

    fun onCategoryChange(category: String) {
        _uiState.update { it.copy(selectedCategory = category) }
        loadFeed(reset = true)
    }

    fun openPostDetail(post: CommunityPost) {
        _uiState.update {
            it.copy(
                activePost = post,
                comments = emptyList(),
                commentError = null,
                replyingToComment = null
            )
        }
        loadPostDetail(post.postId)
        loadComments(post.postId)
    }

    fun closePostDetail() {
        _uiState.update {
            it.copy(
                activePost = null,
                comments = emptyList(),
                commentError = null,
                replyingToComment = null
            )
        }
    }

    fun loadPostDetail(postId: String) {
        viewModelScope.launch {
            try {
                val res = RetrofitClient.apiService.getCommunityPost(postId)
                if (res.isSuccessful && res.body() != null) {
                    val updated = res.body()!!
                    _uiState.update { state ->
                        val updatedFeed = state.feedPosts.map { if (it.postId == postId) updated else it }
                        state.copy(
                            activePost = updated,
                            feedPosts = updatedFeed
                        )
                    }
                }
            } catch (_: Exception) { }
        }
    }

    fun loadComments(postId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingComments = true, commentError = null) }
            try {
                val res = RetrofitClient.apiService.getCommunityComments(postId)
                if (res.isSuccessful && res.body() != null) {
                    _uiState.update {
                        it.copy(
                            isLoadingComments = false,
                            comments = res.body()!!
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isLoadingComments = false,
                            commentError = "Failed to load discussions (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoadingComments = false,
                        commentError = e.localizedMessage ?: "Failed to connect to discussions"
                    )
                }
            }
        }
    }

    fun createPost(
        title: String,
        content: String,
        category: String,
        imageUrl: String?,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val req = CommunityPostCreateRequest(
                    title = title.trim(),
                    content = content.trim(),
                    category = category,
                    imageUrl = imageUrl?.trim()?.ifEmpty { null }
                )
                val res = RetrofitClient.apiService.createCommunityPost(req)
                if (res.isSuccessful && res.body() != null) {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionMessage = "Post published successfully!"
                        )
                    }
                    loadFeed(reset = true)
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Could not publish post (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error publishing post"
                    )
                }
            }
        }
    }

    fun updatePost(
        postId: String,
        title: String,
        content: String,
        category: String,
        imageUrl: String?,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val req = CommunityPostUpdateRequest(
                    title = title.trim(),
                    content = content.trim(),
                    category = category,
                    imageUrl = imageUrl?.trim()?.ifEmpty { null }
                )
                val res = RetrofitClient.apiService.updateCommunityPost(postId, req)
                if (res.isSuccessful && res.body() != null) {
                    val updated = res.body()!!
                    _uiState.update { state ->
                        val updatedFeed = state.feedPosts.map { if (it.postId == postId) updated else it }
                        state.copy(
                            isSubmitting = false,
                            activePost = updated,
                            feedPosts = updatedFeed,
                            actionMessage = "Post updated successfully"
                        )
                    }
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Update failed (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error updating post"
                    )
                }
            }
        }
    }

    fun deletePost(postId: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val res = RetrofitClient.apiService.deleteCommunityPost(postId)
                if (res.isSuccessful) {
                    _uiState.update { state ->
                        state.copy(
                            isSubmitting = false,
                            activePost = null,
                            feedPosts = state.feedPosts.filter { it.postId != postId },
                            actionMessage = "Post deleted successfully"
                        )
                    }
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Failed to delete post (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error deleting post"
                    )
                }
            }
        }
    }

    fun togglePostLike(post: CommunityPost) {
        viewModelScope.launch {
            val previousLiked = post.hasLiked
            val previousCount = post.likesCount
            val optimisticLiked = !previousLiked
            val optimisticCount = if (optimisticLiked) previousCount + 1 else maxOf(0, previousCount - 1)

            // Optimistic update
            updatePostInState(post.copy(hasLiked = optimisticLiked, likesCount = optimisticCount))

            try {
                val res = RetrofitClient.apiService.toggleCommunityReaction(
                    targetType = "post",
                    targetId = post.postId,
                    request = CommunityReactionRequest("like")
                )
                if (res.isSuccessful && res.body() != null) {
                    val rx = res.body()!!
                    updatePostInState(post.copy(hasLiked = rx.hasLiked, likesCount = rx.likesCount))
                } else {
                    // Revert
                    updatePostInState(post.copy(hasLiked = previousLiked, likesCount = previousCount))
                }
            } catch (_: Exception) {
                updatePostInState(post.copy(hasLiked = previousLiked, likesCount = previousCount))
            }
        }
    }

    private fun updatePostInState(post: CommunityPost) {
        _uiState.update { state ->
            val updatedFeed = state.feedPosts.map { if (it.postId == post.postId) post else it }
            val updatedActive = if (state.activePost?.postId == post.postId) post else state.activePost
            state.copy(feedPosts = updatedFeed, activePost = updatedActive)
        }
    }

    fun toggleCommentLike(comment: CommunityComment) {
        viewModelScope.launch {
            try {
                val res = RetrofitClient.apiService.toggleCommunityReaction(
                    targetType = "comment",
                    targetId = comment.commentId,
                    request = CommunityReactionRequest("like")
                )
                if (res.isSuccessful && res.body() != null) {
                    val rx = res.body()!!
                    _uiState.update { state ->
                        state.copy(
                            comments = updateCommentReactionInList(state.comments, comment.commentId, rx.hasLiked, rx.likesCount)
                        )
                    }
                }
            } catch (_: Exception) { }
        }
    }

    private fun updateCommentReactionInList(
        list: List<CommunityComment>,
        targetId: String,
        hasLiked: Boolean,
        likesCount: Int
    ): List<CommunityComment> {
        return list.map { c ->
            if (c.commentId == targetId) {
                c.copy(hasLiked = hasLiked, likesCount = likesCount)
            } else if (c.replies.isNotEmpty()) {
                c.copy(replies = updateCommentReactionInList(c.replies, targetId, hasLiked, likesCount))
            } else {
                c
            }
        }
    }

    fun setReplyingTo(comment: CommunityComment?) {
        _uiState.update { it.copy(replyingToComment = comment) }
    }

    fun clearReplyingTo() {
        _uiState.update { it.copy(replyingToComment = null) }
    }

    fun addComment(
        postId: String,
        commentText: String,
        parentCommentId: String? = null,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val req = CommunityCommentCreateRequest(
                    commentText = commentText.trim(),
                    parentCommentId = parentCommentId
                )
                val res = RetrofitClient.apiService.addCommunityComment(postId, req)
                if (res.isSuccessful && res.body() != null) {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            replyingToComment = null,
                            actionMessage = "Reply posted"
                        )
                    }
                    loadComments(postId)
                    loadPostDetail(postId)
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Failed to post comment (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error adding comment"
                    )
                }
            }
        }
    }

    fun deleteComment(postId: String, commentId: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val res = RetrofitClient.apiService.deleteCommunityComment(commentId)
                if (res.isSuccessful) {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionMessage = "Comment deleted"
                        )
                    }
                    loadComments(postId)
                    loadPostDetail(postId)
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Failed to delete comment (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error deleting comment"
                    )
                }
            }
        }
    }

    fun markAcceptedSolution(postId: String, commentId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val res = RetrofitClient.apiService.acceptCommunityAnswer(postId, commentId)
                if (res.isSuccessful) {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionMessage = "Solution status updated"
                        )
                    }
                    loadComments(postId)
                    loadPostDetail(postId)
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Unable to mark solution (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error updating solution"
                    )
                }
            }
        }
    }

    fun reportContent(
        targetType: String,
        targetId: String,
        reason: String,
        details: String?,
        onSuccess: () -> Unit
    ) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSubmitting = true, actionError = null) }
            try {
                val req = CommunityReportRequest(
                    targetType = targetType,
                    targetId = targetId,
                    reason = reason,
                    details = details?.trim()?.ifEmpty { null }
                )
                val res = RetrofitClient.apiService.reportCommunityContent(req)
                if (res.isSuccessful) {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionMessage = "Report submitted to moderators. Thank you for keeping the community safe."
                        )
                    }
                    onSuccess()
                } else {
                    _uiState.update {
                        it.copy(
                            isSubmitting = false,
                            actionError = "Failed to submit report (HTTP ${res.code()})"
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isSubmitting = false,
                        actionError = e.localizedMessage ?: "Network error submitting report"
                    )
                }
            }
        }
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null, actionError = null) }
    }
}

