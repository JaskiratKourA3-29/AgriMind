"""
AgriMind FastAPI Application Package (Stage A).
Provides high-performance REST endpoints for model health, disease diagnosis,
and multi-agent adaptive case reassessment.
"""
from src.api.app import create_app, app

__all__ = ["create_app", "app"]

