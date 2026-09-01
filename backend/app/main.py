"""FastAPI entry point for the Android Adware Detection System backend.

Run locally:
    uvicorn backend.app.main:app --reload

Interactive API docs (Swagger UI) are then available at:
    http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI

from .config import configure_runtime_temp_dir

# Multipart form parsing happens before upload endpoint code runs. Configure
# tempfile globally at import time so Starlette also spools large APKs here.
configure_runtime_temp_dir()

from .api import (
    explain_router,
    install_source_router,
    notification_router,
    predict_router,
    upload_router,
)
from .services import get_apk_model_service, get_model_service, get_notification_service

app = FastAPI(
    title="Android Adware Detection System API",
    description="Permission-based ML risk scoring for Android applications.",
    version="0.1.0",
)

app.include_router(predict_router)
app.include_router(explain_router)
app.include_router(notification_router)
app.include_router(upload_router)
app.include_router(install_source_router)


@app.get("/", tags=["meta"])
def root() -> dict:
    """Return a simple API landing response instead of a 404."""
    return {
        "status": "ok",
        "message": "Android Adware Detection System API is running.",
        "docs": "/docs",
        "health": "/health",
    }


@app.on_event("startup")
def _warm_models() -> None:
    get_model_service()
    get_apk_model_service()
    get_notification_service()


@app.get("/health", tags=["meta"])
def health() -> dict:
    service = get_model_service()
    return {
        "status": "ok",
        "model": service.model_name,
        "n_features": len(service.feature_names),
        "decision_threshold": service.decision_threshold,
    }
