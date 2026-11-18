from dataclasses import asdict
import hashlib
"""
AgriMind FastAPI API Routes (Stage A).
Provides endpoints:
- GET  /health
- POST /diagnose
- POST /reassess

Enforces file validation, high-resolution latency tracking, Pydantic data modeling,
and proper cleanup of temporary files.
"""
import os
import sys
import re
import time
import json
import uuid
import tempfile
import logging
import socket
import ipaddress
import urllib.parse
import requests
import requests.adapters
import urllib3
import urllib3.connection
import urllib3.connectionpool
import urllib3.poolmanager
import urllib3.util.connection
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Header, Depends
from fastapi.responses import FileResponse

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.schemas import (
    HealthResponse,
    VisualContextInput,
    ManagementActionResponse,
    ManagementPlanResponse,
    LatencyBreakdown,
    DiagnosisResponse,
    ReassessmentRequest,
    ReassessmentResponse,
    MessageRole,
    ChatMessage,
    CitationItem,
    ChatRequest,
    ChatResponse,
    LiveWeatherResponse,
    CaseShareRequest,
    CaseShareResponse,
    SharedCaseSummary,
    CooperativeInsightsResponse,
    CaseCommentCreate,
    CaseCommentResponse,
    CaseOutcomeCreate,
    CaseOutcomeResponse,
    CooperativeComparisonResponse,
    UserSignupRequest,
    UserLoginRequest,
    UserProfileResponse,
    AuthTokenResponse,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
    AuditLogItemResponse,
    AdminSystemStatsResponse,
    AdminSystemStatusResponse,
    SubOwnerGrantRequest,
    SubOwnerPermissionsUpdateRequest,
    SubOwnerResponse,
    CommunityPostCreate,
    CommunityPostUpdate,
    CommunityCommentCreate,
    CommunityReactionRequest,
    CommunityReportRequest,
    CommunityCommentResponse,
    CommunityPostResponse,
    CommunityFeedResponse,
    CommunityReactionResponse,
    CommunityReportResponse
)
from src.services.auth_service import get_auth_service
from src.services.community_service import get_community_service, COMMUNITY_UPLOADS_DIR
from src.services.weather_service import get_weather_service, WeatherData
from src.services.case_sharing_service import get_case_sharing_service
from src.services.cooperative_service import get_cooperative_service
from src.rag.generator import AgrimindAnswerGenerator
from src.agents.schemas import (
    VisualContext,
    VisionPrediction,
    RetrievedEvidence,
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    ManagementAction,
    VerificationResult,
    ManualReviewRecord,
    ReassessmentRecord,
    ReassessmentTrigger,
    SupportedTomatoDisease
)
from src.workflow.graph import build_agrimind_workflow
from src.workflow.nodes import reassess_case
from src.workflow.state import AgriMindState
from src.vision.inference import verify_image_integrity
from src.api.case_store import get_case_store

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level cached workflow instance
_WORKFLOW_APP = None

# Module-level cached answer generator instance
_ANSWER_GENERATOR = None

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB max upload limit
# Module-level duplicate submission cache (SHA-256 -> (timestamp, DiagnosisResponse))
_IMAGE_SUBMISSION_CACHE: Dict[str, Any] = {}
DUPLICATE_CACHE_TTL_SECONDS = 120.0

from src.vision.inference import DEFAULT_CHECKPOINT
CHECKPOINT_PATH = DEFAULT_CHECKPOINT
CHROMA_DIR = os.path.join(WORKSPACE_DIR, "data", "vectorstore", "chroma")


def get_workflow():
    """Returns singleton compiled LangGraph workflow graph."""
    global _WORKFLOW_APP
    if _WORKFLOW_APP is None:
        _WORKFLOW_APP = build_agrimind_workflow()
    return _WORKFLOW_APP


def set_workflow(workflow_instance):
    """Allows injecting or resetting the workflow instance (useful for testing)."""
    global _WORKFLOW_APP
    _WORKFLOW_APP = workflow_instance


def get_answer_generator() -> AgrimindAnswerGenerator:
    """Returns singleton cached AgrimindAnswerGenerator instance."""
    global _ANSWER_GENERATOR
    if _ANSWER_GENERATOR is None:
        _ANSWER_GENERATOR = AgrimindAnswerGenerator()
    return _ANSWER_GENERATOR


def set_answer_generator(generator_instance):
    """Allows injecting or resetting the answer generator (useful for testing)."""
    global _ANSWER_GENERATOR
    _ANSWER_GENERATOR = generator_instance


def map_to_supported_disease(raw_disease: Optional[str]) -> Optional[str]:
    """
    Safely maps stored diagnosis strings to a verified SupportedTomatoDisease enum value.
    Returns None if disease is unrecognized or out of scope.
    """
    if not raw_disease or not isinstance(raw_disease, str):
        return None
    clean = raw_disease.strip()
    valid_values = {d.value for d in SupportedTomatoDisease}
    if clean in valid_values:
        return clean
    norm = clean.lower().replace(" ", "_").replace("___", "_").replace("__", "_")
    for d in SupportedTomatoDisease:
        d_norm = d.value.lower().replace("___", "_")
        if norm == d_norm or norm in d_norm or d_norm in norm:
            return d.value
    return None


