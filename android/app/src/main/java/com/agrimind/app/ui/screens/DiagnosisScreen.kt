package com.agrimind.app.ui.screens

import android.graphics.Bitmap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrimind.app.data.model.DiagnosisResponse
import com.agrimind.app.data.model.ManagementActionResponse
import com.agrimind.app.ui.theme.*
import com.agrimind.app.ui.viewmodel.DiagnosisUiState
import com.agrimind.app.ui.viewmodel.DiagnosisViewModel

@Composable
fun DiagnosisScreen(
    viewModel: DiagnosisViewModel,
    onViewCaseDetails: ((String) -> Unit)? = null,
    onAskAssistant: ((String, String?) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val liveWeather by viewModel.liveWeather.collectAsState()
    val isLoadingWeather by viewModel.isLoadingWeather.collectAsState()
    val pendingOfflineCount by viewModel.offlinePendingCount.collectAsState()
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    // Android System Photo Picker (Zero runtime storage permissions required)
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri ->
        if (uri != null) {
            viewModel.onImageSelected(uri, context.contentResolver)
        }
    }

    // Direct Camera Photo Capture Launcher
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicturePreview()
    ) { bitmap ->
        if (bitmap != null) {
            viewModel.onBitmapCaptured(bitmap)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(scrollState),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // 1. Regulatory & Academic AI Disclaimer Banner
        DisclaimerBanner()

        // 2. Real-time Microclimate Weather Bar
        LiveWeatherCard(
            weather = liveWeather,
            isLoading = isLoadingWeather,
            onRefresh = { viewModel.fetchLiveWeather() }
        )

        // 3. Offline Pending Synchronization Bar (if any queued requests)
        if (pendingOfflineCount > 0) {
            OfflinePendingSyncCard(
                pendingCount = pendingOfflineCount,
                onSyncClicked = { viewModel.syncOfflineQueue() }
            )
        }

        // 4. Image Selection & Preview Card
        when (val state = uiState) {
            is DiagnosisUiState.Idle -> {
                ImagePickerPlaceholder(
                    onTakePhotoClicked = { cameraLauncher.launch(null) },
                    onChooseImageClicked = {
                        photoPickerLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    }
                )
            }
            is DiagnosisUiState.ImageSelected -> {
                ImagePreviewCard(
                    bitmap = state.bitmap,
                    fileName = state.fileName,
                    fileSize = state.fileSizeBytes,
                    onChangeImageClicked = {
                        photoPickerLauncher.launch(
                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                        )
                    },
                    onRemoveImageClicked = { viewModel.onRemoveImage() }
                )
            }
            is DiagnosisUiState.Diagnosing -> {
                ImagePreviewCard(
                    bitmap = state.bitmap,
                    fileName = "Submitting for diagnosis...",
                    fileSize = 0L,
                    onChangeImageClicked = {},
                    onRemoveImageClicked = {},
                    isActionsEnabled = false
                )
            }
            is DiagnosisUiState.Success -> {
                if (state.bitmap != null) {
                    SmallImageThumbnail(bitmap = state.bitmap)
                }
            }
            is DiagnosisUiState.QueuedOffline -> {
                SmallImageThumbnail(bitmap = state.bitmap)
            }
            is DiagnosisUiState.Error -> {
                if (state.bitmap != null) {
                    ImagePreviewCard(
                        bitmap = state.bitmap,
                        fileName = "Diagnosis failed",
                        fileSize = 0L,
                        onChangeImageClicked = {
                            photoPickerLauncher.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            )
                        },
                        onRemoveImageClicked = { viewModel.onRemoveImage() }
                    )
                } else {
                    ImagePickerPlaceholder(
                        onTakePhotoClicked = { cameraLauncher.launch(null) },
                        onChooseImageClicked = {
                            photoPickerLauncher.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            )
                        }
                    )
                }
            }
        }

        // 5. Action Buttons & Interactive State Containers
        when (val state = uiState) {
            is DiagnosisUiState.Idle -> {
                // Submit disabled in idle
                Button(
                    onClick = {},
                    enabled = false,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text("Select an Image to Diagnose", fontSize = 16.sp)
                }
            }

            is DiagnosisUiState.ImageSelected -> {
                Button(
                    onClick = { viewModel.runDiagnosis() },
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                ) {
                    Icon(imageVector = Icons.Default.Search, contentDescription = "Run Diagnosis")
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Run AI Diagnosis", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }

            is DiagnosisUiState.Diagnosing -> {
                DiagnosingLoadingCard()
            }

            is DiagnosisUiState.Success -> {
                DiagnosisResultCard(
                    response = state.response,
                    onNewDiagnosisClicked = { viewModel.onRemoveImage() },
                    onViewDetailsClicked = onViewCaseDetails?.let { callback -> { callback(state.response.caseId) } },
                    onAskAssistantClicked = onAskAssistant?.let { callback -> { callback(state.response.caseId, state.response.primaryDiagnosis) } }
                )
            }

            is DiagnosisUiState.QueuedOffline -> {
                QueuedOfflineResultCard(
                    message = state.message,
                    onNewDiagnosisClicked = { viewModel.onRemoveImage() },
                    onRetrySync = { viewModel.syncOfflineQueue() }
                )
            }

            is DiagnosisUiState.Error -> {
                DiagnosisErrorCard(
                    errorMessage = state.errorMessage,
                    canRetry = state.canRetry,
                    onRetryClicked = { viewModel.runDiagnosis() },
                    onResetClicked = { viewModel.onRemoveImage() }
                )
            }
        }
    }
}

