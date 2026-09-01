"""Notification spam detection and volume monitoring routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import NOTIFICATION_MONITOR_WINDOW_SECONDS
from ..schemas.notification import (
    AnalyzeNotificationRequest,
    AnalyzeNotificationResponse,
    MonitorStatsResponse,
    NotificationAlertItem,
    NotificationAlertsResponse,
)
from ..services.notification_monitor import get_notification_monitor
from ..services.notification_service import get_notification_service

router = APIRouter(tags=["notifications"])


def _alert_message(stats) -> str | None:
    if stats.spam_heavy and stats.unusual_volume:
        return (
            f"Unusual notification activity: {stats.total_in_window} notifications "
            f"({stats.spam_in_window} spam) in the last "
            f"{NOTIFICATION_MONITOR_WINDOW_SECONDS // 60} minutes."
        )
    if stats.unusual_volume:
        return (
            f"High notification volume: {stats.total_in_window} notifications in "
            f"the last {NOTIFICATION_MONITOR_WINDOW_SECONDS // 60} minutes."
        )
    if stats.spam_heavy:
        return f"Spam-heavy app: {stats.spam_in_window} spam notifications in the monitoring window."
    return None


@router.post("/analyze-notification", response_model=AnalyzeNotificationResponse)
def analyze_notification(request: AnalyzeNotificationRequest) -> AnalyzeNotificationResponse:
    """Classify one notification message as Spam or Ham using the Random Forest model."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="'text' must not be empty.")

    service = get_notification_service()
    result = service.analyze(text)

    # Optional: log to the volume monitor when the Android client supplies a package.
    if request.package:
        monitor = get_notification_monitor()
        is_spam = result["prediction"] == service.SPAM_LABEL
        monitor.record(request.package.strip(), is_spam, text)

    return AnalyzeNotificationResponse(
        prediction=result["prediction"],
        confidence=result["confidence"],
    )


@router.get("/monitor/notifications/alerts", response_model=NotificationAlertsResponse)
def monitor_alerts() -> NotificationAlertsResponse:
    """List apps currently flagged for unusual notification volume or spam-heavy behaviour."""
    flagged = get_notification_monitor().all_alerts()
    return NotificationAlertsResponse(
        window_seconds=NOTIFICATION_MONITOR_WINDOW_SECONDS,
        alerts=[
            NotificationAlertItem(
                package=s.package,
                total_in_window=s.total_in_window,
                spam_in_window=s.spam_in_window,
                unusual_volume=s.unusual_volume,
                spam_heavy=s.spam_heavy,
                rate_per_minute=s.rate_per_minute,
            )
            for s in flagged
        ],
    )


@router.get("/monitor/notifications/{package}", response_model=MonitorStatsResponse)
def monitor_package(package: str) -> MonitorStatsResponse:
    """Return sliding-window notification stats for one app (no new event recorded)."""
    stats = get_notification_monitor().stats(package)
    return MonitorStatsResponse(
        package=stats.package,
        total_in_window=stats.total_in_window,
        spam_in_window=stats.spam_in_window,
        ham_in_window=stats.ham_in_window,
        rate_per_minute=stats.rate_per_minute,
        window_seconds=NOTIFICATION_MONITOR_WINDOW_SECONDS,
        unusual_volume=stats.unusual_volume,
        spam_heavy=stats.spam_heavy,
        alert_message=_alert_message(stats) if (stats.unusual_volume or stats.spam_heavy) else None,
    )
