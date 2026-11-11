package com.agrimind.app.report

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.net.Uri
import android.os.Environment
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import androidx.core.content.FileProvider
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.ManagementActionResponse
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

/**
 * Native Android PDF Crop-Health Report Generator.
 * Uses Android platform standard android.graphics.pdf.PdfDocument with zero external dependencies.
 */
class PdfReportGenerator(private val context: Context) {

    companion object {
        private const val PAGE_WIDTH = 595 // Standard A4 width in points at 72 dpi
        private const val PAGE_HEIGHT = 842 // Standard A4 height in points at 72 dpi
        private const val MARGIN_LEFT = 40f
        private const val MARGIN_RIGHT = 40f
        private const val MARGIN_TOP = 40f
        private const val MARGIN_BOTTOM = 50f
        private const val USABLE_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT // 515f
        private const val MAX_CONTENT_Y = PAGE_HEIGHT - MARGIN_BOTTOM // 792f

        // Brand colors
        private const val COLOR_HEADER = 0xFF1B5E20.toInt() // Dark forest green
        private const val COLOR_ACCENT = 0xFF2E7D32.toInt() // Primary leaf green
        private const val COLOR_ACCENT_LIGHT = 0xFFE8F5E9.toInt() // Light green surface
        private const val COLOR_AMBER = 0xFFE65100.toInt() // Warning orange / amber
        private const val COLOR_AMBER_LIGHT = 0xFFFFF3E0.toInt() // Amber surface
        private const val COLOR_TEXT_DARK = 0xFF212121.toInt()
        private const val COLOR_TEXT_MUTED = 0xFF616161.toInt()
        private const val COLOR_BORDER = 0xFFBDBDBD.toInt()
    }

    private class PageManager(private val document: PdfDocument) {
        var pageNumber = 1
            private set
        var currentPage: PdfDocument.Page = document.startPage(PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create())
            private set
        var canvas: Canvas = currentPage.canvas
            private set
        var cursorY: Float = 0f

        fun ensureSpace(neededHeight: Float, onNewPageHeader: (Canvas, Float) -> Float) {
            if (cursorY + neededHeight > MAX_CONTENT_Y) {
                // Finish current page
                drawFooter()
                document.finishPage(currentPage)

                // Start new page
                pageNumber++
                currentPage = document.startPage(PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create())
                canvas = currentPage.canvas
                cursorY = onNewPageHeader(canvas, pageNumber.toFloat())
            }
        }

        fun drawFooter() {
            val paint = Paint().apply {
                isAntiAlias = true
                color = 0xFFB0BEC5.toInt()
                strokeWidth = 0.8f
            }
            canvas.drawLine(MARGIN_LEFT, 805f, PAGE_WIDTH - MARGIN_RIGHT, 805f, paint)

            val textPaint = Paint().apply {
                isAntiAlias = true
                color = COLOR_TEXT_MUTED
                textSize = 7.5f
                typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            }
            canvas.drawText("AgriMind Crop-Health Decision Support | Preliminary AI Assessment", MARGIN_LEFT, 818f, textPaint)

            val pageStr = "Page $pageNumber"
            val pageStrWidth = textPaint.measureText(pageStr)
            canvas.drawText(pageStr, PAGE_WIDTH - MARGIN_RIGHT - pageStrWidth, 818f, textPaint)
        }

        fun finish() {
            drawFooter()
            document.finishPage(currentPage)
        }
    }

