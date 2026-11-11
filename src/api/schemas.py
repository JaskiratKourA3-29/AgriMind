"""
AgriMind API Pydantic Schemas (Stage A).
Defines strongly typed request/response contracts for FastAPI endpoints,
isolating API clients from internal LangGraph workflow state dicts.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class HealthResponse(BaseModel):
    """System health check and component availability status."""
    status: str = Field(description="Operational status: 'healthy' or 'degraded'")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of health check")
    version: str = Field(default="1.0.0", description="AgriMind API version")
    models_available: Dict[str, bool] = Field(description="Availability of core ML and RAG models")
    rag_chunks: int = Field(description="Number of indexed agricultural literature chunks")
    active_classes: List[str] = Field(description="Supported crop disease classes")
    device: str = Field(default="cpu", description="Active PyTorch compute device")

    model_config = ConfigDict(extra="ignore")


class VisualContextInput(BaseModel):
    """User-supplied canopy and field observations."""
    leaf_damage_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Estimated percentage of leaf area exhibiting symptoms"
    )
    affected_organs: List[str] = Field(
        default_factory=lambda: ["leaves"],
        description="Organs exhibiting visible symptoms (leaves, stems, fruit)"
    )
    canopy_spread: Optional[str] = Field(
        default=None,
        description="Spread within canopy: 'lower_canopy', 'mid_canopy', 'upper_canopy', 'whole_plant', 'field_scale'"
    )
    weather_conditions: Optional[str] = Field(
        default=None,
        description="Recent ambient weather (e.g. 'cool_wet', 'warm_humid', 'hot_dry', 'prolonged_leaf_wetness')"
    )
    field_notes: Optional[str] = Field(
        default=None,
        description="Free-text field observations or scouting notes"
    )

    model_config = ConfigDict(extra="ignore")


class ManagementActionResponse(BaseModel):
    """Structured individual agronomic management recommendation."""
    category: str = Field(description="Control category: cultural, resistant_variety, chemical, monitoring")
    action_summary: str = Field(description="Concise description of the action")
    details: str = Field(description="Detailed application or execution guidance")
    is_chemical: bool = Field(default=False, description="Whether this recommendation involves chemical application")
    citation_numbers: List[int] = Field(default_factory=list, description="Grounding reference citation numbers")

    model_config = ConfigDict(extra="ignore")


class ManagementPlanResponse(BaseModel):
    """Complete agronomic decision plan organized along the IPM hierarchy."""
    plan_id: Optional[str] = None
    disease: Optional[str] = None
    urgency: Optional[str] = Field(default=None, description="Urgency: low, moderate, high, critical, deferred")
    cultural_controls: List[ManagementActionResponse] = Field(default_factory=list)
    resistant_varieties: List[ManagementActionResponse] = Field(default_factory=list)
    chemical_controls: List[ManagementActionResponse] = Field(default_factory=list)
    monitoring_actions: List[ManagementActionResponse] = Field(default_factory=list)
    uncertainty_disclosures: List[str] = Field(default_factory=list)
    pesticide_safety_notice: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class LatencyBreakdown(BaseModel):
    """High-resolution latency measurements for performance profiling."""
    model_inference_ms: Optional[float] = Field(
        default=None,
        description="Time taken by ResNet-50 vision inference in milliseconds"
    )
    total_workflow_ms: float = Field(
        description="Total round-trip workflow execution time in milliseconds"
    )

    model_config = ConfigDict(extra="ignore")


class DiagnosisResponse(BaseModel):
    """Comprehensive diagnostic response from the multi-agent workflow."""
    case_id: str = Field(description="Unique case identifier")
    workflow_status: str = Field(description="Final workflow status (e.g. completed, pending_manual_review, error)")
    primary_diagnosis: Optional[str] = Field(default=None, description="Predicted disease class")
    diagnosis_confidence: Optional[float] = Field(default=None, description="Diagnostic confidence score (0.0 - 1.0)")
    class_probabilities: Optional[Dict[str, float]] = Field(default=None, description="Softmax probabilities across classes")
    assigned_severity: Optional[str] = Field(default=None, description="Assigned severity level (low, moderate, high, critical)")
    epidemic_risk: Optional[str] = Field(default=None, description="Assessed epidemic transmission risk")
    plan_urgency: Optional[str] = Field(default=None, description="Recommended management response urgency")
    is_verified: bool = Field(default=False, description="Whether plan passed Critic Agent verification")
    verification_status: Optional[str] = Field(default=None, description="Detailed Critic Agent verification status")
    requires_manual_review: bool = Field(default=False, description="Whether case requires agricultural expert review")
    manual_review_status: Optional[str] = Field(default=None, description="Status of expert review (pending, approved, etc.)")
    management_plan: Optional[ManagementPlanResponse] = Field(default=None, description="Grounded IPM management plan")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Authoritative university extension citations")
    pesticide_safety_notice: Optional[str] = Field(default=None, description="Mandatory regulatory pesticide disclaimer")
    error_message: Optional[str] = Field(default=None, description="Error message if workflow failed")
    is_low_confidence: bool = Field(default=False, description="Whether diagnostic confidence falls below verified threshold (0.65)")
    low_confidence_guidance: Optional[str] = Field(default=None, description="Clear farmer instructions for retaking image or seeking manual expert review")
    latency_breakdown: LatencyBreakdown = Field(description="Measured latency breakdown")
    raw_state: Optional[Dict[str, Any]] = Field(default=None, description="Serializable workflow state for case continuity")

    model_config = ConfigDict(extra="ignore")


class ReassessmentRequest(BaseModel):
    """Payload for adaptive case reassessment."""
    case_id: str = Field(description="Case ID to re-evaluate")
    trigger: str = Field(description="Valid ReassessmentTrigger enum value")
    new_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Newly observed agricultural evidence (e.g. weather conditions, updated damage %, lab result)"
    )
    rationale: Optional[str] = Field(default=None, description="Contextual explanation for reassessment")
    completed_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Deprecated/Ignored: Server retrieves authoritative state from internal CaseStore."
    )

    model_config = ConfigDict(extra="ignore")


class ReassessmentResponse(BaseModel):
    """Outcome of adaptive case reassessment."""
    case_id: str = Field(description="Case identifier")
    workflow_status: str = Field(description="Final workflow status after reassessment")
    reassessment_outcome: Optional[str] = Field(default=None, description="Outcome: revised, unresolved, escalated")
    reassessment_count: int = Field(default=1, description="Number of reassessment cycles executed for this case")
    max_reassessments: int = Field(default=2, description="Upper bound on allowable reassessments per case")
    primary_diagnosis: Optional[str] = Field(default=None, description="Updated or preserved primary diagnosis")
    diagnosis_confidence: Optional[float] = Field(default=None, description="Updated or preserved diagnosis confidence")
    assigned_severity: Optional[str] = Field(default=None, description="Updated or preserved severity level")
    epidemic_risk: Optional[str] = Field(default=None, description="Updated or preserved epidemic risk")
    plan_urgency: Optional[str] = Field(default=None, description="Updated or preserved plan urgency")
    is_verified: bool = Field(default=False, description="Whether revised plan passed Critic verification")
    verification_status: Optional[str] = Field(default=None, description="Critic verification status")
    requires_manual_review: bool = Field(default=False, description="Whether revised case requires expert review")
    management_plan: Optional[ManagementPlanResponse] = Field(default=None, description="Updated IPM decision plan")
    citations: List[Dict[str, Any]] = Field(default_factory=list, description="Grounding literature citations")
    pesticide_safety_notice: Optional[str] = Field(default=None, description="Mandatory pesticide disclaimer")
    reassessment_records: List[Dict[str, Any]] = Field(default_factory=list, description="Audit log of all reassessment iterations")
    case_history_length: int = Field(default=0, description="Number of historical snapshots preserved")
    error_message: Optional[str] = Field(default=None, description="Error details if reassessment encountered failure")
    latency_breakdown: LatencyBreakdown = Field(description="Measured latency breakdown for reassessment cycle")
    completed_state: Optional[Dict[str, Any]] = Field(default=None, description="Serializable workflow state after reassessment")

    model_config = ConfigDict(extra="ignore")


# =====================================================================
# Conversational AI & Decision Support Schemas
# =====================================================================

class MessageRole(str, Enum):
    """Supported conversational message roles for chat."""
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """A single turn in conversational dialogue."""
    role: MessageRole = Field(description="Role of the speaker: 'user' or 'assistant'")
    content: str = Field(
        min_length=1,
        max_length=2000,
        description="Message text content (max 2000 chars)"
    )

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty or whitespace-only.")
        return v.strip()

    model_config = ConfigDict(extra="forbid")


class CitationItem(BaseModel):
    """Authoritative university extension publication citation metadata."""
    citation_number: int = Field(description="Sequential citation reference number [1], [2], etc.")
    doc_id: str = Field(description="Unique document identifier (e.g. DOC-CORNELL-001)")
    title: str = Field(description="Publication or extension bulletin title")
    institution: str = Field(description="Publishing university or extension service")
    source_url: str = Field(description="Direct URL to official publication")
    chunk_id: Optional[str] = Field(default=None, description="Specific chunk identifier")
    similarity_score: Optional[float] = Field(default=None, description="Cosine relevance similarity score")

    model_config = ConfigDict(extra="ignore")


class ChatRequest(BaseModel):
    """Payload for conversational question-answering."""
    query: str = Field(
        min_length=1,
        max_length=1000,
        description="User question about tomato disease management (max 1000 chars)"
    )
    case_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional case identifier to anchor retrieval and advice to prior diagnosis"
    )
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        max_length=10,
        description="Optional prior dialogue turns for conversational context (max 10 messages)"
    )
    language: str = Field(
        default="en",
        description="User language preference: 'en' (English), 'hi' (Hindi), or 'doi' (Dogri)"
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only.")
        return v.strip()

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            return clean if clean else None
        return None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> str:
        if not v or not v.strip():
            return "en"
        code = v.strip().lower()
        if code not in ["en", "hi", "doi"]:
            raise ValueError(f"Unsupported language code '{v}'. Supported languages are 'en', 'hi', and 'doi'.")
        return code

    model_config = ConfigDict(extra="forbid")


class ChatResponse(BaseModel):
    """Evidence-grounded agronomic conversational response."""
    query: str = Field(description="Original user question")
    answer: str = Field(description="Evidence-grounded agronomic recommendation")
    citations: List[CitationItem] = Field(
        default_factory=list,
        description="Authoritative university extension citations supporting the answer"
    )
    has_sufficient_evidence: bool = Field(
        description="Whether retrieved evidence met the calibrated confidence threshold"
    )
    generation_mode: str = Field(
        description="Synthesis mode: 'gemini_llm', 'grounded_extractive', 'grounded_extractive_fallback', or 'insufficient_evidence_fallback'"
    )
    case_id: Optional[str] = Field(
        default=None,
        description="Linked case ID if query was contextualized to a diagnosis"
    )
    disease_target: Optional[str] = Field(
        default=None,
        description="Filtered tomato disease target applied to retrieval (if linked to case)"
    )
    language: str = Field(
        default="en",
        description="Language of the returned response ('en', 'hi', or 'doi')"
    )
    model: Optional[str] = Field(
        default=None,
        description="Underlying synthesis engine or model name"
    )
    error: Optional[str] = Field(
        default=None,
        description="Sanitized error description if fallback was triggered"
    )

    model_config = ConfigDict(extra="ignore")


class LiveWeatherResponse(BaseModel):
    latitude: float
    longitude: float
    temperature_c: float
    relative_humidity_pct: float
    precipitation_mm: float
    wind_speed_kmh: float
    weather_code: int
    condition_summary: str
    rain_forecast_24h_mm: float
    is_live: bool
    source: str
    timestamp: str

    model_config = ConfigDict(extra="ignore")


class CaseShareRequest(BaseModel):
    case_id: str = Field(description="Unique case ID to be shared")
    owner_farmer_id: str = Field(description="ID of the farmer owning the case")
    target_entity: str = Field(default="cooperative_all", description="Recipient farmer ID or 'cooperative_all'")
    access_level: str = Field(default="cooperative", description="'view' or 'cooperative'")
    anonymize_pii: bool = Field(default=True, description="Whether to mask farmer name and fuzz coordinates")
    notes: Optional[str] = Field(default=None, description="Optional scouting or cooperative notes")

    model_config = ConfigDict(extra="ignore")


class CaseShareResponse(BaseModel):
    share_id: str
    case_id: str
    owner_farmer_id: str
    target_entity: str
    access_level: str
    share_token: str
    anonymize_pii: bool
    notes: Optional[str] = None
    created_at: str
    status: str

    model_config = ConfigDict(extra="ignore")


class SharedCaseSummary(BaseModel):
    share_id: str
    case_id: str
    target_entity: str
    access_level: str
    created_at: str
    notes: Optional[str] = None
    case_summary: Dict[str, Any]

    model_config = ConfigDict(extra="ignore")


class CooperativeInsightsResponse(BaseModel):
    region: str
    total_cases_analyzed: int
    disease_distribution: Dict[str, Dict[str, Any]]
    severity_distribution: Dict[str, int]
    risk_level_distribution: Dict[str, int]
    dominant_pathogen: Optional[str] = None
    regional_risk_level: str
    outbreak_alerts: List[str]
    collective_ipm_actions: List[str]
    generated_at: str

    model_config = ConfigDict(extra="ignore")


class CaseCommentCreate(BaseModel):
    author_id: str = Field(default="farmer_local", description="Author identifier")
    comment_text: str = Field(min_length=1, description="Comment or observation text")
    author_role: str = Field(default="farmer", description="Role: 'farmer', 'agronomist', 'cooperative_lead'")
    is_ai: bool = Field(default=False, description="Explicit flag separating AI vs farmer content")

    model_config = ConfigDict(extra="ignore")


class CaseCommentResponse(BaseModel):
    comment_id: str
    case_id: str
    author_id: str
    author_role: str
    comment_text: str
    created_at: str
    is_ai: bool

    model_config = ConfigDict(extra="ignore")


class CaseOutcomeCreate(BaseModel):
    farmer_id: str = Field(default="farmer_local", description="Farmer ID reporting the outcome")
    outcome: str = Field(description="Treatment outcome: 'helped', 'did_not_help', 'pending'")
    details: Optional[str] = Field(default=None, description="Agronomic details on why treatment succeeded or failed")

    model_config = ConfigDict(extra="ignore")


class CaseOutcomeResponse(BaseModel):
    case_id: str
    farmer_id: str
    outcome: str
    details: Optional[str] = ""
    updated_at: str

    model_config = ConfigDict(extra="ignore")


class CooperativeComparisonRegion(BaseModel):
    region_name: str
    cooperative_id: str
    is_local_pilot: bool
    data_status: str
    total_cases: int
    dominant_pathogen: str
    regional_risk_level: str
    outbreak_alerts: List[str]
    disease_distribution: Dict[str, Dict[str, Any]]

    model_config = ConfigDict(extra="ignore")


class CooperativeComparisonResponse(BaseModel):
    generated_at: str
    is_live_partnership: bool
    disclaimer: str
    regions: List[CooperativeComparisonRegion]

    model_config = ConfigDict(extra="ignore")


# =========================================================================
# Authentication & Role Separation Schemas (Stage C)
# =========================================================================

class UserSignupRequest(BaseModel):
    email: str = Field(description="Farmer or administrator email address")
    password: str = Field(min_length=6, description="Account password (min 6 characters)")
    full_name: str = Field(min_length=1, description="User full name")
    role: str = Field(default="farmer", description="Account role (public registration forces 'farmer')")
    phone: Optional[str] = Field(default=None, description="Contact phone number")

    model_config = ConfigDict(extra="ignore")


class UserLoginRequest(BaseModel):
    email: Optional[str] = Field(default=None, description="Registered email address")
    username: Optional[str] = Field(default=None, description="Registered username or email")
    password: str = Field(description="Account password")

    model_config = ConfigDict(extra="ignore")


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    phone: Optional[str] = ""
    is_active: bool = True
    created_at: str
    permissions: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse

    model_config = ConfigDict(extra="ignore")


class UserRoleUpdateRequest(BaseModel):
    role: str = Field(description="Target role: 'farmer', 'admin', 'sub_owner', or 'owner'")

    model_config = ConfigDict(extra="ignore")


class UserStatusUpdateRequest(BaseModel):
    is_active: bool = Field(description="Account active status")

    model_config = ConfigDict(extra="ignore")


class AuditLogItemResponse(BaseModel):
    log_id: str
    actor_id: str
    actor_email: str
    actor_role: str
    target_user_id: Optional[str] = None
    action: str
    details: Optional[str] = None
    timestamp: str

    model_config = ConfigDict(extra="ignore")


class AdminSystemStatsResponse(BaseModel):
    total_users: int
    total_farmers: int
    total_admins: int
    total_sub_owners: int = 0
    active_users: int
    suspended_users: int
    total_audit_events: int

    model_config = ConfigDict(extra="ignore")


class AdminSystemStatusResponse(BaseModel):
    server_time: str
    total_cases: int
    total_users: int
    total_shared_cases: int
    total_comments: int
    vectorstore_chunks: int
    vision_model_status: str
    active_classes: List[str]
    system_stats: Optional[AdminSystemStatsResponse] = None

    model_config = ConfigDict(extra="ignore")


# =========================================================================
# Sub-Owner Governance Schemas
# =========================================================================

class SubOwnerGrantRequest(BaseModel):
    user_id: str = Field(description="Target user ID to grant sub_owner role")
    permissions: List[str] = Field(
        default_factory=lambda: ["can_view_telemetry"],
        description="Assigned permissions: 'can_manage_users', 'can_moderate_cases', 'can_view_telemetry', 'can_view_audit_logs'"
    )

    model_config = ConfigDict(extra="ignore")


class SubOwnerPermissionsUpdateRequest(BaseModel):
    permissions: List[str] = Field(
        description="Updated permissions list"
    )

    model_config = ConfigDict(extra="ignore")


class SubOwnerResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str = "sub_owner"
    is_active: bool = True
    permissions: List[str] = Field(default_factory=list)
    granted_by: Optional[str] = "Main Owner"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


# =========================================================================
# Farmer Community & Social Connection Schemas
# =========================================================================

class CommunityPostCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200, description="Post title / discussion subject")
    content: str = Field(min_length=5, description="Main discussion body or question details")
    category: str = Field(default="general_farming", description="Agricultural category")
    image_url: Optional[str] = Field(default=None, description="Optional attached image URL")

    model_config = ConfigDict(extra="ignore")


class CommunityPostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    content: Optional[str] = Field(default=None, min_length=5)
    category: Optional[str] = None
    image_url: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class CommunityCommentCreate(BaseModel):
    comment_text: str = Field(min_length=1, description="Comment or reply content")
    parent_comment_id: Optional[str] = Field(default=None, description="Optional parent comment ID for threaded replies")

    model_config = ConfigDict(extra="ignore")


class CommunityReactionRequest(BaseModel):
    reaction_type: str = Field(default="like", description="Reaction type ('like' or 'helpful')")

    model_config = ConfigDict(extra="ignore")


class CommunityReportRequest(BaseModel):
    target_type: str = Field(description="'post' or 'comment'")
    target_id: str = Field(description="ID of the post or comment being reported")
    reason: str = Field(description="Reason for report: spam, harassment, misleading, inappropriate, other")
    details: Optional[str] = Field(default=None, description="Additional context for community moderators")

    model_config = ConfigDict(extra="ignore")


class CommunityCommentResponse(BaseModel):
    comment_id: str
    post_id: str
    parent_comment_id: Optional[str] = None
    author_id: str
    author_name: str
    author_role: str = "farmer"
    comment_text: str
    likes_count: int = 0
    has_liked: bool = False
    is_accepted: bool = False
    created_at: str
    updated_at: str
    replies: List["CommunityCommentResponse"] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class CommunityPostResponse(BaseModel):
    post_id: str
    author_id: str
    author_name: str
    author_role: str = "farmer"
    title: str
    content: str
    category: str = "general_farming"
    category_label: Optional[str] = None
    image_url: Optional[str] = None
    likes_count: int = 0
    comments_count: int = 0
    has_liked: bool = False
    is_pinned: bool = False
    is_resolved: bool = False
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="ignore")


class CommunityFeedResponse(BaseModel):
    posts: List[CommunityPostResponse]
    total_count: int
    limit: int
    offset: int
    has_more: bool

    model_config = ConfigDict(extra="ignore")


class CommunityReactionResponse(BaseModel):
    status: str
    message: str
    target_type: str
    target_id: str
    likes_count: int
    has_liked: bool

    model_config = ConfigDict(extra="ignore")


class CommunityReportResponse(BaseModel):
    report_id: str
    reporter_id: str
    target_type: str
    target_id: str
    reason: str
    details: Optional[str] = None
    status: str = "pending"
    created_at: str

    model_config = ConfigDict(extra="ignore")


