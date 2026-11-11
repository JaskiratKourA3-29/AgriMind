package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

/**
 * Data models matching the FastAPI POST /diagnose response schema.
 */
data class DiagnosisResponse(
    @SerializedName("case_id")
    val caseId: String,

    @SerializedName("workflow_status")
    val workflowStatus: String,

    @SerializedName("primary_diagnosis")
    val primaryDiagnosis: String?,

    @SerializedName("diagnosis_confidence")
    val diagnosisConfidence: Float?,

    @SerializedName("class_probabilities")
    val classProbabilities: Map<String, Float>?,

    @SerializedName("assigned_severity")
    val assignedSeverity: String?,

    @SerializedName("epidemic_risk")
    val epidemicRisk: String?,

    @SerializedName("plan_urgency")
    val planUrgency: String?,

    @SerializedName("is_verified")
    val isVerified: Boolean,

    @SerializedName("verification_status")
    val verificationStatus: String?,

    @SerializedName("requires_manual_review")
    val requiresManualReview: Boolean,

    @SerializedName("manual_review_status")
    val manualReviewStatus: String?,

    @SerializedName("management_plan")
    val managementPlan: ManagementPlanResponse?,

    @SerializedName("citations")
    val citations: List<CitationItem>?,

    @SerializedName("pesticide_safety_notice")
    val pesticideSafetyNotice: String?,

    @SerializedName("error_message")
    val errorMessage: String?,

    @SerializedName("is_low_confidence")
    val isLowConfidence: Boolean = false,

    @SerializedName("low_confidence_guidance")
    val lowConfidenceGuidance: String? = null,

    @SerializedName("latency_breakdown")
    val latencyBreakdown: LatencyBreakdown?
)

data class ManagementPlanResponse(
    @SerializedName("plan_id")
    val planId: String?,

    @SerializedName("disease")
    val disease: String?,

    @SerializedName("urgency")
    val urgency: String?,

    @SerializedName("cultural_controls")
    val culturalControls: List<ManagementActionResponse>?,

    @SerializedName("resistant_varieties")
    val resistantVarieties: List<ManagementActionResponse>?,

    @SerializedName("chemical_controls")
    val chemicalControls: List<ManagementActionResponse>?,

    @SerializedName("monitoring_actions")
    val monitoringActions: List<ManagementActionResponse>?,

    @SerializedName("uncertainty_disclosures")
    val uncertaintyDisclosures: List<String>?,

    @SerializedName("pesticide_safety_notice")
    val pesticideSafetyNotice: String?
)

data class ManagementActionResponse(
    @SerializedName("category")
    val category: String,

    @SerializedName("action_summary")
    val actionSummary: String,

    @SerializedName("details")
    val details: String,

    @SerializedName("is_chemical")
    val isChemical: Boolean,

    @SerializedName("citation_numbers")
    val citationNumbers: List<Int>?
)

data class CitationItem(
    @SerializedName("citation_number")
    val citationNumber: Int,

    @SerializedName("doc_id")
    val docId: String?,

    @SerializedName("title")
    val title: String?,

    @SerializedName("institution")
    val institution: String?,

    @SerializedName("source_url")
    val sourceUrl: String?,

    @SerializedName("chunk_id")
    val chunkId: String?,

    @SerializedName("similarity_score")
    val similarityScore: Float?
)

data class LatencyBreakdown(
    @SerializedName("model_inference_ms")
    val modelInferenceMs: Float?,

    @SerializedName("total_workflow_ms")
    val totalWorkflowMs: Float
)

