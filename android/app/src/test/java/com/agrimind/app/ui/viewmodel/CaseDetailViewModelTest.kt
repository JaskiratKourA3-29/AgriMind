package com.agrimind.app.ui.viewmodel

import android.app.Application
import com.agrimind.app.data.model.DiagnosisResponse
import com.agrimind.app.data.model.LocalCaseRecord
import com.agrimind.app.data.model.ReassessmentRecordItem
import com.agrimind.app.data.model.ReassessmentResponse
import com.agrimind.app.data.model.ReassessmentTriggers
import com.agrimind.app.ui.screens.formatTimelineTimestamp
import com.agrimind.app.ui.screens.formatTriggerLabel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for CaseDetailViewModel and Reassessment History Timeline data models (Stage C.3).
 */
@OptIn(ExperimentalCoroutinesApi::class)
class CaseDetailViewModelTest {

    private lateinit var viewModel: CaseDetailViewModel
    private lateinit var app: Application

    @Before
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
        app = Application()
        viewModel = CaseDetailViewModel(app)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun testInitialState_isIdle() {
        assertNull(viewModel.activeCase.value)
        assertTrue(viewModel.reassessmentState.value is ReassessmentState.Idle)
        assertTrue(viewModel.pdfExportState.value is PdfExportState.Idle)
    }

    @Test
    fun testSetCase_updatesActiveCase() {
        val dummyRecord = createDummyCase(
            caseId = "CASE-TEST-001",
            reassessmentCount = 0
        )
        viewModel.setCase(dummyRecord)

        assertEquals("CASE-TEST-001", viewModel.activeCase.value?.caseId)
        assertEquals("Tomato___Early_blight", viewModel.activeCase.value?.primaryDiagnosis)
        assertTrue(viewModel.reassessmentState.value is ReassessmentState.Idle)
    }

    @Test
    fun testResetStates_revertsToIdle() {
        viewModel.resetReassessmentState()
        assertTrue(viewModel.reassessmentState.value is ReassessmentState.Idle)

        viewModel.resetPdfExportState()
        assertTrue(viewModel.pdfExportState.value is PdfExportState.Idle)
    }

    @Test
    fun testFormatTriggerLabel_mapsKnownAndUnknownTriggers() {
        assertEquals("Weather Update", formatTriggerLabel(ReassessmentTriggers.WEATHER_UPDATE))
        assertEquals("New Field Observation", formatTriggerLabel(ReassessmentTriggers.NEW_FIELD_OBSERVATION))
        assertEquals("Treatment Ineffective", formatTriggerLabel(ReassessmentTriggers.TREATMENT_INEFFECTIVE))
        assertEquals("Lab Diagnostic Update", formatTriggerLabel(ReassessmentTriggers.LAB_DIAGNOSTIC_UPDATE))

        // Null / blank fallback
        assertEquals("Field Evidence Update", formatTriggerLabel(null))
        assertEquals("Field Evidence Update", formatTriggerLabel("   "))

        // Custom snake_case formatting
        assertEquals("Severe canopy wilt", formatTriggerLabel("severe_canopy_wilt"))
    }

    @Test
    fun testFormatTimelineTimestamp_formatsIsoDatesCleanly() {
        val isoUtc = "2026-11-02T14:49:06Z"
        val formatted = formatTimelineTimestamp(isoUtc)
        assertTrue(formatted.contains("Nov 2, 2026"))

        // Null / blank fallback
        assertEquals("Timestamp not recorded", formatTimelineTimestamp(null))
        assertEquals("Timestamp not recorded", formatTimelineTimestamp("  "))

        // Malformed fallback preserves string
        val malformed = "not-a-valid-date"
        assertEquals("not-a-valid-date", formatTimelineTimestamp(malformed))
    }

    @Test
    fun testTimelineEmptyHistory_preservesBaselineIntegrity() {
        val caseRecord = createDummyCase(
            caseId = "CASE-EMPTY-001",
            reassessmentCount = 0
        )

        assertEquals(0, caseRecord.reassessmentCount)
        assertTrue(caseRecord.reassessmentHistory.isEmpty())
        assertNull(caseRecord.latestReassessment)
        assertEquals("Tomato___Early_blight", caseRecord.activeDiagnosis)
        assertEquals("moderate", caseRecord.activeSeverity)
        assertEquals("low", caseRecord.activeEpidemicRisk)
    }