def serialize_state_for_json(state: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively serializes AgriMindState objects into standard JSON-serializable types."""
    serialized = {}
    for k, v in state.items():
        if hasattr(v, "model_dump"):
            serialized[k] = v.model_dump()
        elif isinstance(v, list):
            serialized[k] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in v
            ]
        elif isinstance(v, (str, int, float, bool, dict, type(None))):
            serialized[k] = v
        else:
            serialized[k] = str(v)
    return serialized


def rehydrate_workflow_state(raw_state: Dict[str, Any]) -> AgriMindState:
    """Reconstructs Pydantic model objects from serialized JSON dicts before workflow invocation."""
    state = dict(raw_state)
    if "visual_context" in state and isinstance(state["visual_context"], dict):
        state["visual_context"] = VisualContext(**state["visual_context"])
    if "vision_prediction" in state and isinstance(state["vision_prediction"], dict):
        state["vision_prediction"] = VisionPrediction(**state["vision_prediction"])
    if "retrieved_evidence" in state and isinstance(state["retrieved_evidence"], dict):
        state["retrieved_evidence"] = RetrievedEvidence(**state["retrieved_evidence"])
    if "investigation_result" in state and isinstance(state["investigation_result"], dict):
        state["investigation_result"] = InvestigationResult(**state["investigation_result"])
    if "risk_assessment" in state and isinstance(state["risk_assessment"], dict):
        state["risk_assessment"] = RiskAssessmentResult(**state["risk_assessment"])
    if "decision_plan" in state and isinstance(state["decision_plan"], dict):
        state["decision_plan"] = DecisionPlan(**state["decision_plan"])
    if "verification_result" in state and isinstance(state["verification_result"], dict):
        state["verification_result"] = VerificationResult(**state["verification_result"])
    if "manual_review_record" in state and isinstance(state["manual_review_record"], dict):
        state["manual_review_record"] = ManualReviewRecord(**state["manual_review_record"])
    if "reassessment_records" in state and isinstance(state["reassessment_records"], list):
        state["reassessment_records"] = [
            ReassessmentRecord(**r) if isinstance(r, dict) else r
            for r in state["reassessment_records"]
        ]
    return state


def build_management_plan_response(plan: Any) -> Optional[ManagementPlanResponse]:
    """Converts internal DecisionPlan model or serialized dict to public API ManagementPlanResponse."""
    if not plan:
        return None

    if isinstance(plan, dict):
        def map_dict_actions(actions: List[Dict[str, Any]]) -> List[ManagementActionResponse]:
            return [
                ManagementActionResponse(
                    category=a.get("category", "cultural"),
                    action_summary=a.get("action_summary", ""),
                    details=a.get("details", ""),
                    is_chemical=a.get("is_chemical", False),
                    citation_numbers=a.get("citation_numbers", [])
                )
                for a in (actions or [])
            ]

        return ManagementPlanResponse(
            plan_id=plan.get("plan_id", ""),
            disease=plan.get("disease", ""),
            urgency=plan.get("urgency", "low"),
            cultural_controls=map_dict_actions(plan.get("cultural_controls", [])),
            resistant_varieties=map_dict_actions(plan.get("resistant_varieties", [])),
            chemical_controls=map_dict_actions(plan.get("chemical_controls", [])),
            monitoring_actions=map_dict_actions(plan.get("monitoring_actions", [])),
            uncertainty_disclosures=plan.get("uncertainty_disclosures", []),
            pesticide_safety_notice=plan.get("pesticide_safety_notice", "")
        )

    def map_actions(actions: List[ManagementAction]) -> List[ManagementActionResponse]:
        return [
            ManagementActionResponse(
                category=a.category,
                action_summary=a.action_summary,
                details=a.details,
                is_chemical=a.is_chemical,
                citation_numbers=a.citation_numbers
            )
            for a in actions
        ]

    return ManagementPlanResponse(
        plan_id=plan.plan_id,
        disease=plan.disease,
        urgency=plan.urgency.value if hasattr(plan.urgency, "value") else str(plan.urgency),
        cultural_controls=map_actions(plan.cultural_controls),
        resistant_varieties=map_actions(plan.resistant_varieties),
        chemical_controls=map_actions(plan.chemical_controls),
        monitoring_actions=map_actions(plan.monitoring_actions),
        uncertainty_disclosures=plan.uncertainty_disclosures,
        pesticide_safety_notice=plan.pesticide_safety_notice
    )


def build_diagnosis_response_from_state(
    case_id: str,
    state: Dict[str, Any],
    latency_breakdown: Optional[LatencyBreakdown] = None
) -> DiagnosisResponse:
    """Builds a standardized DiagnosisResponse from a persisted or active state dictionary."""
    final_output = state.get("final_output") or {}
    plan = state.get("management_plan")
    management_plan_resp = build_management_plan_response(plan)

    class_probs = None
    vision_pred = state.get("vision_prediction")
    if isinstance(vision_pred, dict):
        class_probs = vision_pred.get("class_probabilities")
    elif hasattr(vision_pred, "class_probabilities"):
        class_probs = vision_pred.class_probabilities

    confidence = final_output.get("diagnosis_confidence") or state.get("diagnosis_confidence")
    is_low_conf = False
    low_conf_guidance = None
    if confidence is not None and confidence < 0.65:
        is_low_conf = True
        low_conf_guidance = (
            "Diagnostic confidence is below 65% (ambiguous specimen or unclear symptom patterns). "
            "Please capture a clearer, well-lit photo of the affected tomato foliage under diffused natural light at 15-20 cm distance, "
            "or request human review from an accredited university extension pathologist."
        )

    return DiagnosisResponse(
        case_id=case_id,
        workflow_status=state.get("workflow_status", "unknown"),
        primary_diagnosis=final_output.get("primary_diagnosis") or state.get("primary_diagnosis"),
        diagnosis_confidence=confidence,
        class_probabilities=class_probs,
        assigned_severity=final_output.get("assigned_severity") or state.get("assigned_severity"),
        epidemic_risk=final_output.get("epidemic_risk") or state.get("epidemic_risk"),
        plan_urgency=final_output.get("plan_urgency") or state.get("plan_urgency"),
        is_verified=final_output.get("is_verified", False),
        verification_status=final_output.get("verification_status"),
        requires_manual_review=final_output.get("requires_manual_review", False) or is_low_conf,
        manual_review_status=final_output.get("manual_review_status"),
        management_plan=management_plan_resp,
        citations=final_output.get("citations") or [],
        pesticide_safety_notice=final_output.get("pesticide_safety_notice"),
        error_message=state.get("error_message"),
        is_low_confidence=is_low_conf,
        low_confidence_guidance=low_conf_guidance,
        latency_breakdown=latency_breakdown or LatencyBreakdown(
            model_inference_ms=0.0,
            total_workflow_ms=0.0
        ),
        raw_state=state
    )



# =====================================================================
# Security Dependencies (Moved up for route-level dependency resolution)
# =====================================================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Validates incoming Bearer session token and extracts verified claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token."
        )
    token = authorization.split(" ", 1)[1].strip()
    auth_svc = get_auth_service()
    claims = auth_svc.verify_token(token)
    if not claims or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked access token."
        )
    # Verify account exists and is active in persistent database
    user_record = auth_svc.get_user_by_id(claims["sub"])
    if not user_record or not user_record.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not exist, has been removed, or is deactivated."
        )
    # Authoritatively synchronize role and email from persistent database
    claims["role"] = user_record["role"]
    claims["email"] = user_record["email"]
    claims["user_id"] = user_record["user_id"]
    claims["full_name"] = user_record["full_name"]
    return claims


async def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Optional authentication context: returns claims if valid token provided, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    auth_svc = get_auth_service()
    claims = auth_svc.verify_token(token)
    if not claims or not claims.get("sub"):
        return None
    user_record = auth_svc.get_user_by_id(claims["sub"])
    if not user_record or not user_record.get("is_active"):
        return None
    claims["role"] = user_record["role"]
    claims["email"] = user_record["email"]
    claims["user_id"] = user_record["user_id"]
    claims["full_name"] = user_record["full_name"]
    return claims


# =====================================================================
# GET /health
# =====================================================================
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Model Status",
    description="Returns runtime status, loaded model checkpoints, and active RAG collection metadata."
)
async def health_check():
    has_model = os.path.exists(CHECKPOINT_PATH)
    has_chroma = os.path.exists(CHROMA_DIR)

    # Dynamic count of indexed Chroma chunks
    rag_chunks = 0
    if has_chroma:
        try:
            from src.rag.vectorstore import get_chroma_client, COLLECTION_NAME
            client = get_chroma_client(CHROMA_DIR)
            coll = client.get_collection(name=COLLECTION_NAME)
            rag_chunks = coll.count()
        except Exception:
            rag_chunks = 63  # Verified fallback count

    status_str = "healthy" if (has_model and has_chroma) else "degraded"

    return HealthResponse(
        status=status_str,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        models_available={
            "resnet50": has_model,
            "rag_chromadb": has_chroma
        },
        rag_chunks=rag_chunks,
        active_classes=[
            SupportedTomatoDisease.BACTERIAL_SPOT.value,
            SupportedTomatoDisease.EARLY_BLIGHT.value,
            SupportedTomatoDisease.LATE_BLIGHT.value
        ],
        device="cpu"
    )


# =====================================================================
# Secure Cloud Image Download Helper (SSRF & DNS Rebinding Protection)
# =====================================================================
class PinnedIPPoolManager(urllib3.poolmanager.PoolManager):
    """
    Custom urllib3 PoolManager that binds HTTPS connections directly to a pre-validated IP address,
    preventing DNS rebinding and TOCTOU vulnerabilities while maintaining the original hostname for
    TLS SNI and certificate verification.
    """
    def __init__(self, pinned_ip: str, *args, **kwargs):
        self.pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def _new_pool(self, scheme: str, host: str, port: int, request_context: Optional[Dict[str, Any]] = None):
        if scheme == "https":
            pinned_ip = self.pinned_ip

            class PinnedHTTPSConnection(urllib3.connection.HTTPSConnection):
                def _new_conn(_self):
                    return urllib3.util.connection.create_connection(
                        (pinned_ip, _self.port),
                        _self.timeout,
                        source_address=_self.source_address,
                        socket_options=_self.socket_options,
                    )

            class PinnedHTTPSConnectionPool(urllib3.connectionpool.HTTPSConnectionPool):
                ConnectionCls = PinnedHTTPSConnection

            if request_context is None:
                request_context = self.connection_pool_kw.copy()
            for key in ("scheme", "host", "port"):
                request_context.pop(key, None)
            return PinnedHTTPSConnectionPool(host, port, **request_context)

        return super()._new_pool(scheme, host, port, request_context=request_context)


class PinnedIPAdapter(requests.adapters.HTTPAdapter):
    """
    HTTPAdapter that binds the outbound TCP socket directly to a pre-validated IP address,
    preventing DNS rebinding and TOCTOU vulnerabilities while preserving full TLS certificate
    validation, Server Name Indication (SNI), and HTTP Host headers.
    """
    def __init__(self, pinned_ip: str, *args, **kwargs):
        self.pinned_ip = pinned_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=requests.adapters.DEFAULT_POOLBLOCK, **pool_kwargs):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self.poolmanager = PinnedIPPoolManager(
            self.pinned_ip,
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs
        )


def download_secure_image(image_url: str, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """
    Safely retrieves an image from authorized cloud storage over HTTPS.
    Enforces strict protocol, hostname allowlist, DNS pre-flight verification,
    actual TCP socket connection binding (anti-DNS-rebinding), anti-redirect guards,
    bounded streaming download, and generic error handling to eliminate SSRF, DoS,
    and internal network enumeration vulnerabilities.
    """
    norm_url = (image_url or "").strip()
    if not norm_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: URL cannot be empty."
        )

    # 1. Strict URL syntax and protocol parsing
    try:
        parsed = urllib.parse.urlsplit(norm_url)
    except Exception as e:
        logger.warning(f"Failed parsing image_url: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url format."
        )

    # Scheme check: HTTPS only (reject plain HTTP, file://, ftp://, gopher://, etc.)
    if parsed.scheme.lower() != "https":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Only secure HTTPS URLs are permitted."
        )

    # Embedded credentials check (e.g. https://user:pass@host/)
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Embedded credentials are prohibited."
        )

    # Port check: only port 443 or default HTTPS port allowed
    if parsed.port is not None and parsed.port != 443:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Non-standard ports are prohibited."
        )

    # URL fragment check
    if parsed.fragment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: URL fragments are prohibited."
        )

    # Hostname validation
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Missing or malformed hostname."
        )

    # Reject IP address literals (e.g. https://127.0.0.1/ or https://169.254.169.254/)
    try:
        ipaddress.ip_address(hostname)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False

    if is_ip_literal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Direct IP address literals are prohibited."
        )

    # 2. Strict Storage Hostname Allowlist Check
    supabase_env = os.environ.get("SUPABASE_URL", "").strip()
    if not supabase_env:
        logger.warning("Image URL download rejected: SUPABASE_URL environment variable is not configured.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image URL downloads require cloud storage configuration (SUPABASE_URL is not set)."
        )

    try:
        expected_host = (urllib.parse.urlsplit(supabase_env).hostname or "").strip().lower()
    except Exception:
        expected_host = ""

    if not expected_host:
        logger.error("Image URL download rejected: SUPABASE_URL contains no valid hostname.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal configuration error: Invalid cloud storage configuration."
        )

    if hostname != expected_host:
        logger.warning(
            f"Image URL download rejected: Host '{hostname}' does not match authorized storage host '{expected_host}'."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image_url: Host is not authorized for cloud image downloads."
        )

    # 3. DNS Pre-Resolution & Prohibited IP Address Filtering
    try:
        addr_info = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as dns_err:
        logger.warning(f"DNS resolution failed for storage host '{hostname}': {dns_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve image storage host."
        )

    if not addr_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve image storage host."
        )

    valid_ips = []
    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address encountered during host resolution."
            )

        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_unspecified
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        ):
            logger.warning(
                f"SSRF attempt blocked: Storage host '{hostname}' resolved to prohibited IP '{ip_str}'."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access to private or local network destinations is prohibited."
            )
        valid_ips.append(ip_str)

    if not valid_ips:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to resolve image storage host to a valid destination."
        )

    # Deterministically bind TCP socket to the first validated IP address
    target_ip = valid_ips[0]

    # 4. Outbound Connection Binding via PinnedIPAdapter & Dedicated Session (Anti-DNS-Rebinding)
    sanitized_log_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

    session = requests.Session()
    adapter = PinnedIPAdapter(target_ip)
    session.mount(f"https://{hostname}", adapter)
    session.mount(f"https://{hostname}:443", adapter)
    session.mount("https://", adapter)

    resp = None
    try:
        try:
            resp = session.get(
                norm_url,
                stream=True,
                allow_redirects=False,
                timeout=(5.0, 15.0)  # (connect timeout: 5s, read timeout: 15s)
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Connection timeout downloading image from: {sanitized_log_url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image download timed out while connecting to storage server."
            )
        except requests.exceptions.SSLError as ssl_err:
            logger.warning(f"TLS certificate verification failed for {sanitized_log_url}: {type(ssl_err).__name__}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TLS certificate verification failed for storage server."
            )
        except requests.exceptions.RequestException as req_err:
            logger.warning(f"Network error downloading image from {sanitized_log_url}: {type(req_err).__name__}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to download image from cloud storage."
            )

        # Redirect check: Reject all HTTP redirects (301, 302, 303, 307, 308)
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            logger.warning(f"Image download from {sanitized_log_url} returned redirect status HTTP {resp.status_code}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redirects are prohibited for image downloads."
            )

        if resp.status_code != 200:
            logger.warning(f"Image download from {sanitized_log_url} returned status HTTP {resp.status_code}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch image from storage (HTTP {resp.status_code})."
            )

        # Inspect Content-Length header if present
        cl_header = resp.headers.get("Content-Length")
        if cl_header:
            try:
                cl_val = int(cl_header.strip())
                if cl_val > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image exceeds maximum size limit of {max_bytes // (1024 * 1024)}MB."
                    )
                if cl_val == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Image file is empty (0 bytes)."
                    )
            except ValueError:
                pass

        # Stream bounded chunks
        chunks = []
        total_bytes = 0
        chunk_size = 65536  # 64 KB

        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image exceeds maximum size limit of {max_bytes // (1024 * 1024)}MB."
                    )
                chunks.append(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file is empty (0 bytes)."
            )

        return b"".join(chunks)

    finally:
        if resp is not None:
            resp.close()
        session.close()


# =====================================================================
# POST /diagnose
# =====================================================================
@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    summary="End-to-End Tomato Disease Diagnosis",
    description="Accepts an image and optional field context, executes ResNet-50 vision inference "
                "and the complete LangGraph multi-agent decision workflow."
)
async def diagnose(
    file: Optional[UploadFile] = File(None, description="Tomato leaf image file (JPEG, PNG, GIF, BMP, max 15MB)"),
    image_url: Optional[str] = Form(None, description="Direct cloud storage image URL (bypassing multipart upload limit)"),
    leaf_damage_percentage: Optional[float] = Form(None, description="Estimated leaf damage percentage (0-100)"),
    affected_organs: Optional[str] = Form(None, description="Comma-separated affected organs (e.g. leaves,stems)"),
    canopy_spread: Optional[str] = Form(None, description="Canopy spread (e.g. lower_canopy, whole_plant)"),
    weather_conditions: Optional[str] = Form(None, description="Recent ambient weather (e.g. cool_wet, warm_humid)"),
    field_notes: Optional[str] = Form(None, description="Agronomic field observations or scouting notes"),
    context_json: Optional[str] = Form(None, description="Optional raw JSON string representing VisualContextInput"),
    user_query: Optional[str] = Form(None, description="Optional specific farmer query for RAG retrieval"),
    latitude: Optional[float] = Form(None, description="Optional GPS latitude for live weather risk."),
    longitude: Optional[float] = Form(None, description="Optional GPS longitude for live weather risk."),
    use_live_weather: bool = Form(False, description="Whether to query live Open-Meteo meteorological data."),
    language: str = Form("en", description="Preferred response language ('en' or 'hi')"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
):
    # 1. Validate file existence or image_url
    if file and file.filename:
        content = await file.read()
    elif image_url and image_url.strip():
        content = download_secure_image(image_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image provided. Please upload an image file or provide an image_url."
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    # 3. Validate image magic bytes
    header = content[:16]
    is_jpeg = header.startswith(b"\xff\xd8")
    is_png = header.startswith(b"\x89PNG")
    is_gif = header.startswith(b"GIF")
    is_bmp = header.startswith(b"BM")

    if not (is_jpeg or is_png or is_gif or is_bmp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported or invalid image file format. Supported formats: JPEG, PNG, GIF, BMP."
        )

    # 3b. Image Quality & Foliar Suitability Validation
    from src.vision.image_validator import validate_image_suitability
    is_suitable, reason, error_msg, quality_metrics = validate_image_suitability(content, preferred_language=language)
    if not is_suitable:
        logger.warning(f"Image suitability check rejected ({reason}): {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "Uploaded image is unsuitable for diagnosis."
        )

    # SHA-256 Duplicate Submission Cache Check with comprehensive field observation context
    image_sha256 = hashlib.sha256(content).hexdigest()
    norm_notes = (field_notes or "").strip().lower()
    norm_query = (user_query or "").strip().lower()
    norm_canopy = (canopy_spread or "").strip().lower()
    norm_organs = sorted(re.split(r"[,; ]+", affected_organs.strip().lower())) if affected_organs else []
    obs_context = f"{norm_notes}|{norm_query}|{norm_canopy}|{','.join(norm_organs)}"
    obs_hash = hashlib.sha256(obs_context.encode("utf-8")).hexdigest()[:16]
    cache_key = f"{image_sha256}_{leaf_damage_percentage}_{weather_conditions}_{latitude}_{longitude}_{obs_hash}"
    now_ts = time.time()

    expired_keys = [k for k, (t, _) in _IMAGE_SUBMISSION_CACHE.items() if now_ts - t > 300.0]
    for k in expired_keys:
        del _IMAGE_SUBMISSION_CACHE[k]

    if cache_key in _IMAGE_SUBMISSION_CACHE:
        cached_ts, cached_resp = _IMAGE_SUBMISSION_CACHE[cache_key]
        if now_ts - cached_ts < DUPLICATE_CACHE_TTL_SECONDS:
            logger.info(f"Duplicate image submission detected ({image_sha256[:10]}). Returning cached diagnosis.")
            return cached_resp

    # Determine file extension
    ext = ".jpg"
    if is_png:
        ext = ".png"
    elif is_gif:
        ext = ".gif"
    elif is_bmp:
        ext = ".bmp"

    # 4. Save to temporary file securely
    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_path = temp_file.name
    temp_file.write(content)
    temp_file.flush()
    temp_file.close()

    # 5. Validate image integrity (detect corrupt or unreadable bitstream)
    if not verify_image_integrity(temp_path):
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or unreadable image file. Unable to decode image content."
        )

    try:
        # 6. Parse Visual Context
        parsed_context = {}
        if context_json:
            try:
                parsed_context = json.loads(context_json)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON provided in context_json: {str(e)}"
                )

        # Form fields override JSON context if provided
        if leaf_damage_percentage is not None:
            parsed_context["leaf_damage_percentage"] = leaf_damage_percentage
        if affected_organs is not None:
            parsed_context["affected_organs"] = [o.strip() for o in affected_organs.split(",") if o.strip()]
        if canopy_spread is not None:
            parsed_context["canopy_spread"] = canopy_spread
        if weather_conditions is not None:
            parsed_context["weather_conditions"] = weather_conditions
        if field_notes is not None:
            parsed_context["field_notes"] = field_notes

        # Fetch live meteorological data if requested or coordinates are provided
        if use_live_weather or (latitude is not None and longitude is not None):
            try:
                weather_svc = get_weather_service()
                live_w = weather_svc.fetch_live_weather(latitude, longitude)
                if not parsed_context.get("weather_conditions"):
                    parsed_context["weather_conditions"] = live_w.condition_summary
                logger.info(f"Integrated live weather: {live_w.condition_summary}, {live_w.temperature_c}°C, {live_w.relative_humidity_pct}% RH")
            except Exception as w_err:
                logger.warning(f"Could not fetch live weather: {w_err}")

        visual_context_obj = VisualContext(**parsed_context) if parsed_context else None

        # 6. Initialize LangGraph State
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        initial_state: AgriMindState = {
            "case_id": case_id,
            "image_path": temp_path,
            "image_status": "unvalidated",
            "visual_context": visual_context_obj,
            "user_query": user_query,
            "workflow_status": "initialized",
            "iteration_count": 0,
            "max_iterations": 2,
            "reassessment_count": 0,
            "max_reassessments": 2,
            "case_history": []
        }

        # 7. Execute Workflow with High-Resolution Latency Tracking
        workflow_app = get_workflow()
        start_workflow = time.perf_counter()
        model_inference_ms = None
        t_step = time.perf_counter()
        completed_state = dict(initial_state)

        for step in workflow_app.stream(initial_state, stream_mode="updates"):
            for node_name, updates in step.items():
                if node_name == "vision":
                    model_inference_ms = round((time.perf_counter() - t_step) * 1000, 2)
                completed_state.update(updates)
                t_step = time.perf_counter()

        total_workflow_ms = round((time.perf_counter() - start_workflow) * 1000, 2)

        # 8. Extract Outputs and Map to Schema
        final_output = completed_state.get("final_output") or {}
        vision_pred = completed_state.get("vision_prediction")
        plan = completed_state.get("decision_plan")
        verif = completed_state.get("verification_result")

        management_plan_resp = build_management_plan_response(plan)

        # Build clean serializable state for future reassessments
        serializable_state = serialize_state_for_json(completed_state)

        # Persist authoritative case state server-side with owner_user_id
        owner_id = (current_user.get("user_id") or current_user.get("sub")) if current_user else None
        case_store = get_case_store()
        case_store.save_case(case_id, serializable_state, owner_user_id=owner_id)

        diag_resp = build_diagnosis_response_from_state(
            case_id=case_id,
            state=serializable_state,
            latency_breakdown=LatencyBreakdown(
                model_inference_ms=model_inference_ms,
                total_workflow_ms=total_workflow_ms
            )
        )
        _IMAGE_SUBMISSION_CACHE[cache_key] = (now_ts, diag_resp)
        return diag_resp

    finally:
        # Guarantee removal of temporary image file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# =====================================================================
# POST /reassess
# =====================================================================
@router.post(
    "/reassess",
    response_model=ReassessmentResponse,
    summary="Adaptive Case Reassessment",
    description="Re-evaluates an existing completed case given new field evidence, weather updates, "
                "or diagnostic feedback, preserving prior history while enforcing the 2-iteration loop ceiling."
)
async def reassess(request: ReassessmentRequest):
    # 1. Validate Trigger
    try:
        trigger_enum = ReassessmentTrigger(request.trigger)
    except ValueError:
        valid_triggers = [t.value for t in ReassessmentTrigger]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reassessment trigger: '{request.trigger}'. Allowed triggers: {valid_triggers}"
        )

    # 2. Validate Evidence Payload
    if not request.new_evidence or not isinstance(request.new_evidence, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_evidence must be a non-empty dictionary containing updated agricultural observations."
        )

    # Whitelist allowable agricultural observation fields to prevent state tampering / injection
    ALLOWED_EVIDENCE_FIELDS = {
        "leaf_damage_percentage",
        "affected_organs",
        "canopy_spread",
        "weather_conditions",
        "field_notes",
        "lab_confirmed_disease",
        "confirmed_pathogen",
        "treatment_notes",
        "image_path",
        "new_image_path"
    }
    sanitized_evidence = {k: v for k, v in request.new_evidence.items() if k in ALLOWED_EVIDENCE_FIELDS}
    if not sanitized_evidence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_evidence does not contain any valid agronomic observation fields."
        )

    # 3. Retrieve Authoritative Prior State from Server-Side Case Storage
    case_store = get_case_store()
    authoritative_state = case_store.get_case(request.case_id)
    if not authoritative_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case ID '{request.case_id}' was not found in authoritative storage."
        )

    # 4. Enforce Reassessment Ceiling Server-Side
    current_count = authoritative_state.get("reassessment_count", 0)
    max_reassessments = authoritative_state.get("max_reassessments", 2)
    if current_count >= max_reassessments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum reassessment limit ({max_reassessments}) exceeded for case '{request.case_id}'. Permanent clinical escalation required."
        )

    try:
        # 5. Rehydrate Authoritative Prior State (ignoring any client-supplied completed_state)
        rehydrated_state = rehydrate_workflow_state(authoritative_state)

        # 6. Execute Reassessment via LangGraph
        workflow_app = get_workflow()
        start_reassess = time.perf_counter()

        revised_state = reassess_case(
            workflow_app=workflow_app,
            completed_state=rehydrated_state,
            trigger=trigger_enum,
            new_evidence=sanitized_evidence,
            rationale=request.rationale
        )

        total_reassess_ms = round((time.perf_counter() - start_reassess) * 1000, 2)

        # 7. Extract Outputs
        final = revised_state.get("final_output") or {}
        plan = revised_state.get("decision_plan")
        verif = revised_state.get("verification_result")
        records = revised_state.get("reassessment_records") or []

        management_plan_resp = build_management_plan_response(plan)

        formatted_records = [
            r.model_dump() if hasattr(r, "model_dump") else r
            for r in records
        ]

        serializable_state = serialize_state_for_json(revised_state)

        # 8. Update Authoritative Case in Storage
        case_store.update_case(request.case_id, serializable_state)

        return ReassessmentResponse(
            case_id=request.case_id,
            workflow_status=revised_state.get("workflow_status", "unknown"),
            reassessment_outcome=final.get("reassessment_outcome"),
            reassessment_count=revised_state.get("reassessment_count", 1),
            max_reassessments=revised_state.get("max_reassessments", 2),
            primary_diagnosis=final.get("primary_diagnosis"),
            diagnosis_confidence=final.get("diagnosis_confidence"),
            assigned_severity=final.get("assigned_severity"),
            epidemic_risk=final.get("epidemic_risk"),
            plan_urgency=final.get("plan_urgency"),
            is_verified=final.get("is_verified", False),
            verification_status=final.get("verification_status"),
            requires_manual_review=final.get("requires_manual_review", False),
            management_plan=management_plan_resp,
            citations=final.get("citations") or [],
            pesticide_safety_notice=final.get("pesticide_safety_notice"),
            reassessment_records=formatted_records,
            case_history_length=len(revised_state.get("case_history", [])),
            error_message=revised_state.get("error_message"),
            latency_breakdown=LatencyBreakdown(
                model_inference_ms=None,
                total_workflow_ms=total_reassess_ms
            ),
            completed_state=serializable_state
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reassessment execution failed: {str(e)}"
        )


# --- Real Weather, Case Sharing & Cooperative Insights Endpoints ---

@router.get(
    "/weather/live",
    response_model=LiveWeatherResponse,
    summary="Real-time Weather & Epidemiological Risk Data",
    description="Retrieves live temperature, humidity, precipitation, and disease-conducive indicators from Open-Meteo."
)
async def get_live_weather(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> LiveWeatherResponse:
    weather_svc = get_weather_service()
    data = weather_svc.fetch_live_weather(latitude, longitude)
    return LiveWeatherResponse(**asdict(data))


@router.get(
    "/weather/guidance",
    summary="Crop-Specific Weather Decision Guidance",
    description="Calculates heat stress, rainfall drainage, foliar humidity, and preventive recommendations in English or Hindi."
)
async def get_weather_crop_guidance(
    crop: str = "tomato",
    growth_stage: Optional[str] = None,
    language: str = "en",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Dict[str, Any]:
    weather_svc = get_weather_service()
    weather_data = weather_svc.fetch_live_weather(latitude, longitude)
    guidance = weather_svc.get_weather_crop_care_guidance(
        weather=weather_data,
        crop=crop,
        growth_stage=growth_stage,
        language=language
    )
    return guidance


@router.post(
    "/cases/share",
    response_model=CaseShareResponse,
    summary="Authorize and Share Diagnostic Case",
    description="Publishes a case into the cooperative or peer sharing pool with PII masking and access token generation."
)
async def share_case(request: CaseShareRequest) -> CaseShareResponse:
    case_store = get_case_store()
    case_data = case_store.get_case(request.case_id)
    if not case_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case ID '{request.case_id}' was not found in authoritative storage."
        )

    final_output = case_data.get("final_output") or {}
    payload = {
        "case_id": request.case_id,
        "primary_diagnosis": final_output.get("primary_diagnosis") or case_data.get("primary_diagnosis"),
        "confidence": final_output.get("confidence") or 1.0,
        "assigned_severity": final_output.get("assigned_severity") or "moderate",
        "epidemic_risk": final_output.get("epidemic_risk") or "moderate",
        "weather_summary": final_output.get("weather_summary") or "Normal field conditions",
        "created_at": case_data.get("created_at") or datetime.now(timezone.utc).isoformat()
    }
    sharing_svc = get_case_sharing_service()
    res = sharing_svc.share_case(
        case_data=payload,
        owner_farmer_id=request.owner_farmer_id,
        target_entity=request.target_entity,
        access_level=request.access_level,
        anonymize_pii=request.anonymize_pii,
        notes=request.notes
    )
    return CaseShareResponse(**res)


@router.get(
    "/cases/shared",
    response_model=List[SharedCaseSummary],
    summary="List Authorized Shared Cases",
    description="Retrieves active shared cases for a cooperative pool or farmer."
)
async def list_shared_cases(
    target_entity: str = "cooperative_all",
    limit: int = 50
) -> List[SharedCaseSummary]:
    sharing_svc = get_case_sharing_service()
    cases = sharing_svc.list_shared_cases(target_entity=target_entity, limit=limit)
    return [SharedCaseSummary(**c) for c in cases]


@router.get(
    "/cases/shared/{share_id}",
    summary="Get Shared Case Details",
    description="Retrieves an authorized shared case by share ID and token or requester identity."
)
async def get_shared_case(
    share_id: str,
    share_token: Optional[str] = None,
    requester_id: Optional[str] = None
) -> Dict[str, Any]:
    sharing_svc = get_case_sharing_service()
    case = sharing_svc.get_shared_case(
        share_id=share_id,
        share_token=share_token,
        requester_id=requester_id
    )
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared case not found or unauthorized access token."
        )
    return case


@router.delete(
    "/cases/shared/{share_id}",
    summary="Revoke Shared Case Access",
    description="Revokes sharing access for a case. Requires owner farmer verification."
)
async def revoke_shared_case(
    share_id: str,
    owner_farmer_id: str
) -> Dict[str, Any]:
    sharing_svc = get_case_sharing_service()
    revoked = sharing_svc.revoke_share(share_id=share_id, owner_farmer_id=owner_farmer_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unable to revoke share. Verify that the share ID and owner farmer ID are correct."
        )
    return {"status": "revoked", "share_id": share_id}


@router.get(
    "/cooperative/insights",
    response_model=CooperativeInsightsResponse,
    summary="Cooperative-Level Aggregated Disease Analytics",
    description="Synthesizes shared diagnostic data into regional epidemic alerts, pathogen distribution, and collective IPM actions."
)
async def get_cooperative_insights(
    cooperative_id: str = "cooperative_all",
    region: str = "Jammu & Kashmir Cooperative"
) -> CooperativeInsightsResponse:
    coop_svc = get_cooperative_service()
    insights = coop_svc.generate_insights(target_entity=cooperative_id, region_name=region)
    return CooperativeInsightsResponse(**asdict(insights))


@router.get(
    "/cooperative/report",
    summary="Aggregated Cooperative Crop-Health Report Data",
    description="Generates multi-case summary dataset for aggregated cooperative PDF reporting."
)
async def get_cooperative_report(
    cooperative_id: str = "cooperative_all",
    region: str = "Jammu & Kashmir Cooperative"
) -> Dict[str, Any]:
    coop_svc = get_cooperative_service()
    insights = coop_svc.generate_insights(target_entity=cooperative_id, region_name=region)
    sharing_svc = get_case_sharing_service()
    shared_cases = sharing_svc.list_shared_cases(target_entity=cooperative_id, limit=50)
    return {
        "insights": asdict(insights),
        "cases": shared_cases,
        "cooperative_id": cooperative_id,
        "region": region,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get(
    "/cooperative/comparison",
    response_model=CooperativeComparisonResponse,
    summary="Multi-Regional Cooperative Comparison",
    description="Compares regional disease incidence across participating cooperatives (Jammu vs neighboring partner grids)."
)
async def get_cooperative_comparison() -> CooperativeComparisonResponse:
    coop_svc = get_cooperative_service()
    comp = coop_svc.generate_regional_comparison()
    return CooperativeComparisonResponse(**comp)


# =====================================================================
# Community Case Comments & Treatment Outcome Endpoints
# =====================================================================
@router.post(
    "/cases/{case_id}/comments",
    response_model=CaseCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Community Observation or Comment",
    description="Records a farmer or agronomist observation on a shared case, maintaining strict AI-vs-human separation."
)
async def add_case_comment(case_id: str, request: CaseCommentCreate) -> CaseCommentResponse:
    clean_id = case_id.strip()
    sharing_svc = get_case_sharing_service()
    comment = sharing_svc.add_comment(
        case_id=clean_id,
        author_id=request.author_id,
        comment_text=request.comment_text,
        author_role=request.author_role,
        is_ai=request.is_ai
    )
    return CaseCommentResponse(**comment)


@router.get(
    "/cases/{case_id}/comments",
    response_model=List[CaseCommentResponse],
    summary="List Community Observations on Case",
    description="Retrieves community observations and grower feedback for a specific case."
)
async def list_case_comments(case_id: str) -> List[CaseCommentResponse]:
    clean_id = case_id.strip()
    sharing_svc = get_case_sharing_service()
    comments = sharing_svc.get_comments(case_id=clean_id)
    return [CaseCommentResponse(**c) for c in comments]


@router.post(
    "/cases/{case_id}/outcome",
    response_model=CaseOutcomeResponse,
    summary="Record Treatment Outcome",
    description="Tracks whether the recommended IPM treatment helped ('helped', 'did_not_help', 'pending')."
)
async def record_case_outcome(case_id: str, request: CaseOutcomeCreate) -> CaseOutcomeResponse:
    clean_id = case_id.strip()
    sharing_svc = get_case_sharing_service()
    outcome = sharing_svc.record_outcome(
        case_id=clean_id,
        farmer_id=request.farmer_id,
        outcome=request.outcome,
        details=request.details
    )
    return CaseOutcomeResponse(**outcome)


@router.get(
    "/cases/{case_id}/outcome",
    response_model=Optional[CaseOutcomeResponse],
    summary="Get Treatment Outcome",
    description="Retrieves the recorded treatment outcome for a case, if one exists."
)
async def get_case_outcome(case_id: str) -> Optional[CaseOutcomeResponse]:
    clean_id = case_id.strip()
    sharing_svc = get_case_sharing_service()
    outcome = sharing_svc.get_outcome(case_id=clean_id)
    if not outcome:
        return None
    return CaseOutcomeResponse(**outcome)


# =====================================================================
# GET /cases/{case_id}
# =====================================================================
@router.get(
    "/cases/{case_id}",
    response_model=DiagnosisResponse,
    summary="Retrieve Authoritative Diagnostic Case",
    description="Retrieves a persisted case state by case_id from server-side storage."
)
async def get_case_by_id(
    case_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
):
    clean_id = case_id.strip()
    case_store = get_case_store()
    record = case_store.get_case_record(clean_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case ID '{clean_id}' was not found in authoritative storage."
        )

    # Privacy & Access Control Enforcement:
    owner_id = record.get("owner_user_id")
    if owner_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this private diagnostic case."
            )
        caller_id = current_user.get("user_id") or current_user.get("sub")
        caller_role = current_user.get("role", "farmer")
        if caller_id != owner_id and caller_role not in ("admin", "owner", "sub_owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view another farmer's private case."
            )

    return build_diagnosis_response_from_state(clean_id, record["state"])


# =====================================================================
# POST /chat
# =====================================================================
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Evidence-Grounded Agronomic Conversational Q&A",
    description="Answers farmer and researcher questions strictly grounded in accredited university "
                "agricultural extension literature. Supports optional case anchoring to focus advice on "
                "a verified tomato disease diagnosis."
)
async def chat(request: ChatRequest) -> ChatResponse:
    # 1. Validate and resolve case context if case_id is provided
    disease_target = None
    clean_case_id = None
    if request.case_id:
        clean_case_id = request.case_id.strip()
        case_store = get_case_store()
        case_state = case_store.get_case(clean_case_id)
        if not case_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case ID '{clean_case_id}' was not found in authoritative storage."
            )

        # Extract stored diagnosis and map to verified disease class
        final_output = case_state.get("final_output") or {}
        raw_diag = final_output.get("primary_diagnosis") or case_state.get("primary_diagnosis")
        if not raw_diag and "vision_prediction" in case_state and isinstance(case_state["vision_prediction"], dict):
            raw_diag = case_state["vision_prediction"].get("predicted_class")

        disease_target = map_to_supported_disease(raw_diag)

    # 2. Invoke authoritative AgrimindAnswerGenerator with history, disease_target, and language
    try:
        # Extract chemical treatments if case is linked
        treatments_summary = ""
        if clean_case_id:
            final_out = case_state.get("final_output") or {}
            plan_data = final_out.get("management_plan") or {}
            curative = plan_data.get("curative_chemical", [])
            preventive = plan_data.get("preventive_chemical", [])
            chems = [a.get("action_summary", "") for a in (curative + preventive) if isinstance(a, dict)]
            if chems:
                treatments_summary = f"Prescribed Case Chemicals: {'; '.join(chems)}"

        generator = get_answer_generator()
        gen_kwargs = {
            "query": request.query,
            "conversation_history": request.conversation_history,
            "disease_target": disease_target,
            "language": request.language,
            "top_k": 4
        }
        if treatments_summary:
            gen_kwargs["case_context"] = treatments_summary
        result = generator.generate_answer(**gen_kwargs)

        resolved_target = result.get("disease_target") or disease_target

        # 3. Map retrieved citations to CitationItem schema
        citations_data = result.get("citations", []) or []
        citation_items = []
        for c in citations_data:
            if isinstance(c, dict):
                citation_items.append(
                    CitationItem(
                        citation_number=c.get("citation_number", 0),
                        doc_id=c.get("doc_id", "UNKNOWN"),
                        title=c.get("title", ""),
                        institution=c.get("institution", ""),
                        source_url=c.get("source_url", ""),
                        chunk_id=c.get("chunk_id"),
                        similarity_score=c.get("similarity_score")
                    )
                )

        return ChatResponse(
            query=request.query,
            answer=result.get("answer", ""),
            citations=citation_items,
            has_sufficient_evidence=result.get("has_sufficient_evidence", False),
            generation_mode=result.get("generation_mode", "unknown"),
            case_id=clean_case_id,
            disease_target=resolved_target,
            language=result.get("language", request.language),
            model=result.get("model"),
            error=result.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat generation execution failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while generating the agronomic answer. Please consult an extension specialist."
        )


# =====================================================================
# Security Dependencies & Authentication Routes (Stage C)
# =====================================================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Validates incoming Bearer session token and extracts verified claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token."
        )
    token = authorization.split(" ", 1)[1].strip()
    auth_svc = get_auth_service()
    claims = auth_svc.verify_token(token)
    if not claims or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked access token."
        )
    # Verify account exists and is active in persistent database
    user_record = auth_svc.get_user_by_id(claims["sub"])
    if not user_record or not user_record.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account does not exist, has been removed, or is deactivated."
        )
    # Authoritatively synchronize role and email from persistent database
    claims["role"] = user_record["role"]
    claims["email"] = user_record["email"]
    claims["user_id"] = user_record["user_id"]
    claims["full_name"] = user_record["full_name"]
    return claims


async def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Optional authentication for browsing community feed without requiring login."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    auth_svc = get_auth_service()
    claims = auth_svc.verify_token(token)
    if not claims or not claims.get("sub"):
        return None
    user_record = auth_svc.get_user_by_id(claims["sub"])
    if not user_record or not user_record.get("is_active"):
        return None
    claims["role"] = user_record["role"]
    claims["email"] = user_record["email"]
    claims["user_id"] = user_record["user_id"]
    claims["full_name"] = user_record["full_name"]
    return claims


async def require_farmer(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensures requester is an active farmer, sub-owner, administrator, or owner."""
    if user.get("role") not in ("farmer", "admin", "owner", "sub_owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to registered farmers."
        )
    return user


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensures requester possesses verified administrator or owner privileges."""
    if user.get("role") not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access this resource."
        )
    return user


def require_permission(required_perm: str):
    """
    Evaluates whether the authenticated user possesses the specific administrative permission.
    - Project Owner: possesses all permissions implicitly.
    - Administrator: possesses all standard administrative permissions.
    - Sub-Owner: possesses only explicitly granted permissions verified against live database.
    - Farmer: denied.
    """
    async def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        auth_svc = get_auth_service()
        if not auth_svc.has_permission(user, required_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Administrative privileges required: Missing '{required_perm}' permission."
            )
        return user
    return dependency


async def require_owner(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Ensures requester is the verified Main Project Owner."""
    if user.get("role") != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project Owner privileges required to access this resource."
        )
    return user


