package com.agrimind.app.ui.screens

import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agrimind.app.data.model.CooperativeInsightsData
import com.agrimind.app.data.model.CooperativeComparisonResponse
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.SharedCaseSummary
import com.agrimind.app.ui.theme.*
import com.agrimind.app.ui.viewmodel.HistoryViewModel
import com.agrimind.app.ui.viewmodel.PdfExportState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    viewModel: HistoryViewModel,
    onCaseSelected: (LocalCaseRecord) -> Unit,
    modifier: Modifier = Modifier
) {
    val cases by viewModel.casesFlow.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val cooperativeInsights by viewModel.cooperativeInsights.collectAsState()
    val sharedCases by viewModel.sharedCases.collectAsState()
    val cooperativeComparison by viewModel.cooperativeComparison.collectAsState()
    val isLoadingCooperative by viewModel.isLoadingCooperative.collectAsState()
    val cooperativePdfState by viewModel.cooperativePdfState.collectAsState()

    var selectedSegment by remember { mutableIntStateOf(0) }
    val context = LocalContext.current

    // Listen for Cooperative PDF export result
    LaunchedEffect(cooperativePdfState) {
        when (val state = cooperativePdfState) {
            is PdfExportState.Ready -> {
                try {
                    val uri = androidx.core.content.FileProvider.getUriForFile(
                        context,
                        "${context.packageName}.fileprovider",
                        state.file
                    )
                    val intent = Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(uri, "application/pdf")
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(Intent.createChooser(intent, "Open Cooperative Health Audit"))
                } catch (e: Exception) {
                    Toast.makeText(context, "Report exported: ${state.file.absolutePath}", Toast.LENGTH_LONG).show()
                } finally {
                    viewModel.resetCooperativePdfState()
                }
            }
            is PdfExportState.Error -> {
                Toast.makeText(context, "Cooperative PDF Error: ${state.message}", Toast.LENGTH_LONG).show()
                viewModel.resetCooperativePdfState()
            }
            else -> {}
        }
    }

    val filteredCases = remember(cases, searchQuery) {
        if (searchQuery.isBlank()) {
            cases
        } else {
            cases.filter {
                it.caseId.contains(searchQuery, ignoreCase = true) ||
                it.activeDiagnosis.contains(searchQuery, ignoreCase = true) ||
                it.primaryDiagnosis.contains(searchQuery, ignoreCase = true)
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Segmented Control (My Farm Cases vs Cooperative Surveillance)
        TabRow(
            selectedTabIndex = selectedSegment,
            containerColor = Color.White,
            contentColor = ForestGreenPrimary,
            modifier = Modifier.fillMaxWidth()
        ) {
            Tab(
                selected = selectedSegment == 0,
                onClick = { selectedSegment = 0 },
                text = { Text("My Farm Cases (${cases.size})", fontWeight = FontWeight.Bold) }
            )
            Tab(
                selected = selectedSegment == 1,
                onClick = {
                    selectedSegment = 1
                    viewModel.fetchCooperativeData()
                },
                text = { Text("Cooperative Surveillance", fontWeight = FontWeight.Bold) }
            )
        }

        if (selectedSegment == 0) {
            // Explanatory Banner distinguishing Local Device Records from Server Records
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenLight.copy(alpha = 0.5f))
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Info,
                        contentDescription = null,
                        tint = ForestGreenPrimary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = "Local Investigation History",
                            fontWeight = FontWeight.Bold,
                            color = ForestGreenDark,
                            fontSize = 13.sp
                        )
                        Text(
                            text = "Recorded locally on this device. Continuity and adaptive reassessments are verified server-side by Case ID.",
                            fontSize = 11.sp,
                            color = TextMuted,
                            lineHeight = 15.sp
                        )
                    }
                }
            }

            // Search bar
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { viewModel.onSearchQueryChanged(it) },
                placeholder = { Text("Search by Case ID or Disease name...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = TextMuted) },
                trailingIcon = {
                    if (searchQuery.isNotBlank()) {
                        IconButton(onClick = { viewModel.onSearchQueryChanged("") }) {
                            Icon(Icons.Default.Clear, contentDescription = "Clear search", tint = TextMuted)
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                singleLine = true
            )

            // Case List or Empty State
            if (filteredCases.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.FolderOpen,
                            contentDescription = null,
                            tint = TextMuted.copy(alpha = 0.5f),
                            modifier = Modifier.size(64.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = if (searchQuery.isBlank()) "No Diagnostic Cases Saved Yet" else "No matching cases found",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = if (searchQuery.isBlank())
                                "Diagnoses submitted from the Diagnosis tab will appear here automatically."
                            else
                                "Try searching with a different Case ID or disease keyword.",
                            style = MaterialTheme.typography.bodySmall,
                            color = TextMuted,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(filteredCases, key = { it.caseId }) { record ->
                        HistoryItemCard(
                            record = record,
                            onClick = { onCaseSelected(record) }
                        )
                    }
                }
            }
        } else {
            // Cooperative Surveillance Tab
            CooperativeSurveillanceView(
                insights = cooperativeInsights,
                sharedCases = sharedCases,
                comparison = cooperativeComparison,
                isLoading = isLoadingCooperative,
                isExportingPdf = cooperativePdfState is PdfExportState.Generating,
                onRefresh = { viewModel.fetchCooperativeData() },
                onExportPdf = { viewModel.exportCooperativePdf() }
            )
        }
    }
}

@Composable
private fun CooperativeSurveillanceView(
    insights: CooperativeInsightsData?,
    sharedCases: List<SharedCaseSummary>,
    comparison: CooperativeComparisonResponse?,
    isLoading: Boolean,
    isExportingPdf: Boolean,
    onRefresh: () -> Unit,
    onExportPdf: () -> Unit
) {
    if (isLoading && insights == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = ForestGreenPrimary)
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Header & Export Action Row
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Jammu & Kashmir Cooperative",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenDark
                    )
                    Text(
                        text = "Aggregated Disease Surveillance Network",
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                }

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    IconButton(onClick = onRefresh, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ForestGreenPrimary)
                    }
                }
            }
        }

        // Regional Risk Level Banner
        item {
            val riskLevel = insights?.regionalRiskLevel ?: "MODERATE"
            val (riskBg, riskText, riskDesc) = when (riskLevel.uppercase()) {
                "CRITICAL" -> Triple(Color(0xFFFFEBEE), Color(0xFFC62828), "Critical regional pathogen activity detected. Rapid preventative containment advised.")
                "HIGH" -> Triple(Color(0xFFFFF3E0), Color(0xFFE65100), "Elevated sporulation conditions. Active field monitoring and fungicide readiness required.")
                "MODERATE" -> Triple(Color(0xFFFFFDE7), Color(0xFFF57F17), "Moderate pathogen pressure across regional acreage. Maintain routine sanitation.")
                else -> Triple(Color(0xFFE8F5E9), Color(0xFF2E7D32), "Low regional disease spread. Continue standard crop scouting.")
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = riskBg)
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = if (riskLevel == "CRITICAL" || riskLevel == "HIGH") Icons.Default.Warning else Icons.Default.Shield,
                        contentDescription = null,
                        tint = riskText,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "Regional Risk Level: $riskLevel",
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                            color = riskText
                        )
                        Text(
                            text = riskDesc,
                            fontSize = 11.sp,
                            color = riskText.copy(alpha = 0.9f)
                        )
                    }
                }
            }
        }

        // Outbreak Alerts (if present)
        val alerts = insights?.outbreakAlerts
        if (!alerts.isNullOrEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE)),
                    border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFEF9A9A))
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Emergency, contentDescription = null, tint = ErrorRed, modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Active Outbreak Warning", fontWeight = FontWeight.Bold, fontSize = 13.sp, color = ErrorRed)
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        alerts.forEach { alert ->
                            Text("• $alert", fontSize = 12.sp, color = TextPrimary)
                        }
                    }
                }
            }
        }

        // Analytics Overview Cards
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MetricCard(
                    title = "Total Specimen",
                    value = "${insights?.totalCasesAnalyzed ?: sharedCases.size}",
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    title = "Dominant",
                    value = (insights?.dominantPathogen ?: "N/A").replace("Tomato___", "").replace("_", " "),
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    title = "Shared Cases",
                    value = "${sharedCases.size}",
                    modifier = Modifier.weight(1f)
                )
            }
        }

        // Pathogen Distribution breakdown
        val dist = insights?.diseaseDistribution
        if (!dist.isNullOrEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = "Regional Pathogen Distribution",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            color = ForestGreenDark
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        dist.entries.forEach { entry ->
                            val cleanName = entry.key.replace("Tomato___", "").replace("_", " ")
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 3.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(cleanName, fontSize = 12.sp, color = TextPrimary, modifier = Modifier.weight(1f))
                                Text("${"%.1f".format(entry.value.percentage)}%", fontWeight = FontWeight.Bold, fontSize = 12.sp, color = ForestGreenPrimary)
                            }
                        }
                    }
                }
            }
        }

        // Collective IPM Strategy recommendation
        val ipmActions = insights?.collectiveIpmActions
        if (!ipmActions.isNullOrEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = "Cooperative Collective IPM Actions",
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp,
                            color = ForestGreenDark
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        ipmActions.forEach { rec ->
                            Text("• $rec", fontSize = 12.sp, color = TextPrimary, modifier = Modifier.padding(bottom = 3.dp))
                        }
                    }
                }
            }
        }

        // Inter-Cooperative Regional Comparison (Feature 5)
        if (comparison != null && comparison.regions.isNotEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard),
                    border = androidx.compose.foundation.BorderStroke(1.dp, ForestGreenLight)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.CompareArrows, contentDescription = null, tint = ForestGreenPrimary)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Inter-Cooperative Regional Surveillance Comparison",
                                fontWeight = FontWeight.Bold,
                                fontSize = 13.sp,
                                color = ForestGreenDark
                            )
                        }
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = comparison.disclaimer,
                            fontSize = 11.sp,
                            color = TextMuted,
                            lineHeight = 15.sp
                        )
                        Spacer(modifier = Modifier.height(10.dp))

                        comparison.regions.forEach { reg ->
                            val isLocal = reg.isLocalPilot
                            val headerBg = if (isLocal) SuccessGreenLight else Color(0xFFF5F5F5)
                            val riskColor = when (reg.regionalRiskLevel.uppercase()) {
                                "CRITICAL" -> Color(0xFFC62828)
                                "HIGH" -> Color(0xFFE65100)
                                "MODERATE" -> Color(0xFFF57F17)
                                else -> ForestGreenDark
                            }

                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp),
                                shape = RoundedCornerShape(8.dp),
                                colors = CardDefaults.cardColors(containerColor = headerBg)
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = reg.regionName,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 12.sp,
                                            color = TextPrimary
                                        )
                                        Surface(
                                            shape = RoundedCornerShape(4.dp),
                                            color = if (isLocal) ForestGreenPrimary else Color(0xFF757575)
                                        ) {
                                            Text(
                                                text = reg.dataStatus,
                                                fontSize = 10.sp,
                                                color = Color.White,
                                                fontWeight = FontWeight.SemiBold,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(4.dp))
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text(
                                            text = "Dominant: ${reg.dominantPathogen.replace("Tomato___", "").replace("_", " ")}",
                                            fontSize = 11.sp,
                                            color = TextSecondary
                                        )
                                        Text(
                                            text = "Risk: ${reg.regionalRiskLevel}",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = riskColor
                                        )
                                    }

                                    reg.outbreakAlerts?.firstOrNull()?.let { alert ->
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(
                                            text = "Alert: $alert",
                                            fontSize = 10.5.sp,
                                            color = Color(0xFFC62828)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // Export Full Cooperative Audit Report (PDF)
        item {
            Button(
                onClick = onExportPdf,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ForestGreenPrimary),
                enabled = !isExportingPdf
            ) {
                if (isExportingPdf) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.White)
                } else {
                    Icon(Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Export Cooperative Health Audit (PDF)", fontWeight = FontWeight.Bold, fontSize = 13.sp)
                }
            }
        }

        // Shared Cases in Cooperative
        item {
            Text(
                text = "Authorized Shared Cases (${sharedCases.size})",
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
                color = ForestGreenDark
            )
        }

        if (sharedCases.isEmpty()) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard)
                ) {
                    Text(
                        text = "No cases shared with this cooperative yet. Use the 'Share' button in any Case Details screen to share diagnostic specimens.",
                        fontSize = 12.sp,
                        color = TextMuted,
                        modifier = Modifier.padding(14.dp)
                    )
                }
            }
        } else {
            items(sharedCases, key = { it.shareId }) { item ->
                val primaryDiag = (item.caseSummary["primary_diagnosis"] as? String ?: "Tomato specimen")
                    .replace("Tomato___", "").replace("_", " ")
                val assignedSev = (item.caseSummary["assigned_severity"] as? String ?: "indeterminate")
                    .uppercase()
                val isPiiMasked = item.caseSummary["anonymized"] as? Boolean ?: true

                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceCard)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "Case: ${item.caseId}",
                                fontWeight = FontWeight.Bold,
                                fontSize = 12.sp,
                                color = ForestGreenPrimary
                            )
                            Text(
                                text = item.createdAt.take(10),
                                fontSize = 11.sp,
                                color = TextMuted
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "$primaryDiag ($assignedSev)",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp,
                            color = TextPrimary
                        )
                        if (item.notes != null) {
                            Text(
                                text = "Notes: ${item.notes}",
                                fontSize = 11.sp,
                                color = TextSecondary
                            )
                        }
                        Text(
                            text = "Target: ${item.targetEntity} • PII Masked: ${if (isPiiMasked) "Yes" else "No"}",
                            fontSize = 10.sp,
                            color = TextMuted
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricCard(title: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard)
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(title, fontSize = 10.sp, color = TextMuted, maxLines = 1)
            Spacer(modifier = Modifier.height(4.dp))
            Text(value, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = ForestGreenDark)
        }
    }
}

