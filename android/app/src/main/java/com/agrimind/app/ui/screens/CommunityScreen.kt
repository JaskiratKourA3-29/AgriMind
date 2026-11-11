package com.agrimind.app.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrimind.app.data.local.UserSessionManager
import com.agrimind.app.data.model.*
import com.agrimind.app.ui.theme.*
import com.agrimind.app.ui.viewmodel.CommunityViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CommunityScreen(
    viewModel: CommunityViewModel,
    sessionManager: UserSessionManager,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val currentUserId = sessionManager.getUserId()
    val canModerate = sessionManager.isOwner() || sessionManager.hasPermission("can_moderate_cases")

    var showCreateDialog by remember { mutableStateOf(false) }
    var postToEdit by remember { mutableStateOf<CommunityPost?>(null) }
    var reportTarget by remember { mutableStateOf<Pair<String, String>?>(null) } // Pair(targetType, targetId)
    var postToDelete by remember { mutableStateOf<CommunityPost?>(null) }
    var commentToDelete by remember { mutableStateOf<Pair<String, String>?>(null) } // Pair(postId, commentId)

    // SnackBar / Action Message handling
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }
    LaunchedEffect(uiState.actionError) {
        uiState.actionError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            if (uiState.activePost == null) {
                FloatingActionButton(
                    onClick = { showCreateDialog = true },
                    containerColor = ForestGreenPrimary,
                    contentColor = Color.White
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "New Discussion")
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("New Post", fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        },
        containerColor = LightGreenBackground
    ) { innerPadding ->
        Box(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Main content: either Post Detail or Feed
            if (uiState.activePost != null) {
                BackHandler {
                    viewModel.closePostDetail()
                }
                CommunityPostDetailView(
                    post = uiState.activePost!!,
                    comments = uiState.comments,
                    isLoadingComments = uiState.isLoadingComments,
                    commentError = uiState.commentError,
                    replyingToComment = uiState.replyingToComment,
                    currentUserId = currentUserId,
                    canModerate = canModerate,
                    onBack = { viewModel.closePostDetail() },
                    onToggleLikePost = { viewModel.togglePostLike(it) },
                    onToggleLikeComment = { viewModel.toggleCommentLike(it) },
                    onReplyToComment = { viewModel.setReplyingTo(it) },
                    onClearReply = { viewModel.clearReplyingTo() },
                    onSendComment = { text, parentId ->
                        viewModel.addComment(
                            postId = uiState.activePost!!.postId,
                            commentText = text,
                            parentCommentId = parentId,
                            onSuccess = {}
                        )
                    },
                    onMarkAccepted = { cId ->
                        viewModel.markAcceptedSolution(uiState.activePost!!.postId, cId)
                    },
                    onEditPost = { postToEdit = it },
                    onDeletePost = { postToDelete = it },
                    onDeleteComment = { pId, cId -> commentToDelete = Pair(pId, cId) },
                    onReport = { tType, tId -> reportTarget = Pair(tType, tId) }
                )
            } else {
                CommunityFeedView(
                    posts = uiState.feedPosts,
                    isLoading = uiState.isLoadingFeed,
                    feedError = uiState.feedError,
                    searchQuery = uiState.searchQuery,
                    selectedCategory = uiState.selectedCategory,
                    onSearchQueryChange = { viewModel.onSearchQueryChange(it) },
                    onCategoryChange = { viewModel.onCategoryChange(it) },
                    onRefresh = { viewModel.loadFeed(reset = true) },
                    onPostClick = { viewModel.openPostDetail(it) },
                    onToggleLike = { viewModel.togglePostLike(it) }
                )
            }

            // Dialogs
            if (showCreateDialog) {
                CreateCommunityPostDialog(
                    onDismiss = { showCreateDialog = false },
                    onSubmit = { title, content, category, imageUrl ->
                        viewModel.createPost(title, content, category, imageUrl) {
                            showCreateDialog = false
                        }
                    }
                )
            }

            postToEdit?.let { post ->
                EditCommunityPostDialog(
                    post = post,
                    onDismiss = { postToEdit = null },
                    onSubmit = { title, content, category, imageUrl ->
                        viewModel.updatePost(post.postId, title, content, category, imageUrl) {
                            postToEdit = null
                        }
                    }
                )
            }

            reportTarget?.let { (tType, tId) ->
                ReportCommunityContentDialog(
                    targetType = tType,
                    targetId = tId,
                    onDismiss = { reportTarget = null },
                    onSubmit = { reason, details ->
                        viewModel.reportContent(tType, tId, reason, details) {
                            reportTarget = null
                        }
                    }
                )
            }

            postToDelete?.let { post ->
                AlertDialog(
                    onDismissRequest = { postToDelete = null },
                    icon = { Icon(Icons.Default.DeleteOutline, contentDescription = null, tint = ErrorRed) },
                    title = { Text("Delete Discussion?") },
                    text = { Text("Are you sure you want to delete '${post.title}'? This action cannot be undone.") },
                    confirmButton = {
                        Button(
                            onClick = {
                                viewModel.deletePost(post.postId) {
                                    postToDelete = null
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = ErrorRed)
                        ) {
                            Text("Delete", color = Color.White)
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { postToDelete = null }) {
                            Text("Cancel")
                        }
                    }
                )
            }

            commentToDelete?.let { (pId, cId) ->
                AlertDialog(
                    onDismissRequest = { commentToDelete = null },
                    icon = { Icon(Icons.Default.DeleteOutline, contentDescription = null, tint = ErrorRed) },
                    title = { Text("Delete Comment?") },
                    text = { Text("Are you sure you want to remove this comment?") },
                    confirmButton = {
                        Button(
                            onClick = {
                                viewModel.deleteComment(pId, cId) {
                                    commentToDelete = null
                                }
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = ErrorRed)
                        ) {
                            Text("Delete", color = Color.White)
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { commentToDelete = null }) {
                            Text("Cancel")
                        }
                    }
                )
            }
        }
    }
}

// =========================================================================
// Feed View Components
// =========================================================================

@Composable
fun CommunityFeedView(
    posts: List<CommunityPost>,
    isLoading: Boolean,
    feedError: String?,
    searchQuery: String,
    selectedCategory: String,
    onSearchQueryChange: (String) -> Unit,
    onCategoryChange: (String) -> Unit,
    onRefresh: () -> Unit,
    onPostClick: (CommunityPost) -> Unit,
    onToggleLike: (CommunityPost) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        // 1. Search Bar
        Surface(
            color = Color.White,
            shadowElevation = 2.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = onSearchQueryChange,
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("Search farmer questions, symptoms, crops...", fontSize = 13.sp) },
                    leadingIcon = {
                        Icon(Icons.Default.Search, contentDescription = "Search", tint = ForestGreenPrimary)
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { onSearchQueryChange("") }) {
                                Icon(Icons.Default.Close, contentDescription = "Clear", tint = Color.Gray)
                            }
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(24.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = ForestGreenPrimary,
                        unfocusedBorderColor = Color(0xFFE0E0E0),
                        focusedContainerColor = Color(0xFFF9FBF9),
                        unfocusedContainerColor = Color(0xFFF9FBF9)
                    )
                )

                Spacer(modifier = Modifier.height(10.dp))

                // 2. Categories Horizontal Scroll Chips
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    CommunityCategories.ALL.forEach { (catKey, catLabel) ->
                        val isSelected = selectedCategory == catKey
                        FilterChip(
                            selected = isSelected,
                            onClick = { onCategoryChange(catKey) },
                            label = {
                                Text(
                                    text = catLabel,
                                    fontSize = 12.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                                )
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ForestGreenPrimary,
                                selectedLabelColor = Color.White,
                                containerColor = Color(0xFFEFEFEF),
                                labelColor = Color.DarkGray
                            ),
                            border = FilterChipDefaults.filterChipBorder(
                                enabled = true,
                                selected = isSelected,
                                selectedBorderColor = ForestGreenPrimary,
                                borderColor = Color.Transparent
                            ),
                            shape = RoundedCornerShape(16.dp)
                        )
                    }
                }
            }
        }

        // 3. Peer Discussion Safety Disclaimer Banner
        CommunityPeerDisclaimerBanner()

        // 4. Feed Content List / States
        Box(modifier = Modifier.weight(1f)) {
            if (isLoading && posts.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = ForestGreenPrimary)
                }
            } else if (feedError != null && posts.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Default.CloudOff, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(54.dp))
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(text = feedError, color = Color.Gray, style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = onRefresh,
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                    ) {
                        Text("Retry")
                    }
                }
            } else if (posts.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Outlined.Forum, contentDescription = null, tint = ForestGreenLight, modifier = Modifier.size(64.dp))
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "No farmer discussions found",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Be the first farmer to ask a question or share field observations!",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.Gray
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(posts, key = { it.postId }) { post ->
                        CommunityPostCard(
                            post = post,
                            onClick = { onPostClick(post) },
                            onToggleLike = { onToggleLike(post) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CommunityPeerDisclaimerBanner() {
    Surface(
        color = Color(0xFFFFF8E1),
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFFE082)),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        Row(
            modifier = Modifier.padding(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Default.Info,
                contentDescription = null,
                tint = Color(0xFFF57F17),
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Community Advice Notice: Discussions represent grower peer experiences. Always verify chemical treatments against official ICAR/SAU recommendations.",
                fontSize = 11.sp,
                color = Color(0xFF5D4037),
                lineHeight = 15.sp
            )
        }
    }
}

@Composable
fun CommunityPostCard(
    post: CommunityPost,
    onClick: () -> Unit,
    onToggleLike: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header Row: Category Badge, Solved Badge, Timestamp
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Category Chip
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = getCategoryBadgeBg(post.category),
                    modifier = Modifier.padding(end = 8.dp)
                ) {
                    Text(
                        text = post.displayCategory,
                        color = getCategoryBadgeFg(post.category),
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }

                // Solved Badge
                if (post.isResolved) {
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = Color(0xFFE8F5E9),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF4CAF50)),
                        modifier = Modifier.padding(end = 8.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenPrimary, modifier = Modifier.size(11.dp))
                            Spacer(modifier = Modifier.width(3.dp))
                            Text("SOLVED", color = ForestGreenPrimary, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }

                Spacer(modifier = Modifier.weight(1f))

                // Relative Timestamp
                Text(
                    text = post.createdAt.take(10),
                    fontSize = 11.sp,
                    color = Color.Gray
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Post Title
            Text(
                text = post.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(6.dp))

            // Content Snippet
            Text(
                text = post.content,
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF37474F),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Footer Row: Author Info and Interactions
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                // Author Avatar Circle
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(CircleShape)
                        .background(getRoleColor(post.authorRole).copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = if (post.isAuthorOfficerOrOwner) Icons.Default.VerifiedUser else Icons.Default.Person,
                        contentDescription = null,
                        tint = getRoleColor(post.authorRole),
                        modifier = Modifier.size(14.dp)
                    )
                }

                Spacer(modifier = Modifier.width(6.dp))

                // Author Name & Badge
                Text(
                    text = post.authorName,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.DarkGray
                )

                Spacer(modifier = Modifier.width(4.dp))

                Surface(
                    shape = RoundedCornerShape(4.dp),
                    color = getRoleColor(post.authorRole).copy(alpha = 0.15f)
                ) {
                    Text(
                        text = post.displayAuthorBadge,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold,
                        color = getRoleColor(post.authorRole),
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                    )
                }

                Spacer(modifier = Modifier.weight(1f))

                // Likes count & button
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .clickable { onToggleLike() }
                        .padding(horizontal = 6.dp, vertical = 4.dp)
                ) {
                    Icon(
                        imageVector = if (post.hasLiked) Icons.Default.ThumbUp else Icons.Outlined.ThumbUp,
                        contentDescription = "Helpful",
                        tint = if (post.hasLiked) ForestGreenPrimary else Color.Gray,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "${post.likesCount}",
                        fontSize = 12.sp,
                        fontWeight = if (post.hasLiked) FontWeight.Bold else FontWeight.Normal,
                        color = if (post.hasLiked) ForestGreenPrimary else Color.DarkGray
                    )
                }

                Spacer(modifier = Modifier.width(12.dp))

                // Comments count
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp)
                ) {
                    Icon(
                        Icons.Outlined.ChatBubbleOutline,
                        contentDescription = "Discussions",
                        tint = Color.Gray,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "${post.commentsCount}",
                        fontSize = 12.sp,
                        color = Color.DarkGray
                    )
                }
            }
        }
    }
}

