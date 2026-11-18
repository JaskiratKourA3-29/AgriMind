"""
AgriMind Vercel Serverless Function Entry Point.
Adapts the existing FastAPI application instance for Vercel's Python runtime.
"""
import os
import sys

# Ensure repository root is on Python module search path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import authoritative configured FastAPI application instance
from src.api.app import app  # noqa: E402

# Vercel's Python runtime discovers and serves the top-level 'app' ASGI callable
__all__ = ["app"]