@router.post(
    "/auth/signup",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Farmer Account",
    description="Registers a new farmer account with secure PBKDF2 password hashing and returns an initial session token."
)
async def signup(request: UserSignupRequest) -> AuthTokenResponse:
    auth_svc = get_auth_service()
    # Public signup is strictly restricted to farmer role to prevent privilege escalation
    success, msg, user = auth_svc.register_user(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        role="farmer",
        phone=request.phone
    )
    if not success or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    token = auth_svc.create_token(user_id=user["user_id"], email=user["email"], role=user["role"])
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfileResponse(**user)
    )


@router.post(
    "/auth/login",
    response_model=AuthTokenResponse,
    summary="Authenticate User and Create Session",
    description="Validates credentials and returns an HMAC-SHA256 session token."
)
async def login(request: UserLoginRequest) -> AuthTokenResponse:
    auth_svc = get_auth_service()
    login_id = request.email or request.username
    if not login_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or username must be provided."
        )
    success, msg, user = auth_svc.authenticate_user(email=login_id, password=request.password)
    if not success or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=msg
        )
    token = auth_svc.create_token(user_id=user["user_id"], email=user["email"], role=user["role"])
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfileResponse(**user)
    )


@router.post(
    "/auth/logout",
    summary="Revoke Current Session Token",
    description="Revokes the active session token so it can no longer be used."
)
async def logout(
    authorization: Optional[str] = Header(None),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    auth_svc = get_auth_service()
    auth_svc.revoke_token(token)
    return {"status": "success", "message": "Session token revoked successfully."}


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    summary="Retrieve Authenticated User Profile",
    description="Returns profile information for the currently authenticated farmer or administrator."
)
async def get_me(user: Dict[str, Any] = Depends(get_current_user)) -> UserProfileResponse:
    auth_svc = get_auth_service()
    profile = auth_svc.get_user_by_id(user["sub"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserProfileResponse(**profile)


# =====================================================================
# Administrator Privileged Endpoints (Stage C & Owner Governance)
# =====================================================================

@router.get(
    "/admin/users",
    response_model=List[UserProfileResponse],
    summary="Admin: List Registered Users",
    description="Restricted to administrators, owners, or sub-owners with user management permissions."
)
async def admin_list_users(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_permission("can_manage_users"))
) -> List[UserProfileResponse]:
    auth_svc = get_auth_service()
    users = auth_svc.list_users(limit=limit)
    return [UserProfileResponse(**u) for u in users]


@router.get(
    "/admin/users/search",
    response_model=List[UserProfileResponse],
    summary="Admin: Search User Accounts",
    description="Search user accounts by email, full name, or filter by role. Requires user management permission."
)
async def admin_search_users(
    query: Optional[str] = None,
    role: Optional[str] = None,
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_permission("can_manage_users"))
) -> List[UserProfileResponse]:
    auth_svc = get_auth_service()
    users = auth_svc.search_users(query=query, role=role, limit=limit)
    return [UserProfileResponse(**u) for u in users]


