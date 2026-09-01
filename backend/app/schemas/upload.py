"""Schemas for POST /upload-apk."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .assessment import IntegratedAssessmentResponse


class UploadAPKResponse(IntegratedAssessmentResponse):
    """Full APK upload analysis result."""

    package: Optional[str] = Field(
        default=None,
        description="Package name from AndroidManifest.xml.",
        deprecated="Use summary.app.package.",
    )
    filename: str = Field(
        ...,
        description="Original uploaded filename.",
        deprecated="Use summary.app.filename.",
    )
    permissions: List[str] = Field(
        default_factory=list,
        description="Raw permissions from manifest.",
        deprecated="Use advanced_details.permissions.",
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