    @Test
    fun testTimelineMultiCycleReassessment_preservesChronologicalEvolution() {
        val cycle1Audit = ReassessmentRecordItem(
            reassessmentId = "REA-001",
            caseId = "CASE-MULTI-001",
            reassessmentCount = 1,
            maxReassessments = 2,
            trigger = ReassessmentTriggers.WEATHER_UPDATE,
            triggerRationale = "Continuous rainfall observed",
            newEvidence = mapOf("weather_conditions" to "rain"),
            priorSeverity = "moderate",
            revisedSeverity = "severe",
            priorUrgency = "medium",
            revisedUrgency = "high",
            priorDiagnosis = "Tomato___Early_blight",
            revisedDiagnosis = "Tomato___Late_blight",
            outcome = "revised",
            isTerminal = false,
            notes = "Epidemic weather alert",
            timestamp = "2026-11-02T15:00:00Z"
        )

        val cycle1 = ReassessmentResponse(
            caseId = "CASE-MULTI-001",
            workflowStatus = "completed",
            reassessmentOutcome = "revised",
            reassessmentCount = 1,
            maxReassessments = 2,
            primaryDiagnosis = "Tomato___Late_blight",
            diagnosisConfidence = 0.98f,
            assignedSeverity = "severe",
            epidemicRisk = "high",
            planUrgency = "high",
            isVerified = true,
            verificationStatus = "verified",
            requiresManualReview = false,
            managementPlan = null,
            citations = emptyList(),
            pesticideSafetyNotice = null,
            reassessmentRecords = listOf(cycle1Audit),
            caseHistoryLength = 1,
            errorMessage = null,
            latencyBreakdown = null
        )

        val cycle2Audit = ReassessmentRecordItem(
            reassessmentId = "REA-002",
            caseId = "CASE-MULTI-001",
            reassessmentCount = 2,
            maxReassessments = 2,
            trigger = ReassessmentTriggers.TREATMENT_INEFFECTIVE,
            triggerRationale = "Foliar damage increased to 50%",
            newEvidence = mapOf("leaf_damage_percentage" to 50),
            priorSeverity = "severe",
            revisedSeverity = "critical",
            priorUrgency = "high",
            revisedUrgency = "critical",
            priorDiagnosis = "Tomato___Late_blight",
            revisedDiagnosis = "Tomato___Late_blight",
            outcome = "escalated",
            isTerminal = true,
            notes = "Emergency rogueing required",
            timestamp = "2026-11-02T16:00:00Z"
        )

        val cycle2 = ReassessmentResponse(
            caseId = "CASE-MULTI-001",
            workflowStatus = "completed",
            reassessmentOutcome = "escalated",
            reassessmentCount = 2,
            maxReassessments = 2,
            primaryDiagnosis = "Tomato___Late_blight",
            diagnosisConfidence = 0.99f,
            assignedSeverity = "critical",
            epidemicRisk = "critical",
            planUrgency = "critical",
            isVerified = true,
            verificationStatus = "verified",
            requiresManualReview = true,
            managementPlan = null,
            citations = emptyList(),
            pesticideSafetyNotice = null,
            reassessmentRecords = listOf(cycle2Audit),
            caseHistoryLength = 2,
            errorMessage = null,
            latencyBreakdown = null
        )

        val multiCycleCase = createDummyCase(
            caseId = "CASE-MULTI-001",
            reassessmentCount = 2
        ).copy(
            latestReassessment = cycle2,
            reassessmentHistory = listOf(cycle1, cycle2)
        )

        assertEquals(2, multiCycleCase.reassessmentCount)
        assertEquals(2, multiCycleCase.reassessmentHistory.size)
        assertEquals("Tomato___Late_blight", multiCycleCase.activeDiagnosis)
        assertEquals("critical", multiCycleCase.activeSeverity)
        assertEquals("critical", multiCycleCase.activeEpidemicRisk)

        // Verify Cycle 1 progression
        val c1 = multiCycleCase.reassessmentHistory[0]
        assertEquals(1, c1.reassessmentCount)
        assertEquals("revised", c1.reassessmentOutcome)
        assertEquals("severe", c1.assignedSeverity)
        assertEquals(ReassessmentTriggers.WEATHER_UPDATE, c1.reassessmentRecords?.first()?.trigger)
        assertEquals("moderate", c1.reassessmentRecords?.first()?.priorSeverity)

        // Verify Cycle 2 progression
        val c2 = multiCycleCase.reassessmentHistory[1]
        assertEquals(2, c2.reassessmentCount)
        assertEquals("escalated", c2.reassessmentOutcome)
        assertEquals("critical", c2.assignedSeverity)
        assertEquals(ReassessmentTriggers.TREATMENT_INEFFECTIVE, c2.reassessmentRecords?.first()?.trigger)
        assertEquals("severe", c2.reassessmentRecords?.first()?.priorSeverity)
    }

    private fun createDummyCase(
        caseId: String,
        reassessmentCount: Int
    ): LocalCaseRecord {
        val dummyInitial = DiagnosisResponse(
            caseId = caseId,
            workflowStatus = "completed",
            primaryDiagnosis = "Tomato___Early_blight",
            diagnosisConfidence = 0.94f,
            classProbabilities = mapOf(
                "Tomato___Bacterial_spot" to 0.02f,
                "Tomato___Early_blight" to 0.94f,
                "Tomato___Late_blight" to 0.04f
            ),
            assignedSeverity = "moderate",
            epidemicRisk = "low",
            planUrgency = "medium",
            isVerified = true,
            verificationStatus = "verified",
            requiresManualReview = false,
            manualReviewStatus = null,
            managementPlan = null,
            citations = emptyList(),
            pesticideSafetyNotice = null,
            errorMessage = null,
            latencyBreakdown = null
        )

        return LocalCaseRecord(
            caseId = caseId,
            createdAtIso = "2026-11-02T14:49:06Z",
            primaryDiagnosis = "Tomato___Early_blight",
            diagnosisConfidence = 0.94f,
            assignedSeverity = "moderate",
            epidemicRisk = "low",
            planUrgency = "medium",
            isVerified = true,
            imageUriString = null,
            imageFileName = null,
            initialDiagnosis = dummyInitial,
            latestReassessment = null,
            reassessmentCount = reassessmentCount,
            reassessmentHistory = emptyList()
        )
    }
}

