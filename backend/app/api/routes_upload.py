"""APK file upload route - full end-to-end APK Analysis Mode pipeline."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...apk_analysis.permission_extractor import analyze_apk
from ..config import RUNTIME_TEMP_DIR
from ..schemas.upload import UploadAPKResponse
from ..services import get_apk_model_service, get_category_model_service
from ..services.assessment_integrator import integrate_assessment
from ..services.explanation_service import explain

router = APIRouter(tags=["apk-upload"])
logger = logging.getLogger(__name__)

_MAX_APK_BYTES = 200 * 1024 * 1024  # 200 MB
_UPLOAD_CHUNK_BYTES = 1024 * 1024  # 1 MB


@router.post("/upload-apk", response_model=UploadAPKResponse)
async def upload_apk(
    file: UploadFile = File(..., description="Android .apk file"),
    install_source: str = Form(
        default="apk_sideload",
        description="google_play_store | website_download | apk_sideload | unknown_source",
    ),
) -> UploadAPKResponse:
    """Upload an APK, extract manifest permissions, score, and explain.

    Pipeline:
        1. Save uploaded ``.apk`` to a temporary file
        2. Parse ``AndroidManifest.xml`` (binary AXML via pyaxmlparser)
        3. Extract ``android.permission.*`` declarations
        4. Score with the permission-only APK Random Forest model
        5. Return risk score, risk level, and human-readable explanation
    """
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".apk"):
        raise HTTPException(status_code=400, detail="Uploaded file must have a .apk extension.")

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".apk",
            delete=False,
            dir=RUNTIME_TEMP_DIR,
        ) as tmp:
            tmp_path = Path(tmp.name)
            total_bytes = 0
            while chunk := await file.read(_UPLOAD_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > _MAX_APK_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="APK file exceeds the 200 MB limit.",
                    )
                tmp.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded APK file is empty.")

        try:
            extraction = analyze_apk(tmp_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc) or "APK parser unavailable. Install pyaxmlparser.",
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to parse APK: {exc}") from exc

        apk_service = get_apk_model_service()
        score = apk_service.predict_from_permissions(extraction.raw_permissions)

        explanation = explain(
            extraction.raw_permissions,
            score["risk_score"],
            score["risk_level"],
            dangerous_count=extraction.dangerous_permission_count,
            safe_count=extraction.safe_permission_count,
            canonical_labels=extraction.mapped_features,
        )

        integrated = integrate_assessment(
            score,
            install_source,
            explanation,
            package=extraction.package,
            filename=filename,
            permissions=extraction.raw_permissions,
            legacy_flagged_permission_count=extraction.dangerous_permission_count,
            legacy_safe_permission_count=extraction.safe_permission_count,
            mode="APK Analysis Mode",
        )

        # Experimental post-binary sidecar. Category classification cannot
        # alter the already-final binary, permission-risk, or overall-risk data.
        if score["model_prediction"] == "Malicious":
            try:
                category_result = get_category_model_service().classify_from_permissions(
                    extraction.raw_permissions
                )
                integrated["threat_assessment"] = category_result["threat_assessment"]
                integrated["diagnostics"]["category_classification"] = category_result[
                    "diagnostics"
                ]
            except Exception:
                # Keep the completed binary/risk response available. Do not
                # misrepresent an operational sidecar failure as Uncertain.
                logger.exception(
                    "Experimental category classification failed; returning binary assessment."
                )

        return UploadAPKResponse(
            package=extraction.package,
            filename=filename,
            permissions=extraction.raw_permissions,
            permissions_detected=len(extraction.raw_permissions),
            mode="APK Analysis Mode",
            **integrated,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
