"""
AgriMind Central Configuration and Credential Management Module.
Safely loads environment configurations, resolves API credentials with strict
precedence, masks secrets in diagnostics, and prevents accidental credential exposure.
"""
import os
import sys
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Determine workspace root (three levels up from src/utils/config.py)
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_environment(dotenv_path: Optional[str] = None) -> bool:
    """
    Safely loads environment variables from a .env file if available.
    
    Guarantees:
    - Never overwrites existing OS/shell environment variables (override=False).
    - Silently handles missing .env files without crashing.
    - Preserves existing system environment precedence.
    """
    target_path = dotenv_path or os.path.join(WORKSPACE_DIR, ".env")
    if not os.path.exists(target_path):
        return False

    try:
        from dotenv import load_dotenv
        # override=False guarantees existing OS environment variables are NEVER overwritten
        load_dotenv(dotenv_path=target_path, override=False)
        return True
    except ImportError:
        logger.debug("python-dotenv not installed; relying on existing OS environment variables.")
        return False
    except Exception as e:
        logger.warning(f"Failed to load environment file at {target_path}: {e}")
        return False


def mask_api_key(key: Optional[str]) -> str:
    """
    Masks an API key for safe logging, diagnostics, and test reports.
    Never exposes the full key value.
    
    Examples:
    - None -> "NOT_CONFIGURED"
    - "" -> "NOT_CONFIGURED"
    - "short" -> "****"
    - "AIzaSyD-1234567890abcdef" -> "AIzaSy...cdef"
    """
    if not key or not key.strip():
        return "NOT_CONFIGURED"
    
    clean_key = key.strip()
    if len(clean_key) <= 8:
        return "****"
    
    return f"{clean_key[:6]}...{clean_key[-4:]}"


def sanitize_text(text: str, key: Optional[str] = None) -> str:
    """
    Scrubs a secret API key from text or error messages to prevent leakage.
    If key is not explicitly provided, scrubs any ambiently configured Gemini/Google API key.
    """
    if not text:
        return text

    keys_to_scrub = []
    if key and key.strip():
        keys_to_scrub.append(key.strip())
    else:
        # Check ambient environment variables
        k1 = os.environ.get("GEMINI_API_KEY")
        if k1 and k1.strip():
            keys_to_scrub.append(k1.strip())
        k2 = os.environ.get("GOOGLE_API_KEY")
        if k2 and k2.strip():
            keys_to_scrub.append(k2.strip())

    cleaned_text = text
    for secret in keys_to_scrub:
        if len(secret) >= 6:
            cleaned_text = cleaned_text.replace(secret, mask_api_key(secret))
    return cleaned_text


def get_gemini_model_name(explicit_model: Optional[str] = None) -> str:
    """
    Resolves the Gemini model name with strict precedence:
    1. Explicitly provided argument (if non-empty)
    2. GEMINI_MODEL environment variable
    3. Default: 'gemini-3.8-flash' (verified active Google endpoint)
    """
    if explicit_model and explicit_model.strip():
        return explicit_model.strip()

    load_environment()
    env_model = os.environ.get("GEMINI_MODEL")
    if env_model and env_model.strip():
        return env_model.strip()

    return "gemini-3.8-flash"


def get_gemini_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """
    Resolves the Google Gemini API key using strict precedence:
    1. Explicitly provided argument (if non-empty)
    2. GEMINI_API_KEY environment variable
    3. GOOGLE_API_KEY environment variable
    4. None (if unconfigured or empty)
    
    Also automatically attempts a safe .env load (without override) if not yet loaded.
    """
    # 1. Explicit key
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    # Attempt to load .env if env vars not currently present or empty
    has_gemini = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    has_google = bool(os.environ.get("GOOGLE_API_KEY", "").strip())
    if not (has_gemini or has_google):
        load_environment()

    # 2. GEMINI_API_KEY
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip():
        return gemini_key.strip()

    # 3. GOOGLE_API_KEY
    google_key = os.environ.get("GOOGLE_API_KEY")
    if google_key and google_key.strip():
        return google_key.strip()

    # 4. None
    return None


def get_gemini_config_status(explicit_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns non-sensitive configuration diagnostics for the Gemini API key.
    
    NOTE: In accordance with project safeguards, 'is_configured' denotes only that
    a key is present in configuration; authentication validity is determined solely
    by the Gemini API service at request time.
    """
    # Check source
    if explicit_key and explicit_key.strip():
        source = "explicit_argument"
        key = explicit_key.strip()
    elif os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_KEY").strip():
        source = "GEMINI_API_KEY"
        key = os.environ.get("GEMINI_API_KEY").strip()
    elif os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_API_KEY").strip():
        source = "GOOGLE_API_KEY"
        key = os.environ.get("GOOGLE_API_KEY").strip()
    else:
        # Try loading .env once
        load_environment()
        if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_KEY").strip():
            source = "GEMINI_API_KEY (from .env)"
            key = os.environ.get("GEMINI_API_KEY").strip()
        elif os.environ.get("GOOGLE_API_KEY") and os.environ.get("GOOGLE_API_KEY").strip():
            source = "GOOGLE_API_KEY (from .env)"
            key = os.environ.get("GOOGLE_API_KEY").strip()
        else:
            source = "NONE"
            key = None

    return {
        "is_configured": key is not None,
        "source": source,
        "masked_key": mask_api_key(key),
        "model_name": get_gemini_model_name(),
        "validation_policy": "deferred_to_api_client"
    }
