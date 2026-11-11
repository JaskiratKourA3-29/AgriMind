"""
Automated Isolated Unit Tests for AgriMind Credential and Configuration Management.
Verifies environment-variable precedence, .env loading, safe key masking,
diagnostics, and unauthenticated fallback behavior without real network calls.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.utils.config import (
    load_environment,
    get_gemini_api_key,
    get_gemini_model_name,
    mask_api_key,
    sanitize_text,
    get_gemini_config_status
)
from src.rag.generator import AgrimindAnswerGenerator


class TestAgriMindConfig(unittest.TestCase):

    def setUp(self):
        # Save original environment to ensure clean isolation
        self.orig_env = os.environ.copy()

    def tearDown(self):
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_01_precedence_explicit_over_env(self):
        """Explicitly passed key must take precedence over environment variables."""
        os.environ["GEMINI_API_KEY"] = "env-gemini-key-123456"
        os.environ["GOOGLE_API_KEY"] = "env-google-key-123456"
        
        resolved = get_gemini_api_key(explicit_key="explicit-key-999999")
        self.assertEqual(resolved, "explicit-key-999999")

    def test_02_precedence_gemini_over_google(self):
        """GEMINI_API_KEY must take precedence over GOOGLE_API_KEY."""
        os.environ["GEMINI_API_KEY"] = "gemini-priority-123456"
        os.environ["GOOGLE_API_KEY"] = "google-fallback-123456"
        
        resolved = get_gemini_api_key()
        self.assertEqual(resolved, "gemini-priority-123456")

    def test_03_fallback_to_google_api_key(self):
        """When GEMINI_API_KEY is absent, resolve GOOGLE_API_KEY."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        os.environ["GOOGLE_API_KEY"] = "google-standalone-123456"
        
        resolved = get_gemini_api_key()
        self.assertEqual(resolved, "google-standalone-123456")

    def test_04_missing_and_empty_credentials(self):
        """Unset or whitespace credentials must safely evaluate to None."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
            
        with patch("src.utils.config.load_environment", return_value=False):
            self.assertIsNone(get_gemini_api_key())
            self.assertIsNone(get_gemini_api_key(explicit_key=""))
            self.assertIsNone(get_gemini_api_key(explicit_key="   "))

            os.environ["GEMINI_API_KEY"] = "   "
            self.assertIsNone(get_gemini_api_key())

    def test_05_mask_api_key_variations(self):
        """Masking must never expose the complete secret value."""
        self.assertEqual(mask_api_key(None), "NOT_CONFIGURED")
        self.assertEqual(mask_api_key(""), "NOT_CONFIGURED")
        self.assertEqual(mask_api_key("   "), "NOT_CONFIGURED")
        self.assertEqual(mask_api_key("short"), "****")
        self.assertEqual(mask_api_key("12345678"), "****")
        
        # Realistic length API key
        masked = mask_api_key("AIzaSyD-TestKey1234567890abcdef")
        self.assertTrue(masked.startswith("AIzaSy"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertIn("...", masked)
        self.assertNotIn("TestKey1234567890", masked)

    def test_06_load_dotenv_precedence_preserves_os_env(self):
        """Existing OS environment variables must NOT be overwritten by .env (override=False)."""
        os.environ["GEMINI_API_KEY"] = "original-os-key"
        
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("GEMINI_API_KEY=file-key-from-dotenv\n")
            temp_path = f.name
            
        try:
            loaded = load_environment(dotenv_path=temp_path)
            self.assertTrue(loaded)
            # Must retain original OS value, NOT the one from the file
            self.assertEqual(os.environ["GEMINI_API_KEY"], "original-os-key")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_07_load_dotenv_populates_unset_env(self):
        """When an environment variable is unset, .env must populate it."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("GEMINI_API_KEY=loaded-from-temp-dotenv-12345\n")
            temp_path = f.name
            
        try:
            loaded = load_environment(dotenv_path=temp_path)
            self.assertTrue(loaded)
            self.assertEqual(os.environ.get("GEMINI_API_KEY"), "loaded-from-temp-dotenv-12345")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_08_config_status_diagnostics_safe(self):
        """Diagnostics dictionary must report status without exposing raw credentials."""
        os.environ["GEMINI_API_KEY"] = "AIzaSyD-SecretKey9876543210"
        
        status = get_gemini_config_status()
        self.assertTrue(status["is_configured"])
        self.assertEqual(status["source"], "GEMINI_API_KEY")
        self.assertNotIn("SecretKey9876543210", str(status))
        self.assertEqual(status["masked_key"], "AIzaSy...3210")
        self.assertEqual(status["validation_policy"], "deferred_to_api_client")
        self.assertEqual(status["model_name"], "gemini-3.8-flash")

    def test_09_sanitize_text(self):
        """Error messages and logs containing the raw key must be sanitized."""
        secret = "AIzaSyD-VerySecretKey12345"
        error_msg = f"Failed to authenticate with token {secret} on Google endpoint."
        
        clean = sanitize_text(error_msg, key=secret)
        self.assertNotIn(secret, clean)
        self.assertIn("AIzaSy...2345", clean)

    def test_10_generator_unauthenticated_fallback_integration(self):
        """AgrimindAnswerGenerator initializes safely without credentials and preserves local fallback."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

        with patch("src.utils.config.load_environment", return_value=False):
            generator = AgrimindAnswerGenerator()
            self.assertIsNone(generator._api_key)
            self.assertIsNone(generator._init_gemini_llm())
            self.assertEqual(generator.model_name, "gemini-3.8-flash")

    def test_11_gemini_model_name_precedence_and_default(self):
        """Model resolution must follow: explicit > GEMINI_MODEL > gemini-3.8-flash."""
        if "GEMINI_MODEL" in os.environ:
            del os.environ["GEMINI_MODEL"]

        # Default
        self.assertEqual(get_gemini_model_name(), "gemini-3.8-flash")

        # Environment variable
        os.environ["GEMINI_MODEL"] = "gemini-3.6-flash"
        self.assertEqual(get_gemini_model_name(), "gemini-3.6-flash")

        # Explicit argument overrides env var
        self.assertEqual(get_gemini_model_name("gemini-1.5-pro"), "gemini-1.5-pro")

    def test_12_sanitize_text_auto_ambient_key(self):
        """sanitize_text must automatically scrub ambient environment keys when key is omitted."""
        secret = "AIzaSyD-AmbientEnvKey987654"
        os.environ["GEMINI_API_KEY"] = secret

        error_msg = f"Google API 403 Forbidden: Invalid key {secret} for project."
        clean = sanitize_text(error_msg)
        self.assertNotIn(secret, clean)
        self.assertIn("AIzaSy...7654", clean)

    def test_13_empty_env_var_does_not_block_dotenv_loading(self):
        """Whitespace or empty env vars must not block loading valid keys from .env."""
        os.environ["GEMINI_API_KEY"] = "   "
        os.environ["GOOGLE_API_KEY"] = ""

        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("GEMINI_API_KEY=loaded-from-fallback-dotenv-999\n")
            temp_path = f.name

        try:
            # Clear whitespace from env before loading to simulate unconfigured OS state
            del os.environ["GEMINI_API_KEY"]
            del os.environ["GOOGLE_API_KEY"]
            loaded = load_environment(dotenv_path=temp_path)
            self.assertTrue(loaded)
            self.assertEqual(get_gemini_api_key(), "loaded-from-fallback-dotenv-999")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_14_mock_chat_google_generative_ai_initialization(self):
        """ChatGoogleGenerativeAI must initialize with resolved model, temperature, and API key."""
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_chat_cls:
            mock_instance = MagicMock()
            mock_chat_cls.return_value = mock_instance

            gen = AgrimindAnswerGenerator(
                api_key="AIzaSyD-TestKey1234567890abcdef",
                model_name="gemini-3.8-flash",
                temperature=0.2
            )
            llm = gen._init_gemini_llm()

            self.assertIsNotNone(llm)
            mock_chat_cls.assert_called_once_with(
                model="gemini-3.8-flash",
                temperature=0.2,
                google_api_key="AIzaSyD-TestKey1234567890abcdef"
            )

    def test_15_mock_llm_invocation_error_masking_integration(self):
        """When LLM invocation fails, generator sanitizes secret from error and falls back."""
        secret = "AIzaSyD-SecretKeyExposedInError"
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError(f"API Error at https://generativelanguage.googleapis.com?key={secret}")

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = {
            "has_sufficient_evidence": True,
            "results": [{"text": "Rotate crops every 2 years to reduce bacterial spot.", "metadata": {"title": "Cornell Extension", "institution": "Cornell"}}],
            "citations": [{"citation_number": 1, "title": "Cornell Extension", "institution": "Cornell", "source_url": "https://cornell.edu"}],
            "context_text": "Rotate crops every 2 years."
        }

        gen = AgrimindAnswerGenerator(
            retriever=mock_retriever,
            llm=mock_llm,
            api_key=secret
        )

        res = gen.generate_answer(query="How to manage bacterial spot?", disease_target="Tomato___Bacterial_spot")

        self.assertEqual(res["generation_mode"], "grounded_extractive_fallback")
        self.assertNotIn(secret, res["error"])
        self.assertIn("AIzaSy...rror", res["error"])
        self.assertTrue(res["has_sufficient_evidence"])


if __name__ == "__main__":
    unittest.main()
