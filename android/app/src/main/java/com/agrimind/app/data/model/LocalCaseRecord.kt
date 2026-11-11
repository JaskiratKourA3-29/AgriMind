package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Local device persistence model for an AgriMind diagnostic case.
 * Stores original diagnosis response, image references, and reassessment history.
 */
data class LocalCaseRecord(
    @SerializedName("case_id")
    val caseId: String,

    @SerializedName("created_at_iso")
    val createdAtIso: String,

    @SerializedName("primary_diagnosis")
    val primaryDiagnosis: String,

    @SerializedName("diagnosis_confidence")
    val diagnosisConfidence: Float,

    @SerializedName("assigned_severity")
    val assignedSeverity: String,

    @SerializedName("epidemic_risk")
    val epidemicRisk: String,

    @SerializedName("plan_urgency")
    val planUrgency: String?,

    @SerializedName("is_verified")
    val isVerified: Boolean,

    @SerializedName("image_uri_string")
    val imageUriString: String?,

    @SerializedName("image_file_name")
    val imageFileName: String?,

    @SerializedName("initial_diagnosis")
    val initialDiagnosis: DiagnosisResponse,

    @SerializedName("latest_reassessment")
    val latestReassessment: ReassessmentResponse? = null,

    @SerializedName("reassessment_count")
    val reassessmentCount: Int = 0,

    @SerializedName("reassessment_history")
    val reassessmentHistory: List<ReassessmentResponse> = emptyList()
) {
    /**
     * Active disease prediction (revised if reassessed, otherwise initial).
     */
    val activeDiagnosis: String
        get() = latestReassessment?.primaryDiagnosis ?: primaryDiagnosis

    /**
     * Active confidence score (revised if reassessed, otherwise initial).
     */
    val activeConfidence: Float
        get() = latestReassessment?.diagnosisConfidence ?: diagnosisConfidence

    /**
     * Active severity (revised if reassessed, otherwise initial).
     */
    val activeSeverity: String
        get() = latestReassessment?.assignedSeverity ?: assignedSeverity

    /**
     * Active epidemic risk (revised if reassessed, otherwise initial).
     */
    val activeEpidemicRisk: String
        get() = latestReassessment?.epidemicRisk ?: epidemicRisk

    /**
     * Active IPM management plan.
     */
    val activeManagementPlan: ManagementPlanResponse?
        get() = latestReassessment?.managementPlan ?: initialDiagnosis.managementPlan
}