@Composable
private fun DisclaimerBanner() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF8E1)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFFD54F))
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.Info,
                contentDescription = "Notice",
                tint = Color(0xFFF57F17),
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "AI-supported preliminary assessment. Results may be incorrect and must not replace accredited university extension or expert agronomic advice.",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF5D4037)
            )
        }
    }
}

@Composable
private fun ImagePickerPlaceholder(
    onTakePhotoClicked: () -> Unit,
    onChooseImageClicked: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(250.dp),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
        border = androidx.compose.foundation.BorderStroke(1.5.dp, ForestGreenLight.copy(alpha = 0.5f))
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                imageVector = Icons.Default.AddPhotoAlternate,
                contentDescription = "Pick Photo",
                tint = ForestGreenPrimary,
                modifier = Modifier.size(56.dp)
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Capture or Select Tomato Leaf Photo",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Ensure good lighting and sharp leaf focus (Max 15 MB)",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted
            )
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    onClick = onTakePhotoClicked,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                ) {
                    Icon(imageVector = Icons.Default.PhotoCamera, contentDescription = null, tint = Color.White)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Take Photo", color = Color.White, fontWeight = FontWeight.SemiBold)
                }
                FilledTonalButton(
                    onClick = onChooseImageClicked,
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.filledTonalButtonColors(containerColor = SuccessGreenLight)
                ) {
                    Icon(imageVector = Icons.Default.PhotoLibrary, contentDescription = null, tint = ForestGreenPrimary)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Gallery", color = ForestGreenPrimary, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun ImagePreviewCard(
    bitmap: Bitmap,
    fileName: String,
    fileSize: Long,
    onChangeImageClicked: () -> Unit,
    onRemoveImageClicked: () -> Unit,
    isActionsEnabled: Boolean = true
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Leaf Preview
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = "Selected Tomato Leaf Preview",
                modifier = Modifier
                    .fillMaxWidth()
                    .height(230.dp)
                    .clip(RoundedCornerShape(10.dp)),
                contentScale = ContentScale.Crop
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Metadata row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = fileName,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = TextPrimary,
                        maxLines = 1
                    )
                    if (fileSize > 0) {
                        Text(
                            text = "${fileSize / 1024} KB",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted
                        )
                    }
                }

                if (isActionsEnabled) {
                    Row {
                        TextButton(onClick = onChangeImageClicked) {
                            Text("Change", color = ForestGreenPrimary)
                        }
                        TextButton(onClick = onRemoveImageClicked) {
                            Text("Remove", color = ErrorRed)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SmallImageThumbnail(bitmap: Bitmap) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard)
    ) {
        Row(
            modifier = Modifier.padding(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Image(
                bitmap = bitmap.asImageBitmap(),
                contentDescription = "Thumbnail",
                modifier = Modifier
                    .size(60.dp)
                    .clip(RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Crop
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(
                    text = "Diagnosed Leaf Specimen",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenPrimary
                )
                Text(
                    text = "Analysis verified by AgriMind Critic Agent",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary
                )
            }
        }
    }
}

@Composable
private fun DiagnosingLoadingCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(
                color = ForestGreenPrimary,
                strokeWidth = 3.5.dp,
                modifier = Modifier.size(48.dp)
            )
            Spacer(modifier = Modifier.height(18.dp))
            Text(
                text = "Executing AI Diagnostic Pipeline...",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenPrimary
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "1. ResNet-50 visual feature extraction\n2. ChromaDB RAG literature retrieval\n3. LangGraph multi-agent risk assessment\n4. Critic Agent safety verification",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary
            )
        }
    }
}

