"""Shared schemas for install source analysis."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

InstallSourceType = Literal[
    "google_play_store",
    "website_download",
    "apk_sideload",
    "unknown_source",
]


class InstallSourceAssessment(BaseModel):
    install_source: str
    install_source_display: str
    source_risk_level: str = Field(..., description="Low | Moderate | High | Very High")
    source_risk_points: int = Field(..., ge=0, le=100)
    source_explanation: str


class OverallRiskAssessment(BaseModel):
    permission_risk_score: int = Field(..., ge=0, le=100)
    permission_risk_level: str
    overall_risk_score: int = Field(..., ge=0, le=100)
    overall_risk_level: str
    overall_band_range: str
    integration_note: str


class AnalyzeInstallSourceRequest(BaseModel):
    install_source: str = Field(
        ...,
        description="google_play_store | website_download | apk_sideload | unknown_source",
    )

    model_config = {
        "json_schema_extra": {"example": {"install_source": "apk_sideload"}}
    }


class AnalyzeInstallSourceResponse(InstallSourceAssessment):
    pass
