package com.agrimind.app.data.model

import com.google.gson.annotations.SerializedName

data class LiveWeatherData(
    @SerializedName("latitude") val latitude: Double,
    @SerializedName("longitude") val longitude: Double,
    @SerializedName("temperature_c") val temperatureC: Double,
    @SerializedName("relative_humidity_pct") val relativeHumidityPct: Double,
    @SerializedName("precipitation_mm") val precipitationMm: Double,
    @SerializedName("wind_speed_kmh") val windSpeedKmh: Double,
    @SerializedName("weather_code") val weatherCode: Int,
    @SerializedName("condition_summary") val conditionSummary: String,
    @SerializedName("rain_forecast_24h_mm") val rainForecast24hMm: Double,
    @SerializedName("is_live") val isLive: Boolean,
    @SerializedName("source") val source: String,
    @SerializedName("timestamp") val timestamp: String
)

data class CaseShareRequest(
    @SerializedName("case_id") val caseId: String,
    @SerializedName("owner_farmer_id") val ownerFarmerId: String = "farmer_local",
    @SerializedName("target_entity") val targetEntity: String = "cooperative_all",
    @SerializedName("access_level") val accessLevel: String = "cooperative",
    @SerializedName("anonymize_pii") val anonymizePii: Boolean = true,
    @SerializedName("notes") val notes: String? = null
)

data class CaseShareResponse(
    @SerializedName("share_id") val shareId: String,
    @SerializedName("case_id") val caseId: String,
    @SerializedName("owner_farmer_id") val ownerFarmerId: String,
    @SerializedName("target_entity") val targetEntity: String,
    @SerializedName("access_level") val accessLevel: String,
    @SerializedName("share_token") val shareToken: String,
    @SerializedName("anonymize_pii") val anonymizePii: Boolean,
    @SerializedName("notes") val notes: String?,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("status") val status: String
)

data class SharedCaseSummary(
    @SerializedName("share_id") val shareId: String,
    @SerializedName("case_id") val caseId: String,
    @SerializedName("target_entity") val targetEntity: String,
    @SerializedName("access_level") val accessLevel: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("notes") val notes: String?,
    @SerializedName("case_summary") val caseSummary: Map<String, Any?>
)

data class DiseaseDistributionStats(
    @SerializedName("count") val count: Int,
    @SerializedName("percentage") val percentage: Double
)

data class CooperativeInsightsData(
    @SerializedName("region") val region: String,
    @SerializedName("total_cases_analyzed") val totalCasesAnalyzed: Int,
    @SerializedName("disease_distribution") val diseaseDistribution: Map<String, DiseaseDistributionStats>?,
    @SerializedName("severity_distribution") val severityDistribution: Map<String, Int>?,
    @SerializedName("risk_level_distribution") val riskLevelDistribution: Map<String, Int>?,
    @SerializedName("dominant_pathogen") val dominantPathogen: String?,
    @SerializedName("regional_risk_level") val regionalRiskLevel: String,
    @SerializedName("outbreak_alerts") val outbreakAlerts: List<String>?,
    @SerializedName("collective_ipm_actions") val collectiveIpmActions: List<String>?,
    @SerializedName("generated_at") val generatedAt: String
)

data class QueuedAction(
    val id: Long = 0,
    val actionType: String, // "DIAGNOSE", "SHARE"
    val payloadJson: String,
    val localImageUri: String?,
    val status: String,     // "PENDING", "SYNCED", "FAILED"
    val createdAt: String
)

data class CaseComment(
    @SerializedName("comment_id") val commentId: String,
    @SerializedName("case_id") val caseId: String,
    @SerializedName("author_id") val authorId: String,
    @SerializedName("author_role") val authorRole: String,
    @SerializedName("comment_text") val commentText: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("is_ai") val isAi: Boolean
)

data class CaseCommentCreate(
    @SerializedName("author_id") val authorId: String = "farmer_local",
    @SerializedName("comment_text") val commentText: String,
    @SerializedName("author_role") val authorRole: String = "farmer",
    @SerializedName("is_ai") val isAi: Boolean = false
)

data class CaseOutcome(
    @SerializedName("case_id") val caseId: String,
    @SerializedName("farmer_id") val farmerId: String,
    @SerializedName("outcome") val outcome: String,
    @SerializedName("details") val details: String?,
    @SerializedName("updated_at") val updatedAt: String
)

data class CaseOutcomeCreate(
    @SerializedName("farmer_id") val farmerId: String = "farmer_local",
    @SerializedName("outcome") val outcome: String,
    @SerializedName("details") val details: String? = null
)

data class CooperativeComparisonRegion(
    @SerializedName("region_name") val regionName: String,
    @SerializedName("cooperative_id") val cooperativeId: String,
    @SerializedName("is_local_pilot") val isLocalPilot: Boolean,
    @SerializedName("data_status") val dataStatus: String,
    @SerializedName("total_cases") val totalCases: Int,
    @SerializedName("dominant_pathogen") val dominantPathogen: String,
    @SerializedName("regional_risk_level") val regionalRiskLevel: String,
    @SerializedName("outbreak_alerts") val outbreakAlerts: List<String>?,
    @SerializedName("disease_distribution") val diseaseDistribution: Map<String, DiseaseDistributionStats>?
)

data class CooperativeComparisonResponse(
    @SerializedName("generated_at") val generatedAt: String,
    @SerializedName("is_live_partnership") val isLivePartnership: Boolean,
    @SerializedName("disclaimer") val disclaimer: String,
    @SerializedName("regions") val regions: List<CooperativeComparisonRegion>
)