@Composable
private fun DiagnosisResultCard(
    response: DiagnosisResponse,
    onNewDiagnosisClicked: () -> Unit,
    onViewDetailsClicked: (() -> Unit)? = null,
    onAskAssistantClicked: (() -> Unit)? = null
) {
    val cleanDiseaseName = response.primaryDiagnosis
        ?.replace("Tomato___", "")
        ?.replace("_", " ")
        ?: "Unknown Pathogen"

    val confidencePct = ((response.diagnosisConfidence ?: 0f) * 100).let { "%.1f".format(it) }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SuccessGreenLight),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = "Verified",
                        tint = SuccessGreen,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Diagnosis Result",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = SuccessGreen
                    )
                }

                Badge(containerColor = ForestGreenPrimary) {
                    Text(text = "Case: ${response.caseId}", color = Color.White, fontSize = 11.sp)
                }
            }

            Divider(modifier = Modifier.padding(vertical = 12.dp), color = SuccessGreen.copy(alpha = 0.3f))

            // Primary Disease Name
            Text(
                text = cleanDiseaseName,
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = ForestGreenDark
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Key Metrics Pill Badges
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatusPill(
                    label = "Confidence",
                    value = "$confidencePct%",
                    backgroundColor = Color(0xFFC8E6C9),
                    textColor = ForestGreenDark
                )
                StatusPill(
                    label = "Severity",
                    value = (response.assignedSeverity ?: "N/A").uppercase(),
                    backgroundColor = Color(0xFFFFE0B2),
                    textColor = Color(0xFFE65100)
                )
                StatusPill(
                    label = "Risk",
                    value = (response.epidemicRisk ?: "N/A").uppercase(),
                    backgroundColor = Color(0xFFFFCDD2),
                    textColor = Color(0xFFB71C1C)
                )
            }

            // Low Confidence Threshold Policy (Feature 2)
            val isLowConf = response.isLowConfidence || (response.diagnosisConfidence ?: 1f) < 0.65f
            if (isLowConf) {
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0)),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFFB74D))
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = "Low Confidence Warning",
                                tint = Color(0xFFE65100),
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Low Confidence Detection (< 65%)",
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp,
                                color = Color(0xFFE65100)
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = response.lowConfidenceGuidance ?: "Diagnostic confidence is below threshold. Please retake a clear photo under diffused natural light at 15-20 cm distance, or route this specimen to an extension specialist.",
                            fontSize = 12.sp,
                            color = Color(0xFF5D4037),
                            lineHeight = 16.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(
                                onClick = onNewDiagnosisClicked,
                                modifier = Modifier.weight(1f).height(36.dp),
                                shape = RoundedCornerShape(6.dp)
                            ) {
                                Icon(Icons.Default.PhotoCamera, contentDescription = null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Retake Photo", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                            if (onViewDetailsClicked != null) {
                                Button(
                                    onClick = onViewDetailsClicked,
                                    modifier = Modifier.weight(1f).height(36.dp),
                                    shape = RoundedCornerShape(6.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE65100))
                                ) {
                                    Icon(Icons.Default.SupportAgent, contentDescription = null, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Human Review", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Management Recommendations
            response.managementPlan?.let { plan ->
                Text(
                    text = "Recommended IPM Management Actions",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenPrimary
                )
                Spacer(modifier = Modifier.height(6.dp))

                // Cultural Controls
                plan.culturalControls?.forEach { action ->
                    ActionItem(category = "Cultural", action = action)
                }

                // Resistant Varieties
                plan.resistantVarieties?.forEach { action ->
                    ActionItem(category = "Resistant Variety", action = action)
                }

                // Chemical Controls
                plan.chemicalControls?.forEach { action ->
                    ActionItem(category = "Chemical Control", action = action, isWarning = true)
                }
            }

            // Citations
            if (!response.citations.isNullOrEmpty()) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Accredited University Extension Sources",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                response.citations.take(3).forEach { citation ->
                    Text(
                        text = "• [${citation.citationNumber}] ${citation.title ?: "Diagnostic Fact Sheet"} (${citation.institution ?: "Extension"})",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                }
            }

            // Mandatory Pesticide Notice
            response.pesticideSafetyNotice?.let { notice ->
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(8.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0))
                ) {
                    Text(
                        text = notice,
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFE65100),
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }

            // Latency Breakdown
            response.latencyBreakdown?.let { latency ->
                Spacer(modifier = Modifier.height(10.dp))
                val inferenceMs = latency.modelInferenceMs?.toInt() ?: 0
                val workflowMs = latency.totalWorkflowMs.toInt()
                Text(
                    text = "Measured Latency: Vision Inference ${inferenceMs}ms | Multi-Agent RAG Pipeline ${workflowMs}ms",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextMuted
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (onAskAssistantClicked != null) {
                Button(
                    onClick = onAskAssistantClicked,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                ) {
                    Icon(imageVector = Icons.Default.Forum, contentDescription = null)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Ask Assistant About This Case", fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            if (onViewDetailsClicked != null) {
                OutlinedButton(
                    onClick = onViewDetailsClicked,
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(imageVector = Icons.Default.Assessment, contentDescription = null)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("View Full Case Details & Reassess", fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            OutlinedButton(
                onClick = onNewDiagnosisClicked,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp)
            ) {
                Icon(imageVector = Icons.Default.AddPhotoAlternate, contentDescription = null)
                Spacer(modifier = Modifier.width(6.dp))
                Text("Diagnose Another Leaf")
            }
        }
    }
}

@Composable
private fun StatusPill(
    label: String,
    value: String,
    backgroundColor: Color,
    textColor: Color
) {
    Surface(
        shape = RoundedCornerShape(6.dp),
        color = backgroundColor,
        modifier = Modifier.padding(vertical = 2.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)) {
            Text(text = label, fontSize = 10.sp, color = textColor.copy(alpha = 0.8f))
            Text(text = value, fontSize = 13.sp, fontWeight = FontWeight.Bold, color = textColor)
        }
    }
}

@Composable
private fun ActionItem(
    category: String,
    action: ManagementActionResponse,
    isWarning: Boolean = false
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isWarning) Color(0xFFFFF9C4) else SurfaceCard
        )
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(
                text = "[$category] ${action.actionSummary}",
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Bold,
                color = if (isWarning) Color(0xFFBF360C) else ForestGreenPrimary
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = action.details,
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary
            )
        }
    }
}

