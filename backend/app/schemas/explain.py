"""Schemas for POST /explain."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    """Input for the standalone explanation endpoint."""

    permissions: List[str] = Field(
        ...,
        description="Detected permissions (android.permission.* or bare names like SEND_SMS).",
    )
    risk_score: int = Field(..., ge=0, le=100, description="Risk score 0-100.")
    risk_tier: str = Field(..., description="Safe | Suspicious | High Risk.")
    dangerous_permission_count: Optional[int] = Field(default=None, ge=0)
    safe_permission_count: Optional[int] = Field(default=None, ge=0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "permissions": [
                    "android.permission.SEND_SMS",
                    "android.permission.READ_SMS",
                    "android.permission.RECEIVE_BOOT_COMPLETED",
                    "android.permission.ACCESS_FINE_LOCATION",
                ],
                "risk_score": 61,
                "risk_tier": "Suspicious",
            }
        }
    }


class ExplainResponse(BaseModel):
    """Explanation output."""

    explanation: str = Field(..., description="One-sentence human-readable summary.")
    reasons: List[str] = Field(default_factory=list, description="Supporting explanation lines.")
