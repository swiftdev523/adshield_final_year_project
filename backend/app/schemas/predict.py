"""Request/response schemas for POST /predict-apk.

These Pydantic models define and validate the API contract. FastAPI uses them
to parse incoming JSON, reject malformed input automatically, and document the
endpoint in the generated OpenAPI / Swagger UI.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .assessment import IntegratedAssessmentResponse


class AppMetadata(BaseModel):
    """Optional store metadata.

    APK Analysis Mode (before install) usually cannot supply these - the model
    service then fills them with the medians learned during training. Installed
    App Mode can provide real values when the app is on a store.
    """

    rating: Optional[float] = Field(default=None, ge=0, le=5, description="Average store rating (0-5).")
    number_of_ratings: Optional[float] = Field(default=None, ge=0, description="How many ratings the app has.")
    price: Optional[float] = Field(default=None, ge=0, description="App price.")
    dangerous_permission_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Legacy dataset (D)-suffix count override; not a curated sensitive count.",
    )
    safe_permission_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Legacy dataset (S)-suffix count override.",
    )


class PredictAPKRequest(BaseModel):
    """Input for a single app prediction.

    ``features`` maps the model's permission-column labels to 0/1, exactly as
    produced by ``backend.apk_analysis`` (the ``feature_vector`` field). Unknown
    keys are ignored; missing permission columns default to 0.
    """

    features: Dict[str, float] = Field(
        ...,
        description="Permission-feature labels -> 0/1 (from the APK extractor's feature_vector).",
    )
    metadata: Optional[AppMetadata] = Field(default=None, description="Optional store metadata.")
    install_source: Optional[str] = Field(
        default="google_play_store",
        description="google_play_store | website_download | apk_sideload | unknown_source",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "features": {
                    "Services that cost you money : send SMS messages (D)": 1,
                    "System tools : automatically start at boot (S)": 1,
                    "System tools : display system-level alerts (D)": 1,
                    "Phone calls : read phone state and identity (D)": 1,
                    "Your location : fine (GPS) location (D)": 1,
                },
                "metadata": {"rating": 3.1, "number_of_ratings": 12, "price": 0.0},
            }
        }
    }


class PredictAPKResponse(IntegratedAssessmentResponse):
    """Scoring result returned to the caller."""

    mode: str = Field(
        default="Installed App Mode",
        deprecated="Use diagnostics.mode.",
    )


class AnalyzeAPKRequest(BaseModel):
    """Input for APK Analysis Mode: the app's declared permissions.

    ``permissions`` is the list of raw Android permission strings read from the
    APK manifest (or device PackageManager), e.g. 'android.permission.SEND_SMS'.
    """

    permissions: List[str] = Field(..., description="Raw android.permission.* strings.")
    package: Optional[str] = Field(default=None, description="Optional package name.")
    install_source: Optional[str] = Field(
        default="apk_sideload",
        description="google_play_store | website_download | apk_sideload | unknown_source",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "package": "com.sample.flashlight",
                "permissions": [
                    "android.permission.SEND_SMS",
                    "android.permission.RECEIVE_BOOT_COMPLETED",
                    "android.permission.SYSTEM_ALERT_WINDOW",
                    "android.permission.READ_PHONE_STATE",
                    "android.permission.ACCESS_FINE_LOCATION",
                    "android.permission.INTERNET",
                ],
            }
        }
    }


class AnalyzeAPKResponse(IntegratedAssessmentResponse):
    """APK Analysis Mode result (permission-only model)."""

    package: Optional[str] = Field(
        default=None,
        deprecated="Use summary.app.package.",
    )
    permissions_detected: int = Field(
        ...,
        ge=0,
        deprecated="Use summary.total_permission_count or advanced_details.total_permission_count.",
    )
    mode: str = Field(
        default="APK Analysis Mode",
        deprecated="Use diagnostics.mode.",
    )