// =========================================================================
// Post Detail View Components
// =========================================================================

@Composable
fun CommunityPostDetailView(
    post: CommunityPost,
    comments: List<CommunityComment>,
    isLoadingComments: Boolean,
    commentError: String?,
    replyingToComment: CommunityComment?,
    currentUserId: String?,
    canModerate: Boolean,
    onBack: () -> Unit,
    onToggleLikePost: (CommunityPost) -> Unit,
    onToggleLikeComment: (CommunityComment) -> Unit,
    onReplyToComment: (CommunityComment) -> Unit,
    onClearReply: () -> Unit,
    onSendComment: (text: String, parentId: String?) -> Unit,
    onMarkAccepted: (commentId: String) -> Unit,
    onEditPost: (CommunityPost) -> Unit,
    onDeletePost: (CommunityPost) -> Unit,
    onDeleteComment: (postId: String, commentId: String) -> Unit,
    onReport: (targetType: String, targetId: String) -> Unit
) {
    val isPostAuthor = currentUserId != null && currentUserId == post.authorId
    var newCommentText by remember { mutableStateOf("") }

    Column(modifier = Modifier.fillMaxSize()) {
        // Detail Top Bar
        Surface(
            color = Color.White,
            shadowElevation = 2.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = ForestGreenDark)
                }

                Text(
                    text = "Discussion",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenDark
                )

                Spacer(modifier = Modifier.weight(1f))

                // Post Actions Menu: Author Edit/Delete, Moderator Delete, Report
                if (isPostAuthor) {
                    IconButton(onClick = { onEditPost(post) }) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit Post", tint = ForestGreenPrimary)
                    }
                    IconButton(onClick = { onDeletePost(post) }) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete Post", tint = ErrorRed)
                    }
                } else if (canModerate) {
                    IconButton(onClick = { onDeletePost(post) }) {
                        Icon(Icons.Default.DeleteSweep, contentDescription = "Moderate Post", tint = ErrorRed)
                    }
                }

                IconButton(onClick = { onReport("post", post.postId) }) {
                    Icon(Icons.Outlined.Flag, contentDescription = "Report Post", tint = Color.Gray)
                }
            }
        }

        // Scrollable Body: Post Details + Comments Tree
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // 1. Post Header Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        // Badges Row
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Surface(
                                shape = RoundedCornerShape(6.dp),
                                color = getCategoryBadgeBg(post.category),
                                modifier = Modifier.padding(end = 8.dp)
                            ) {
                                Text(
                                    text = post.displayCategory,
                                    color = getCategoryBadgeFg(post.category),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                )
                            }

                            if (post.isResolved) {
                                Surface(
                                    shape = RoundedCornerShape(6.dp),
                                    color = Color(0xFFE8F5E9),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF4CAF50))
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                    ) {
                                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenPrimary, modifier = Modifier.size(13.dp))
                                        Spacer(modifier = Modifier.width(4.dp))
                                        Text("ACCEPTED SOLUTION MARKED", color = ForestGreenPrimary, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        // Title
                        Text(
                            text = post.title,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = ForestGreenDark
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        // Author Profile Bar
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .clip(CircleShape)
                                    .background(getRoleColor(post.authorRole).copy(alpha = 0.2f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = if (post.isAuthorOfficerOrOwner) Icons.Default.VerifiedUser else Icons.Default.Person,
                                    contentDescription = null,
                                    tint = getRoleColor(post.authorRole),
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = post.authorName,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 13.sp,
                                        color = Color.DarkGray
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Surface(
                                        shape = RoundedCornerShape(4.dp),
                                        color = getRoleColor(post.authorRole).copy(alpha = 0.15f)
                                    ) {
                                        Text(
                                            text = post.displayAuthorBadge,
                                            fontSize = 9.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = getRoleColor(post.authorRole),
                                            modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp)
                                        )
                                    }
                                }
                                Text(
                                    text = "Posted on ${post.createdAt.take(16).replace("T", " ")}",
                                    fontSize = 10.sp,
                                    color = Color.Gray
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(14.dp))
                        Divider(color = Color(0xFFEEEEEE))
                        Spacer(modifier = Modifier.height(14.dp))

                        // Post Full Content
                        Text(
                            text = post.content,
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color(0xFF263238),
                            lineHeight = 22.sp
                        )

                        // Post Optional Image Banner
                        post.imageUrl?.let { url ->
                            Spacer(modifier = Modifier.height(14.dp))
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = Color(0xFFF1F8E9),
                                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFDCEDC8)),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(Icons.Default.Image, contentDescription = null, tint = ForestGreenPrimary)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Crop Visual Attachment: $url", fontSize = 11.sp, color = ForestGreenDark)
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        // Like Post Row
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Button(
                                onClick = { onToggleLikePost(post) },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (post.hasLiked) ForestGreenPrimary else Color(0xFFEEEEEE),
                                    contentColor = if (post.hasLiked) Color.White else Color.DarkGray
                                ),
                                shape = RoundedCornerShape(20.dp),
                                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
                            ) {
                                Icon(
                                    imageVector = if (post.hasLiked) Icons.Default.ThumbUp else Icons.Outlined.ThumbUp,
                                    contentDescription = null,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = if (post.hasLiked) "Helpful (${post.likesCount})" else "Mark Helpful (${post.likesCount})",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }
            }

            // 2. Comments Section Header
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Icon(Icons.Default.QuestionAnswer, contentDescription = null, tint = ForestGreenDark, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Farmer Suggestions & Advice (${comments.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                }
            }

            // 3. Comments Items
            if (isLoadingComments && comments.isEmpty()) {
                item {
                    Box(modifier = Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = ForestGreenPrimary, modifier = Modifier.size(32.dp))
                    }
                }
            } else if (comments.isEmpty()) {
                item {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color.White,
                        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(Icons.Outlined.Comment, contentDescription = null, tint = Color.LightGray, modifier = Modifier.size(42.dp))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = "No suggestions posted yet.",
                                fontSize = 13.sp,
                                color = Color.Gray
                            )
                            Text(
                                text = "Share your agricultural experience below!",
                                fontSize = 12.sp,
                                color = Color.Gray
                            )
                        }
                    }
                }
            } else {
                items(comments, key = { it.commentId }) { comment ->
                    CommunityCommentItem(
                        comment = comment,
                        isPostAuthor = isPostAuthor,
                        currentUserId = currentUserId,
                        canModerate = canModerate,
                        postId = post.postId,
                        onToggleLike = { onToggleLikeComment(comment) },
                        onReply = { onReplyToComment(comment) },
                        onMarkAccepted = { onMarkAccepted(comment.commentId) },
                        onDelete = { onPostId, onCommentId -> onDeleteComment(onPostId, onCommentId) },
                        onReport = { onReport("comment", comment.commentId) },
                        level = 0
                    )
                }
            }
        }

        // Bottom Bar: Reply banner + Input Field
        Surface(
            color = Color.White,
            shadowElevation = 8.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
                // If replying to a specific comment
                if (replyingToComment != null) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFFE8F5E9), shape = RoundedCornerShape(6.dp))
                            .padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Reply, contentDescription = null, tint = ForestGreenDark, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Replying to ${replyingToComment.authorName}: \"${replyingToComment.commentText.take(30)}...\"",
                            fontSize = 11.sp,
                            color = ForestGreenDark,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        IconButton(onClick = onClearReply, modifier = Modifier.size(20.dp)) {
                            Icon(Icons.Default.Close, contentDescription = "Cancel reply", tint = Color.Gray, modifier = Modifier.size(14.dp))
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                }

                // Comment Text Field & Send Button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = newCommentText,
                        onValueChange = { newCommentText = it },
                        modifier = Modifier.weight(1f),
                        placeholder = {
                            Text(
                                if (replyingToComment != null) "Write your reply..." else "Suggest advice or ask a follow-up...",
                                fontSize = 13.sp
                            )
                        },
                        shape = RoundedCornerShape(20.dp),
                        maxLines = 4,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ForestGreenPrimary,
                            unfocusedBorderColor = Color(0xFFDDDDDD),
                            focusedContainerColor = Color(0xFFF9FBF9),
                            unfocusedContainerColor = Color(0xFFF9FBF9)
                        )
                    )

                    Spacer(modifier = Modifier.width(8.dp))

                    IconButton(
                        onClick = {
                            if (newCommentText.isNotBlank()) {
                                onSendComment(newCommentText.trim(), replyingToComment?.commentId)
                                newCommentText = ""
                            }
                        },
                        enabled = newCommentText.isNotBlank(),
                        colors = IconButtonDefaults.iconButtonColors(
                            containerColor = ForestGreenPrimary,
                            contentColor = Color.White,
                            disabledContainerColor = Color(0xFFE0E0E0),
                            disabledContentColor = Color.White
                        )
                    ) {
                        Icon(Icons.Default.Send, contentDescription = "Send")
                    }
                }
            }
        }
    }
}

