"""Prediction routes.

POST /predict-apk
    Installed App Mode: accepts permission features (+ optional store metadata),
    scores with the metadata-aware production model.

POST /analyze/apk
    APK Analysis Mode: accepts raw declared permissions, scores with the
    permission-only model (no store metadata needed) and returns distinct model,
    permission-risk, contextual-risk, and overall assessment fields.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ...apk_analysis.permission_extractor import analyze_permission_list
from ..schemas import (
    AnalyzeAPKRequest,
    AnalyzeAPKResponse,
    PredictAPKRequest,
    PredictAPKResponse,
)
from ..services import (
    get_apk_model_service,
    get_category_model_service,
    get_model_service,
)
from ..services.assessment_integrator import integrate_assessment
from ..services.explanation_service import explain

router = APIRouter(tags=["prediction"])
logger = logging.getLogger(__name__)


@router.post("/predict-apk", response_model=PredictAPKResponse)
def predict_apk(request: PredictAPKRequest) -> PredictAPKResponse:
    if not request.features:
        raise HTTPException(status_code=422, detail="'features' must not be empty.")

    service = get_model_service()
    metadata = request.metadata.model_dump() if request.metadata else None

    result = service.predict(request.features, metadata)

    active = {label for label, v in request.features.items() if float(v) >= 1}
    explanation = explain(
        list(active),
        result["risk_score"],
        result["risk_level"],
        dangerous_count=result["dangerous_permission_count"],
        safe_count=result["safe_permission_count"],
        canonical_labels=active,
    )

    integrated = integrate_assessment(
        result,
        request.install_source,
        explanation,
        permissions=sorted(active),
        legacy_flagged_permission_count=result["dangerous_permission_count"],
        legacy_safe_permission_count=result["safe_permission_count"],
        mode="Installed App Mode",
    )

    return PredictAPKResponse(mode="Installed App Mode", **integrated)


@router.post("/analyze/apk", response_model=AnalyzeAPKResponse)
def analyze_apk(request: AnalyzeAPKRequest) -> AnalyzeAPKResponse:
    if not request.permissions:
        raise HTTPException(status_code=422, detail="'permissions' must not be empty.")

    # Score with the permission-only APK model.
    apk_service = get_apk_model_service()
    result = apk_service.predict_from_permissions(request.permissions)

    # Reuse the extractor to derive dangerous/safe counts and the active
    # human-readable permission labels (for the explanation engine).
    extraction = analyze_permission_list(request.permissions)

    explanation = explain(
        request.permissions,
        result["risk_score"],
        result["risk_level"],
        dangerous_count=extraction.dangerous_permission_count,
        safe_count=extraction.safe_permission_count,
        canonical_labels=extraction.mapped_features,
    )

    integrated = integrate_assessment(
        result,
        request.install_source,
        explanation,
        package=request.package,
        permissions=extraction.raw_permissions,
        legacy_flagged_permission_count=extraction.dangerous_permission_count,
        legacy_safe_permission_count=extraction.safe_permission_count,
        mode="APK Analysis Mode",
    )

    # Experimental post-binary sidecar. The integrated binary/overall risk
    # fields above are already final and are never inputs to category output.
    if result["model_prediction"] == "Malicious":
        try:
            category_result = get_category_model_service().classify_from_permissions(
                extraction.raw_permissions
            )
            integrated["threat_assessment"] = category_result["threat_assessment"]
            integrated["diagnostics"]["category_classification"] = category_result[
                "diagnostics"
            ]
        except Exception:
            # The experimental sidecar must never suppress or mutate the already
            # completed binary/risk response. Operational failure is not the same
            # as score-based uncertainty, so leave the optional sidecar null.
            logger.exception(
                "Experimental category classification failed; returning binary assessment."
            )

    return AnalyzeAPKResponse(
        package=request.package,
        permissions_detected=len(extraction.raw_permissions),
        mode="APK Analysis Mode",
        **integrated,
    )