@Composable
private fun DiagnosisErrorCard(
    errorMessage: String,
    canRetry: Boolean,
    onRetryClicked: () -> Unit,
    onResetClicked: () -> Unit
) {
    val isImageUnsuitable = errorMessage.contains("plant", ignoreCase = true) ||
            errorMessage.contains("human", ignoreCase = true) ||
            errorMessage.contains("person", ignoreCase = true) ||
            errorMessage.contains("skin", ignoreCase = true) ||
            errorMessage.contains("sky", ignoreCase = true) ||
            errorMessage.contains("vehicle", ignoreCase = true) ||
            errorMessage.contains("wall", ignoreCase = true) ||
            errorMessage.contains("dark", ignoreCase = true) ||
            errorMessage.contains("glare", ignoreCase = true) ||
            errorMessage.contains("blurry", ignoreCase = true) ||
            errorMessage.contains("पौधा", ignoreCase = true) ||
            errorMessage.contains("इंसान", ignoreCase = true) ||
            errorMessage.contains("तस्वीर", ignoreCase = true)

    val containerBg = if (isImageUnsuitable) WarningOrangeLight else ErrorRedLight
    val accentColor = if (isImageUnsuitable) WarningOrange else ErrorRed
    val cardTitle = if (isImageUnsuitable) "Image Unsuitable for Diagnosis" else "Diagnosis Submission Failed"
    val cardIcon = if (isImageUnsuitable) Icons.Default.Warning else Icons.Default.Error

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = containerBg)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = cardIcon,
                    contentDescription = "Status",
                    tint = accentColor,
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = cardTitle,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = accentColor
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = errorMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                if (canRetry && !isImageUnsuitable) {
                    Button(
                        onClick = onRetryClicked,
                        colors = ButtonDefaults.buttonColors(containerColor = accentColor),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Retry Diagnosis")
                    }
                }

                Button(
                    onClick = onResetClicked,
                    colors = ButtonDefaults.buttonColors(containerColor = if (isImageUnsuitable) accentColor else ForestGreenPrimary),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Select Another Photo")
                }
            }
        }
    }
}