@Composable
fun CommunityCommentItem(
    comment: CommunityComment,
    isPostAuthor: Boolean,
    currentUserId: String?,
    canModerate: Boolean,
    postId: String,
    onToggleLike: () -> Unit,
    onReply: () -> Unit,
    onMarkAccepted: () -> Unit,
    onDelete: (postId: String, commentId: String) -> Unit,
    onReport: () -> Unit,
    level: Int = 0
) {
    val isCommentAuthor = currentUserId != null && currentUserId == comment.authorId

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = (level * 16).dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (comment.isAccepted) Color(0xFFF1F8E9) else Color.White
            ),
            border = if (comment.isAccepted) androidx.compose.foundation.BorderStroke(1.5.dp, Color(0xFF4CAF50)) else null,
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                // Accepted Solution Banner
                if (comment.isAccepted) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color(0xFFE8F5E9), shape = RoundedCornerShape(4.dp))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenPrimary, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "ACCEPTED SOLUTION (VERIFIED BY QUESTION AUTHOR)",
                            color = ForestGreenPrimary,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }

                // Author Header Row
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(24.dp)
                            .clip(CircleShape)
                            .background(getRoleColor(comment.authorRole).copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (comment.authorRole in listOf("owner", "sub_owner", "admin")) Icons.Default.VerifiedUser else Icons.Default.Person,
                            contentDescription = null,
                            tint = getRoleColor(comment.authorRole),
                            modifier = Modifier.size(14.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = comment.authorName,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 12.sp,
                        color = Color.DarkGray
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Surface(
                        shape = RoundedCornerShape(4.dp),
                        color = getRoleColor(comment.authorRole).copy(alpha = 0.15f)
                    ) {
                        Text(
                            text = comment.displayAuthorBadge,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Bold,
                            color = getRoleColor(comment.authorRole),
                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                        )
                    }

                    Spacer(modifier = Modifier.weight(1f))

                    Text(
                        text = comment.createdAt.take(10),
                        fontSize = 10.sp,
                        color = Color.Gray
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Comment Content
                Text(
                    text = comment.commentText,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color(0xFF263238),
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Actions Row: Helpful Vote, Reply, Mark Accepted, Report, Delete
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    // Like / Helpful button
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .clip(RoundedCornerShape(6.dp))
                            .clickable { onToggleLike() }
                            .padding(horizontal = 6.dp, vertical = 3.dp)
                    ) {
                        Icon(
                            imageVector = if (comment.hasLiked) Icons.Default.ThumbUp else Icons.Outlined.ThumbUp,
                            contentDescription = "Helpful",
                            tint = if (comment.hasLiked) ForestGreenPrimary else Color.Gray,
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "${comment.likesCount}",
                            fontSize = 11.sp,
                            color = if (comment.hasLiked) ForestGreenPrimary else Color.DarkGray,
                            fontWeight = if (comment.hasLiked) FontWeight.Bold else FontWeight.Normal
                        )
                    }

                    Spacer(modifier = Modifier.width(8.dp))

                    // Reply button
                    TextButton(
                        onClick = onReply,
                        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Icon(Icons.Default.Reply, contentDescription = null, modifier = Modifier.size(13.dp), tint = ForestGreenDark)
                        Spacer(modifier = Modifier.width(3.dp))
                        Text("Reply", fontSize = 11.sp, color = ForestGreenDark)
                    }

                    Spacer(modifier = Modifier.weight(1f))

                    // Post Author Solution Acceptance Toggle Button
                    if (isPostAuthor) {
                        TextButton(
                            onClick = onMarkAccepted,
                            contentPadding = PaddingValues(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Icon(
                                imageVector = if (comment.isAccepted) Icons.Default.CheckCircle else Icons.Outlined.CheckCircle,
                                contentDescription = null,
                                tint = if (comment.isAccepted) ForestGreenPrimary else Color.Gray,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(3.dp))
                            Text(
                                text = if (comment.isAccepted) "Accepted" else "Accept Answer",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (comment.isAccepted) ForestGreenPrimary else Color.DarkGray
                            )
                        }
                    }

                    // Delete comment button
                    if (isCommentAuthor || canModerate) {
                        IconButton(
                            onClick = { onDelete(postId, comment.commentId) },
                            modifier = Modifier.size(24.dp)
                        ) {
                            Icon(Icons.Outlined.Delete, contentDescription = "Delete", tint = Color.Gray, modifier = Modifier.size(14.dp))
                        }
                    }

                    // Report comment button
                    IconButton(
                        onClick = onReport,
                        modifier = Modifier.size(24.dp)
                    ) {
                        Icon(Icons.Outlined.Flag, contentDescription = "Report", tint = Color.Gray, modifier = Modifier.size(14.dp))
                    }
                }
            }
        }

        // Render child replies recursively
        if (comment.replies.isNotEmpty()) {
            Spacer(modifier = Modifier.height(6.dp))
            comment.replies.forEach { child ->
                CommunityCommentItem(
                    comment = child,
                    isPostAuthor = isPostAuthor,
                    currentUserId = currentUserId,
                    canModerate = canModerate,
                    postId = postId,
                    onToggleLike = onToggleLike,
                    onReply = onReply,
                    onMarkAccepted = onMarkAccepted,
                    onDelete = onDelete,
                    onReport = onReport,
                    level = level + 1
                )
                Spacer(modifier = Modifier.height(6.dp))
            }
        }
    }
}