@Composable
private fun HistoryItemCard(
    record: LocalCaseRecord,
    onClick: () -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceCard),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.5.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Header Row: Case ID & Date
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Description,
                        contentDescription = null,
                        tint = ForestGreenPrimary,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = record.caseId,
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = ForestGreenPrimary
                    )
                }

                Text(
                    text = record.createdAtIso.take(16).replace("T", " "),
                    fontSize = 11.sp,
                    color = TextMuted
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Primary Disease Name
            val formattedDisease = record.activeDiagnosis
                .replace("Tomato___", "")
                .replace("_", " ")

            Text(
                text = formattedDisease,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Metrics Row: Confidence %, Severity, Risk, Reassessment Count
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                StatusBadge(
                    text = "${"%.1f".format(record.activeConfidence * 100)}%",
                    containerColor = ForestGreenLight.copy(alpha = 0.25f),
                    contentColor = ForestGreenDark
                )
                StatusBadge(
                    text = record.activeSeverity.uppercase(),
                    containerColor = WarningOrangeLight,
                    contentColor = WarningOrange
                )
                StatusBadge(
                    text = record.activeEpidemicRisk.uppercase(),
                    containerColor = ErrorRedLight,
                    contentColor = ErrorRed
                )
                if (record.reassessmentCount > 0) {
                    StatusBadge(
                        text = "Reassessed ${record.reassessmentCount}x",
                        containerColor = Color(0xFFE1BEE7),
                        contentColor = Color(0xFF4A148C)
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusBadge(
    text: String,
    containerColor: Color,
    contentColor: Color
) {
    Box(
        modifier = Modifier
            .background(containerColor, RoundedCornerShape(6.dp))
            .padding(horizontal = 6.dp, vertical = 3.dp)
    ) {
        Text(
            text = text,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            color = contentColor
        )
    }
}
