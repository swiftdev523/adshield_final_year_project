"""HTTP route definitions."""

from .routes_explain import router as explain_router
from .routes_install_source import router as install_source_router
from .routes_notification import router as notification_router
from .routes_predict import router as predict_router
from .routes_upload import router as upload_router

__all__ = [
    "predict_router",
    "explain_router",
    "notification_router",
    "upload_router",
    "install_source_router",
]
