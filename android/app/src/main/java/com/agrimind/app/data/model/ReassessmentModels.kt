package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Request payload for adaptive case reassessment (POST /reassess).
 */
data class ReassessmentRequest(
    @SerializedName("case_id")
    val caseId: String,

    @SerializedName("trigger")
    val trigger: String,

    @SerializedName("new_evidence")
    val newEvidence: Map<String, Any>,

    @SerializedName("rationale")
    val rationale: String? = null,

    @SerializedName("completed_state")
    val completedState: Map<String, Any>? = null
)

/**
 * Response payload returned by adaptive case reassessment (POST /reassess).
 */
data class ReassessmentResponse(
    @SerializedName("case_id")
    val caseId: String,

    @SerializedName("workflow_status")
    val workflowStatus: String,

    @SerializedName("reassessment_outcome")
    val reassessmentOutcome: String?,

    @SerializedName("reassessment_count")
    val reassessmentCount: Int = 1,

    @SerializedName("max_reassessments")
    val maxReassessments: Int = 2,

    @SerializedName("primary_diagnosis")
    val primaryDiagnosis: String?,

    @SerializedName("diagnosis_confidence")
    val diagnosisConfidence: Float?,

    @SerializedName("assigned_severity")
    val assignedSeverity: String?,

    @SerializedName("epidemic_risk")
    val epidemicRisk: String?,

    @SerializedName("plan_urgency")
    val planUrgency: String?,

    @SerializedName("is_verified")
    val isVerified: Boolean = false,

    @SerializedName("verification_status")
    val verificationStatus: String?,

    @SerializedName("requires_manual_review")
    val requiresManualReview: Boolean = false,

    @SerializedName("management_plan")
    val managementPlan: ManagementPlanResponse?,

    @SerializedName("citations")
    val citations: List<CitationItem>?,

    @SerializedName("pesticide_safety_notice")
    val pesticideSafetyNotice: String?,

    @SerializedName("reassessment_records")
    val reassessmentRecords: List<ReassessmentRecordItem>?,

    @SerializedName("case_history_length")
    val caseHistoryLength: Int = 0,

    @SerializedName("error_message")
    val errorMessage: String?,

    @SerializedName("latency_breakdown")
    val latencyBreakdown: LatencyBreakdown?,

    @SerializedName("completed_state")
    val completedState: Map<String, Any>? = null
)

/**
 * Individual audit record of a prior or current reassessment cycle.
 */
data class ReassessmentRecordItem(
    @SerializedName("reassessment_id")
    val reassessmentId: String?,

    @SerializedName("case_id")
    val caseId: String?,

    @SerializedName("reassessment_count")
    val reassessmentCount: Int?,

    @SerializedName("max_reassessments")
    val maxReassessments: Int?,

    @SerializedName("trigger")
    val trigger: String?,

    @SerializedName("trigger_rationale")
    val triggerRationale: String?,

    @SerializedName("new_evidence")
    val newEvidence: Map<String, Any>?,

    @SerializedName("prior_severity")
    val priorSeverity: String?,

    @SerializedName("revised_severity")
    val revisedSeverity: String?,

    @SerializedName("prior_urgency")
    val priorUrgency: String?,

    @SerializedName("revised_urgency")
    val revisedUrgency: String?,

    @SerializedName("prior_diagnosis")
    val priorDiagnosis: String?,

    @SerializedName("revised_diagnosis")
    val revisedDiagnosis: String?,

    @SerializedName("outcome")
    val outcome: String?,

    @SerializedName("is_terminal")
    val isTerminal: Boolean?,

    @SerializedName("notes")
    val notes: String?,

    @SerializedName("timestamp")
    val timestamp: String?
)

/**
 * Verified reassessment triggers matching backend ReassessmentTrigger enum.
 */
object ReassessmentTriggers {
    const val NEW_FIELD_OBSERVATION = "new_field_observation"
    const val WEATHER_UPDATE = "weather_update"
    const val TREATMENT_INEFFECTIVE = "treatment_ineffective"
    const val LAB_DIAGNOSTIC_UPDATE = "lab_diagnostic_update"

    val ALL = listOf(
        NEW_FIELD_OBSERVATION to "New Field Observation",
        WEATHER_UPDATE to "Weather Update",
        TREATMENT_INEFFECTIVE to "Treatment Ineffective",
        LAB_DIAGNOSTIC_UPDATE to "Lab Diagnostic Update"
    )
}

