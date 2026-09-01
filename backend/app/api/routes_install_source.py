"""Install source analysis route."""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas.install_source import AnalyzeInstallSourceRequest, AnalyzeInstallSourceResponse
from ..services.install_source_service import analyze_install_source

router = APIRouter(tags=["install-source"])


@router.post("/analyze/install-source", response_model=AnalyzeInstallSourceResponse)
def analyze_install_source_endpoint(
    request: AnalyzeInstallSourceRequest,
) -> AnalyzeInstallSourceResponse:
    """Return install-source risk level and explanation (no permission scan)."""
    return AnalyzeInstallSourceResponse(**analyze_install_source(request.install_source))
