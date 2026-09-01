"""Standalone explanation route."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.explain import ExplainRequest, ExplainResponse
from ..services.explanation_service import explain

router = APIRouter(tags=["explanation"])


@router.post("/explain", response_model=ExplainResponse)
def explain_permissions(request: ExplainRequest) -> ExplainResponse:
    """Rule-based explanation from permissions + risk score + tier.

    Does not run the ML model - use this when you already have a score and tier
    (e.g. from a client-side cache or a prior ``/analyze/apk`` call).
    """
    if not request.permissions:
        raise HTTPException(status_code=422, detail="'permissions' must not be empty.")

    result = explain(
        request.permissions,
        request.risk_score,
        request.risk_tier,
        dangerous_count=request.dangerous_permission_count,
        safe_count=request.safe_permission_count,
    )
    return ExplainResponse(**result)
