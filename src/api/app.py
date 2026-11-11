"""
AgriMind FastAPI Application Entry Point (Stage A).
Configures middleware, lifecycle hooks, routing, and restricted CORS origins
for local and Android emulator communication.
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.routes import router as api_router, get_workflow

# Strict non-wildcard CORS configuration specifically for local development
# and Android Studio emulator loopback addressing (10.0.2.2).
ALLOWED_CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://10.0.2.2",
    "http://10.0.2.2:8000",
    "http://10.0.2.16",
    "http://10.0.2.16:8000"
]

# Allow dynamic production / cloud domain overrides via environment variable
_env_origins = os.environ.get("ALLOWED_CORS_ORIGINS", "").strip()
if _env_origins == "*":
    ALLOWED_CORS_ORIGINS = ["*"]
elif _env_origins:
    ALLOWED_CORS_ORIGINS.extend([o.strip() for o in _env_origins.split(",") if o.strip()])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Pre-compiles the LangGraph multi-agent workflow on startup to eliminate cold-start
    graph compilation overhead on subsequent user requests.
    """
    # Pre-warm compiled workflow
    try:
        workflow = get_workflow()
        app.state.workflow = workflow
    except Exception as e:
        print(f"[AgriMind Lifespan Warning] Failed pre-warming workflow: {e}")

    yield

    # Clean shutdown tasks (if any)
    pass


def create_app() -> FastAPI:
    """Factory function initializing the configured FastAPI instance."""
    app_instance = FastAPI(
        title="AgriMind Agricultural Multi-Agent Decision API",
        description=(
            "REST backend for AgriMind — Multi-Agent AI System for Crop Disease Investigation, "
            "Risk Assessment & Adaptive Decision Support. Powered by ResNet-50, LangChain RAG, "
            "and LangGraph StateGraph orchestration."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Configure restricted CORS middleware
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )

    # Register API route endpoints
    app_instance.include_router(api_router)

    return app_instance


# Top-level instance for uvicorn runner (e.g. `uvicorn src.api.app:app --host 0.0.0.0 --port 8000`)
app = create_app()

