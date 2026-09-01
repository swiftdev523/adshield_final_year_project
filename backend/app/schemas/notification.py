"""Schemas for notification spam analysis and monitoring."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeNotificationRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Notification message text.")
    package: Optional[str] = Field(
        default=None,
        description="Optional app package name - when set, the event is logged in the volume monitor.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Congratulations! Claim your free reward now.",
                "package": "com.sample.flashlight",
            }
        }
    }


class AnalyzeNotificationResponse(BaseModel):
    prediction: str = Field(..., description="Spam or Ham.")
    confidence: float = Field(..., ge=0, le=100, description="Confidence in the verdict (0-100%).")


class MonitorStatsResponse(BaseModel):
    package: str
    total_in_window: int
    spam_in_window: int
    ham_in_window: int
    rate_per_minute: float
    window_seconds: int
    unusual_volume: bool = Field(..., description="True if notification count exceeds the volume threshold.")
    spam_heavy: bool = Field(..., description="True if spam count in the window exceeds the spam threshold.")
    alert_message: Optional[str] = None


class NotificationAlertItem(BaseModel):
    package: str
    total_in_window: int
    spam_in_window: int
    unusual_volume: bool
    spam_heavy: bool
    rate_per_minute: float


class NotificationAlertsResponse(BaseModel):
    alerts: List[NotificationAlertItem]
    window_seconds: int