    /**
     * Generates a comprehensive PDF crop-health report for the given case record.
     * Writes to the app's secure cache/reports directory and returns the File.
     */
    @Throws(IOException::class)
    fun generateReport(record: LocalCaseRecord): File {
        val document = PdfDocument()
        val pageManager = PageManager(document)

        // Draw initial page header
        pageManager.cursorY = drawDocumentHeader(pageManager.canvas, record)

        // 1. Case Metadata Box
        pageManager.ensureSpace(85f) { canvas, _ -> drawContinuationHeader(canvas, record) }
        drawCaseMetadataBox(pageManager, record)

        // 2. Primary Diagnostic Findings
        pageManager.ensureSpace(120f) { canvas, _ -> drawContinuationHeader(canvas, record) }
        drawDiagnosticFindings(pageManager, record)

        // 3. Adaptive Reassessment History (if present)
        val historyRecords = record.reassessmentHistory
        if (historyRecords.isNotEmpty() || record.latestReassessment != null) {
            drawReassessmentHistory(pageManager, record)
        }

        // 4. Integrated Pest Management (IPM) Recommendations
        drawManagementPlan(pageManager, record)

        // 5. Supporting University Extension Citations (if present)
        drawCitations(pageManager, record)

        // 6. Regulatory & Safety Disclaimer
        drawDisclaimer(pageManager, record)

        // Finalize PDF document
        pageManager.finish()

        // Write to output file
        val reportsDir = File(context.cacheDir, "reports")
        if (!reportsDir.exists()) {
            reportsDir.mkdirs()
        }
        val safeCaseId = record.caseId.replace(Regex("[^a-zA-Z0-9_-]"), "_")
        val outputFile = File(reportsDir, "AgriMind_Report_${safeCaseId}.pdf")

        FileOutputStream(outputFile).use { out ->
            document.writeTo(out)
        }
        document.close()

        return outputFile
    }