@Composable
private fun LiveWeatherCard(
    weather: com.agrimind.app.data.model.LiveWeatherData?,
    isLoading: Boolean,
    onRefresh: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5E9)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFA5D6A7))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.Cloud,
                    contentDescription = "Live Weather",
                    tint = ForestGreenPrimary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = if (weather != null) "Live Microclimate: ${weather.temperatureC}°C, RH ${weather.relativeHumidityPct}%" else "Real-time Field Microclimate",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                    Text(
                        text = if (weather != null) {
                            "${weather.conditionSummary} • Rain 24h: ${weather.rainForecast24hMm} mm"
                        } else if (isLoading) {
                            "Fetching real-time satellite & station weather..."
                        } else {
                            "Tap refresh to load real-time microclimate forecast"
                        },
                        fontSize = 11.sp,
                        color = TextSecondary,
                        maxLines = 2,
                        overflow = androidx.compose.ui.text.style.TextOverflow.Ellipsis
                    )
                }
            }

            IconButton(
                onClick = onRefresh,
                enabled = !isLoading,
                modifier = Modifier.size(32.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = ForestGreenPrimary)
                } else {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh Weather",
                        tint = ForestGreenPrimary,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun OfflinePendingSyncCard(
    pendingCount: Int,
    onSyncClicked: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFFB74D))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.CloudQueue,
                    contentDescription = "Offline Pending",
                    tint = Color(0xFFE65100),
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "$pendingCount Investigation${if (pendingCount > 1) "s" else ""} Queued Offline",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFE65100)
                    )
                    Text(
                        text = "Specimen cached locally. Auto-sync occurs when connectivity restores.",
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                }
            }
            TextButton(onClick = onSyncClicked) {
                Text("Sync Now", fontWeight = FontWeight.Bold, color = Color(0xFFE65100), fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun QueuedOfflineResultCard(
    message: String,
    onNewDiagnosisClicked: () -> Unit,
    onRetrySync: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF8E1)),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFFD54F))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Schedule,
                    contentDescription = "Queued",
                    tint = Color(0xFFF57F17),
                    modifier = Modifier.size(28.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = "Request Queued in Offline Storage",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFFF57F17)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = onRetrySync,
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Attempt Sync")
                }

                OutlinedButton(
                    onClick = onNewDiagnosisClicked,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Text("New Specimen")
                }
            }
        }
    }
}

