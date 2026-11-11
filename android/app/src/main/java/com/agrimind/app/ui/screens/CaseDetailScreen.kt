package com.agrimind.app.ui.screens

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.ManagementActionResponse
import com.agrimind.app.data.model.ReassessmentTriggers
import com.agrimind.app.data.model.CaseComment
import com.agrimind.app.data.model.CaseOutcome
import com.agrimind.app.report.PdfReportGenerator
import com.agrimind.app.ui.theme.*
import com.agrimind.app.ui.viewmodel.CaseDetailViewModel
import com.agrimind.app.ui.viewmodel.CaseShareState
import com.agrimind.app.ui.viewmodel.PdfExportState
import com.agrimind.app.ui.viewmodel.ReassessmentState
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaseDetailScreen(
    caseRecord: LocalCaseRecord,
    viewModel: CaseDetailViewModel,
    onBackClicked: () -> Unit,
    onAskAssistantClicked: ((caseId: String) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val activeCase by viewModel.activeCase.collectAsState()
    val reassessmentState by viewModel.reassessmentState.collectAsState()
    val pdfExportState by viewModel.pdfExportState.collectAsState()
    val caseShareState by viewModel.caseShareState.collectAsState()
    val scrollState = rememberScrollState()
    val context = LocalContext.current
    val pdfGenerator = remember { PdfReportGenerator(context) }

    var showReassessSheet by remember { mutableStateOf(false) }
    var showShareDialog by remember { mutableStateOf(false) }
    var shareTargetEntity by remember { mutableStateOf("cooperative_all") }
    var shareAnonymize by remember { mutableStateOf(true) }
    var shareNotes by remember { mutableStateOf("") }

    val comments by viewModel.comments.collectAsState()
    val isSubmittingComment by viewModel.isSubmittingComment.collectAsState()
    val treatmentOutcome by viewModel.treatmentOutcome.collectAsState()
    val isSubmittingOutcome by viewModel.isSubmittingOutcome.collectAsState()
    var newCommentText by remember { mutableStateOf("") }
    var selectedOutcome by remember { mutableStateOf("helped") }
    var outcomeNotes by remember { mutableStateOf("") }

    // Use latest state from ViewModel if available, fallback to initial passed record
    val current = activeCase ?: caseRecord

    LaunchedEffect(current.caseId) {
        viewModel.loadComments(current.caseId)
        viewModel.loadOutcome(current.caseId)
    }

    // Attempt to decode thumbnail from local URI if accessible
    val localBitmap = remember(current.imageUriString) {
        current.imageUriString?.let { uriStr ->
            try {
                val uri = Uri.parse(uriStr)
                context.contentResolver.openInputStream(uri)?.use { stream ->
                    val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
                    BitmapFactory.decodeStream(stream, null, opts)
                }
            } catch (e: Exception) {
                null
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Case Details",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(
                            text = current.caseId,
                            fontSize = 12.sp,
                            color = Color.White.copy(alpha = 0.85f)
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBackClicked) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    IconButton(
                        onClick = { onAskAssistantClicked?.invoke(current.caseId) }
                    ) {
                        Icon(
                            imageVector = Icons.Default.Chat,
                            contentDescription = "Ask AgriMind Assistant",
                            tint = Color.White
                        )
                    }
                    IconButton(
                        onClick = { showShareDialog = true }
                    ) {
                        Icon(
                            imageVector = Icons.Default.Share,
                            contentDescription = "Share Case with Cooperative",
                            tint = Color.White
                        )
                    }
                    IconButton(
                        onClick = { viewModel.generatePdfReport() }
                    ) {
                        Icon(
                            imageVector = Icons.Default.PictureAsPdf,
                            contentDescription = "Export PDF Report",
                            tint = Color.White
                        )
                    }
                    FilledTonalButton(
                        onClick = { showReassessSheet = true },
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = Color.White.copy(alpha = 0.2f),
                            contentColor = Color.White
                        ),
                        modifier = Modifier.padding(end = 8.dp)
                    ) {
                        Icon(imageVector = Icons.Default.Update, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Reassess", fontSize = 13.sp)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = ForestGreenPrimary)
            )
        }
    ) { innerPadding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp)
                .verticalScroll(scrollState),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Reassessment Success / Alert Banner
            when (val state = reassessmentState) {
                is ReassessmentState.Success -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = SuccessGreenLight),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenPrimary)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = ForestGreenPrimary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(
                                    text = "Adaptive Reassessment Complete (${state.response.reassessmentOutcome?.uppercase() ?: "REVISED"})",
                                    fontWeight = FontWeight.Bold,
                                    color = ForestGreenDark,
                                    fontSize = 14.sp
                                )
                                Text(
                                    text = "Reassessment ${state.response.reassessmentCount} of ${state.response.maxReassessments}. Plan and severity updated.",
                                    fontSize = 12.sp,
                                    color = TextMuted
                                )
                            }
                        }
                    }
                }
                is ReassessmentState.Error -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = ErrorRedLight),
                        border = androidx.compose.foundation.BorderStroke(1.dp, ErrorRed)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Error, contentDescription = null, tint = ErrorRed)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = state.message,
                                color = ErrorRed,
                                fontSize = 13.sp
                            )
                        }
                    }
                }
                else -> {}
            }

            // Specimen Summary Card
            ElevatedCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = current.caseId,
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = ForestGreenPrimary
                            )
                            Text(
                                text = "Recorded: ${current.createdAtIso}",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted
                            )
                        }
                        if (current.isVerified) {
                            AssistChip(
                                onClick = {},
                                label = { Text("Critic Verified", fontSize = 11.sp, fontWeight = FontWeight.Bold) },
                                leadingIcon = {
                                    Icon(Icons.Default.Verified, contentDescription = null, tint = ForestGreenPrimary, modifier = Modifier.size(14.dp))
                                },
                                colors = AssistChipDefaults.assistChipColors(
                                    containerColor = SuccessGreenLight,
                                    labelColor = ForestGreenDark
                                )
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    if (localBitmap != null) {
                        Image(
                            bitmap = localBitmap.asImageBitmap(),
                            contentDescription = "Specimen Thumbnail",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(180.dp)
                                .clip(RoundedCornerShape(10.dp)),
                            contentScale = ContentScale.Crop
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }

                    // Diagnosis & Confidence
                    val formattedDisease = current.activeDiagnosis
                        .replace("Tomato___", "")
                        .replace("_", " ")

                    Text(
                        text = formattedDisease,
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    // Metrics Row: Confidence | Severity | Epidemic Risk
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        MetricPill(
                            label = "Confidence",
                            value = "${"%.1f".format(current.activeConfidence * 100)}%",
                            backgroundColor = ForestGreenLight.copy(alpha = 0.2f),
                            textColor = ForestGreenDark,
                            modifier = Modifier.weight(1f)
                        )
                        MetricPill(
                            label = "Severity",
                            value = current.activeSeverity.uppercase(),
                            backgroundColor = WarningOrangeLight,
                            textColor = WarningOrange,
                            modifier = Modifier.weight(1f)
                        )
                        MetricPill(
                            label = "Epidemic Risk",
                            value = current.activeEpidemicRisk.uppercase(),
                            backgroundColor = ErrorRedLight,
                            textColor = ErrorRed,
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // Expandable Chronological Reassessment History Timeline (Stage C.3)
            ReassessmentTimelineSection(caseRecord = current)

            // Management Recommendations
            val plan = current.activeManagementPlan
            if (plan != null) {
                Text(
                    text = "Recommended IPM Management Plan",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )

                plan.culturalControls?.takeIf { it.isNotEmpty() }?.let { actions ->
                    ControlCategoryGroup(title = "Cultural Controls", actions = actions, color = ForestGreenPrimary)
                }

                plan.resistantVarieties?.takeIf { it.isNotEmpty() }?.let { actions ->
                    ControlCategoryGroup(title = "Resistant Cultivars", actions = actions, color = Color(0xFF2E7D32))
                }

                plan.chemicalControls?.takeIf { it.isNotEmpty() }?.let { actions ->
                    ControlCategoryGroup(title = "Targeted Chemical Controls", actions = actions, color = WarningOrange)
                }

                plan.monitoringActions?.takeIf { it.isNotEmpty() }?.let { actions ->
                    ControlCategoryGroup(title = "Scouting & Monitoring", actions = actions, color = Color(0xFF0277BD))
                }
            }

            // Citations
            val citations = current.initialDiagnosis.citations
            if (!citations.isNullOrEmpty()) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.MenuBook, contentDescription = null, tint = ForestGreenPrimary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "University Extension Citations",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = TextPrimary
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        citations.forEach { c ->
                            Text(
                                text = "• [${c.citationNumber}] ${c.title ?: "Extension Bulletin"} (${c.institution ?: "Agricultural Extension"})",
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted,
                                modifier = Modifier.padding(vertical = 2.dp)
                            )
                        }
                    }
                }
            }

            // Crop-Health PDF Report Section
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenLight)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(
                            imageVector = Icons.Default.PictureAsPdf,
                            contentDescription = null,
                            tint = ForestGreenPrimary,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Crop-Health Diagnostic PDF Report",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = ForestGreenDark
                        )
                    }

                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Generate a native offline PDF summary report formatted for extension records, lab documentation, and field consultation.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextMuted
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    when (val pdfState = pdfExportState) {
                        is PdfExportState.Idle -> {
                            Button(
                                onClick = { viewModel.generatePdfReport() },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(48.dp),
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                            ) {
                                Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Generate & Export PDF Report", fontWeight = FontWeight.Bold)
                            }
                        }
                        is PdfExportState.Generating -> {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 8.dp),
                                horizontalArrangement = Arrangement.Center,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    strokeWidth = 2.dp,
                                    color = ForestGreenPrimary
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(
                                    text = "Rendering multi-page PDF document...",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = TextPrimary
                                )
                            }
                        }
                        is PdfExportState.Ready -> {
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                colors = CardDefaults.cardColors(containerColor = SuccessGreenLight),
                                shape = RoundedCornerShape(8.dp)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(
                                            Icons.Default.CheckCircle,
                                            contentDescription = null,
                                            tint = ForestGreenPrimary,
                                            modifier = Modifier.size(18.dp)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = "PDF Ready: ${pdfState.fileName}",
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            color = ForestGreenDark
                                        )
                                    }
                                    Text(
                                        text = "Size: ${(pdfState.file.length() + 1023) / 1024} KB • Location: Device cache/reports",
                                        fontSize = 11.sp,
                                        color = TextMuted,
                                        modifier = Modifier.padding(top = 2.dp, bottom = 8.dp)
                                    )
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        OutlinedButton(
                                            onClick = {
                                                try {
                                                    val shareIntent = pdfGenerator.createShareIntent(pdfState.file)
                                                    context.startActivity(Intent.createChooser(shareIntent, "Share AgriMind Report"))
                                                } catch (e: Exception) {
                                                    Toast.makeText(context, "No sharing app available: ${e.message}", Toast.LENGTH_SHORT).show()
                                                }
                                            },
                                            modifier = Modifier.weight(1f),
                                            shape = RoundedCornerShape(6.dp)
                                        ) {
                                            Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                                            Spacer(modifier = Modifier.width(4.dp))
                                            Text("Share", fontSize = 12.sp)
                                        }

                                        Button(
                                            onClick = {
                                                try {
                                                    val viewIntent = pdfGenerator.createViewIntent(pdfState.file)
                                                    context.startActivity(viewIntent)
                                                } catch (e: Exception) {
                                                    Toast.makeText(context, "No PDF viewer app found: ${e.message}", Toast.LENGTH_SHORT).show()
                                                }
                                            },
                                            modifier = Modifier.weight(1f),
                                            shape = RoundedCornerShape(6.dp),
                                            colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                                        ) {
                                            Icon(Icons.Default.OpenInNew, contentDescription = null, modifier = Modifier.size(16.dp))
                                            Spacer(modifier = Modifier.width(4.dp))
                                            Text("Open", fontSize = 12.sp)
                                        }
                                    }
                                }
                            }
                        }
                        is PdfExportState.Error -> {
                            Column {
                                Text(
                                    text = "Error generating report: ${pdfState.message}",
                                    color = ErrorRed,
                                    fontSize = 12.sp,
                                    modifier = Modifier.padding(bottom = 6.dp)
                                )
                                OutlinedButton(
                                    onClick = { viewModel.generatePdfReport() },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text("Retry PDF Generation", fontSize = 12.sp)
                                }
                            }
                        }
                    }
                }
            }

            // Conversational Decision Support Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(12.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Surface(
                            shape = CircleShape,
                            color = Color(0xFFE8F5E9),
                            modifier = Modifier.size(36.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.Forum,
                                    contentDescription = null,
                                    tint = ForestGreenPrimary,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = "AgriMind Decision Assistant",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = ForestGreenDark
                            )
                            Text(
                                text = "Evidence-Grounded Interactive Q&A",
                                fontSize = 11.sp,
                                color = TextMuted
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    Text(
                        text = "Have questions about this ${current.primaryDiagnosis?.replace("Tomato___", "")?.replace("_", " ") ?: "case"}? Ask our assistant about registered protectants, spray intervals, or sanitation practices grounded in extension literature.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                        lineHeight = 16.sp
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    Button(
                        onClick = { onAskAssistantClicked?.invoke(current.caseId) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(44.dp),
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                    ) {
                        Icon(Icons.Default.Chat, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Ask AgriMind Assistant About This Case",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }
                }
            }

            // Treatment Outcome Tracking Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenLight)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.FactCheck,
                                contentDescription = null,
                                tint = ForestGreenPrimary,
                                modifier = Modifier.size(22.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Treatment Outcome Tracking",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = ForestGreenDark
                            )
                        }

                        // Badge showing recorded outcome
                        val currentOutcome = treatmentOutcome?.outcome?.lowercase() ?: "not_reported"
                        val (badgeBg, badgeText, badgeLabel) = when (currentOutcome) {
                            "helped" -> Triple(SuccessGreenLight, ForestGreenDark, "Helped")
                            "did_not_help" -> Triple(ErrorRedLight, ErrorRed, "Did Not Help")
                            "pending" -> Triple(Color(0xFFFFF8E1), Color(0xFFE65100), "Pending")
                            else -> Triple(Color(0xFFEEEEEE), TextMuted, "Not Yet Assessed")
                        }
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = badgeBg
                        ) {
                            Text(
                                text = badgeLabel,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = badgeText,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Did the recommended IPM cultural controls or registered sprays improve crop vigor?",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextMuted
                    )

                    treatmentOutcome?.details?.takeIf { it.isNotBlank() }?.let { det ->
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Last Report: $det",
                            fontSize = 12.sp,
                            color = TextSecondary,
                            modifier = Modifier
                                .background(Color(0xFFF5F5F5), RoundedCornerShape(6.dp))
                                .padding(8.dp)
                                .fillMaxWidth()
                        )
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Buttons to select outcome
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = selectedOutcome == "helped",
                            onClick = { selectedOutcome = "helped" },
                            label = { Text("Helped", fontSize = 12.sp) },
                            leadingIcon = {
                                if (selectedOutcome == "helped") {
                                    Icon(Icons.Default.ThumbUp, contentDescription = null, modifier = Modifier.size(14.dp))
                                }
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = SuccessGreenLight,
                                selectedLabelColor = ForestGreenDark
                            ),
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = selectedOutcome == "did_not_help",
                            onClick = { selectedOutcome = "did_not_help" },
                            label = { Text("Did Not Help", fontSize = 12.sp) },
                            leadingIcon = {
                                if (selectedOutcome == "did_not_help") {
                                    Icon(Icons.Default.ThumbDown, contentDescription = null, modifier = Modifier.size(14.dp))
                                }
                            },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = ErrorRedLight,
                                selectedLabelColor = ErrorRed
                            ),
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = selectedOutcome == "pending",
                            onClick = { selectedOutcome = "pending" },
                            label = { Text("Pending", fontSize = 12.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = Color(0xFFFFF8E1),
                                selectedLabelColor = Color(0xFFE65100)
                            ),
                            modifier = Modifier.weight(1f)
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    OutlinedTextField(
                        value = outcomeNotes,
                        onValueChange = { outcomeNotes = it },
                        placeholder = { Text("Add outcome observation (e.g. spray date, weather impact)", fontSize = 12.sp) },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 2,
                        textStyle = LocalTextStyle.current.copy(fontSize = 12.sp)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Button(
                        onClick = {
                            viewModel.recordOutcome(current.caseId, selectedOutcome, outcomeNotes)
                            outcomeNotes = ""
                        },
                        modifier = Modifier.fillMaxWidth().height(40.dp),
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                        enabled = !isSubmittingOutcome
                    ) {
                        if (isSubmittingOutcome) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                        } else {
                            Text("Record Treatment Outcome", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Farmer Social Network: Observations & Community Feedback Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE0E0E0))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Groups,
                                contentDescription = null,
                                tint = ForestGreenPrimary,
                                modifier = Modifier.size(22.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Farmer Observations & Feedback (${comments.size})",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = ForestGreenDark
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Peer field observations strictly separated from AI predictions.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextMuted,
                        fontSize = 11.sp
                    )

                    Spacer(modifier = Modifier.height(10.dp))

                    if (comments.isEmpty()) {
                        Text(
                            text = "No grower observations shared for this specimen yet. Be the first to share your field experience.",
                            fontSize = 12.sp,
                            color = TextMuted,
                            modifier = Modifier.padding(vertical = 4.dp)
                        )
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            comments.forEach { c ->
                                val isAi = c.isAi
                                val cardBg = if (isAi) Color(0xFFF3E5F5) else Color(0xFFF1F8E9)
                                val tagColor = if (isAi) Color(0xFF7B1FA2) else ForestGreenDark
                                val tagText = if (isAi) "AI System Guidance" else "Farmer Observation"

                                Surface(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(8.dp),
                                    color = cardBg
                                ) {
                                    Column(modifier = Modifier.padding(10.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Surface(
                                                shape = RoundedCornerShape(6.dp),
                                                color = tagColor.copy(alpha = 0.15f)
                                            ) {
                                                Text(
                                                    text = tagText,
                                                    fontSize = 10.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = tagColor,
                                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                )
                                            }
                                            Text(
                                                text = c.authorId,
                                                fontSize = 11.sp,
                                                fontWeight = FontWeight.Medium,
                                                color = TextMuted
                                            )
                                        }
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(
                                            text = c.commentText,
                                            fontSize = 12.sp,
                                            color = TextPrimary
                                        )
                                    }
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    // Input new observation
                    OutlinedTextField(
                        value = newCommentText,
                        onValueChange = { newCommentText = it },
                        placeholder = { Text("Share your observation or treatment experience...", fontSize = 12.sp) },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 3,
                        textStyle = LocalTextStyle.current.copy(fontSize = 12.sp)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Button(
                        onClick = {
                            viewModel.addComment(current.caseId, newCommentText)
                            newCommentText = ""
                        },
                        modifier = Modifier.fillMaxWidth().height(40.dp),
                        shape = RoundedCornerShape(8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                        enabled = newCommentText.isNotBlank() && !isSubmittingComment
                    ) {
                        if (isSubmittingComment) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                        } else {
                            Icon(Icons.Default.AddComment, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Post Observation", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }

            // Reassess Action Button
            Button(
                onClick = { showReassessSheet = true },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                enabled = current.reassessmentCount < 2
            ) {
                Icon(Icons.Default.Update, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (current.reassessmentCount < 2) "Adaptive Case Reassessment" else "Reassessment Limit (2) Reached",
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp
                )
            }
        }
    }

    // Reassessment Bottom Sheet Dialog
    if (showReassessSheet) {
        ReassessmentBottomSheet(
            caseId = current.caseId,
            currentCount = current.reassessmentCount,
            isSubmitting = reassessmentState is ReassessmentState.Submitting,
            onSubmit = { trigger, evidence, rationale ->
                viewModel.submitReassessment(trigger, evidence, rationale)
                showReassessSheet = false
            },
            onDismiss = { showReassessSheet = false }
        )
    }

    if (showShareDialog) {
        AlertDialog(
            onDismissRequest = { showShareDialog = false },
            title = {
                Text(
                    text = "Share Case with Cooperative",
                    fontWeight = FontWeight.Bold,
                    color = ForestGreenDark
                )
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "Share this specimen with the regional cooperative surveillance network to strengthen collective pathogen intelligence.",
                        fontSize = 13.sp,
                        color = TextPrimary
                    )

                    OutlinedTextField(
                        value = shareTargetEntity,
                        onValueChange = { shareTargetEntity = it },
                        label = { Text("Target Cooperative / Entity") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Checkbox(
                            checked = shareAnonymize,
                            onCheckedChange = { shareAnonymize = it }
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "Anonymize location & farm details (fuzz GPS)",
                            fontSize = 12.sp,
                            color = TextSecondary
                        )
                    }

                    OutlinedTextField(
                        value = shareNotes,
                        onValueChange = { shareNotes = it },
                        label = { Text("Field Notes / Observations (Optional)") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 3
                    )

                    if (caseShareState is CaseShareState.Error) {
                        Text(
                            text = (caseShareState as CaseShareState.Error).message,
                            fontSize = 12.sp,
                            color = ErrorRed
                        )
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.shareCase(
                            targetEntity = shareTargetEntity,
                            anonymizePii = shareAnonymize,
                            notes = shareNotes.takeIf { it.isNotBlank() }
                        )
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                    enabled = caseShareState !is CaseShareState.Sharing
                ) {
                    if (caseShareState is CaseShareState.Sharing) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.White)
                    } else {
                        Text("Share Specimen")
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    showShareDialog = false
                    viewModel.resetCaseShareState()
                }) {
                    Text("Cancel")
                }
            }
        )
    }

    if (caseShareState is CaseShareState.Success) {
        val shareRes = (caseShareState as CaseShareState.Success).response
        AlertDialog(
            onDismissRequest = {
                viewModel.resetCaseShareState()
                showShareDialog = false
            },
            title = {
                Text("Case Shared Successfully", fontWeight = FontWeight.Bold, color = ForestGreenDark)
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "Specimen registered in cooperative disease surveillance.",
                        fontSize = 13.sp
                    )
                    Surface(
                        color = Color(0xFFF1F8E9),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("Share ID: ${shareRes.shareId}", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                            Text("Token: ${shareRes.shareToken}", fontSize = 12.sp, color = TextMuted)
                            Text("Target: ${shareRes.targetEntity}", fontSize = 12.sp, color = TextSecondary)
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(
                                Intent.EXTRA_TEXT,
                                "AgriMind Surveillance: Diagnostic Case ${shareRes.caseId} shared with ${shareRes.targetEntity}. Access Token: ${shareRes.shareToken}."
                            )
                        }
                        context.startActivity(Intent.createChooser(shareIntent, "Share with Cooperative via"))
                        viewModel.resetCaseShareState()
                        showShareDialog = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
                ) {
                    Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Send via...")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    viewModel.resetCaseShareState()
                    showShareDialog = false
                }) {
                    Text("Done")
                }
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ReassessmentBottomSheet(
    caseId: String,
    currentCount: Int,
    isSubmitting: Boolean,
    onSubmit: (trigger: String, evidence: Map<String, Any>, rationale: String?) -> Unit,
    onDismiss: () -> Unit
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ) {
        var selectedTrigger by remember { mutableStateOf(ReassessmentTriggers.WEATHER_UPDATE) }
        var weatherCondition by remember { mutableStateOf("cool_wet") }
        var damagePercentageText by remember { mutableStateOf("25.0") }
        var canopySpread by remember { mutableStateOf("mid_canopy") }
        var fieldNotes by remember { mutableStateOf("") }
        var treatmentNotes by remember { mutableStateOf("") }
        var rationale by remember { mutableStateOf("Sudden temperature drop and continuous rainfall accelerating lesion expansion.") }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text(
                text = "Adaptive Case Reassessment",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = ForestGreenPrimary
            )
            Text(
                text = "Case: $caseId | Reassessment Cycle: ${currentCount + 1} of 2",
                style = MaterialTheme.typography.bodySmall,
                color = TextMuted
            )

            HorizontalDivider()

            // Trigger Selector
            Text("Reassessment Trigger", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            ReassessmentTriggers.ALL.forEach { (triggerKey, triggerLabel) ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    RadioButton(
                        selected = selectedTrigger == triggerKey,
                        onClick = { selectedTrigger = triggerKey }
                    )
                    Text(text = triggerLabel, style = MaterialTheme.typography.bodyMedium)
                }
            }

            // Weather Conditions
            OutlinedTextField(
                value = weatherCondition,
                onValueChange = { weatherCondition = it },
                label = { Text("Weather Conditions") },
                placeholder = { Text("cool_wet, warm_humid, hot_dry") },
                modifier = Modifier.fillMaxWidth()
            )

            // Leaf Damage Percentage
            OutlinedTextField(
                value = damagePercentageText,
                onValueChange = { damagePercentageText = it },
                label = { Text("Updated Leaf Damage % (0-100)") },
                modifier = Modifier.fillMaxWidth()
            )

            // Canopy Spread
            OutlinedTextField(
                value = canopySpread,
                onValueChange = { canopySpread = it },
                label = { Text("Canopy Spread") },
                placeholder = { Text("lower_canopy, mid_canopy, whole_plant") },
                modifier = Modifier.fillMaxWidth()
            )

            // Treatment & Field Notes
            OutlinedTextField(
                value = treatmentNotes,
                onValueChange = { treatmentNotes = it },
                label = { Text("Treatment Notes (Optional)") },
                placeholder = { Text("E.g. Fixed copper applied 5 days ago") },
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = fieldNotes,
                onValueChange = { fieldNotes = it },
                label = { Text("Field Scouting Notes (Optional)") },
                placeholder = { Text("Observed lesion progression or stem cankers") },
                modifier = Modifier.fillMaxWidth()
            )

            // Rationale
            OutlinedTextField(
                value = rationale,
                onValueChange = { rationale = it },
                label = { Text("Reassessment Rationale") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 2
            )

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = {
                    val damage = damagePercentageText.toFloatOrNull() ?: 20.0f
                    val evidence = mutableMapOf<String, Any>(
                        "weather_conditions" to weatherCondition,
                        "leaf_damage_percentage" to damage,
                        "canopy_spread" to canopySpread
                    )
                    if (fieldNotes.isNotBlank()) evidence["field_notes"] = fieldNotes
                    if (treatmentNotes.isNotBlank()) evidence["treatment_notes"] = treatmentNotes

                    onSubmit(selectedTrigger, evidence, rationale.takeIf { it.isNotBlank() })
                },
                enabled = !isSubmitting,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary)
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(color = Color.White, modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Reassessing...")
                } else {
                    Icon(Icons.Default.Send, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Submit Adaptive Reassessment", fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun MetricPill(
    label: String,
    value: String,
    backgroundColor: Color,
    textColor: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = backgroundColor)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(text = label, style = MaterialTheme.typography.bodySmall, color = TextMuted)
            Text(text = value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold, color = textColor)
        }
    }
}

@Composable
private fun ControlCategoryGroup(
    title: String,
    actions: List<ManagementActionResponse>,
    color: Color
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = color
            )
            Spacer(modifier = Modifier.height(6.dp))
            actions.forEach { action ->
                Text(
                    text = "• ${action.actionSummary}",
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp,
                    color = TextPrimary
                )
                Text(
                    text = action.details,
                    fontSize = 12.sp,
                    color = TextMuted,
                    modifier = Modifier.padding(start = 12.dp, bottom = 6.dp)
                )
            }
        }
    }
}

/**
 * Expandable / collapsible chronological timeline displaying diagnostic baseline
 * and progressive adaptive reassessment cycles (Stage C.3).
 */
@Composable
fun ReassessmentTimelineSection(
    caseRecord: LocalCaseRecord,
    modifier: Modifier = Modifier
) {
    var isExpanded by remember { mutableStateOf(caseRecord.reassessmentCount > 0) }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
        border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenLight)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header Row (Clickable for expand/collapse)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { isExpanded = !isExpanded }
                    .padding(vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.History,
                    contentDescription = null,
                    tint = ForestGreenPrimary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Reassessment History Timeline",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                    Text(
                        text = "${caseRecord.reassessmentCount} of 2 cycles completed",
                        fontSize = 12.sp,
                        color = TextMuted
                    )
                }
                IconButton(onClick = { isExpanded = !isExpanded }) {
                    Icon(
                        imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = if (isExpanded) "Collapse timeline" else "Expand timeline",
                        tint = ForestGreenDark
                    )
                }
            }

            if (isExpanded) {
                Spacer(modifier = Modifier.height(10.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(1.dp)
                        .background(ForestGreenLight.copy(alpha = 0.5f))
                )
                Spacer(modifier = Modifier.height(12.dp))

                // Chronological Timeline Sequence
                // Node 0: Initial Baseline Diagnostic Event
                TimelineNodeItem(
                    isFirst = true,
                    isLast = caseRecord.reassessmentHistory.isEmpty(),
                    badgeColor = ForestGreenPrimary,
                    icon = Icons.Default.Flag,
                    cycleTitle = "Initial Diagnosis (Baseline)",
                    timestamp = formatTimelineTimestamp(caseRecord.createdAtIso),
                    diagnosis = caseRecord.primaryDiagnosis,
                    confidence = caseRecord.diagnosisConfidence,
                    severity = caseRecord.assignedSeverity,
                    risk = caseRecord.epidemicRisk,
                    trigger = "Initial Specimen Submission",
                    rationale = null,
                    outcome = "BASELINE"
                )

                // Subsequent Reassessment Nodes
                if (caseRecord.reassessmentHistory.isNotEmpty()) {
                    caseRecord.reassessmentHistory.forEachIndexed { index, reassessment ->
                        val auditRecord = reassessment.reassessmentRecords?.firstOrNull()
                        val isLastNode = (index == caseRecord.reassessmentHistory.lastIndex)

                        val badgeColor = when (reassessment.reassessmentOutcome?.lowercase()) {
                            "confirmed" -> ForestGreenPrimary
                            "revised" -> WarningOrange
                            "escalated" -> ErrorRed
                            else -> ForestGreenDark
                        }

                        TimelineNodeItem(
                            isFirst = false,
                            isLast = isLastNode,
                            badgeColor = badgeColor,
                            icon = Icons.Default.Update,
                            cycleTitle = "Cycle #${index + 1} — ${reassessment.reassessmentOutcome?.uppercase() ?: "REVISED"}",
                            timestamp = formatTimelineTimestamp(auditRecord?.timestamp),
                            diagnosis = reassessment.primaryDiagnosis ?: caseRecord.primaryDiagnosis,
                            confidence = reassessment.diagnosisConfidence,
                            severity = reassessment.assignedSeverity ?: "indeterminate",
                            risk = reassessment.epidemicRisk ?: "UNKNOWN",
                            priorSeverity = auditRecord?.priorSeverity,
                            trigger = formatTriggerLabel(auditRecord?.trigger),
                            rationale = auditRecord?.triggerRationale ?: auditRecord?.notes,
                            evidence = auditRecord?.newEvidence,
                            outcome = reassessment.reassessmentOutcome?.uppercase() ?: "REVISED",
                            isVerified = reassessment.isVerified
                        )
                    }
                } else {
                    // Empty Reassessment State Notice
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(LightGreenBackground, RoundedCornerShape(8.dp))
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Info,
                            contentDescription = null,
                            tint = ForestGreenPrimary,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "No adaptive reassessments recorded",
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 12.sp,
                                color = TextPrimary
                            )
                            Text(
                                text = "This case is operating on initial baseline evidence. 2 of 2 reassessments available.",
                                fontSize = 11.sp,
                                color = TextMuted
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TimelineNodeItem(
    isFirst: Boolean,
    isLast: Boolean,
    badgeColor: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    cycleTitle: String,
    timestamp: String,
    diagnosis: String,
    confidence: Float?,
    severity: String,
    risk: String,
    priorSeverity: String? = null,
    trigger: String,
    rationale: String? = null,
    evidence: Map<String, Any>? = null,
    outcome: String,
    isVerified: Boolean = true
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(IntrinsicSize.Min)
    ) {
        // Vertical Timeline Column (Indicator circle + connecting line)
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .width(36.dp)
                .fillMaxHeight()
        ) {
            // Indicator Circle
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(badgeColor.copy(alpha = 0.15f))
                    .border(2.dp, badgeColor, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = badgeColor,
                    modifier = Modifier.size(16.dp)
                )
            }

            // Connecting vertical line (unless last node)
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .width(2.dp)
                        .weight(1f)
                        .background(ForestGreenLight.copy(alpha = 0.7f))
                )
            }
        }

        Spacer(modifier = Modifier.width(10.dp))

        // Content Column
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(bottom = if (isLast) 4.dp else 16.dp)
        ) {
            // Header Row: Cycle title + Outcome Chip
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = cycleTitle,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )
                OutcomeBadge(outcome = outcome, color = badgeColor)
            }

            // Timestamp
            Text(
                text = timestamp,
                fontSize = 11.sp,
                color = TextMuted
            )

            Spacer(modifier = Modifier.height(4.dp))

            // Trigger & Diagnosis Info
            val cleanDisease = diagnosis.replace("Tomato___", "").replace("_", " ")
            val confStr = confidence?.let { " (${(it * 100).toInt()}%)" } ?: ""
            Text(
                text = "$cleanDisease$confStr • Trigger: $trigger",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                color = ForestGreenDark
            )

            // Severity Shift or Severity Value
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (priorSeverity != null && priorSeverity.lowercase() != severity.lowercase()) {
                    SeverityBadge(label = "Prior: ${priorSeverity.uppercase()}", isWarning = false)
                    Text("→", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                    SeverityBadge(label = "Revised: ${severity.uppercase()}", isWarning = true)
                } else {
                    SeverityBadge(
                        label = "Severity: ${severity.uppercase()}",
                        isWarning = severity.lowercase() in listOf("severe", "critical")
                    )
                }
                RiskBadge(risk = risk)
            }

            // Optional Rationale Box
            if (!rationale.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = LightGreenBackground,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "Rationale: \"$rationale\"",
                        fontSize = 11.sp,
                        fontStyle = androidx.compose.ui.text.font.FontStyle.Italic,
                        color = TextPrimary,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)
                    )
                }
            }

            // Optional Evidence Highlights
            if (evidence != null && evidence.isNotEmpty()) {
                val evidenceItems = evidence.entries.filter { it.value != null && it.value.toString().isNotBlank() }
                if (evidenceItems.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Evidence: " + evidenceItems.joinToString(", ") { "${it.key.replace("_", " ")}: ${it.value}" },
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                }
            }
        }
    }
}