    private fun drawDocumentHeader(canvas: Canvas, record: LocalCaseRecord): Float {
        // Green banner bar
        val bannerPaint = Paint().apply {
            color = COLOR_HEADER
            style = Paint.Style.FILL
        }
        canvas.drawRect(0f, 0f, PAGE_WIDTH.toFloat(), 70f, bannerPaint)

        // Document Title
        val titlePaint = Paint().apply {
            color = Color.WHITE
            textSize = 15f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText("AgriMind — AI Crop-Health Diagnostic Report", MARGIN_LEFT, 32f, titlePaint)

        // Subtitle
        val subPaint = Paint().apply {
            color = 0xFFC8E6C9.toInt() // light green
            textSize = 9.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        canvas.drawText("Tomato Disease Investigation, Severity Assessment & Decision Support", MARGIN_LEFT, 48f, subPaint)

        // Date on right
        val dateText = "Generated: ${record.createdAtIso.take(19).replace('T', ' ')}"
        val datePaint = Paint().apply {
            color = Color.WHITE
            textSize = 8.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val dateWidth = datePaint.measureText(dateText)
        canvas.drawText(dateText, PAGE_WIDTH - MARGIN_RIGHT - dateWidth, 32f, datePaint)

        return 85f
    }

    private fun drawContinuationHeader(canvas: Canvas, record: LocalCaseRecord): Float {
        val bannerPaint = Paint().apply {
            color = COLOR_HEADER
            style = Paint.Style.FILL
        }
        canvas.drawRect(0f, 0f, PAGE_WIDTH.toFloat(), 40f, bannerPaint)

        val titlePaint = Paint().apply {
            color = Color.WHITE
            textSize = 10f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText("AgriMind Crop-Health Report — Case: ${record.caseId}", MARGIN_LEFT, 24f, titlePaint)

        return 55f
    }

    private fun drawCaseMetadataBox(pm: PageManager, record: LocalCaseRecord) {
        val boxHeight = 70f
        val rect = RectF(MARGIN_LEFT, pm.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pm.cursorY + boxHeight)

        val bgPaint = Paint().apply {
            color = COLOR_ACCENT_LIGHT
            style = Paint.Style.FILL
        }
        pm.canvas.drawRoundRect(rect, 6f, 6f, bgPaint)

        val borderPaint = Paint().apply {
            color = 0xFFA5D6A7.toInt()
            style = Paint.Style.STROKE
            strokeWidth = 1f
        }
        pm.canvas.drawRoundRect(rect, 6f, 6f, borderPaint)

        val labelPaint = Paint().apply {
            color = COLOR_TEXT_MUTED
            textSize = 8.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val valuePaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 9.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }

        val col1X = MARGIN_LEFT + 14f
        val col2X = MARGIN_LEFT + 180f
        val col3X = MARGIN_LEFT + 340f

        val row1Y = pm.cursorY + 22f
        val row2Y = pm.cursorY + 50f

        // Row 1
        pm.canvas.drawText("CASE IDENTIFIER", col1X, row1Y, labelPaint)
        pm.canvas.drawText(record.caseId, col1X, row1Y + 12f, valuePaint)

        pm.canvas.drawText("DIAGNOSIS TIMESTAMP", col2X, row1Y, labelPaint)
        pm.canvas.drawText(record.createdAtIso.take(19).replace('T', ' ') + " UTC", col2X, row1Y + 12f, valuePaint)

        pm.canvas.drawText("CRITIC AGENT STATUS", col3X, row1Y, labelPaint)
        val statusText = if (record.isVerified) "VERIFIED (Approved)" else "MANUAL REVIEW REQUIRED"
        val statusColor = if (record.isVerified) COLOR_ACCENT else COLOR_AMBER
        val statusPaint = Paint().apply {
            color = statusColor
            textSize = 9.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        pm.canvas.drawText(statusText, col3X, row1Y + 12f, statusPaint)

        pm.cursorY += boxHeight + 14f
    }

    private fun drawDiagnosticFindings(pm: PageManager, record: LocalCaseRecord) {
        drawSectionHeader(pm.canvas, pm.cursorY, "1. PRIMARY DIAGNOSTIC FINDINGS")
        pm.cursorY += 20f

        // Table grid for findings
        val tableHeight = 65f
        val rect = RectF(MARGIN_LEFT, pm.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pm.cursorY + tableHeight)

        val bgPaint = Paint().apply {
            color = 0xFFFAFAFA.toInt()
            style = Paint.Style.FILL
        }
        pm.canvas.drawRoundRect(rect, 4f, 4f, bgPaint)

        val borderPaint = Paint().apply {
            color = COLOR_BORDER
            style = Paint.Style.STROKE
            strokeWidth = 0.8f
        }
        pm.canvas.drawRoundRect(rect, 4f, 4f, borderPaint)

        // Draw columns: Disease, Confidence, Severity, Risk
        val colWidth = USABLE_WIDTH / 4f
        val labelPaint = Paint().apply {
            color = COLOR_TEXT_MUTED
            textSize = 8f
            isAntiAlias = true
        }
        val valPaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 10f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }

        // Col 1: Predicted Disease
        val c1X = MARGIN_LEFT + 12f
        pm.canvas.drawText("PREDICTED DISEASE", c1X, pm.cursorY + 20f, labelPaint)
        val diseaseFormatted = formatDiseaseName(record.activeDiagnosis)
        pm.canvas.drawText(diseaseFormatted, c1X, pm.cursorY + 38f, valPaint)
        val latinName = getLatinName(record.activeDiagnosis)
        if (latinName.isNotEmpty()) {
            val latinPaint = Paint().apply {
                color = COLOR_TEXT_MUTED
                textSize = 7.5f
                typeface = Typeface.create(Typeface.SERIF, Typeface.ITALIC)
            }
            pm.canvas.drawText(latinName, c1X, pm.cursorY + 52f, latinPaint)
        }

        // Col 2: Confidence
        val c2X = MARGIN_LEFT + colWidth + 15f
        pm.canvas.drawText("AI CONFIDENCE", c2X, pm.cursorY + 20f, labelPaint)
        val confPct = "%.1f%%".format(record.activeConfidence * 100f)
        pm.canvas.drawText(confPct, c2X, pm.cursorY + 38f, valPaint)
        val confNotePaint = Paint().apply {
            color = COLOR_TEXT_MUTED
            textSize = 7f
        }
        val latencyMs = record.initialDiagnosis.latencyBreakdown?.modelInferenceMs?.toInt()
        val confSubText = if (latencyMs != null && latencyMs > 0) {
            "(ResNet-50: ${latencyMs}ms)"
        } else {
            "(ResNet-50 Checkpoint)"
        }
        pm.canvas.drawText(confSubText, c2X, pm.cursorY + 52f, confNotePaint)

        // Col 3: Severity
        val c3X = MARGIN_LEFT + colWidth * 2 + 15f
        pm.canvas.drawText("ACTIVE SEVERITY", c3X, pm.cursorY + 20f, labelPaint)
        val sevText = record.activeSeverity.uppercase()
        val sevPaint = Paint(valPaint).apply {
            color = getSeverityColor(record.activeSeverity)
        }
        pm.canvas.drawText(sevText, c3X, pm.cursorY + 38f, sevPaint)

        // Col 4: Epidemic Risk
        val c4X = MARGIN_LEFT + colWidth * 3 + 15f
        pm.canvas.drawText("EPIDEMIC RISK", c4X, pm.cursorY + 20f, labelPaint)
        val riskText = record.activeEpidemicRisk.uppercase()
        val riskPaint = Paint(valPaint).apply {
            color = getRiskColor(record.activeEpidemicRisk)
        }
        pm.canvas.drawText(riskText, c4X, pm.cursorY + 38f, riskPaint)

        pm.cursorY += tableHeight + 16f
    }

    private fun drawReassessmentHistory(pm: PageManager, record: LocalCaseRecord) {
        val history = record.reassessmentHistory
        val latest = record.latestReassessment

        pm.ensureSpace(60f) { canvas, _ -> drawContinuationHeader(canvas, record) }
        drawSectionHeader(pm.canvas, pm.cursorY, "2. ADAPTIVE REASSESSMENT AUDIT LOG", COLOR_AMBER)
        pm.cursorY += 20f

        val cycles = if (history.isNotEmpty()) history else listOfNotNull(latest)
        cycles.forEachIndexed { index, resp ->
            pm.ensureSpace(70f) { canvas, _ -> drawContinuationHeader(canvas, record) }

            val itemHeight = 65f
            val rect = RectF(MARGIN_LEFT, pm.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pm.cursorY + itemHeight)

            val bgPaint = Paint().apply {
                color = COLOR_AMBER_LIGHT
                style = Paint.Style.FILL
            }
            pm.canvas.drawRoundRect(rect, 4f, 4f, bgPaint)

            val borderPaint = Paint().apply {
                color = 0xFFFFCC80.toInt()
                style = Paint.Style.STROKE
                strokeWidth = 0.8f
            }
            pm.canvas.drawRoundRect(rect, 4f, 4f, borderPaint)

            val titlePaint = Paint().apply {
                color = COLOR_AMBER
                textSize = 9.5f
                typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
                isAntiAlias = true
            }
            val cycleTitle = "Reassessment Cycle #${resp.reassessmentCount} — Outcome: ${(resp.reassessmentOutcome ?: "REVISED").uppercase()}"
            pm.canvas.drawText(cycleTitle, MARGIN_LEFT + 10f, pm.cursorY + 18f, titlePaint)

            val subPaint = Paint().apply {
                color = COLOR_TEXT_DARK
                textSize = 8.5f
                isAntiAlias = true
            }
            val metricsSummary = "Resulting Severity: ${resp.assignedSeverity?.uppercase() ?: "CRITICAL"}  |  Resulting Risk: ${resp.epidemicRisk?.uppercase() ?: "CRITICAL"}"
            pm.canvas.drawText(metricsSummary, MARGIN_LEFT + 10f, pm.cursorY + 33f, subPaint)

            // Extract notes/rationale from history records if present
            val recordItem = resp.reassessmentRecords?.firstOrNull()
            val trigger = recordItem?.trigger ?: "Field update"
            val rationale = recordItem?.triggerRationale ?: "Adaptive update of environmental risk & lesion severity"
            val detailText = "Trigger: $trigger  •  Rationale: $rationale"
            drawWrappedText(pm.canvas, detailText, MARGIN_LEFT + 10f, pm.cursorY + 46f, USABLE_WIDTH - 20f, 8f, COLOR_TEXT_MUTED)

            pm.cursorY += itemHeight + 10f
        }

        pm.cursorY += 6f
    }

    private fun drawManagementPlan(pm: PageManager, record: LocalCaseRecord) {
        val plan = record.activeManagementPlan ?: return

        pm.ensureSpace(50f) { canvas, _ -> drawContinuationHeader(canvas, record) }
        drawSectionHeader(pm.canvas, pm.cursorY, "3. INTEGRATED PEST MANAGEMENT (IPM) RECOMMENDATIONS")
        pm.cursorY += 20f

        // Draw categories
        drawCategoryBlock(pm, record, "Cultural Controls", plan.culturalControls, COLOR_ACCENT)
        drawCategoryBlock(pm, record, "Resistant Cultivars", plan.resistantVarieties, 0xFF1565C0.toInt())
        drawCategoryBlock(pm, record, "Targeted Chemical Controls", plan.chemicalControls, 0xFFC62828.toInt())
        drawCategoryBlock(pm, record, "Scouting & Monitoring", plan.monitoringActions, 0xFF6A1B9A.toInt())
    }

    private fun drawCategoryBlock(
        pm: PageManager,
        record: LocalCaseRecord,
        title: String,
        actions: List<ManagementActionResponse>?,
        categoryColor: Int
    ) {
        if (actions.isNullOrEmpty()) return

        pm.ensureSpace(40f) { canvas, _ -> drawContinuationHeader(canvas, record) }

        // Category Subheader
        val catPaint = Paint().apply {
            color = categoryColor
            textSize = 9.5f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            isAntiAlias = true
        }
        pm.canvas.drawText("▶  $title", MARGIN_LEFT + 4f, pm.cursorY + 12f, catPaint)
        pm.cursorY += 20f

        actions.forEach { action ->
            // Action summary
            val summaryLayout = createStaticLayout("• ${action.actionSummary}", USABLE_WIDTH - 16f, 8.5f, COLOR_TEXT_DARK, Typeface.BOLD)
            val detailsLayout = createStaticLayout(action.details, USABLE_WIDTH - 28f, 8f, COLOR_TEXT_MUTED, Typeface.NORMAL)

            val neededHeight = summaryLayout.height + detailsLayout.height + 10f
            pm.ensureSpace(neededHeight) { canvas, _ -> drawContinuationHeader(canvas, record) }

            // Draw summary
            pm.canvas.save()
            pm.canvas.translate(MARGIN_LEFT + 12f, pm.cursorY)
            summaryLayout.draw(pm.canvas)
            pm.canvas.restore()
            pm.cursorY += summaryLayout.height + 2f

            // Draw details (indented)
            pm.canvas.save()
            pm.canvas.translate(MARGIN_LEFT + 22f, pm.cursorY)
            detailsLayout.draw(pm.canvas)
            pm.canvas.restore()
            pm.cursorY += detailsLayout.height + 8f
        }
    }

    private fun drawCitations(pm: PageManager, record: LocalCaseRecord) {
        val citations = record.initialDiagnosis.citations ?: record.latestReassessment?.citations
        if (citations.isNullOrEmpty()) return

        pm.ensureSpace(50f) { canvas, _ -> drawContinuationHeader(canvas, record) }
        drawSectionHeader(pm.canvas, pm.cursorY, "4. SUPPORTING UNIVERSITY EXTENSION CITATIONS")
        pm.cursorY += 20f

        citations.forEach { citation ->
            val citeText = "• [${citation.citationNumber}] ${citation.title ?: "Extension Document"} — ${citation.institution ?: "Agricultural Extension"}"
            val layout = createStaticLayout(citeText, USABLE_WIDTH - 16f, 8f, COLOR_TEXT_MUTED, Typeface.NORMAL)

            pm.ensureSpace(layout.height + 6f) { canvas, _ -> drawContinuationHeader(canvas, record) }

            pm.canvas.save()
            pm.canvas.translate(MARGIN_LEFT + 8f, pm.cursorY)
            layout.draw(pm.canvas)
            pm.canvas.restore()
            pm.cursorY += layout.height + 6f
        }
        pm.cursorY += 10f
    }

    private fun drawDisclaimer(pm: PageManager, record: LocalCaseRecord) {
        val disclaimerText = "REGULATORY NOTICE & CERTIFICATION BOUNDARY: This document is an automated AI-assisted preliminary diagnostic evaluation generated by the AgriMind decision support platform. AI image analysis alone does NOT issue an official disease-free certificate. Any formal phytosanitary certification requires an authorized inspection and approved certification process by competent state agricultural authorities. It is NOT an official agricultural certification, state regulatory phytosanitary clearance, or guaranteed biological diagnosis. Pesticide application and cultural management strategies must strictly comply with current regional university agricultural extension guidelines and manufacturer EPA-approved product labels. Always consult an accredited plant pathologist or county extension specialist before initiating chemical controls."

        val layout = createStaticLayout(disclaimerText, USABLE_WIDTH - 24f, 7.5f, 0xFF4E342E.toInt(), Typeface.NORMAL)
        val boxHeight = layout.height + 24f

        pm.ensureSpace(boxHeight + 10f) { canvas, _ -> drawContinuationHeader(canvas, record) }

        val rect = RectF(MARGIN_LEFT, pm.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pm.cursorY + boxHeight)

        val bgPaint = Paint().apply {
            color = COLOR_AMBER_LIGHT
            style = Paint.Style.FILL
        }
        pm.canvas.drawRoundRect(rect, 4f, 4f, bgPaint)

        val borderPaint = Paint().apply {
            color = 0xFFFFB74D.toInt()
            style = Paint.Style.STROKE
            strokeWidth = 1f
        }
        pm.canvas.drawRoundRect(rect, 4f, 4f, borderPaint)

        pm.canvas.save()
        pm.canvas.translate(MARGIN_LEFT + 12f, pm.cursorY + 12f)
        layout.draw(pm.canvas)
        pm.canvas.restore()

        pm.cursorY += boxHeight + 10f
    }

    private fun drawSectionHeader(canvas: Canvas, y: Float, title: String, color: Int = COLOR_HEADER) {
        val paint = Paint().apply {
            this.color = color
            textSize = 10.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        canvas.drawText(title, MARGIN_LEFT, y + 10f, paint)

        val linePaint = Paint().apply {
            this.color = color
            strokeWidth = 1.2f
            isAntiAlias = true
        }
        canvas.drawLine(MARGIN_LEFT, y + 14f, PAGE_WIDTH - MARGIN_RIGHT, y + 14f, linePaint)
    }

    private fun createStaticLayout(
        text: String,
        maxWidth: Float,
        textSize: Float,
        textColor: Int,
        style: Int
    ): StaticLayout {
        val textPaint = TextPaint().apply {
            isAntiAlias = true
            this.color = textColor
            this.textSize = textSize
            typeface = Typeface.create(Typeface.SANS_SERIF, style)
        }

        return StaticLayout.Builder.obtain(text, 0, text.length, textPaint, maxWidth.toInt().coerceAtLeast(10))
            .setAlignment(Layout.Alignment.ALIGN_NORMAL)
            .setLineSpacing(0f, 1.15f)
            .setIncludePad(false)
            .build()
    }

    private fun drawWrappedText(
        canvas: Canvas,
        text: String,
        x: Float,
        y: Float,
        maxWidth: Float,
        textSize: Float,
        textColor: Int
    ): Float {
        val layout = createStaticLayout(text, maxWidth, textSize, textColor, Typeface.NORMAL)
        canvas.save()
        canvas.translate(x, y)
        layout.draw(canvas)
        canvas.restore()
        return layout.height.toFloat()
    }

    private fun formatDiseaseName(raw: String): String {
        return when {
            raw.contains("Late_blight", ignoreCase = true) -> "Late Blight"
            raw.contains("Early_blight", ignoreCase = true) -> "Early Blight"
            raw.contains("Bacterial_spot", ignoreCase = true) -> "Bacterial Spot"
            else -> raw.replace("Tomato___", "").replace("_", " ")
        }
    }

    private fun getLatinName(raw: String): String {
        return when {
            raw.contains("Late_blight", ignoreCase = true) -> "Phytophthora infestans"
            raw.contains("Early_blight", ignoreCase = true) -> "Alternaria solani"
            raw.contains("Bacterial_spot", ignoreCase = true) -> "Xanthomonas perforans"
            else -> ""
        }
    }

    private fun getSeverityColor(sev: String): Int {
        return when (sev.lowercase()) {
            "critical" -> 0xFFB71C1C.toInt()
            "high" -> 0xFFE65100.toInt()
            "moderate" -> 0xFFF57F17.toInt()
            "low" -> 0xFF2E7D32.toInt()
            else -> COLOR_TEXT_DARK
        }
    }

    private fun getRiskColor(risk: String): Int {
        return when (risk.lowercase()) {
            "critical" -> 0xFFB71C1C.toInt()
            "high" -> 0xFFE65100.toInt()
            "moderate" -> 0xFFF57F17.toInt()
            "low" -> 0xFF2E7D32.toInt()
            else -> COLOR_TEXT_DARK
        }
    }

    /**
     * Generates a comprehensive multi-case Cooperative Crop-Health Audit & Surveillance PDF report.
     */
    @Throws(IOException::class)
    fun generateAggregatedHealthReport(
        insights: com.agrimind.app.data.model.CooperativeInsightsData,
        cases: List<com.agrimind.app.data.model.SharedCaseSummary>
    ): File {
        val document = PdfDocument()
        val pageManager = PageManager(document)

        // Draw Aggregated Document Header
        val headerPaint = Paint().apply {
            color = COLOR_HEADER
            isAntiAlias = true
        }
        pageManager.canvas.drawRect(0f, 0f, PAGE_WIDTH.toFloat(), 65f, headerPaint)

        val titlePaint = Paint().apply {
            color = Color.WHITE
            textSize = 15f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        pageManager.canvas.drawText("AgriMind Cooperative Crop-Health Audit & Surveillance", MARGIN_LEFT, 32f, titlePaint)

        val subPaint = Paint().apply {
            color = 0xFFC8E6C9.toInt()
            textSize = 9f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val genDate = if (insights.generatedAt.length >= 19) insights.generatedAt.take(19).replace("T", " ") else insights.generatedAt
        pageManager.canvas.drawText("Region: ${insights.region} | Generated: $genDate", MARGIN_LEFT, 50f, subPaint)
        pageManager.cursorY = 85f

        // Regional Risk Level Banner
        val riskColor = when (insights.regionalRiskLevel.uppercase()) {
            "CRITICAL" -> 0xFFD32F2F.toInt()
            "HIGH" -> COLOR_AMBER
            "MODERATE" -> 0xFFFBC02D.toInt()
            else -> COLOR_ACCENT
        }
        val bannerPaint = Paint().apply {
            color = riskColor
            isAntiAlias = true
        }
        pageManager.canvas.drawRoundRect(RectF(MARGIN_LEFT, pageManager.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pageManager.cursorY + 35f), 6f, 6f, bannerPaint)

        val bannerTextPaint = Paint().apply {
            color = Color.WHITE
            textSize = 12f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        pageManager.canvas.drawText("REGIONAL EPIDEMIC RISK: ${insights.regionalRiskLevel.uppercase()} (Total Cases: ${insights.totalCasesAnalyzed})", MARGIN_LEFT + 15f, pageManager.cursorY + 22f, bannerTextPaint)
        pageManager.cursorY += 50f

        // Disease Distribution Section
        val sectionTitlePaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 12f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        pageManager.canvas.drawText("Pathogen Distribution in Cooperative Pool", MARGIN_LEFT, pageManager.cursorY, sectionTitlePaint)
        pageManager.cursorY += 15f

        val distPaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 9.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val dist = insights.diseaseDistribution ?: emptyMap()
        if (dist.isEmpty()) {
            pageManager.canvas.drawText("No pathogen incidence recorded in pool yet.", MARGIN_LEFT, pageManager.cursorY, distPaint)
            pageManager.cursorY += 16f
        } else {
            for ((pathogen, stats) in dist) {
                val cleanName = pathogen.replace("Tomato___", "").replace("_", " ")
                pageManager.canvas.drawText("• $cleanName: ${stats.count} case(s) (${stats.percentage}%)", MARGIN_LEFT + 10f, pageManager.cursorY, distPaint)
                pageManager.cursorY += 15f
            }
        }
        pageManager.cursorY += 10f

        // Outbreak Alerts Section
        pageManager.canvas.drawText("Active Outbreak Warnings & Epidemiological Alerts", MARGIN_LEFT, pageManager.cursorY, sectionTitlePaint)
        pageManager.cursorY += 15f
        val alertPaint = Paint().apply {
            color = 0xFFC62828.toInt()
            textSize = 9f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        for (alert in (insights.outbreakAlerts ?: emptyList())) {
            pageManager.canvas.drawText("! $alert", MARGIN_LEFT + 10f, pageManager.cursorY, alertPaint)
            pageManager.cursorY += 15f
        }
        pageManager.cursorY += 10f

        // Collective IPM Recommendations
        pageManager.canvas.drawText("Collective Cooperative IPM Actions", MARGIN_LEFT, pageManager.cursorY, sectionTitlePaint)
        pageManager.cursorY += 15f
        val ipmPaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 8.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        for (action in (insights.collectiveIpmActions ?: emptyList())) {
            pageManager.canvas.drawText("→ $action", MARGIN_LEFT + 10f, pageManager.cursorY, ipmPaint)
            pageManager.cursorY += 14f
        }
        pageManager.cursorY += 15f

        // Case Summary Table
        pageManager.canvas.drawText("Surveillance Registry (Recent Shared Holdings)", MARGIN_LEFT, pageManager.cursorY, sectionTitlePaint)
        pageManager.cursorY += 15f

        val tableHeaderPaint = Paint().apply {
            color = 0xFFECEFF1.toInt()
            isAntiAlias = true
        }
        pageManager.canvas.drawRect(MARGIN_LEFT, pageManager.cursorY, PAGE_WIDTH - MARGIN_RIGHT, pageManager.cursorY + 18f, tableHeaderPaint)

        val thTextPaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 8.5f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        pageManager.canvas.drawText("Share ID", MARGIN_LEFT + 5f, pageManager.cursorY + 13f, thTextPaint)
        pageManager.canvas.drawText("Diagnosis", MARGIN_LEFT + 85f, pageManager.cursorY + 13f, thTextPaint)
        pageManager.canvas.drawText("Severity", MARGIN_LEFT + 260f, pageManager.cursorY + 13f, thTextPaint)
        pageManager.canvas.drawText("Risk", MARGIN_LEFT + 340f, pageManager.cursorY + 13f, thTextPaint)
        pageManager.canvas.drawText("Date", MARGIN_LEFT + 410f, pageManager.cursorY + 13f, thTextPaint)
        pageManager.cursorY += 22f

        val rowPaint = Paint().apply {
            color = COLOR_TEXT_DARK
            textSize = 8f
            isAntiAlias = true
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }

        for (c in cases.take(15)) {
            val summary = c.caseSummary
            val diag = (summary["primary_diagnosis"] as? String ?: "Unknown").replace("Tomato___", "").replace("_", " ")
            val sev = (summary["assigned_severity"] as? String ?: "-").uppercase()
            val rsk = (summary["epidemic_risk"] as? String ?: "-").uppercase()
            val dt = if (c.createdAt.length >= 10) c.createdAt.take(10) else c.createdAt

            pageManager.canvas.drawText(c.shareId.take(12), MARGIN_LEFT + 5f, pageManager.cursorY, rowPaint)
            pageManager.canvas.drawText(diag.take(28), MARGIN_LEFT + 85f, pageManager.cursorY, rowPaint)
            pageManager.canvas.drawText(sev, MARGIN_LEFT + 260f, pageManager.cursorY, rowPaint)
            pageManager.canvas.drawText(rsk, MARGIN_LEFT + 340f, pageManager.cursorY, rowPaint)
            pageManager.canvas.drawText(dt, MARGIN_LEFT + 410f, pageManager.cursorY, rowPaint)
            pageManager.cursorY += 15f
        }

        pageManager.finish()

        val reportsDir = File(context.cacheDir, "reports").apply { mkdirs() }
        val outputFile = File(reportsDir, "AgriMind_Cooperative_Report_${System.currentTimeMillis()}.pdf")
        FileOutputStream(outputFile).use { out ->
            document.writeTo(out)
        }
        document.close()
        return outputFile
    }

    /**
     * Creates an Android ACTION_SEND Intent for sharing the generated PDF.
     */
    fun createShareIntent(file: File): Intent {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        return Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, "AgriMind Crop-Health Diagnostic Report - ${file.nameWithoutExtension}")
            putExtra(Intent.EXTRA_TEXT, "Attached is the AgriMind AI crop-health diagnostic evaluation report.")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
    }

    /**
     * Creates an Android ACTION_VIEW Intent for opening the generated PDF.
     */
    fun createViewIntent(file: File): Intent {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        return Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/pdf")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }
}