// =========================================================================
// Dialogs: Create Post, Edit Post, Report Content
// =========================================================================

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateCommunityPostDialog(
    onDismiss: () -> Unit,
    onSubmit: (title: String, content: String, category: String, imageUrl: String?) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var content by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("general_farming") }
    var imageUrl by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.PostAdd, contentDescription = null, tint = ForestGreenPrimary)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Ask Farmer Community", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                validationError?.let {
                    Text(text = it, color = ErrorRed, fontSize = 12.sp)
                }

                // Title
                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it; validationError = null },
                    label = { Text("Discussion Title / Question") },
                    placeholder = { Text("e.g. Yellow spots on lower tomato leaves") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                // Category Selector
                Text("Category:", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = ForestGreenDark)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    CommunityCategories.CREATION_LIST.forEach { (catKey, catLabel) ->
                        val isSelected = category == catKey
                        FilterChip(
                            selected = isSelected,
                            onClick = { category = catKey },
                            label = { Text(catLabel, fontSize = 11.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ForestGreenPrimary,
                                selectedLabelColor = Color.White
                            )
                        )
                    }
                }

                // Content
                OutlinedTextField(
                    value = content,
                    onValueChange = { content = it; validationError = null },
                    label = { Text("Details / Symptoms / Field Notes") },
                    placeholder = { Text("Describe crop variety, soil conditions, symptoms observed, recent sprays...") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 4,
                    maxLines = 8
                )

                // Optional Image URL
                OutlinedTextField(
                    value = imageUrl,
                    onValueChange = { imageUrl = it },
                    label = { Text("Image URL / Attachment (Optional)") },
                    placeholder = { Text("e.g. /community/images/leaf.jpg") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (title.trim().length < 3) {
                        validationError = "Title must be at least 3 characters."
                    } else if (content.trim().length < 5) {
                        validationError = "Content must be at least 5 characters."
                    } else {
                        onSubmit(title.trim(), content.trim(), category, imageUrl.trim().ifEmpty { null })
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
            ) {
                Text("Publish Post")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditCommunityPostDialog(
    post: CommunityPost,
    onDismiss: () -> Unit,
    onSubmit: (title: String, content: String, category: String, imageUrl: String?) -> Unit
) {
    var title by remember { mutableStateOf(post.title) }
    var content by remember { mutableStateOf(post.content) }
    var category by remember { mutableStateOf(post.category) }
    var imageUrl by remember { mutableStateOf(post.imageUrl ?: "") }
    var validationError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.Edit, contentDescription = null, tint = ForestGreenPrimary)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Edit Discussion", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                validationError?.let {
                    Text(text = it, color = ErrorRed, fontSize = 12.sp)
                }

                OutlinedTextField(
                    value = title,
                    onValueChange = { title = it; validationError = null },
                    label = { Text("Discussion Title") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Text("Category:", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = ForestGreenDark)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    CommunityCategories.CREATION_LIST.forEach { (catKey, catLabel) ->
                        val isSelected = category == catKey
                        FilterChip(
                            selected = isSelected,
                            onClick = { category = catKey },
                            label = { Text(catLabel, fontSize = 11.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ForestGreenPrimary,
                                selectedLabelColor = Color.White
                            )
                        )
                    }
                }

                OutlinedTextField(
                    value = content,
                    onValueChange = { content = it; validationError = null },
                    label = { Text("Details & Description") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 4,
                    maxLines = 8
                )

                OutlinedTextField(
                    value = imageUrl,
                    onValueChange = { imageUrl = it },
                    label = { Text("Image URL (Optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (title.trim().length < 3) {
                        validationError = "Title must be at least 3 characters."
                    } else if (content.trim().length < 5) {
                        validationError = "Content must be at least 5 characters."
                    } else {
                        onSubmit(title.trim(), content.trim(), category, imageUrl.trim().ifEmpty { null })
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
            ) {
                Text("Save Changes")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
fun ReportCommunityContentDialog(
    targetType: String,
    targetId: String,
    onDismiss: () -> Unit,
    onSubmit: (reason: String, details: String?) -> Unit
) {
    var selectedReason by remember { mutableStateOf("misleading") }
    var details by remember { mutableStateOf("") }

    val reasons = listOf(
        "misleading" to "Misleading Agricultural / Chemical Advice",
        "spam" to "Spam, Promotion or Irrelevant Advertising",
        "harassment" to "Harassment, Offensive or Abusive Language",
        "inappropriate" to "Inappropriate or False Content",
        "other" to "Other Concern"
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        icon = { Icon(Icons.Default.ReportProblem, contentDescription = null, tint = WarningOrange) },
        title = { Text("Report Community $targetType") },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "Help maintain verified and safe agricultural communication for all growers.",
                    fontSize = 12.sp,
                    color = Color.DarkGray
                )

                Text("Select Reason:", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = ForestGreenDark)

                reasons.forEach { (key, label) ->
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { selectedReason = key }
                            .padding(vertical = 4.dp)
                    ) {
                        RadioButton(
                            selected = selectedReason == key,
                            onClick = { selectedReason = key },
                            colors = RadioButtonDefaults.colors(selectedColor = ForestGreenPrimary)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(label, fontSize = 12.sp, color = Color.DarkGray)
                    }
                }

                OutlinedTextField(
                    value = details,
                    onValueChange = { details = it },
                    label = { Text("Additional Details (Optional)") },
                    placeholder = { Text("Provide context for project administrators...") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 2,
                    maxLines = 4
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onSubmit(selectedReason, details.trim().ifEmpty { null }) },
                colors = ButtonDefaults.buttonColors(containerColor = WarningOrange)
            ) {
                Text("Submit Report", color = Color.White)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

// Helpers for badges & roles
fun getCategoryBadgeBg(category: String): Color {
    return when (category.lowercase()) {
        "crop_disease" -> Color(0xFFFFEBEE)
        "pest_management" -> Color(0xFFFFF3E0)
        "irrigation" -> Color(0xFFE1F5FE)
        "soil_health" -> Color(0xFFEFEBE9)
        "fertilizers" -> Color(0xFFF3E5F5)
        "weather_impacts" -> Color(0xFFEDE7F6)
        else -> Color(0xFFE8F5E9)
    }
}

fun getCategoryBadgeFg(category: String): Color {
    return when (category.lowercase()) {
        "crop_disease" -> Color(0xFFC62828)
        "pest_management" -> Color(0xFFE65100)
        "irrigation" -> Color(0xFF0277BD)
        "soil_health" -> Color(0xFF4E342E)
        "fertilizers" -> Color(0xFF6A1B9A)
        "weather_impacts" -> Color(0xFF4527A0)
        else -> ForestGreenPrimary
    }
}

fun getRoleColor(role: String): Color {
    return when (role.lowercase()) {
        "owner" -> Color(0xFFE65100) // Gold / Deep Orange
        "sub_owner" -> Color(0xFF1565C0) // Rich Blue
        "admin" -> Color(0xFF2E7D32) // Emerald Green
        else -> Color(0xFF455A64) // Slate / Farmer Gray
    }
}