@Composable
private fun OutcomeBadge(outcome: String, color: Color) {
    Surface(
        shape = RoundedCornerShape(4.dp),
        color = color.copy(alpha = 0.15f),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.5f))
    ) {
        Text(
            text = outcome,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            color = color,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun SeverityBadge(label: String, isWarning: Boolean) {
    val bgColor = if (isWarning) WarningOrangeLight else ForestGreenLight.copy(alpha = 0.3f)
    val txtColor = if (isWarning) WarningOrange else ForestGreenDark
    Surface(
        shape = RoundedCornerShape(4.dp),
        color = bgColor
    ) {
        Text(
            text = label,
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = txtColor,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

@Composable
private fun RiskBadge(risk: String) {
    val isHigh = risk.lowercase() in listOf("high", "critical")
    val bgColor = if (isHigh) ErrorRedLight else ForestGreenLight.copy(alpha = 0.2f)
    val txtColor = if (isHigh) ErrorRed else ForestGreenDark
    Surface(
        shape = RoundedCornerShape(4.dp),
        color = bgColor
    ) {
        Text(
            text = "Risk: ${risk.uppercase()}",
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = txtColor,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

internal fun formatTimelineTimestamp(isoString: String?): String {
    if (isoString.isNullOrBlank()) return "Timestamp not recorded"
    return try {
        val clean = isoString.trim()
        val withoutZ = if (clean.endsWith("Z", ignoreCase = true)) clean.substring(0, clean.length - 1) else clean
        val parser = if (withoutZ.contains(".")) {
            val fracLen = withoutZ.substringAfter(".").length
            val fracPattern = "S".repeat(minOf(fracLen, 6))
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.$fracPattern", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
        } else {
            SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
        }
        val date = parser.parse(withoutZ) ?: return clean
        SimpleDateFormat("MMM d, yyyy • h:mm a", Locale.US).format(date)
    } catch (e: Exception) {
        isoString
    }
}

internal fun formatTriggerLabel(rawTrigger: String?): String {
    if (rawTrigger.isNullOrBlank()) return "Field Evidence Update"
    return ReassessmentTriggers.ALL.find { it.first == rawTrigger }?.second
        ?: rawTrigger.replace("_", " ").replaceFirstChar { it.uppercase() }
}