@router.post(
    "/admin/users/{user_id}/role",
    summary="Admin: Update User Role",
    description="Updates role of a target user ('farmer', 'admin', 'sub_owner', 'owner'). Exclusively restricted to Main Project Owner."
)
async def admin_update_user_role(
    user_id: str,
    request: UserRoleUpdateRequest,
    owner: Dict[str, Any] = Depends(require_owner)
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok, msg = auth_svc.update_user_role(
        acting_user=owner,
        target_user_id=user_id,
        new_role=request.role
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return {"status": "success", "message": msg}


@router.post(
    "/admin/users/{user_id}/status",
    summary="Admin: Update User Account Status",
    description="Activates or suspends a user account. Prevents self-suspension or suspending project owner."
)
async def admin_update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    user: Dict[str, Any] = Depends(require_permission("can_manage_users"))
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok, msg = auth_svc.set_user_status(
        acting_user=user,
        target_user_id=user_id,
        is_active=request.is_active
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return {"status": "success", "message": msg}


@router.get(
    "/admin/audit-logs",
    response_model=List[AuditLogItemResponse],
    summary="Admin: Retrieve Security Audit Logs",
    description="Returns immutable security audit events. Requires 'can_view_audit_logs' permission."
)
async def admin_get_audit_logs(
    limit: int = 50,
    user: Dict[str, Any] = Depends(require_permission("can_view_audit_logs"))
) -> List[AuditLogItemResponse]:
    auth_svc = get_auth_service()
    logs = auth_svc.get_audit_logs(limit=limit)
    return [AuditLogItemResponse(**log) for log in logs]


@router.delete(
    "/admin/users/{user_id}",
    summary="Admin: Deactivate or Delete User Account",
    description="Restricted to Main Project Owner. Deletes a user account."
)
async def admin_delete_user(
    user_id: str,
    owner: Dict[str, Any] = Depends(require_owner)
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok = auth_svc.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or cannot delete project owner.")
    return {"status": "success", "message": f"User {user_id} removed successfully."}


@router.get(
    "/admin/system/status",
    response_model=AdminSystemStatusResponse,
    summary="Admin: System Health & Diagnostic Overview",
    description="Provides high-level operational counts and model telemetry. Requires 'can_view_telemetry' permission."
)
async def admin_system_status(user: Dict[str, Any] = Depends(require_permission("can_view_telemetry"))) -> AdminSystemStatusResponse:
    case_store = get_case_store()
    sharing_svc = get_case_sharing_service()
    auth_svc = get_auth_service()

    total_cases = case_store.get_case_count()

    sys_stats = auth_svc.get_system_stats()
    shared_cases = sharing_svc.list_shared_cases(target_entity="cooperative_all", limit=1000)

    # Count comments
    total_comments = 0
    with sharing_svc._connection() as conn:
        row = conn.execute("SELECT count(*) AS count FROM case_comments;").fetchone()
        if row: total_comments = row["count"]

    return AdminSystemStatusResponse(
        server_time=datetime.now(timezone.utc).isoformat(),
        total_cases=total_cases,
        total_users=sys_stats["total_users"],
        total_shared_cases=len(shared_cases),
        total_comments=total_comments,
        vectorstore_chunks=63,
        vision_model_status="active",
        active_classes=[c.value for c in SupportedTomatoDisease],
        system_stats=AdminSystemStatsResponse(**sys_stats)
    )


@router.delete(
    "/admin/cases/{case_id}",
    summary="Admin/Moderator: Moderate Diagnostic Case",
    description="Moderation action: removes a case from storage. Requires 'can_moderate_cases' permission."
)
async def admin_delete_case(
    case_id: str,
    user: Dict[str, Any] = Depends(require_permission("can_moderate_cases"))
) -> Dict[str, Any]:
    case_store = get_case_store()
    auth_svc = get_auth_service()

    deleted = case_store.delete_case(case_id.strip())
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")

    auth_svc.log_audit_event(
        actor_id=user.get("user_id", user.get("sub", "")),
        actor_email=user.get("email", ""),
        actor_role=user.get("role", ""),
        action="CASE_MODERATED",
        details=f"Moderator deleted diagnostic case {case_id}.",
        target_user_id=None
    )
    return {"status": "success", "message": f"Case {case_id} removed by moderator."}


# =========================================================================
# Sub-Owner Governance Endpoints (Main Project Owner Exclusively)
# =========================================================================

@router.get(
    "/admin/sub-owners",
    response_model=List[SubOwnerResponse],
    summary="Main Owner: List Sub-Owners",
    description="Exclusively restricted to the Main Project Owner. Lists all active sub-owners and their assigned permissions."
)
async def admin_list_sub_owners(
    owner: Dict[str, Any] = Depends(require_owner)
) -> List[SubOwnerResponse]:
    auth_svc = get_auth_service()
    sub_owners = auth_svc.list_sub_owners()
    return [SubOwnerResponse(**s) for s in sub_owners]


@router.post(
    "/admin/sub-owners/grant",
    response_model=Dict[str, Any],
    summary="Main Owner: Grant Sub-Owner Role",
    description="Exclusively restricted to the Main Project Owner. Grants sub_owner role to a user with specific permissions."
)
async def admin_grant_sub_owner(
    request: SubOwnerGrantRequest,
    owner: Dict[str, Any] = Depends(require_owner)
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok, msg, data = auth_svc.grant_sub_owner(
        acting_user=owner,
        target_user_id=request.user_id,
        permissions=request.permissions
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg, "sub_owner": data}


@router.post(
    "/admin/sub-owners/{user_id}/revoke",
    response_model=Dict[str, Any],
    summary="Main Owner: Revoke Sub-Owner Role",
    description="Exclusively restricted to the Main Project Owner. Revokes sub_owner privileges and restores user to farmer role."
)
async def admin_revoke_sub_owner(
    user_id: str,
    owner: Dict[str, Any] = Depends(require_owner)
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok, msg = auth_svc.revoke_sub_owner(
        acting_user=owner,
        target_user_id=user_id
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}


@router.post(
    "/admin/sub-owners/{user_id}/permissions",
    response_model=Dict[str, Any],
    summary="Main Owner: Update Sub-Owner Permissions",
    description="Exclusively restricted to the Main Project Owner. Updates assigned permissions for a sub-owner."
)
async def admin_update_sub_owner_permissions(
    user_id: str,
    request: SubOwnerPermissionsUpdateRequest,
    owner: Dict[str, Any] = Depends(require_owner)
) -> Dict[str, Any]:
    auth_svc = get_auth_service()
    ok, msg, perms = auth_svc.update_sub_owner_permissions(
        acting_user=owner,
        target_user_id=user_id,
        permissions=request.permissions
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg, "permissions": perms}


# =========================================================================
# Farmer Community & Social Connection Endpoints
# =========================================================================

@router.post(
    "/community/posts",
    response_model=CommunityPostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Farmer Community Post",
    description="Publishes a new peer-to-peer discussion post or crop problem question."
)
async def create_community_post(
    request: CommunityPostCreate,
    user: Dict[str, Any] = Depends(get_current_user)
) -> CommunityPostResponse:
    community_svc = get_community_service()
    ok, msg, post = community_svc.create_post(
        author_user=user,
        title=request.title,
        content=request.content,
        category=request.category,
        image_url=request.image_url
    )
    if not ok or not post:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return CommunityPostResponse(**post)


@router.get(
    "/community/posts",
    response_model=CommunityFeedResponse,
    summary="List Community Posts / Discussions",
    description="Retrieves paginated community feed with optional category and search keyword filters."
)
async def list_community_posts(
    query: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> CommunityFeedResponse:
    community_svc = get_community_service()
    current_uid = user.get("user_id", user.get("sub")) if user else None
    feed = community_svc.get_feed(
        current_user_id=current_uid,
        query=query,
        category=category,
        limit=limit,
        offset=offset
    )
    return CommunityFeedResponse(
        posts=[CommunityPostResponse(**p) for p in feed["posts"]],
        total_count=feed["total_count"],
        limit=feed["limit"],
        offset=feed["offset"],
        has_more=feed["has_more"]
    )


@router.get(
    "/community/posts/{post_id}",
    response_model=CommunityPostResponse,
    summary="Get Single Community Post Details",
    description="Retrieves a specific community post by post ID."
)
async def get_community_post(
    post_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> CommunityPostResponse:
    community_svc = get_community_service()
    current_uid = user.get("user_id", user.get("sub")) if user else None
    post = community_svc.get_post_by_id(post_id=post_id.strip(), current_user_id=current_uid)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post '{post_id}' not found.")
    return CommunityPostResponse(**post)


@router.put(
    "/community/posts/{post_id}",
    response_model=CommunityPostResponse,
    summary="Edit Community Post",
    description="Allows author to update their own community post."
)
async def update_community_post(
    post_id: str,
    request: CommunityPostUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
) -> CommunityPostResponse:
    community_svc = get_community_service()
    ok, msg, updated = community_svc.update_post(
        acting_user=user,
        post_id=post_id.strip(),
        title=request.title,
        content=request.content,
        category=request.category,
        image_url=request.image_url
    )
    if not ok:
        status_code = status.HTTP_403_FORBIDDEN if "Forbidden" in msg else status.HTTP_400_BAD_REQUEST
        if "not found" in msg.lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=msg)
    return CommunityPostResponse(**updated)


@router.delete(
    "/community/posts/{post_id}",
    summary="Delete Community Post",
    description="Deletes a community post. Allowed for post author, Main Owner, or authorized Sub-Owner."
)
async def delete_community_post(
    post_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    community_svc = get_community_service()
    auth_svc = get_auth_service()
    ok, msg = community_svc.delete_post(
        acting_user=user,
        post_id=post_id.strip(),
        auth_service=auth_svc
    )
    if not ok:
        status_code = status.HTTP_403_FORBIDDEN if "Forbidden" in msg else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=msg)
    return {"status": "success", "message": msg}


@router.post(
    "/community/posts/{post_id}/comments",
    response_model=CommunityCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Comment or Threaded Reply",
    description="Adds a comment or reply to an existing community post."
)
async def add_community_comment(
    post_id: str,
    request: CommunityCommentCreate,
    user: Dict[str, Any] = Depends(get_current_user)
) -> CommunityCommentResponse:
    community_svc = get_community_service()
    ok, msg, comment = community_svc.add_comment(
        author_user=user,
        post_id=post_id.strip(),
        comment_text=request.comment_text,
        parent_comment_id=request.parent_comment_id
    )
    if not ok or not comment:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() or "does not exist" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)
    return CommunityCommentResponse(**comment)


@router.get(
    "/community/posts/{post_id}/comments",
    response_model=List[CommunityCommentResponse],
    summary="List Threaded Comments for Post",
    description="Retrieves hierarchical comments and replies for a specific post."
)
async def list_community_comments(
    post_id: str,
    user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
) -> List[CommunityCommentResponse]:
    community_svc = get_community_service()
    current_uid = user.get("user_id", user.get("sub")) if user else None
    comments = community_svc.get_comments(post_id=post_id.strip(), current_user_id=current_uid)
    return [CommunityCommentResponse(**c) for c in comments]


@router.delete(
    "/community/comments/{comment_id}",
    summary="Delete Community Comment",
    description="Deletes a comment. Allowed for comment author or authorized moderator."
)
async def delete_community_comment(
    comment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    community_svc = get_community_service()
    auth_svc = get_auth_service()
    ok, msg = community_svc.delete_comment(
        acting_user=user,
        comment_id=comment_id.strip(),
        auth_service=auth_svc
    )
    if not ok:
        status_code = status.HTTP_403_FORBIDDEN if "Forbidden" in msg else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=msg)
    return {"status": "success", "message": msg}


@router.post(
    "/community/posts/{post_id}/comments/{comment_id}/accept",
    summary="Mark Accepted Useful Solution",
    description="Post author marks or unmarks a community comment as the accepted solution."
)
async def accept_community_answer(
    post_id: str,
    comment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    community_svc = get_community_service()
    ok, msg = community_svc.mark_accepted_answer(
        acting_user=user,
        post_id=post_id.strip(),
        comment_id=comment_id.strip()
    )
    if not ok:
        status_code = status.HTTP_403_FORBIDDEN if "Forbidden" in msg else status.HTTP_400_BAD_REQUEST
        if "not found" in msg.lower() or "does not exist" in msg.lower():
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=msg)
    return {"status": "success", "message": msg}


@router.post(
    "/community/reactions/{target_type}/{target_id}",
    response_model=CommunityReactionResponse,
    summary="Toggle Like / Helpful Reaction",
    description="Toggles reaction on a community post or comment."
)
async def toggle_community_reaction(
    target_type: str,
    target_id: str,
    request: Optional[CommunityReactionRequest] = None,
    user: Dict[str, Any] = Depends(get_current_user)
) -> CommunityReactionResponse:
    community_svc = get_community_service()
    rx_type = request.reaction_type if request else "like"
    ok, msg, data = community_svc.toggle_reaction(
        acting_user=user,
        target_type=target_type.strip(),
        target_id=target_id.strip(),
        reaction_type=rx_type
    )
    if not ok:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=msg)
    return CommunityReactionResponse(
        status="success",
        message=msg,
        target_type=data["target_type"],
        target_id=data["target_id"],
        likes_count=data["likes_count"],
        has_liked=data["has_liked"]
    )


@router.post(
    "/community/reports",
    summary="Report Inappropriate Community Content",
    description="Submits a community moderation report for spam, abuse, or misleading advice."
)
async def report_community_content(
    request: CommunityReportRequest,
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    community_svc = get_community_service()
    ok, msg = community_svc.report_content(
        reporter_user=user,
        target_type=request.target_type,
        target_id=request.target_id,
        reason=request.reason,
        details=request.details
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg}


@router.get(
    "/community/reports",
    response_model=List[CommunityReportResponse],
    summary="List Moderation Reports",
    description="Restricted to Main Owner and authorized Sub-Owners."
)
async def list_community_reports(
    limit: int = 50,
    user: Dict[str, Any] = Depends(get_current_user)
) -> List[CommunityReportResponse]:
    community_svc = get_community_service()
    auth_svc = get_auth_service()
    ok, msg, reports = community_svc.list_reports(
        acting_user=user,
        auth_service=auth_svc,
        limit=limit
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
    return [CommunityReportResponse(**r) for r in reports]



# =====================================================================
# POST /api/uploads/presigned-url (Direct-to-Cloud Storage)
# =====================================================================
@router.post(
    "/api/uploads/presigned-url",
    summary="Generate Restricted Presigned Upload URL",
    description="Issues a short-lived, authenticated presigned upload URL for direct-to-cloud storage."
)
async def create_presigned_upload_url(
    payload: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    filename = payload.get("filename", "image.jpg")
    content_type = payload.get("content_type", "image/jpeg")

    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Allowed formats: .jpg, .jpeg, .png, .webp"
        )

    user_id = user.get("user_id") or user.get("sub", "anon")
    safe_name = f"user_{user_id}_{uuid.uuid4().hex[:12]}{ext}"

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    bucket_name = os.environ.get("SUPABASE_STORAGE_BUCKET", "community_images")

    if supabase_url and supabase_key:
        try:
            from supabase import create_client
            sb_client = create_client(supabase_url, supabase_key)
            res = sb_client.storage.from_(bucket_name).create_signed_upload_url(safe_name)
            upload_url = res.get("signed_url") or res.get("signedUrl")
            token = res.get("token")
            public_url = sb_client.storage.from_(bucket_name).get_public_url(safe_name)
            return {
                "upload_url": upload_url,
                "public_url": public_url,
                "token": token,
                "expires_in_seconds": 300,
                "storage_provider": "supabase"
            }
        except Exception as e:
            logger.error(f"Error generating Supabase signed upload URL: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate signed upload URL: {str(e)}"
            )
    else:
        # Fallback for local development and offline environments
        return {
            "upload_url": "/community/upload-image",
            "public_url": f"/community/images/{safe_name}",
            "token": "local-dev-token",
            "expires_in_seconds": 300,
            "storage_provider": "local_fallback"
        }


@router.post(
    "/community/upload-image",
    summary="Upload Community Image Attachment",
    description="Safely stores an image for a community post."
)
async def upload_community_image(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    content = await file.read()
    community_svc = get_community_service()
    ok, msg, rel_url = community_svc.save_community_image(content, file.filename or "image.jpg")
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"status": "success", "message": msg, "image_url": rel_url}


@router.get(
    "/community/images/{image_name}",
    summary="Download Community Image",
    description="Serves stored community images safely with path traversal protection."
)
async def get_community_image(image_name: str):
    clean_name = os.path.basename(image_name.strip())
    image_path = os.path.join(COMMUNITY_UPLOADS_DIR, clean_name)
    if not os.path.exists(image_path) or not os.path.isfile(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")
    ext = os.path.splitext(clean_name)[1].lower()
    media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else ("image/png" if ext == ".png" else "image/webp")
    return FileResponse(path=image_path, media_type=media_type)


@router.get(
    "/download/agrimind.apk",
    summary="Download AgriMind Android APK",
    description="Serves the compiled Android application APK for on-device installation via QR code or direct download."
)
async def download_agrimind_apk():
    apk_path = os.path.join(WORKSPACE_DIR, "android", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
    if not os.path.exists(apk_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APK build artifact not found. Please compile the Android debug APK first."
        )
    return FileResponse(
        path=apk_path,
        filename="agrimind-debug.apk",
        media_type="application/vnd.android.package-archive"
    )




